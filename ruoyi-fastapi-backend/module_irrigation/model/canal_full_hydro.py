"""
两级渠段（父 + 直接子）水动力学仿真：Preissmann 四点隐式 + 线性化双扫（追赶法）。

输入：两级渠系数据 + 每条渠段上游入流时序 (time_min, q_m3s)
输出：每条渠段 (t, x, Q, h, V) 时空序列

数值方法（参考《实用河网水流计算》第四章第四节）：
- 简化四点隐式格式（theta=0.5，无条件稳定，O(dx^2, dt^2) 精度）
- 离散后的圣维南方程组为常系数三对角线性代数方程组
- 追赶法（double sweep / Thomas 算法）由上、下边界递推 S,T,P,V 系数并回代
- 系数在 nΔt 时刻固定为已知（线性化）；为保持与原 Newton 同等精度，
  外层再做 1 次不动点更新

边界条件：
- 上游：每条渠段 inflow_series 给定入流过程（流量边界 Q[0]=Q_up）
- 下游：Manning 正常水深作为水位边界（h[-1] = h_n，与原 Newton 实现对齐）
"""

from __future__ import annotations

import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from tqdm import tqdm

from utils.log_util import logger

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

# 子树仿真常量
DEFAULT_DX_M_SUB: float = 50.0
DEFAULT_DT_SEC_SUB: int = 30
MAX_SIM_DURATION_MIN_SUB: int = 1440
DEFAULT_RAMP_MIN_SUB: float = 5.0
MAX_CANALS_SUB: int = 200
TIMESERIES_DOWNSAMPLE_MIN_SUB: float = 15.0

# Preissmann 求解参数（书 §4-51 简化四点隐式 / §4-4 稳定与精度）
PREISSMANN_THETA: float = 0.5  # 0.5 → 精度 O(dx^2, dt^2)；范围 [0.5, 1.0] 无条件稳定
PREISSMANN_MAX_FIXPOINT: int = 2  # 线性化后外层不动点迭代次数
PREISSMANN_TOL_RES: float = 1e-8  # 残差收敛阈值
PREISSMANN_H_MIN_SAFE: float = 1e-3  # 最小水深保护

# tqdm 在 Windows + asyncio.to_thread 线程上下文中 sys.stderr 不可 seek，
# 会导致 OSError: [Errno 22] Invalid argument；统一在此关闭进度条。
_DISABLE_TQDM: bool = not sys.stderr.isatty()


# ---------------------------------------------------------------------------
# 上下文与结果
# ---------------------------------------------------------------------------


@dataclass
class SubtreeHydroContext:
    """子树仿真上下文。"""

    main_canal_id: str
    records: list[dict[str, Any]]
    parent_ids: Optional[dict[str, Optional[str]]] = None
    sim_duration_min: int = 60
    dt_sec: int = DEFAULT_DT_SEC_SUB
    dx_m: float = DEFAULT_DX_M_SUB
    ramp_min: float = DEFAULT_RAMP_MIN_SUB


@dataclass
class _SubtreeSegmentResult:
    """单条渠段仿真结果。"""

    canal_id: str
    times_min: list[float]
    x_m: list[float]
    Q_grid: list[list[float]]
    h_grid: list[list[float]]
    V_grid: list[list[float]]
    sample_indices: list[int]
    kept_t_indices: list[int] = field(default_factory=list)
    last_residual: float = 0.0

    def to_summary(self) -> dict:
        return {
            'canal_id': self.canal_id,
            'n_t': len(self.times_min),
            'n_x': len(self.x_m),
            'sample_indices': list(self.sample_indices),
            'q_max': round(max(max(row) for row in self.Q_grid), 4),
            'h_max': round(max(max(row) for row in self.h_grid), 4),
        }


@dataclass
class SubtreeHydroResult:
    """子树仿真结果。"""

    summary: dict
    canals: list[dict]
    timeseries: list[dict]
    topology: dict

    def to_dict(self) -> dict:
        return {
            'summary': self.summary,
            'canals': self.canals,
            'timeseries': self.timeseries,
            'topology': self.topology,
        }


# ---------------------------------------------------------------------------
# 断面与摩阻（向量化版本）
# ---------------------------------------------------------------------------


def _area_topwidth_vec(h: np.ndarray, b: float, m: float) -> tuple[np.ndarray, np.ndarray]:
    """梯形断面：给定水深数组 h，返回 (A, T) 数组。"""
    h_arr = np.asarray(h, dtype=np.float64)
    with np.errstate(over='ignore', invalid='ignore'):
        A = (b + m * h_arr) * h_arr
    A = np.where(np.isfinite(A), A, 1e-6)
    T = b + 2.0 * m * h_arr
    return A, T


