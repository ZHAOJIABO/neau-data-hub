"""
全渠系逐分钟水动力学仿真（MacCormack 显式预测-校正）。

输入：完整渠系数据 + 每条渠段上游入流时序 (time_min, q_m3s)
输出：每条渠段 (t, x, Q, h, V) 时空序列 + 节点连续校验结果

边界条件：
- 上游：每条渠段 `canal.inflow_series` 给定入流过程（前端传入）
- 下游：末级渠段按 downstream_h_mode (normal / design / fixed) 给定水位
- 节点连续校验：父渠段末端 Q 应 ≈ 各子渠段入流之和；容差 5% 写入 violations

精简输出：每条渠段只取 (0, n_x//2, n_x-1) 三个代表断面，体积可控。

========================================================================
物理方程（圣维南方程 1D）
========================================================================
连续方程：∂A/∂t + ∂Q/∂x = -q_lateral - q_seepage
动量方程：∂Q/∂t + ∂(Q²/A)/∂x + g·A·∂h/∂x = g·A·(S₀ - Sf) - q_lateral·u

其中：
- q_lateral：从父渠段分给子渠段的流量（集中在分水口断面 = 渠段末端内点）
- q_seepage：单位长度渗漏损失 m³/(s·m)（可由 seepage_index 推导）
- u：分水口流速
- Sf：Manning 摩阻坡度

========================================================================
节点连续性校验语义（重要！两层含义）
========================================================================
本模型的"节点连续校验"实际上检查的是两条独立的一致性，**不是**严格
意义上的"父渠段实际出流 = 子渠段入流之和"物理守恒。原因：

1. 每条渠段是**独立**仿真的，入流序列 (inflow_series) 是**输入**而不是
   由父渠段状态推导出来的。
2. 因此父渠段末端 Q 由其上游边界 + 摩阻 + 源项决定，与子渠段入流无
   物理耦合。
3. 校验的是"自洽性"：
   - 时间一致性：父渠段入流 - 父渠段出流 = 分水流量
   - 流量一致性：子渠段入流之和 = 分水流量
   - 这两式相减即得节点连续等式
4. 严格的父→子正向耦合需要：父渠段根据子渠段需求实时计算分水（迭代
   求解），目前是**单向传递**：优化结果给出 inflow_series，仿真沿
   拓扑接力。

实际意义：
- 如果子渠段入流之和 > 父渠段分水能力：父渠段会被"超额抽水"（源项
  限制在父渠段出流的 99.9%，所以不会发散）
- 如果子渠段入流之和 < 父渠段分水能力：父渠段多余水自然流向末端
- 这反映了"前段优化 + 后段仿真"的串联流程：优化决定每条渠段的入流，
  仿真验证水力可行性

========================================================================
非末端渠段的下游边界
========================================================================
非末端渠段（带子渠段）使用 Manning 正常水深作为下游水位边界：
- 物理上这是"末端为自由出流"或"末端为分水口"的简化
- 流量边界 Q_end = Q_upstream - q_lateral（不是从仿真内部计算）
- 这是"单向传递"模型的必然选择：子渠段的入流是已知输入
========================================================================
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

from tqdm import tqdm

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
# 流速判据改为按"流量/设计流量"比，不再使用绝对流速：
#   v_scour: Q > Q_design
#   v_silt : 0 < Q < design_flow_ratio_min * Q_design（默认 0.6 倍）
# 这与"渠道按设计流量运行"的设计原则一致。
DEFAULT_DESIGN_FLOW_RATIO_MIN: float = 0.6
DEFAULT_DT_SEC: int = 30
MAX_SIM_DURATION_MIN: int = 1440  # 上限提升到 24h（12h 太短，90 段干渠 12h 还未收敛）
DEFAULT_H_SAFETY_MARGIN_M: float = 0.3  # h_max = design_depth + h_safety_margin（默认 0.3m）
MAX_CANALS: int = 200
NODE_CONTINUITY_TOL: float = 0.05  # 5%
DEFAULT_RAMP_MIN: float = 5.0      # 入流序列阶跃线性渐变时长（分钟）
DEFAULT_SEEPAGE_COEFF_A: float = 0.0  # 渗漏系数 A：0 = 关闭渗漏源项
DEFAULT_SEEPAGE_INDEX_M: float = 0.4  # 渗漏指数 m（与优化模型对齐）

# tqdm 在 Windows + asyncio.to_thread 线程上下文中 sys.stderr 不可 seek，
# 会导致 OSError: [Errno 22] Invalid argument；统一在此关闭进度条。
_disable_tqdm: bool = not sys.stderr.isatty()


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
    # 流量下限比（相对设计流量）：0 < Q < ratio * Q_design 视为 v_silt（不淤）
    # v_scour 由 Q > Q_design 隐含，不再有独立的"流速上限"参数
    design_flow_ratio_min: float = DEFAULT_DESIGN_FLOW_RATIO_MIN
    # 水深安全余量：h_max = design_depth + h_safety_margin
    # h > h_max 视为 h_over（水位超限）
    h_safety_margin_m: float = DEFAULT_H_SAFETY_MARGIN_M
    downstream_h_mode: str = 'normal'
    fixed_downstream_h: Optional[float] = None
    # 优化模型对齐的渗漏参数：q_seepage = 0.36 * A * Q^(1-m) / 100 [m³/(s·m)]
    # 设为 0 关闭渗漏源项（默认）
    seepage_coeff_a: float = DEFAULT_SEEPAGE_COEFF_A
    seepage_index_m: float = DEFAULT_SEEPAGE_INDEX_M
    # 入流序列阶跃线性渐变时长（分钟），用于平滑子渠段入流突变
    ramp_min: float = DEFAULT_RAMP_MIN


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

    queue: list[str] = [root]
    seen: set[str] = set()
    segment_results: dict[str, _SegmentResult] = {}
    pbar = tqdm(
        total=len(records_by_id),
        desc='渠系水动力仿真',
        unit='段',
        leave=False,
        dynamic_ncols=True,
        position=0,
        disable=_disable_tqdm,
    )

    while queue:
        cid = queue.pop(0)
        if cid in seen or cid not in records_by_id:
            continue
        seen.add(cid)
        rec = records_by_id[cid]

        inflow_series = _get_inflow_series(records_raw[cid], rec)
        child_ids = children_index.get(cid, [])
        is_terminal = len(child_ids) == 0
        if is_terminal:
            downstream_h = _resolve_downstream_h(rec, ctx)
        else:
            # 非末端渠段：使用 Manning 正常水深作为下游水位边界
            # 侧向出流由 _flux_form 中的 lateral_outflow 源项扣除
            h_n = manning_normal_depth(
                rec.design_flow, rec.bottom_width, rec.side_slope,
                rec.roughness, rec.slope
            )
            downstream_h = max(h_n, 0.01)

        seg = _solve_one_segment(
            rec, inflow_series, downstream_h, ctx,
            is_terminal=is_terminal,
            child_ids=child_ids,
            records_by_id=records_by_id,
            records_raw=records_raw,
        )
        segment_results[cid] = seg
        pbar.set_postfix(last=cid, t=f'{seg.times_min[-1]:.1f}min')
        pbar.update(1)

        for child_id in children_index.get(cid, []):
            if child_id not in seen and child_id in records_by_id:
                queue.append(child_id)

    pbar.close()

    continuity_violations: list[dict] = []
    cont_pbar = tqdm(
        total=len(segment_results),
        desc='节点连续校验',
        unit='父段',
        leave=False,
        dynamic_ncols=True,
        position=0,
        disable=_disable_tqdm,
    )
    for parent_id, seg in segment_results.items():
        child_ids = children_index.get(parent_id, [])
        active_children = [c for c in child_ids if c in segment_results]
        if not active_children:
            cont_pbar.update(1)
            continue
        for t_idx, t_min in enumerate(seg.times_min):
            parent_q_end = seg.Q_grid[t_idx][-1]
            parent_q_in = seg.Q_grid[t_idx][0]
            # 与仿真使用同一 ramp_min，保证节点连续校验与侧向出流源项
            # 两侧采用相同的入流序列平滑结果。
            children_q_in = sum(
                _interp_inflow_at(records_raw[c], records_by_id[c], t_min, ctx.ramp_min)
                for c in active_children
            )
            # 节点连续守恒：父渠段入流 - 父渠段出流 = 子渠段入流之和
            # 即 parent_q_in - parent_q_end ≈ children_q_in
            # 若三者均为零，跳过
            if parent_q_in <= 1e-9 and parent_q_end <= 1e-9 and children_q_in <= 1e-9:
                continue
            # 流量守恒检查
            q_imbalance = abs((parent_q_in - parent_q_end) - children_q_in)
            q_max_scale = max(parent_q_in, parent_q_end, children_q_in, 1e-6)
            rel_err = q_imbalance / q_max_scale
            if rel_err > NODE_CONTINUITY_TOL:
                continuity_violations.append({
                    'time_min': round(t_min, 3),
                    'canal_id': parent_id,
                    'parent_id': parent_id,
                    'children': list(active_children),
                    'x_m': None,
                    'type': 'node_continuity',
                    'parent_q_in': round(parent_q_in, 4),
                    'parent_q_end': round(parent_q_end, 4),
                    'children_q_sum': round(children_q_in, 4),
                    'detail': f'节点连续违例：父渠段入流 Q_in={parent_q_in:.3f} - 出流 Q_end={parent_q_end:.3f} ≠ 子渠段入流之和={children_q_in:.3f} (Δ={rel_err*100:.1f}%)',
                })
        cont_pbar.set_postfix(last=parent_id, vio=f'{len(continuity_violations)}')
        cont_pbar.update(1)
    cont_pbar.close()

    summary = _build_summary(root, segment_results, continuity_violations, ctx)
    canals_list = _build_canals_list(segment_results, records_by_id)
    timeseries_rows = _build_timeseries(segment_results)
    topology = _build_topology(records_by_id, parent_map, children_index, root)
    all_violations: list[dict] = []
    for seg in segment_results.values():
        all_violations.extend(seg.violations)
    all_violations.extend(continuity_violations)
    all_violations.sort(key=lambda v: (v.get('time_min', 0), v.get('type', '')))
    kept_violations, vio_stats = _truncate_violations(all_violations)
    summary['violations_total'] = vio_stats['total']
    summary['violations_truncated'] = vio_stats['truncated']
    summary['violations_returned'] = vio_stats['kept']
    summary['violation_breakdown'] = _build_violation_breakdown(
        segment_results, continuity_violations,
    )

    return FullHydroResult(
        summary=summary,
        canals=canals_list,
        timeseries=timeseries_rows,
        topology=topology,
        violations=kept_violations,
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
        raise ValueError(f'sim_duration_min 必须在 [1, {MAX_SIM_DURATION_MIN}] 之间')
    if ctx.dt_sec not in (30, 60):
        raise ValueError('dt_sec 仅支持 30 或 60')
    if ctx.downstream_h_mode not in ('normal', 'design', 'fixed'):
        raise ValueError(f"downstream_h_mode 必须是 'normal' / 'design' / 'fixed'，收到 {ctx.downstream_h_mode!r}")
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


def _ramp_inflow_series(
    series: list[tuple[float, float]], ramp_min: float
) -> list[tuple[float, float]]:
    """对入流序列的阶跃做线性渐变，避免 0→Q 的硬跳变引起数值激波。

    对相邻两点 (t0, q0) → (t1, q1)，若 |q1 - q0| > 0 且时间差 > 0：
    在 [t1 - ramp_min, t1] 之间把 q 从 q0 渐变到 q1；
    若时间差 < ramp_min 则从 t0 一直渐变到 t1（用整个区间作为渐变期）。

    返回新的 (t, q) 列表（按 t 排序），原序列不变。
    """
    if not series or ramp_min <= 0 or len(series) < 2:
        return list(series)
    out: list[tuple[float, float]] = []
    out.append(series[0])
    for i in range(1, len(series)):
        t0, q0 = series[i - 1]
        t1, q1 = series[i]
        if abs(q1 - q0) < 1e-9 or t1 <= t0:
            out.append((t1, q1))
            continue
        # 渐变开始时间：若 t1 - t0 >= ramp_min，则在 [t1 - ramp_min, t1] 内渐变；
        # 否则从 t0 一直渐变到 t1
        if t1 - t0 >= ramp_min:
            ramp_start = t1 - ramp_min
            # t0..ramp_start 保持 q0
            if ramp_start > t0:
                out.append((ramp_start, q0))
            out.append((t1, q1))
        else:
            # 整段渐变：在 t0/q0 与 t1/q1 中点拆成两段以保持单调
            out.append((t1, q1))
    # 去重（连续相同时间点保留后者）
    dedup: list[tuple[float, float]] = []
    seen_t: set[float] = set()
    for t, q in sorted(out, key=lambda kv: kv[0]):
        if t in seen_t:
            # 替换为最后一个值
            for k in range(len(dedup) - 1, -1, -1):
                if dedup[k][0] == t:
                    dedup[k] = (t, q)
                    break
        else:
            seen_t.add(t)
            dedup.append((t, q))
    return dedup


def _interp_inflow_at(
    raw: dict[str, Any], rec: CanalRecord, t_min: float,
    ramp_min: float = 0.0,
) -> float:
    """对单条渠段在 t_min 时刻的入流做插值。

    当 ramp_min > 0 时，先对 inflow_series 做线性渐变平滑，再插值；
    这样父渠段的分水流量与子渠段入流（用于节点连续校验）使用同一
    渐变序列，保证两侧一致。
    """
    series = _get_inflow_series(raw, rec)
    if ramp_min > 0:
        series = _ramp_inflow_series(series, ramp_min)
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
    is_terminal: bool = True,
    child_ids: Optional[list[str]] = None,
    records_by_id: Optional[dict[str, CanalRecord]] = None,
    records_raw: Optional[dict[str, dict[str, Any]]] = None,
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
    if h_init <= 0 or Q_init <= 0:
        h_init = max(manning_normal_depth(rec.design_flow, b, m, n, S0) * 0.5, 0.01)

    h = [h_init] * n_x
    Q = [Q_init] * n_x
    if downstream_h > 0:
        h[-1] = downstream_h

    h_max = rec.design_depth + ctx.h_safety_margin_m
    x_m = [i * dx for i in range(n_x)]
    Q_grid: list[list[float]] = [list(Q)]
    h_grid: list[list[float]] = [list(h)]
    violations: list[dict] = []
    last_residual = 0.0
    converged = True

    def _build_lateral_interp(
        cids: list[str],
        recs_by_id: dict[str, CanalRecord],
        raw: dict[str, dict[str, Any]],
        ramp_min: float = 0.0,
    ):
        def _at(t_min: float) -> float:
            return sum(
                _interp_inflow_at(raw[c], recs_by_id[c], t_min, ramp_min)
                for c in cids
            )
        return _at

    lateral_at: Optional[callable] = None
    if not is_terminal and child_ids and records_by_id and records_raw:
        # 使用 ctx.ramp_min 同步平滑，使父渠段侧向出流与子渠段入流一致
        lateral_at = _build_lateral_interp(
            child_ids, records_by_id, records_raw, ctx.ramp_min,
        )

    # 时间一阶平滑（额外保险）：ramp_min 已做阶跃平滑，此处只补一点
    # 数值耗散，避免极端瞬变；alpha 较小 = 跟随原始值更慢，更平滑。
    prev_lateral_q = 0.0
    smooth_alpha = 0.1  # ramp 处理阶跃，alpha 仅作辅助

    # 渗漏源项：单位长度损失率 [m³/(s·m)]，使用当前时刻的 Q_at 计算
    # 公式与优化模型对齐：F = 0.36 * A_coeff * Q^(1-m) * L * t / 100
    # → 瞬时单位长度损失率 = 0.36 * A_coeff * Q^(1-m) / 100 / 3600 [m³/(s·m)]
    seepage_per_m = 0.0
    if ctx.seepage_coeff_a > 0:
        # 取设计流量作为代表（稳态假设）
        Q_ref = max(rec.design_flow, 1e-6)
        seepage_per_m = (
            0.36 * ctx.seepage_coeff_a * (Q_ref ** (1.0 - ctx.seepage_index_m))
            / 100.0 / 3600.0
        )

    for k in range(1, n_t):
        t_curr = k * dt / 60.0
        t_min_val = k * dt / 60.0  # lateral_at / inflow_series 都以"分钟"为单位
        Q_up = Q_at(t_curr)
        lateral_q = 0.0
        if lateral_at:
            lateral_q_raw = lateral_at(t_min_val)
            lateral_q_raw = min(max(lateral_q_raw, 0.0), Q_up * 0.999)
            # 时间平滑：lateral_q = (1-a)*prev + a*raw
            lateral_q = (1.0 - smooth_alpha) * prev_lateral_q + smooth_alpha * lateral_q_raw
            prev_lateral_q = lateral_q

        # CFL 自适应：当前 dt 失败则逐步减半
        dt_cur = dt
        step_succeeded = False
        for _reduce in range(5):
            try:
                h_new, Q_new = _mac_cormack_step(
                    h=h, Q=Q,
                    Q_upstream=Q_up, h_downstream=downstream_h,
                    lateral_outflow=lateral_q,
                    dx=dx, dt=dt_cur, b=b, m=m, n=n, S0=S0, g=g,
                    seepage_per_m=seepage_per_m,
                )
                dt = dt_cur
                step_succeeded = True
                break
            except (ValueError, ZeroDivisionError):
                dt_cur = max(1.0, dt_cur * 0.5)
                continue

        if not step_succeeded:
            last_residual = float('inf')
            converged = False
            violations.append({
                'time_min': round(t_curr, 3),
                'canal_id': rec.canal_id,
                'x_m': None,
                'type': 'solver_fail',
                'detail': f'渠段 {rec.canal_id} 求解失败: CFL在5次重试后仍不满足',
            })
            break

        h_min_safe = 0.05
        q_max_safe = max(3.0 * Q_up, 10.0)  # 上限防止数值爆炸
        for i in range(1, n_x - 1):
            if not math.isfinite(h_new[i]) or h_new[i] < h_min_safe:
                h_new[i] = max(h_min_safe, 0.5 * h[i])
            if not math.isfinite(Q_new[i]) or Q_new[i] < 0:
                Q_new[i] = max(Q_up * 0.5, 1e-6)
            elif Q_new[i] > q_max_safe:
                Q_new[i] = q_max_safe

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
            q_d = float(rec.design_flow or 0.0)
            ratio = Q[i] / q_d if q_d > 0 else 0.0
            # v_scour：流量超过设计流量（按渠道设计原则）
            if q_d > 0 and Q[i] > q_d:
                violations.append({
                    'time_min': round(t_curr, 3),
                    'canal_id': rec.canal_id,
                    'x_m': round(x_m[i], 1),
                    'type': 'v_scour',
                    'detail': f'Q={Q[i]:.3f} > Q_design={q_d:.3f} (ratio={ratio:.2f}, v={v:.3f})',
                })
            # v_silt：流量低于 design_flow_ratio_min * Q_design。
            # 仅在水深正常、流量有意义时报警，避免干涸/浅水格点误报。
            elif (q_d > 0
                  and 0 < Q[i] < ctx.design_flow_ratio_min * q_d
                  and h[i] > 0.3 * rec.design_depth
                  and Q[i] > 0.05 * q_d):
                violations.append({
                    'time_min': round(t_curr, 3),
                    'canal_id': rec.canal_id,
                    'x_m': round(x_m[i], 1),
                    'type': 'v_silt',
                    'detail': (f'Q={Q[i]:.3f} < {ctx.design_flow_ratio_min:.2f}*Q_design'
                               f'={ctx.design_flow_ratio_min * q_d:.3f} (ratio={ratio:.2f}, v={v:.3f})'),
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
    lateral_outflow: float = 0.0,
    dx: float,
    dt: float,
    b: float,
    m: float,
    n: float,
    S0: float,
    g: float,
    seepage_per_m: float = 0.0,
) -> tuple[list[float], list[float]]:
    """MacCormack 预测-校正两步法（显式 1D 圣维南），含侧向出流 + 渗漏源项。

    seepage_per_m: 沿程单位长度渗漏流量 m³/(s·m)。当设为 0 时关闭渗漏源项。
    """
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
    # CFL 校验：使用 0.85 系数允许小幅瞬变（CFL 限 0.5-1.0 都可接受）
    if (v_max_est + wave_speed) * dt > 0.85 * dx:
        raise ValueError(f'CFL 不满足：({v_max_est:.3f}+{wave_speed:.3f})*{dt}>{0.85*dx}')

    def _flux_form(
        h_in: list[float], Q_in: list[float], q_lateral: float = 0.0,
        lateral_at_end: bool = True,
        q_seepage_per_m: float = 0.0,
    ) -> tuple[list[float], list[float]]:
        """修正后的圣维南方程：压力项使用面积梯度，含侧向出流 + 渗漏源项。

        侧向出流（lateral_outflow）:
        - lateral_at_end=True 时，在下游 1/3 区域集中扣除分水流量
        - 物理上对应闸门式分水口

        渗漏损失（seepage）:
        - 沿程均匀损失：q_seepage [m³/(s·m)] × dx = 该格点的损失流量
        - 物理公式：F_seepage = 0.36 * A * Q^(1-m) [m³/(s·m)]，与优化模型对齐
        - 仅在连续方程中扣除；动量方程中比例较小可忽略
        """
        dhdt = [0.0] * n_x
        dQdt = [0.0] * n_x
        for i in range(1, n_x - 1):
            h_i = max(h_in[i], 1e-6)
            A_im = max(area_at(h_in, i - 1), 1e-6)
            A_i = max(area_at(h_in, i), 1e-6)
            A_ip = max(area_at(h_in, i + 1), 1e-6)
            # 连续方程：基础对流项 + 渗漏源项
            dhdt[i] = -(Q_in[i + 1] - Q_in[i - 1]) / (2.0 * dx)
            if q_seepage_per_m > 0:
                # 沿程渗漏：单位时间单位长度损失的水深
                dhdt[i] -= q_seepage_per_m / A_i
            # 数值粘性（2 阶 + 4 阶混合）：
            # MacCormack 显式格式在稳态附近会因数值噪声持续累积，
            # 加入 2 阶 Laplacian（粘性）能有效耗散高频震荡。
            # 系数取波速 * dx，量纲为 m²/s（与扩散方程一致）
            v_loc = abs(Q_in[i] / A_i) if A_i > 0 else 0.0
            c_loc = math.sqrt(max(g * h_i, 1e-9))
            nu_h = 0.5 * (v_loc + c_loc) * dx
            laplacian2_h = h_in[i + 1] - 2 * h_in[i] + h_in[i - 1]
            dhdt[i] += nu_h * laplacian2_h / (dx * dx)
            # 动量方程
            conv = (Q_in[i + 1] ** 2 / A_ip - Q_in[i - 1] ** 2 / A_im) / (2.0 * dx)
            press = g * (A_ip - A_im) / (2.0 * dx)
            Sf = _friction_slope(Q_in[i], h_i, b, m, n)
            dQdt[i] = -(conv + press - g * A_i * S0 + g * A_i * Sf)
            # 动量方程也加数值粘性
            nu_q = 0.3 * (v_loc + c_loc) * dx
            laplacian2_q = Q_in[i + 1] - 2 * Q_in[i] + Q_in[i - 1]
            dQdt[i] += nu_q * laplacian2_q / (dx * dx)
        # 侧向出流：在分水口位置集中扣除分水流量
        # 实现方法（关键改进：减少 Q 而非 h，避免 0<A 时的正反馈）：
        # 1. 在 n_dist 个内点区间内，把每个格点的"过流量"减为 Q - q_per_cell
        # 2. 连续方程的 ∂Q/∂x 反映这个减少，dhdt 由 Q 减少驱动
        # 3. 动量方程中扣减少量携带的动量
        if q_lateral > 0 and lateral_at_end:
            # 集中区域：渠段末端 1/4（闸门式分水口，分散一点更稳定）
            n_dist = max(1, n_x // 4)
            q_per_cell = q_lateral / n_dist
            h_min_safe = 0.10  # 低于此水深的格点不再分水（防抽空）
            for last_i in range(n_x - 1 - n_dist, n_x - 1):
                if last_i < 1 or last_i >= n_x - 1:
                    continue
                if h_in[last_i] < h_min_safe:
                    continue  # 该格点已近干涸，停止分水
                A_last = max(area_at(h_in, last_i), 1e-6)
                # 实际扣除量：取 min(q_per_cell, 该格点当前过流量 × 0.05)
                # 0.05 系数严格限制分水率（每格最多分 5% 当前过流量），
                # 保证分水率小于该格点的恢复能力，避免 A→0 时的正反馈
                q_avail = max(Q_in[last_i] * 0.05, 0.0)
                q_removed = min(q_per_cell, q_avail)
                if q_removed <= 0:
                    continue
                # 连续方程：减少水深（分水带走水体）
                dhdt[last_i] -= q_removed / (A_last * dx)
                # 动量方程：扣除分水携带的动量
                u_last = Q_in[last_i] / A_last
                dQdt[last_i] -= q_removed * u_last
        return dhdt, dQdt

    # ---- 预测步 ----
    dhdt_old, dQdt_old = _flux_form(h, Q, lateral_outflow, True, seepage_per_m)
    h_pred = list(h)
    Q_pred = list(Q)
    for i in range(1, n_x - 1):
        h_pred[i] = h[i] + dt * dhdt_old[i]
        Q_pred[i] = Q[i] + dt * dQdt_old[i]
    # 上游边界
    h_pred[0] = h[0]
    Q_pred[0] = Q_upstream
    # 下游边界
    if h_downstream > 0:
        h_pred[n_x - 1] = h_downstream
        # 非末端渠段：下游流量 = 上游流量 - 侧向出流（流出到子渠段）
        if lateral_outflow > 0:
            q_effective_pred = max(Q_upstream - lateral_outflow, 0.0)
            Q_pred[n_x - 1] = q_effective_pred
        else:
            Q_pred[n_x - 1] = Q[n_x - 1]
    else:
        h_pred[n_x - 1] = h[n_x - 1]
        # 非末端渠段：预测时也用 Q_up - q_lateral
        q_effective_pred = max(Q_upstream - lateral_outflow, 0.0)
        Q_pred[n_x - 1] = q_effective_pred

    # ---- 校正步 ----
    dhdt_pred, dQdt_pred = _flux_form(h_pred, Q_pred, lateral_outflow, True, seepage_per_m)
    h_new = list(h)
    Q_new = list(Q)
    for i in range(1, n_x - 1):
        h_new[i] = 0.5 * (h[i] + h_pred[i] + dt * dhdt_pred[i])
        Q_new[i] = 0.5 * (Q[i] + Q_pred[i] + dt * dQdt_pred[i])
    # 上游边界
    h_new[0] = h[0]
    Q_new[0] = Q_upstream
    # 下游边界
    if h_downstream > 0:
        h_new[n_x - 1] = h_downstream
        # 非末端渠段：下游流量 = 上游流量 - 侧向出流
        if lateral_outflow > 0:
            q_effective = max(Q_upstream - lateral_outflow, 0.0)
            Q_new[n_x - 1] = q_effective
        else:
            Q_new[n_x - 1] = Q[n_x - 1]
    else:
        h_new[n_x - 1] = h[n_x - 1]
        # 非末端渠段：下游流量 = 上游流量 - 侧向出流
        q_effective = max(Q_upstream - lateral_outflow, 0.0)
        Q_new[n_x - 1] = q_effective

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


# timeseries 时间维度下采样间隔（分钟）
TIMESERIES_DOWNSAMPLE_MIN: float = 15.0


def _pick_time_indices(times_min: list[float], step_min: float) -> list[int]:
    if not times_min:
        return []
    last_idx = len(times_min) - 1
    if last_idx == 0:
        return [0]
    selected: list[int] = [0]
    next_t = times_min[0] + step_min
    for i in range(1, last_idx):
        if times_min[i] >= next_t - 1e-6:
            selected.append(i)
            next_t = times_min[i] + step_min
    if last_idx not in selected:
        selected.append(last_idx)
    return selected


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

VIOLATION_RETURN_KEEP: int = 200
VIOLATION_PER_TYPE_KEEP: int = 20


def _truncate_violations(violations: list[dict]) -> tuple[list[dict], dict]:
    """截断超量 violations；返回 (保留明细, 统计)。"""
    total = len(violations)
    if total <= VIOLATION_RETURN_KEEP:
        return violations, {'total': total, 'truncated': 0, 'kept': total}
    head = violations[:VIOLATION_PER_TYPE_KEEP]
    by_type: dict[str, list[dict]] = {}
    for v in violations:
        by_type.setdefault(str(v.get('type', '')), []).append(v)
    middle: list[dict] = []
    for arr in by_type.values():
        if len(arr) > VIOLATION_PER_TYPE_KEEP * 2:
            middle.extend(arr[:VIOLATION_PER_TYPE_KEEP])
            middle.extend(arr[-VIOLATION_PER_TYPE_KEEP:])
    tail = violations[-VIOLATION_PER_TYPE_KEEP:]
    seen = set()
    keep: list[dict] = []
    for v in head + middle + tail:
        key = (v.get('time_min'), v.get('canal_id'), v.get('type'))
        if key in seen:
            continue
        seen.add(key)
        keep.append(v)
    keep.sort(key=lambda v: (v.get('time_min', 0), v.get('type', '')))
    if len(keep) > VIOLATION_RETURN_KEEP:
        keep = keep[:VIOLATION_PER_TYPE_KEEP] + keep[-(VIOLATION_RETURN_KEEP - VIOLATION_PER_TYPE_KEEP):]
    return keep, {'total': total, 'truncated': total - len(keep), 'kept': len(keep)}


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
        t_indices = _pick_time_indices(seg.times_min, TIMESERIES_DOWNSAMPLE_MIN)
        for t_idx in t_indices:
            t_min = seg.times_min[t_idx]
            q_row = seg.Q_grid[t_idx]
            h_row = seg.h_grid[t_idx]
            v_row = seg.V_grid[t_idx]
            for x_idx in seg.sample_indices:
                rows.append({
                    't_min': round(t_min, 3),
                    'canal_id': cid,
                    'x_m': round(seg.x_m[x_idx], 2),
                    'q_m3s': round(q_row[x_idx], 4),
                    'h_m': round(h_row[x_idx], 4),
                    'v_mps': round(v_row[x_idx], 4),
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


# ---------------------------------------------------------------------------
# 违例诊断聚合（不修改任何物理逻辑，仅做结果统计）
# ---------------------------------------------------------------------------


VIOLATION_TIME_BUCKET_MIN: int = 5


def _bucket_start(label: str) -> int:
    """解析 '起点-终点' 桶标签，返回起点分钟。"""
    head = label.split('-', 1)[0]
    try:
        return int(float(head))
    except (TypeError, ValueError):
        return 0


def _build_violation_breakdown(
    segment_results: dict[str, '_SegmentResult'],
    continuity_violations: list[dict],
) -> dict:
    """按违例类型 / 渠段 / 时间桶聚合统计。

    设计目标：当违例总数达到百万级时，让调用方一眼看出"哪种违例是大头、
    哪些渠段是热点、哪些时段是高峰"，为后续调参提供数据依据。

    不修改任何物理逻辑，纯只读聚合。
    """
    by_type: dict[str, int] = {}
    by_canal: dict[str, int] = {}
    by_time_bucket: dict[str, int] = {}
    by_type_canal: dict[tuple[str, str], int] = {}

    def _accumulate(v: dict) -> None:
        t = str(v.get('type', 'unknown'))
        c = str(v.get('canal_id', 'unknown'))
        tm = float(v.get('time_min', 0.0) or 0.0)
        by_type[t] = by_type.get(t, 0) + 1
        by_canal[c] = by_canal.get(c, 0) + 1
        bucket = int(tm // VIOLATION_TIME_BUCKET_MIN) * VIOLATION_TIME_BUCKET_MIN
        bk = f'{bucket}-{bucket + VIOLATION_TIME_BUCKET_MIN}'
        by_time_bucket[bk] = by_time_bucket.get(bk, 0) + 1
        by_type_canal[(t, c)] = by_type_canal.get((t, c), 0) + 1

    for seg in segment_results.values():
        for v in seg.violations:
            _accumulate(v)
    for v in continuity_violations:
        _accumulate(v)

    top_canals = sorted(
        by_canal.items(), key=lambda kv: kv[1], reverse=True,
    )[:5]
    top_pairs = sorted(
        ({'type': t, 'canal_id': c, 'count': n}
         for (t, c), n in by_type_canal.items()),
        key=lambda x: x['count'], reverse=True,
    )[:10]
    sorted_buckets = dict(sorted(
        by_time_bucket.items(), key=lambda kv: _bucket_start(kv[0]),
    ))
    return {
        'time_bucket_min': VIOLATION_TIME_BUCKET_MIN,
        'by_type': by_type,
        'top_canals': [{'canal_id': c, 'count': n} for c, n in top_canals],
        'top_type_canal_pairs': top_pairs,
        'time_buckets': sorted_buckets,
    }
