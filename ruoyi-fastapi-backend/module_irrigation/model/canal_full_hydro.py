"""
全渠系逐分钟水动力学仿真（MacCormack 显式预测-校正）。

输入：完整渠系数据 + 每条渠段上游入流时序 (time_min, q_m3s)
输出：每条渠段 (t, x, Q, h, V) 时空序列 + 节点连续校验结果

边界条件：
- 上游：每条渠段 `canal.inflow_series` 给定入流过程（前端传入）
- 下游：末级渠段按 downstream_h_mode (normal / design / fixed) 给定水位
- 节点连续校验：父渠段末端 Q 应 ≈ 各子渠段入流之和；容差 5% 写入 violations

精简输出：每条渠段只取 (0, n_x//2, n_x-1) 三个代表断面，体积可控。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from module_irrigation.model.canal_models import (
    area_topwidth,
    manning_normal_depth,
)
from module_irrigation.model.canals_data import (
    CanalRecord,
    build_canal_record,
    build_children_index,
    build_parent_map,
)


GRAVITY: float = 9.81
DEFAULT_DX_M: float = 200.0
DEFAULT_V_MAX: float = 1.5
DEFAULT_V_MIN: float = 0.3
DEFAULT_DT_SEC: int = 30
MAX_SIM_DURATION_MIN: int = 720
MAX_CANALS: int = 50
NODE_CONTINUITY_TOL: float = 0.05  # 5%


# ---------------------------------------------------------------------------
# 上下文与结果
# ---------------------------------------------------------------------------


@dataclass
class FullHydroContext:
    """全渠系仿真上下文。"""

    main_canal_id: str
    records: list[dict[str, Any]]
    parent_ids: Optional[dict[str, Optional[str]]] = None
    sim_duration_min: int = 60
    dt_sec: int = DEFAULT_DT_SEC
    dx_m: float = DEFAULT_DX_M
    v_max: float = DEFAULT_V_MAX
    v_min: float = DEFAULT_V_MIN
    downstream_h_mode: str = 'normal'
    fixed_downstream_h: Optional[float] = None


@dataclass
class _SegmentResult:
    """单条渠段仿真结果（内部使用，不直接序列化）。"""

    canal_id: str
    times_min: list[float]
    x_m: list[float]
    Q_grid: list[list[float]]
    h_grid: list[list[float]]
    V_grid: list[list[float]]
    sample_indices: list[int]
    violations: list[dict] = field(default_factory=list)
    last_residual: float = 0.0
    converged: bool = True

    def to_summary(self) -> dict:
        return {
            'canal_id': self.canal_id,
            'converged': self.converged,
            'last_residual': self.last_residual if math.isfinite(self.last_residual) else None,
            'n_t': len(self.times_min),
            'n_x': len(self.x_m),
            'violation_count': len(self.violations),
            'sample_indices': list(self.sample_indices),
            'q_max': round(max(max(row) for row in self.Q_grid), 4),
            'h_max': round(max(max(row) for row in self.h_grid), 4),
        }


@dataclass
class FullHydroResult:
    """全渠系仿真结果。"""

    summary: dict
    canals: list[dict]
    timeseries: list[dict]
    topology: dict
    violations: list[dict]

    def to_dict(self) -> dict:
        return {
            'summary': self.summary,
            'canals': self.canals,
            'timeseries': self.timeseries,
            'topology': self.topology,
            'violations': self.violations,
        }


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def solve_full_hydro(ctx: FullHydroContext) -> FullHydroResult:
    """全渠系逐分钟水动力学仿真主入口。"""
    _validate_ctx(ctx)

    # 构造内部查询表
    records_raw: dict[str, dict[str, Any]] = {r['canal_id']: r for r in ctx.records}
    records_by_id: dict[str, CanalRecord] = {
        cid: build_canal_record(r) for cid, r in records_raw.items()
    }
    parent_map = build_parent_map(ctx.records, ctx.parent_ids)
    children_index = build_children_index(records_by_id.keys(), parent_map)

    root = ctx.main_canal_id
    if root not in records_by_id:
        candidates = [cid for cid in records_by_id if '-' not in cid]
        if not candidates:
            raise ValueError(f'未知干渠编号: {root}（数据中也无干渠候选）')
        root = sorted(candidates)[0]

    # BFS 逐条渠段仿真
    queue: list[str] = [root]
    seen: set[str] = set()
    segment_results: dict[str, _SegmentResult] = {}

    while queue:
        cid = queue.pop(0)
        if cid in seen or cid not in records_by_id:
            continue
        seen.add(cid)
        rec = records_by_id[cid]

        inflow_series = _get_inflow_series(records_raw[cid], rec)
        downstream_h = _resolve_downstream_h(rec, ctx)
        seg = _solve_one_segment(rec, inflow_series, downstream_h, ctx)
        segment_results[cid] = seg

        for child_id in children_index.get(cid, []):
            if child_id not in seen and child_id in records_by_id:
                queue.append(child_id)

    # 节点连续校验
    continuity_violations: list[dict] = []
    for parent_id, seg in segment_results.items():
        child_ids = children_index.get(parent_id, [])
        active_children = [c for c in child_ids if c in segment_results]
        if not active_children:
            continue
        for t_idx, t_min in enumerate(seg.times_min):
            parent_q_end = seg.Q_grid[t_idx][-1]
            children_q_in = sum(
                _interp_inflow_at(records_raw[c], records_by_id[c], t_min)
                for c in active_children
            )
            if parent_q_end <= 1e-9 and children_q_in <= 1e-9:
                continue
            denom = max(parent_q_end, children_q_in, 1e-9)
            rel_err = abs(parent_q_end - children_q_in) / denom
            if rel_err > NODE_CONTINUITY_TOL:
                continuity_violations.append({
                    'time_min': round(t_min, 3),
                    'parent_id': parent_id,
                    'children': list(active_children),
                    'type': 'node_continuity',
                    'parent_q_end': round(parent_q_end, 4),
                    'children_q_sum': round(children_q_in, 4),
                    'detail': f'节点连续违例：父渠段末端 Q={parent_q_end:.3f} vs 子渠段入流之和={children_q_in:.3f} (Δ={rel_err*100:.1f}%)',
                })

    summary = _build_summary(root, segment_results, continuity_violations, ctx)
    canals_list = _build_canals_list(segment_results, records_by_id)
    timeseries_rows = _build_timeseries(segment_results)
    topology = _build_topology(records_by_id, parent_map, children_index, root)
    all_violations: list[dict] = []
    for seg in segment_results.values():
        all_violations.extend(seg.violations)
    all_violations.extend(continuity_violations)
    all_violations.sort(key=lambda v: (v.get('time_min', 0), v.get('type', '')))

    return FullHydroResult(
        summary=summary,
        canals=canals_list,
        timeseries=timeseries_rows,
        topology=topology,
        violations=all_violations,
    )


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------


def _validate_ctx(ctx: FullHydroContext) -> None:
    if not ctx.records:
        raise ValueError('canals 不能为空')
    if len(ctx.records) > MAX_CANALS:
        raise ValueError(f'渠段数 {len(ctx.records)} 超过上限 {MAX_CANALS}')
    if ctx.sim_duration_min < 1 or ctx.sim_duration_min > MAX_SIM_DURATION_MIN:
        raise ValueError(
            f'sim_duration_min 必须在 [1, {MAX_SIM_DURATION_MIN}] 之间'
        )
    if ctx.dt_sec not in (30, 60):
        raise ValueError('dt_sec 仅支持 30 或 60')
    if ctx.downstream_h_mode not in ('normal', 'design', 'fixed'):
        raise ValueError(
            f"downstream_h_mode 必须是 'normal' / 'design' / 'fixed'，收到 {ctx.downstream_h_mode!r}"
        )
    if ctx.downstream_h_mode == 'fixed' and (
        ctx.fixed_downstream_h is None or ctx.fixed_downstream_h < 0
    ):
        raise ValueError('downstream_h_mode=fixed 时必须提供 fixed_downstream_h')
    for r in ctx.records:
        if not r.get('canal_id'):
            raise ValueError('每条 canals 必须包含 canal_id')
        if not r.get('inflow_series'):
            r['inflow_series'] = [{
                'time_min': 0.0,
                'q_m3s': float(r.get('design_flow') or 0.0),
            }]


# ---------------------------------------------------------------------------
# 入流与下游水位边界
# ---------------------------------------------------------------------------


def _get_inflow_series(
    raw: dict[str, Any], rec: CanalRecord
) -> list[tuple[float, float]]:
    """读取 raw['inflow_series'] 并按时间排序。"""
    series = raw.get('inflow_series') or []
    if series:
        return sorted(
            ((float(p['time_min']), float(p['q_m3s'])) for p in series),
            key=lambda kv: kv[0],
        )
    return [(0.0, rec.design_flow), (1e9, rec.design_flow)]


def _interp_inflow_at(
    raw: dict[str, Any], rec: CanalRecord, t_min: float
) -> float:
    series = _get_inflow_series(raw, rec)
    if t_min <= series[0][0]:
        return series[0][1]
    if t_min >= series[-1][0]:
        return series[-1][1]
    for i in range(len(series) - 1):
        t0, q0 = series[i]
        t1, q1 = series[i + 1]
        if t0 <= t_min <= t1:
            if t1 == t0:
                return q0
            return q0 + (q1 - q0) * (t_min - t0) / (t1 - t0)
    return series[-1][1]


def _resolve_downstream_h(rec: CanalRecord, ctx: FullHydroContext) -> float:
    """末级渠段的下游水位边界。"""
    if ctx.downstream_h_mode == 'fixed' and ctx.fixed_downstream_h is not None:
        return float(ctx.fixed_downstream_h)
    if ctx.downstream_h_mode == 'design':
        return rec.design_depth
    h_n = manning_normal_depth(
        rec.design_flow, rec.bottom_width, rec.side_slope, rec.roughness, rec.slope
    )
    return h_n if h_n > 0 else rec.design_depth


# ---------------------------------------------------------------------------
# 单段 MacCormack 仿真
# ---------------------------------------------------------------------------


def _solve_one_segment(
    rec: CanalRecord,
    inflow_series: list[tuple[float, float]],
    downstream_h: float,
    ctx: FullHydroContext,
) -> _SegmentResult:
    L = rec.length
    b = rec.bottom_width
    m = rec.side_slope
    n = rec.roughness
    S0 = rec.slope
    g = GRAVITY

    n_x = max(int(math.ceil(L / max(ctx.dx_m, 1.0))), 5)
    n_x = min(n_x, 200)
    dx = L / n_x
    dt = float(ctx.dt_sec)

    cfl_target = 0.5
    while dt > 1.0:
        wave_est = math.sqrt(g * max(rec.design_depth, 0.5))
        v_est = max(
            rec.design_flow / max(area_topwidth(rec.design_depth, b, m)[0], 1e-6),
            0.0,
        )
        if (v_est + wave_est) * dt <= cfl_target * dx:
            break
        dt = max(1.0, dt * 0.5)

    n_t = max(int(ctx.sim_duration_min * 60 / dt) + 1, 2)
    times_min: list[float] = [0.0]
    Q_at = _make_interp(inflow_series, rec.design_flow)

    Q_init = Q_at(0.0)
    h_init = manning_normal_depth(Q_init, b, m, n, S0)
    if h_init <= 0:
        h_init = rec.design_depth

    h = [h_init] * n_x
    Q = [Q_init] * n_x
    h[-1] = downstream_h

    h_max = rec.design_depth + 0.2
    x_m = [i * dx for i in range(n_x)]
    Q_grid: list[list[float]] = [list(Q)]
    h_grid: list[list[float]] = [list(h)]
    violations: list[dict] = []
    last_residual = 0.0
    converged = True

    for k in range(1, n_t):
        t_curr = k * dt / 60.0
        Q_up = Q_at(t_curr)
        try:
            h_new, Q_new = _mac_cormack_step(
                h=h, Q=Q,
                Q_upstream=Q_up, h_downstream=downstream_h,
                dx=dx, dt=dt, b=b, m=m, n=n, S0=S0, g=g,
            )
        except (ValueError, ZeroDivisionError) as exc:
            last_residual = float('inf')
            converged = False
            violations.append({
                'time_min': round(t_curr, 3),
                'canal_id': rec.canal_id,
                'type': 'solver_fail',
                'detail': f'渠段 {rec.canal_id} 求解失败: {exc}',
            })
            break

        h_safe = manning_normal_depth(Q_up, b, m, n, S0) or rec.design_depth
        for i in range(1, n_x - 1):
            if not math.isfinite(h_new[i]) or h_new[i] < 0:
                h_new[i] = max(0.1 * h_safe, 0.01)
            if not math.isfinite(Q_new[i]):
                Q_new[i] = Q_up

        residual = 0.0
        for i in range(n_x):
            residual = max(
                residual,
                abs(h_new[i] - h[i]),
                abs(Q_new[i] - Q[i]),
            )
        h = h_new
        Q = Q_new
        times_min.append(t_curr)
        Q_grid.append(list(Q))
        h_grid.append(list(h))
        last_residual = residual

        for i in range(n_x):
            if h[i] > h_max:
                violations.append({
                    'time_min': round(t_curr, 3),
                    'canal_id': rec.canal_id,
                    'x_m': round(x_m[i], 1),
                    'type': 'h_over',
                    'detail': f'h={h[i]:.3f} > h_max={h_max:.3f}',
                })
            A, _ = area_topwidth(h[i], b, m)
            v = Q[i] / A if A > 0 else 0.0
            if v > ctx.v_max:
                violations.append({
                    'time_min': round(t_curr, 3),
                    'canal_id': rec.canal_id,
                    'x_m': round(x_m[i], 1),
                    'type': 'v_scour',
                    'detail': f'V={v:.3f} > V_max={ctx.v_max:.3f}',
                })
            elif 0 < v < ctx.v_min:
                violations.append({
                    'time_min': round(t_curr, 3),
                    'canal_id': rec.canal_id,
                    'x_m': round(x_m[i], 1),
                    'type': 'v_silt',
                    'detail': f'V={v:.3f} < V_min={ctx.v_min:.3f}',
                })

    V_grid: list[list[float]] = []
    for t_idx in range(len(times_min)):
        row: list[float] = []
        for i in range(n_x):
            A, _ = area_topwidth(h_grid[t_idx][i], b, m)
            row.append(Q_grid[t_idx][i] / A if A > 0 else 0.0)
        V_grid.append(row)

    sample_indices = _pick_sample_indices(n_x)
    return _SegmentResult(
        canal_id=rec.canal_id,
        times_min=times_min,
        x_m=x_m,
        Q_grid=Q_grid,
        h_grid=h_grid,
        V_grid=V_grid,
        sample_indices=sample_indices,
        violations=violations,
        last_residual=last_residual,
        converged=converged,
    )


def _mac_cormack_step(
    *,
    h: list[float],
    Q: list[float],
    Q_upstream: float,
    h_downstream: float,
    dx: float,
    dt: float,
    b: float,
    m: float,
    n: float,
    S0: float,
    g: float,
) -> tuple[list[float], list[float]]:
    """MacCormack 预测-校正两步法（显式 1D 圣维南）。"""
    n_x = len(h)

    def area_at(arr_h: list[float], i: int) -> float:
        return area_topwidth(arr_h[i], b, m)[0]

    v_max_est = 0.0
    h_max_est = 0.0
    for i in range(n_x):
        A = area_at(h, i)
        if A > 0:
            v = abs(Q[i] / A)
            if v > v_max_est:
                v_max_est = v
        if h[i] > h_max_est:
            h_max_est = h[i]
    wave_speed = math.sqrt(max(g * h_max_est, 1e-9))
    if (v_max_est + wave_speed) * dt > dx:
        raise ValueError(f'CFL 不满足：({v_max_est:.3f}+{wave_speed:.3f})*{dt}>{dx}')

    def _flux_form(h_in: list[float], Q_in: list[float]) -> tuple[list[float], list[float]]:
        dhdt = [0.0] * n_x
        dQdt = [0.0] * n_x
        for i in range(1, n_x - 1):
            A_im = area_at(h_in, i - 1)
            A_i = area_at(h_in, i)
            A_ip = area_at(h_in, i + 1)
            dhdt[i] = -(Q_in[i + 1] - Q_in[i - 1]) / (2.0 * dx)
            conv = (Q_in[i + 1] ** 2 / A_ip - Q_in[i - 1] ** 2 / A_im) / (2.0 * dx)
            press = g * A_i * (h_in[i + 1] - h_in[i - 1]) / (2.0 * dx)
            Sf = _friction_slope(Q_in[i], h_in[i], b, m, n)
            dQdt[i] = -(conv + press - g * A_i * S0 + g * A_i * Sf)
        return dhdt, dQdt

    dhdt_old, dQdt_old = _flux_form(h, Q)
    h_pred = list(h)
    Q_pred = list(Q)
    for i in range(1, n_x - 1):
        h_pred[i] = h[i] + dt * dhdt_old[i]
        Q_pred[i] = Q[i] + dt * dQdt_old[i]
    h_pred[0] = h[0]
    Q_pred[0] = Q_upstream
    h_pred[n_x - 1] = h_downstream
    Q_pred[n_x - 1] = Q[n_x - 1]

    dhdt_pred, dQdt_pred = _flux_form(h_pred, Q_pred)
    h_new = list(h)
    Q_new = list(Q)
    for i in range(1, n_x - 1):
        h_new[i] = 0.5 * (h[i] + h_pred[i] + dt * dhdt_pred[i])
        Q_new[i] = 0.5 * (Q[i] + Q_pred[i] + dt * dQdt_pred[i])
    h_new[0] = h[0]
    Q_new[0] = Q_upstream
    h_new[n_x - 1] = h_downstream
    Q_new[n_x - 1] = Q[n_x - 1]
    return h_new, Q_new


def _friction_slope(Q: float, h: float, b: float, m: float, n: float) -> float:
    A, _ = area_topwidth(h, b, m)
    if A <= 0 or n <= 0 or h <= 0:
        return 0.0
    P = b + 2.0 * h * math.sqrt(1.0 + m * m)
    if P <= 0:
        return 0.0
    R = A / P
    return (n * n * Q * abs(Q)) / (A * A * R ** (4.0 / 3.0))


def _make_interp(
    series: list[tuple[float, float]], default: float
):
    if not series:
        return lambda t: default
    sorted_pts = sorted(series, key=lambda kv: kv[0])

    def _at(t: float) -> float:
        if t <= sorted_pts[0][0]:
            return sorted_pts[0][1]
        if t >= sorted_pts[-1][0]:
            return sorted_pts[-1][1]
        for i in range(len(sorted_pts) - 1):
            t0, q0 = sorted_pts[i]
            t1, q1 = sorted_pts[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return q0
                return q0 + (q1 - q0) * (t - t0) / (t1 - t0)
        return sorted_pts[-1][1]

    return _at


def _pick_sample_indices(n_x: int) -> list[int]:
    if n_x <= 1:
        return [0]
    if n_x == 2:
        return [0, 1]
    mid = n_x // 2
    return [0, mid, n_x - 1]


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------


def _build_summary(
    root: str,
    segment_results: dict[str, _SegmentResult],
    continuity_violations: list[dict],
    ctx: FullHydroContext,
) -> dict:
    n_canals = len(segment_results)
    n_converged = sum(1 for s in segment_results.values() if s.converged)
    total_violations = sum(len(s.violations) for s in segment_results.values())
    total_violations += len(continuity_violations)
    return {
        'mode': 'full_hydro',
        'main_canal_id': root,
        'sim_duration_min': int(ctx.sim_duration_min),
        'dt_sec': int(ctx.dt_sec),
        'n_canals': n_canals,
        'n_converged': n_converged,
        'converged_ratio': round(n_converged / max(n_canals, 1), 4),
        'total_violations': total_violations,
        'node_continuity_violations': len(continuity_violations),
        'downstream_h_mode': ctx.downstream_h_mode,
    }


def _build_canals_list(
    segment_results: dict[str, _SegmentResult],
    records_by_id: dict[str, CanalRecord],
) -> list[dict]:
    rows: list[dict] = []
    for cid, seg in segment_results.items():
        rec = records_by_id[cid]
        summary = seg.to_summary()
        summary.update({
            'level': rec.level,
            'length_m': rec.length,
            'design_flow': rec.design_flow,
            'design_depth': rec.design_depth,
        })
        rows.append(summary)
    rows.sort(key=lambda r: r['canal_id'])
    return rows


def _build_timeseries(segment_results: dict[str, _SegmentResult]) -> list[dict]:
    rows: list[dict] = []
    for cid, seg in segment_results.items():
        for t_idx, t_min in enumerate(seg.times_min):
            for x_idx in seg.sample_indices:
                rows.append({
                    't_min': round(t_min, 3),
                    'canal_id': cid,
                    'x_m': round(seg.x_m[x_idx], 2),
                    'q_m3s': round(seg.Q_grid[t_idx][x_idx], 4),
                    'h_m': round(seg.h_grid[t_idx][x_idx], 4),
                    'v_mps': round(seg.V_grid[t_idx][x_idx], 4),
                })
    return rows


def _build_topology(
    records_by_id: dict[str, CanalRecord],
    parent_map: dict[str, Optional[str]],
    children_index: dict[str, list[str]],
    root: str,
) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    for cid, rec in records_by_id.items():
        nodes.append({
            'id': cid,
            'name': rec.canal_name or cid,
            'level': rec.level,
            'length': rec.length,
            'design_flow': rec.design_flow,
            'design_depth': rec.design_depth,
        })
    for cid, parent in parent_map.items():
        if parent is not None:
            edges.append({
                'from': parent,
                'to': cid,
                'length': records_by_id[cid].length,
            })
    return {
        'roots': [root],
        'nodes': nodes,
        'edges': edges,
    }