def _friction_slope_vec(
    Q: np.ndarray, h: np.ndarray, b: float, m: float, n: float
) -> np.ndarray:
    """Manning 摩阻坡度向量化版本：Sf = n^2 * |Q| * Q / (A^2 * R^(4/3))。"""
    h_safe = np.maximum(h, 1e-6)
    A, _ = _area_topwidth_vec(h_safe, b, m)
    A_safe = np.maximum(A, 1e-6)
    P = b + 2.0 * h_safe * math.sqrt(1.0 + m * m)
    P_safe = np.maximum(P, 1e-6)
    R = A_safe / P_safe
    return (n * n * Q * np.abs(Q)) / (A_safe * A_safe * np.power(R, 4.0 / 3.0))


# ---------------------------------------------------------------------------
# 入流与时间网格辅助
# ---------------------------------------------------------------------------


def _make_interp_vec(series_pts: list[tuple[float, float]], default: float):
    """返回基于 np.interp 的向量化插值函数。"""
    if not series_pts:
        def _at(t: np.ndarray) -> np.ndarray:
            return np.full_like(np.asarray(t, dtype=np.float64), default)
        return _at
    sorted_pts = sorted(series_pts, key=lambda kv: kv[0])
    ts = np.array([p[0] for p in sorted_pts], dtype=np.float64)
    qs = np.array([p[1] for p in sorted_pts], dtype=np.float64)

    def _at(t: np.ndarray) -> np.ndarray:
        t_arr = np.asarray(t, dtype=np.float64)
        return np.interp(t_arr, ts, qs)

    return _at


def _sub_validate_ctx(ctx: SubtreeHydroContext) -> None:
    if not ctx.records:
        raise ValueError('canals 不能为空')
    if len(ctx.records) > MAX_CANALS_SUB:
        raise ValueError(f'渠段数 {len(ctx.records)} 超过上限 {MAX_CANALS_SUB}')
    if ctx.sim_duration_min < 1 or ctx.sim_duration_min > MAX_SIM_DURATION_MIN_SUB:
        raise ValueError(f'sim_duration_min 必须在 [1, {MAX_SIM_DURATION_MIN_SUB}] 之间')
    if ctx.dt_sec not in (30, 60):
        raise ValueError('dt_sec 仅支持 30 或 60')
    for r in ctx.records:
        if not r.get('canal_id'):
            raise ValueError('每条 canals 必须包含 canal_id')
        if not r.get('inflow_series'):
            r['inflow_series'] = [{
                'time_min': 0.0,
                'q_m3s': float(r.get('design_flow') or 0.0),
            }]


def _sub_get_inflow_series(raw: dict[str, Any]) -> list[tuple[float, float]]:
    """读取 raw['inflow_series'] 并按时间排序。"""
    series = raw.get('inflow_series') or []
    if series:
        return sorted(
            ((float(p['time_min']), float(p['q_m3s'])) for p in series),
            key=lambda kv: kv[0],
        )
    return [(0.0, float(raw.get('design_flow') or 0.0)),
            (1e9, float(raw.get('design_flow') or 0.0))]


def _sub_make_time_grid(sim_duration_min: int, dt_sec: int) -> list[float]:
    """返回 [0, dt, 2dt, ...] 仿真时间网格（分钟）。"""
    n = max(int(sim_duration_min * 60 / dt_sec) + 1, 2)
    return [k * (dt_sec / 60.0) for k in range(n)]


def _sub_ramp_inflow_series(
    series: list[tuple[float, float]], ramp_min: float
) -> list[tuple[float, float]]:
    """对入流序列的阶跃做线性渐变。"""
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
        if t1 - t0 >= ramp_min:
            ramp_start = t1 - ramp_min
            if ramp_start > t0:
                out.append((ramp_start, q0))
            out.append((t1, q1))
        else:
            out.append((t1, q1))
    dedup: list[tuple[float, float]] = []
    seen_t: set[float] = set()
    for t, q in sorted(out, key=lambda kv: kv[0]):
        if t in seen_t:
            for k in range(len(dedup) - 1, -1, -1):
                if dedup[k][0] == t:
                    dedup[k] = (t, q)
                    break
        else:
            seen_t.add(t)
            dedup.append((t, q))
    return dedup


def _sub_interp_inflow_at(
    raw: dict[str, Any], t_min: float, ramp_min: float = 0.0
) -> float:
    """对单条渠段在 t_min 时刻的入流做插值（带可选 ramp 平滑）。"""
    series = _sub_get_inflow_series(raw)
    if ramp_min > 0:
        series = _sub_ramp_inflow_series(series, ramp_min)
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


# ---------------------------------------------------------------------------
# Preissmann 离散系数（书 §4-4 节，方程 4-53, 4-55, 4-56）
# ---------------------------------------------------------------------------


def _build_preissmann_coefs(
    h_old: np.ndarray,
    Q_old: np.ndarray,
    *,
    dx: float,
    dt: float,
    b: float,
    m: float,
    n: float,
    S0: float,
    g: float,
    q_lat_per_m: float,
    theta: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """构造 cell 系数 (C, D, E, F, G, Phi)，与书式 (4-53) (4-55) 一一对应。

    cell j 跨越格点 j 与 j+1；n_cells = n_x - 1。
    系数按下标 j ∈ [0, n_cells) 返回。
    """
    inv_dx = 1.0 / dx
    inv_dt = 1.0 / dt
    theta_o = 1.0 - theta

    hL = h_old[:-1]
    hR = h_old[1:]
    QL = Q_old[:-1]
    QR = Q_old[1:]

    A_L, T_L = _area_topwidth_vec(hL, b, m)
    A_R, T_R = _area_topwidth_vec(hR, b, m)
    A_L_safe = np.maximum(A_L, 1e-6)
    A_R_safe = np.maximum(A_R, 1e-6)
    A_avg = 0.5 * (A_L_safe + A_R_safe)
    B_avg = 0.5 * (T_L + T_R)

    # 摩阻项在 cell 中点（h_avg, Q_avg）计算（书 4-54 第 5 行）
    h_avg = 0.5 * (hL + hR)
    Q_avg = 0.5 * (QL + QR)
    Sf = _friction_slope_vec(Q_avg, h_avg, b, m, n)

    # α=1.0；u = Q/A
    u_L = QL / A_L_safe
    u_R = QR / A_R_safe

    # —— 连续方程系数 C_j, D_j（书 4-53 + 4-53 之后） ——
    C = B_avg * dx / (2.0 * dt * theta)
    # 注：本项目 q_lat_per_m 表示"渠道沿程出水/分配流量"（灌溉支口），为侧向 OUTFLOW；
    #     圣维南连续方程中 q_l 的定义是"侧向入流"（入为正），故 OUTFLOW 应取负。
    D = (
        -(q_lat_per_m * dx) / theta
        - (theta_o / theta) * (QR - QL)
        + C * (hR + hL)
    )

    # —— 动量方程系数 E_j, F_j, G_j, Φ_j（书 4-55 + 4-54 之后） ——
    # 书 4-54 第 5 行：g|Q|Q/(C²AR) 在格点 j 与 j+1 上展开为
    #     (g|u|/(2C²R))_j · Q_j^{n+1} + (g|u|/(2C²R))_{j+1} · Q_{j+1}^{n+1}
    # 在 E_j / G_j 中再被 1/θ 加权：E_j 包含 -(g|u|/(2θ C² R))_j · Δx，
    # 而 G_j 包含 +(g|u|/(2θ C² R))_{j+1} · Δx。
    # Manning 关系 C² = R^(1/3)/n² ⇒ g|u|/(C²R) = g|u|·n²/R^(4/3)。
    # 真实水力半径 R = A / P，P = b + 2h·√(1+m²)
    cfl = dx / (2.0 * theta * dt)
    P_L_safe = np.maximum(b + 2.0 * hL * math.sqrt(1.0 + m * m), 1e-6)
    P_R_safe = np.maximum(b + 2.0 * hR * math.sqrt(1.0 + m * m), 1e-6)
    R_L = A_L_safe / P_L_safe
    R_R = A_R_safe / P_R_safe
    fric_fac_L = (g * np.abs(u_L) * n * n) / (np.power(R_L, 4.0 / 3.0) * 2.0 * theta)
    fric_fac_R = (g * np.abs(u_R) * n * n) / (np.power(R_R, 4.0 / 3.0) * 2.0 * theta)
    # fric_fac 携带 dx，合并：
    E = cfl - u_L - fric_fac_L * dx  # 摩阻项对 Q_j^{n+1} 是阻力 ⇒ 取负
    G = cfl + u_R + fric_fac_R * dx
    F = g * A_avg

    # Φ_j（书 4-55 之后）：
    #   = Δx/(2θΔt)·(Q_{j+1}^n + Q_j^n)
    #     - (1-θ)/θ·[(αuQ)_{j+1}^n - (αuQ)_j^n]
    #     - (1-θ)/θ·(gA)_{j+1/2}^n·(Z_{j+1}^n - Z_j^n)
    #     + (gA·S0)_{j+1/2}·Δx
    #     - (gA·Sf)_{j+1/2}·Δx
    Phi = (
        cfl * (QR + QL)
        - (theta_o / theta) * (u_R * QR - u_L * QL)
        - (theta_o / theta) * F * (hR - hL)
        + g * A_avg * (S0 - Sf) * dx
    )

    return C, D, E, F, G, Phi


# ---------------------------------------------------------------------------
# 追赶法（书 §4-4 节，方程 4-58 与 4-60）
# ---------------------------------------------------------------------------


def _double_sweep_q_upstream(
    C: np.ndarray, D: np.ndarray, E: np.ndarray, F: np.ndarray,
    G: np.ndarray, Phi: np.ndarray, *,
    Q_upstream: float,
    h_downstream_eq: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """上游流量边界 + 下游水位边界（双扫）。

    与书 §4-4-2 一致：递推方程 (4-59)
        Z_j  = S_{j+1} - T_{j+1} · Z_{j+1}
        Q_{j+1} = P_{j+1} - V_{j+1} · Z_{j+1}
    起点（书 4-59 上半）：Q[0] = Q_upstream = P[0] - V[0]·Z[0] ⇒ P[0]=Q_up, V[0]=0
    末尾：下游 Z 边界（h_downstream）在回代阶段直接强加 Z[-1] = h_downstream。

    返回 (S, T, P, V)，下标对齐格点 j ∈ [0, n_x)；n_x = n_cells + 1。
    """
    n_cells = C.shape[0]
    n_x = n_cells + 1

    S = np.zeros(n_x)
    T = np.zeros(n_x)
    P = np.zeros(n_x)
    V = np.zeros(n_x)

    # 起点（书 4-59 上半）：Q_{L1} = Q_{L1}(t) = P_{L1} - V_{L1}·Z_{L1}
    # ⇒ P_0 = Q_upstream, V_0 = 0  （L1 = 0）
    P[0] = Q_upstream
    V[0] = 0.0

    # 上游 = 流量边界 (书 4-59)：Q[0] = Q_upstream = P[0] - V[0]·Z[0] ⇒ P[0]=Q_up, V[0]=0
    # 下游 = 水位边界 (Z[-1] = h_downstream)，由回代阶段直接强加

    # 主体递推（书 4-60）：j ∈ [0, n_cells-1]，共 n_cells 个 cell
    # 由 Z_j = S_{j+1} - T_{j+1}·Z_{j+1}, Q_{j+1} = P_{j+1} - V_{j+1}·Z_{j+1}
    # 代入 cell_j 方程 (4-56) 解 Y1..Y4 后取 (4-60)
    for j in range(n_cells):
        Y1 = V[j] + C[j]
        Y2 = F[j] + E[j] * V[j]
        Y3 = D[j] + P[j]
        Y4 = Phi[j] - E[j] * P[j]
        denom = Y1 * G[j] + Y2
        S[j + 1] = (G[j] * Y3 - Y4) / denom
        T[j + 1] = (C[j] * G[j] - F[j]) / denom
        P[j + 1] = Y3 - Y1 * S[j + 1]
        V[j + 1] = C[j] - Y1 * T[j + 1]

    return S, T, P, V


def _back_substitute_q_upstream(
    S: np.ndarray, T: np.ndarray, P: np.ndarray, V: np.ndarray,
    h_old: np.ndarray,
    h_downstream: float,
) -> tuple[np.ndarray, np.ndarray]:
    """回代 (书 4-59)：Z_j = S_{j+1} - T_{j+1}·Z_{j+1}, Q_{j+1} = P_{j+1} - V_{j+1}·Z_{j+1}

    起点（下游末端）：Z_{n-1} = h_downstream（Manning 正常水深 / 设计水深边界）
    反向递推得到 Z_0, Z_1, ..., Z_{n-2}；Q_1, Q_2, ..., Q_{n-1}
    Q_0 由上游边界强加 Q[0] = Q_upstream。
    """
    n_x = S.shape[0]
    Z_new = np.zeros(n_x)
    Q_new = np.zeros(n_x)

    Z_new[-1] = float(h_downstream)
    for j in range(n_x - 2, -1, -1):
        Z_new[j] = S[j + 1] - T[j + 1] * Z_new[j + 1]
        Q_new[j + 1] = P[j + 1] - V[j + 1] * Z_new[j + 1]
    # Q[0] 由上游边界在 _preissmann_step 中强加
    return Z_new, Q_new


# ---------------------------------------------------------------------------
# 单步求解（线性化 + 1 次不动点更新）
# ---------------------------------------------------------------------------


def _preissmann_step(
    *,
    h: np.ndarray,
    Q: np.ndarray,
    Q_upstream: float,
    h_downstream: float,
    q_lat_per_m: float,
    dx: float,
    dt: float,
    b: float,
    m: float,
    n: float,
    S0: float,
    g: float,
    theta: float = PREISSMANN_THETA,
    canal_id: str = '',
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Preissmann 四点隐式 + 线性化双扫的单步求解。

    算法：
      1. 系数在 nΔt 时刻固定为已知（C, D, E, F, G, Phi）
      2. 追赶法递推（S, T, P, V）+ 回代得到新时刻 (h, Q)
      3. 可选不动点：再用 (h_new, Q_new) 重新算系数，二次回代，提升精度
      4. 边界强加：Q[0] = Q_upstream（流量边界），h[-1] = h_downstream（水位边界）

    返回 (h_new, Q_new, info)；
    info = {'converged', 'n_iter', 'last_residual_norm'}，与原 Newton 接口兼容。
    """
    n_x = h.shape[0]
    h_old = h
    Q_old = Q

    h_try = h_old.copy()
    Q_try = Q_old.copy()

    info = {
        'converged': False,
        'n_iter': 0,
        'last_residual_norm': float('inf'),
    }
    converged = False
    last_res = float('inf')
    n_iter = 0

    for it in range(PREISSMANN_MAX_FIXPOINT):
        n_iter = it + 1
        C, D, E, F, G, Phi = _build_preissmann_coefs(
            h_try, Q_try,
            dx=dx, dt=dt, b=b, m=m, n=n, S0=S0, g=g,
            q_lat_per_m=q_lat_per_m, theta=theta,
        )
        S, T, P, V = _double_sweep_q_upstream(
            C, D, E, F, G, Phi,
            Q_upstream=Q_upstream,
        )
        Z_new, Q_new = _back_substitute_q_upstream(S, T, P, V, h_try, h_downstream)

        # 边界强加
        Q_new[0] = Q_upstream
        Z_new[-1] = float(h_downstream)

        # 残差：与 n 时刻状态的最大差
        if n_x > 1:
            res = float(max(
                np.max(np.abs(Z_new - h_try)) if Z_new.size else 0.0,
                np.max(np.abs(Q_new - Q_try)) if Q_new.size else 0.0,
            ))
        else:
            res = 0.0
        last_res = res
        info['last_residual_norm'] = res

        # 物理保护
        Z_new = np.where(np.isfinite(Z_new), Z_new, h_try)
        Q_new = np.where(np.isfinite(Q_new), Q_new, Q_try)
        Q_new = np.maximum(Q_new, 0.0)
        Z_new = np.maximum(Z_new, PREISSMANN_H_MIN_SAFE)

        if it > 0 and res < PREISSMANN_TOL_RES:
            converged = True
            h_try = Z_new
            Q_try = Q_new
            break
        h_try = Z_new
        Q_try = Q_new

    info['converged'] = converged
    info['n_iter'] = n_iter

    # 数值退化保护
    bad = (~np.isfinite(h_try)) | (h_try < 0) | (~np.isfinite(Q_try)) | (Q_try < 0)
    if bad.any():
        logger.warning(
            '{}Preissmann 双扫数值发散（iter={}），回退到 n 时刻值',
            f'[{canal_id}] ' if canal_id else '', n_iter,
        )
        h_try = h_old
        Q_try = Q_old
        Q_try[0] = Q_upstream
        info['converged'] = False

    return h_try, Q_try, info


# ---------------------------------------------------------------------------
# 单段仿真
# ---------------------------------------------------------------------------


def _sub_solve_one_segment(
    rec: CanalRecord,
    inflow_series: list[tuple[float, float]],
    lateral_total_series: list[tuple[float, float]],
    ctx: SubtreeHydroContext,
) -> _SubtreeSegmentResult:
    """单段 Preissmann 线性化双扫仿真：均匀旁侧出流 + Manning 正常水深下游边界。

    下游边界条件：与原 Newton 实现保持一致——
      - 末级渠段 (无子渠): downstream_h = manning_normal_depth(Q_design)
      - 非末级渠段: downstream_h = manning_normal_depth(Q_design)
    与原实现的 _resolve_downstream_h / 非末级 manning 路径对齐。
    """
    L = rec.length
    b = rec.bottom_width
    m = rec.side_slope
    n = rec.roughness
    S0 = rec.slope
    g = GRAVITY

    n_x = max(int(math.ceil(L / max(ctx.dx_m, 1.0))), 20)
    n_x = min(n_x, 200)
    dx = L / n_x
    dt = float(ctx.dt_sec)

    n_t = max(int(ctx.sim_duration_min * 60 / dt) + 1, 2)
    n_t = min(n_t, 86400)
    t_min_all = np.arange(n_t, dtype=np.float64) * (dt / 60.0)

    Q_at_vec = _make_interp_vec(inflow_series, rec.design_flow)
    Q_up_arr = Q_at_vec(t_min_all)

    Q_lat_at_vec = _make_interp_vec(lateral_total_series, 0.0)
    Q_lat_arr = Q_lat_at_vec(t_min_all)

    Q_init = float(Q_at_vec(np.array([0.0], dtype=np.float64))[0])
    h_init = manning_normal_depth(Q_init, b, m, n, S0)
    if h_init <= 0 or Q_init <= 0:
        h_init = max(manning_normal_depth(rec.design_flow, b, m, n, S0) * 0.5, 0.01)

    # 下游边界水位：Manning 正常水深（与原 Newton 实现 _resolve_downstream_h / 非末级 manning 路径一致）
    h_downstream = manning_normal_depth(rec.design_flow, b, m, n, S0)
    if h_downstream <= 0:
        h_downstream = rec.design_depth if rec.design_depth > 0 else h_init

    h = np.full(n_x, h_init, dtype=np.float64)
    Q = np.full(n_x, Q_init, dtype=np.float64)
    x_m = [i * dx for i in range(n_x)]

    keep_t_indices: set[int] = set(
        _pick_time_indices(list(t_min_all), TIMESERIES_DOWNSAMPLE_MIN_SUB)
    )
    keep_t_indices.add(0)

    times_min: list[float] = [0.0]
    Q_grid: list[list[float]] = [Q.tolist()]
    h_grid: list[list[float]] = [h.tolist()]
    kept_t_indices: list[int] = [0]
    last_residual = 0.0
    h_min_safe = 0.05
    q_max_cap = max(3.0 * float(Q_init), 10.0)
    h_max_safe = max(rec.design_depth * 5.0, 5.0)

    for k in range(1, n_t):
        t_curr = float(t_min_all[k])
        Q_up = float(Q_up_arr[k])
        q_lat_total = float(Q_lat_arr[k])
        q_lat_per_m = q_lat_total / L if L > 0 else 0.0

        h_new, Q_new, info = _preissmann_step(
            h=h, Q=Q,
            Q_upstream=Q_up,
            h_downstream=h_downstream,
            q_lat_per_m=q_lat_per_m,
            dx=dx, dt=dt, b=b, m=m, n=n, S0=S0, g=g,
            canal_id=rec.canal_id,
        )

        bad_h = ~np.isfinite(h_new) | (h_new < h_min_safe) | (h_new > h_max_safe)
        h_new = np.where(bad_h, np.maximum(h_min_safe, 0.5 * h), h_new)
        bad_q = ~np.isfinite(Q_new) | (Q_new < 0)
        Q_new = np.where(bad_q, np.maximum(Q_up * 0.5, 1e-6), Q_new)
        Q_new = np.where(Q_new > q_max_cap, q_max_cap, Q_new)

        residual = float(max(
            np.max(np.abs(h_new - h)) if h_new.size else 0.0,
            np.max(np.abs(Q_new - Q)) if Q_new.size else 0.0,
        ))

        h = h_new
        Q = Q_new
        times_min.append(t_curr)

        if k in keep_t_indices:
            Q_grid.append(Q.tolist())
            h_grid.append(h.tolist())
            kept_t_indices.append(k)
        last_residual = residual

    V_grid: list[list[float]] = []
    for i_h, h_row in enumerate(h_grid):
        h_arr = np.asarray(h_row, dtype=np.float64)
        A_arr, _ = _area_topwidth_vec(h_arr, b, m)
        Q_arr = np.asarray(Q_grid[i_h], dtype=np.float64)
        v_row = np.where(A_arr > 0, Q_arr / A_arr, 0.0)
        V_grid.append(v_row.tolist())

    sample_indices = _pick_sample_indices(n_x)
    return _SubtreeSegmentResult(
        canal_id=rec.canal_id,
        times_min=times_min,
        x_m=x_m,
        Q_grid=Q_grid,
        h_grid=h_grid,
        V_grid=V_grid,
        sample_indices=sample_indices,
        kept_t_indices=kept_t_indices,
        last_residual=last_residual,
    )


# ---------------------------------------------------------------------------
# 辅助：时间下采样
# ---------------------------------------------------------------------------


def _pick_sample_indices(n_x: int) -> list[int]:
    if n_x <= 1:
        return [0]
    if n_x == 2:
        return [0, 1]
    mid = n_x // 2
    return [0, mid, n_x - 1]


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
# 并行执行 worker
# ---------------------------------------------------------------------------


def _sub_should_parallelize(n_canals: int) -> bool:
    if n_canals < 16:
        return False
    cpu = os.cpu_count() or 1
    workers = min(8, max(1, cpu - 1))
    return n_canals >= max(workers * 2, 16)


def _sub_worker(args: tuple) -> dict:
    """ProcessPoolExecutor worker：包装 _sub_solve_one_segment。"""
    (cid, rec_fields, inflow_series, lateral_total_series, ctx) = args
    from module_irrigation.model.canals_data import build_canal_record
    rec = build_canal_record(rec_fields)
    seg = _sub_solve_one_segment(
        rec=rec,
        inflow_series=inflow_series,
        lateral_total_series=lateral_total_series,
        ctx=ctx,
    )
    return {
        'cid': cid,
        'times_min': seg.times_min,
        'x_m': seg.x_m,
        'Q_grid': seg.Q_grid,
        'h_grid': seg.h_grid,
        'V_grid': seg.V_grid,
        'sample_indices': seg.sample_indices,
        'kept_t_indices': seg.kept_t_indices,
        'last_residual': seg.last_residual,
    }


# ---------------------------------------------------------------------------
# 子树仿真主入口
# ---------------------------------------------------------------------------


def solve_subtree_hydro(ctx: SubtreeHydroContext) -> SubtreeHydroResult:
    """单根渠段 + 子树：逐分钟水动力学仿真主入口。"""
    _sub_validate_ctx(ctx)

    records_raw: dict[str, dict[str, Any]] = {}
    for r in ctx.records:
        cid = str(r['canal_id'])
        records_raw[cid] = r
    records_by_id: dict[str, CanalRecord] = {
        cid: build_canal_record(r) for cid, r in records_raw.items()
    }
    parent_map = build_parent_map(ctx.records, ctx.parent_ids)
    children_index = build_children_index(records_by_id.keys(), parent_map)

    root = ctx.main_canal_id
    if root not in records_by_id and str(root) not in records_by_id:
        candidates = sorted(records_by_id.keys(), key=lambda x: (len(x), x))
        if not candidates:
            raise ValueError(f'未知干渠编号: {root}（数据中也无干渠候选）')
        root = candidates[0]
        logger.warning('solve_subtree_hydro: root %r not found, fell back to %r', ctx.main_canal_id, root)

    subtree: list[str] = []
    queue: list[str] = [root]
    seen: set[str] = set()
    while queue:
        cid = queue.pop(0)
        if cid in seen or cid not in records_by_id:
            continue
        seen.add(cid)
        subtree.append(cid)
        for child_id in children_index.get(cid, []):
            if child_id not in seen and child_id in records_by_id:
                queue.append(child_id)

    seg_inputs: dict[str, dict] = {}
    for cid in subtree:
        child_ids = children_index.get(cid, [])
        inflow_series = _sub_get_inflow_series(records_raw[cid])
        if child_ids:
            child_series_list: list[tuple[float, float]] = []
            for k in range(len(_sub_make_time_grid(ctx.sim_duration_min, ctx.dt_sec))):
                t_min = k * (ctx.dt_sec / 60.0)
                q_total = 0.0
                for c in child_ids:
                    if c in records_by_id and c in records_raw:
                        q_total += _sub_interp_inflow_at(records_raw[c], t_min, ctx.ramp_min)
                child_series_list.append((t_min, q_total))
        else:
            child_series_list = [(0.0, 0.0)]

        seg_inputs[cid] = {
            'inflow_series': inflow_series,
            'lateral_total_series': child_series_list,
        }

    pbar = tqdm(
        total=len(seg_inputs),
        desc='渠系水动力仿真',
        unit='段',
        leave=False,
        dynamic_ncols=True,
        position=0,
        disable=_DISABLE_TQDM,
    )

    segment_results: dict[str, _SubtreeSegmentResult] = {}
    if _sub_should_parallelize(len(seg_inputs)):
        cpu = os.cpu_count() or 1
        workers = min(8, max(1, cpu - 1))
        print(
            f'[subtree_hydro] ProcessPoolExecutor: n_canals={len(seg_inputs)}, '
            f'workers={workers}, cpu_count={cpu}'
        )
        futures = []
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for cid, inp in seg_inputs.items():
                fut = ex.submit(
                    _sub_worker,
                    (
                        cid,
                        records_raw[cid],
                        inp['inflow_series'],
                        inp['lateral_total_series'],
                        ctx,
                    ),
                )
                futures.append((cid, fut))
            for cid, fut in futures:
                d = fut.result()
                segment_results[d['cid']] = _SubtreeSegmentResult(
                    canal_id=d['cid'],
                    times_min=d['times_min'],
                    x_m=d['x_m'],
                    Q_grid=d['Q_grid'],
                    h_grid=d['h_grid'],
                    V_grid=d['V_grid'],
                    sample_indices=d['sample_indices'],
                    kept_t_indices=d['kept_t_indices'],
                    last_residual=d['last_residual'],
                )
                pbar.set_postfix(last=cid, t=f'{segment_results[cid].times_min[-1]:.1f}min')
                pbar.update(1)
    else:
        for cid, inp in seg_inputs.items():
            rec = build_canal_record(records_raw[cid])
            seg = _sub_solve_one_segment(
                rec=rec,
                inflow_series=inp['inflow_series'],
                lateral_total_series=inp['lateral_total_series'],
                ctx=ctx,
            )
            segment_results[cid] = seg
            pbar.set_postfix(last=cid, t=f'{seg.times_min[-1]:.1f}min')
            pbar.update(1)

    pbar.close()

    summary = {
        'mode': 'subtree_hydro_preissmann',
        'solver': 'preissmann_double_sweep',
        'theta': PREISSMANN_THETA,
        'stages': ['preissmann'],
        'main_canal_id': root,
        'sim_duration_min': int(ctx.sim_duration_min),
        'dt_sec': int(ctx.dt_sec),
        'n_canals': len(segment_results),
        'n_steps': max(int(ctx.sim_duration_min * 60 / max(int(ctx.dt_sec), 1)), 1),
    }
    canals_list: list[dict] = []
    for cid, seg in segment_results.items():
        rec = records_by_id[cid]
        s = seg.to_summary()
        s.update({
            'level': rec.level,
            'length_m': rec.length,
            'design_flow': rec.design_flow,
            'design_depth': rec.design_depth,
        })
        canals_list.append(s)
    canals_list.sort(key=lambda r: r['canal_id'])

    timeseries_rows: list[dict] = []
    for cid, seg in segment_results.items():
        n_t_seg = len(seg.times_min)
        n_q_seg = len(seg.Q_grid)
        if n_t_seg == 0 or n_q_seg == 0:
            continue
        # Q_grid 与 times_min 是不同步的：Q_grid 只保留 (1 + 4*15min = 5) 行，
        # 而 times_min 有 121 行。pick 出的下标是相对 times_min 的；
        # 只有当该下标对应的 Q_grid 行也存在时才输出。
        t_indices = _pick_time_indices(seg.times_min, TIMESERIES_DOWNSAMPLE_MIN_SUB)
        for t_idx in t_indices:
            # Q_grid[k] 对应 k ∈ [0, n_q_seg)；0 是初始（t=0），
            # 其余保留的 k 由 keep_t_indices 与 loop k 共同决定。
            # 由于 Q_grid 是被"按需保留"的稀疏子集，需要一个映射：
            # 用 seg.kept_t_indices（保留顺序）作为 Q_grid 行的真下标。
            if t_idx in seg.kept_t_indices:
                q_row_idx = seg.kept_t_indices.index(t_idx)
            else:
                continue
            t_min = seg.times_min[t_idx]
            q_row = seg.Q_grid[q_row_idx]
            h_row = seg.h_grid[q_row_idx]
            v_row = seg.V_grid[q_row_idx]
            for x_idx in seg.sample_indices:
                timeseries_rows.append({
                    't_min': round(t_min, 3),
                    'canal_id': cid,
                    'x_m': round(seg.x_m[x_idx], 2),
                    'q_m3s': round(q_row[x_idx], 4),
                    'h_m': round(h_row[x_idx], 4),
                    'v_mps': round(v_row[x_idx], 4),
                })

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
    topology = {
        'roots': [root],
        'nodes': nodes,
        'edges': edges,
    }

    return SubtreeHydroResult(
        summary=summary,
        canals=canals_list,
        timeseries=timeseries_rows,
        topology=topology,
    )
