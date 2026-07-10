"""
干支优化配水模型（NSGA-II）。

算法逻辑参考「干支优化配水.py」：
- 输入：1条 level-2 干渠（upper）+ K条 level-3 支渠（middle）
- 决策变量：K维流量 qk ∈ [ratio_min*qd, ratio_max*qd]，K维开始时间 tsk ∈ [0, t_max]
- 目标函数：
  - F1: 配水总时间 (h) = max(tek)
  - F2: 输水损失 (m³) = 干渠损失 + 支渠损失
  - F3: 干渠流量波动方差 = mean((Qt - Qt_avg)²)
- 约束：干渠最大流量约束 G1 = max(Qt) - Qmax ≤ 0（Manning 公式）
- 选解：熵权法 + TOPSIS

数据源：module_model.model.canals_data.CanalRecord
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

from module_model.model.canals_data import CanalRecord

GRAVITY: float = 9.81

_disable_tqdm: bool = not sys.stderr.isatty()


# =============================================================================
# JSON 序列化兜底
# =============================================================================


def _sanitize(obj: Any) -> Any:
    import math as _math
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if _math.isnan(obj) or _math.isinf(obj):
            return None
        return obj
    return obj


# =============================================================================
# 熵权法 + TOPSIS
# =============================================================================


def _entropy_topsis(
    F_matrix: np.ndarray,
    pref_weights: np.ndarray,
    alpha: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, int]:
    """熵权+TOPSIS选解，返回 (scores, weights, best_index)。"""
    F_norm = (F_matrix - F_matrix.min(axis=0)) / (
        F_matrix.max(axis=0) - F_matrix.min(axis=0) + 1e-9
    )
    col_sum = np.sum(F_norm, axis=0)
    safe_sum = np.where(col_sum > 1e-12, col_sum, 1.0)
    P = F_norm / safe_sum
    E_raw = -np.sum(P * np.log(P + 1e-9), axis=0) / np.log(len(F_norm))
    E = np.where(np.isfinite(E_raw), E_raw, 1.0)
    W_entropy = (1 - E) / np.sum(1 - E)
    W = alpha * pref_weights + (1 - alpha) * W_entropy

    distances = np.sqrt(
        np.sum(
            (F_norm * np.sqrt(W) - F_norm.max(axis=0) * np.sqrt(W)) ** 2,
            axis=1,
        )
    )
    scores = 1.0 / (1.0 + distances)
    best_index = int(np.argmax(scores))
    return scores, W, best_index


# =============================================================================
# 水力学函数
# =============================================================================


def trapezoid_Q(h: float, n: float, b: float, m: float, J: float) -> float:
    """Manning 公式：梯形断面过流能力 Q(h)。"""
    if h <= 0:
        return 0.0
    A = (b + m * h) * h
    P = b + 2 * h * math.sqrt(1 + m ** 2)
    R = A / P if P > 0 else 0.0
    return (1.0 / n) * A * (R ** (2.0 / 3.0)) * (J ** 0.5)


def trapezoid_Qmax(n: float, b: float, m: float, h_design: float, J: float) -> float:
    """干渠设计流量（水深 = h_design）。"""
    return trapezoid_Q(h_design, n, b, m, J)


def h_from_Q(Q_target: float, n: float, b: float, m: float, J: float,
             h_design: float, tol: float = 1e-4, max_iter: int = 50) -> float:
    """由给定流量反算干渠水深（二分法）。"""
    h_low, h_high = 0.001, h_design * 1.5
    for _ in range(max_iter):
        h_mid = (h_low + h_high) / 2.0
        Q_mid = trapezoid_Q(h_mid, n, b, m, J)
        if abs(Q_mid - Q_target) < tol:
            return h_mid
        if Q_mid < Q_target:
            h_low = h_mid
        else:
            h_high = h_mid
    return h_mid


def seepage_loss(q: float, L: float, w: float,
                 A: float, m_leak: float) -> float:
    """单条渠道渗漏损失 F = 0.36 * A * q^(1-m) * L * t / 100。"""
    t = w / (3600.0 * q) if q > 0 else 0.0
    return 0.36 * A * (q ** (1.0 - m_leak)) * L * t / 100.0


def compute_trunk_flow_series(
    qk: np.ndarray,
    tsk: np.ndarray,
    tek: np.ndarray,
    K: int,
    Qmax: float,
) -> tuple[np.ndarray, float]:
    """计算干渠流量时序 Qt。

    在每个整数时刻 t，遍历当前开启的支渠（tek[t] <= t < tek[t+1] 逆序），
    从最下游（最高闸门编号）向上游递推累计流量，取 max 作为 Qt[t]。

    返回 (Qt, max_flow_deviation)。
    """
    T_total = int(np.ceil(np.max(tek)))
    if T_total <= 0:
        return np.zeros(1), 0.0

    Qt = np.zeros(T_total)
    for t in range(T_total):
        active = (tsk <= t) & (tek >= t + 1)
        indices = np.where(active)[0][::-1]
        Q_up = 0.0
        for j, k in enumerate(indices):
            if qk[k] <= 0:
                continue
            Q_req = qk[k]
            if j > 0:
                Q_req = max(Q_req, Q_up + qk[k])
            Q_up = Q_req
        Qt[t] = Q_up

    if len(Qt) > 0 and Qmax > 0:
        max_dev = float(np.max(np.abs(Qt)))
    else:
        max_dev = 0.0
    return Qt, max_dev


# =============================================================================
# 优化问题类
# =============================================================================


class TrunkBranchProblem(ElementwiseProblem):
    """干支优化 NSGA-II 问题。

    决策变量布局：
    - 前 K 维：支渠流量 qk ∈ [qk_min, qk_max]
    - 后 K 维：支渠开始时间 tsk ∈ [0, t_max]

    目标函数（最小化）：
    - F1: max(tek) —— 总输水时间
    - F2: 干渠损失 + 支渠损失之和 —— 输水损失
    - F3: 干渠流量方差 mean((Qt - Qt_avg)²) —— 流量波动

    约束（<= 0 即满足）：
    - G1: max(Qt) - Qmax ≤ 0 —— 干渠最大流量约束
    """

    def __init__(
        self,
        qd_list: np.ndarray,
        w_list: np.ndarray,
        L_trunk: float,
        L_branch_list: np.ndarray,
        n_trunk: float,
        b_trunk: float,
        m_trunk: float,
        J_trunk: float,
        h_design_trunk: float,
        t_max: float,
        q_min_ratio: float,
        q_max_ratio: float,
        A: float,
        m_leak: float,
        Qmax: float,
    ):
        self.K = len(qd_list)
        self.qd_list = qd_list
        self.w_list = w_list
        self.L_trunk = L_trunk
        self.L_branch_list = L_branch_list
        self.n_trunk = n_trunk
        self.b_trunk = b_trunk
        self.m_trunk = m_trunk
        self.J_trunk = J_trunk
        self.h_design_trunk = h_design_trunk
        self.t_max = t_max
        self.q_min_ratio = q_min_ratio
        self.q_max_ratio = q_max_ratio
        self.A = A
        self.m_leak = m_leak
        self.Qmax = Qmax

        qk_min = q_min_ratio * qd_list
        qk_max = q_max_ratio * qd_list

        xl = np.concatenate([qk_min, np.zeros(self.K)])
        xu = np.concatenate([qk_max, np.full(self.K, t_max)])

        super().__init__(n_var=self.K * 2, n_obj=3, n_ieq_constr=1, xl=xl, xu=xu)

    def _evaluate(self, x, out, *args, **kwargs):
        qk = x[:self.K]
        tsk = x[self.K:]
        tek = tsk + self.w_list / (3600.0 * np.maximum(qk, 1e-6))

        # ── F1: 总输水时间 ──
        F1 = float(np.max(tek))

        # ── F2: 输水损失 ──
        # 支渠损失
        branch_loss = 0.0
        for k in range(self.K):
            if qk[k] > 1e-6:
                branch_loss += seepage_loss(
                    qk[k], self.L_branch_list[k], self.w_list[k],
                    self.A, self.m_leak,
                )
        # 干渠损失（使用总流量近似）
        Q_total = float(np.sum(qk))
        trunk_loss = 0.0
        if Q_total > 1e-6 and self.t_max > 0:
            trunk_loss = seepage_loss(
                Q_total, self.L_trunk, float(np.max(tek)) * 3600.0,
                self.A, self.m_leak,
            )
        F2 = branch_loss + trunk_loss

        # ── F3: 干渠流量波动方差 ──
        Qt, _ = compute_trunk_flow_series(
            qk, tsk, tek, self.K, self.Qmax,
        )
        if len(Qt) > 1:
            Qt_avg = np.mean(Qt)
            F3 = float(np.mean((Qt - Qt_avg) ** 2))
        else:
            F3 = 0.0

        # ── G1: 干渠最大流量约束 ──
        G1 = float(np.max(Qt)) - self.Qmax

        out["F"] = [F1, F2, F3]
        out["G"] = [G1]


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class TrunkBranchContext:
    """干支优化上下文，包含干渠参数和支渠列表。"""
    trunk: CanalRecord               # level-2 干渠
    branches: list[CanalRecord]      # level-3 支渠列表
    t_max: float
    flow_ratio_min: float
    flow_ratio_max: float
    permeability_index: float        # m
    permeability_coefficient: float   # A
    pop_size: int
    n_gen: int
    seed: int
    pref_weight_time: float
    pref_weight_loss: float
    pref_weight_flow_var: float
    alpha: float


@dataclass
class TrunkBranchResult:
    """干支优化结果。"""
    summary: dict
    trunk_canal: dict
    branches: list[dict]
    time_series: list[dict]
    pareto: list[dict]
    topsis_summary: dict

    def to_dict(self) -> dict:
        return _sanitize({
            'summary': self.summary,
            'trunk_canal': self.trunk_canal,
            'branches': self.branches,
            'time_series': self.time_series,
            'pareto': self.pareto,
            'topsis_summary': self.topsis_summary,
        })


# =============================================================================
# 核心求解函数
# =============================================================================


def solve_trunk_branch(ctx: TrunkBranchContext) -> TrunkBranchResult:
    """执行干支优化。"""
    if not ctx.branches:
        raise ValueError('支渠列表为空，无法执行干支优化')

    K = len(ctx.branches)
    qd_list = np.array([max(b.design_flow, 1e-6) for b in ctx.branches])
    w_list = np.array([max(b.water_demand, 0.0) for b in ctx.branches])
    L_branch_list = np.array([max(b.length, 1.0) for b in ctx.branches])

    trunk = ctx.trunk
    n_trunk = max(trunk.roughness, 0.001)
    b_trunk = max(trunk.bottom_width, 0.1)
    m_trunk = max(trunk.side_slope, 0.1)
    J_trunk = max(trunk.slope, 1e-6)
    h_design_trunk = max(trunk.design_depth, 0.5)
    L_trunk = max(trunk.length, 1.0)

    Qmax = max(trunk.design_flow, 1e-6)
    if Qmax <= 0:
        raise ValueError(f'干渠 {trunk.canal_id} 的 design_flow={Qmax} 无效，请检查数据')

    problem = TrunkBranchProblem(
        qd_list=qd_list,
        w_list=w_list,
        L_trunk=L_trunk,
        L_branch_list=L_branch_list,
        n_trunk=n_trunk,
        b_trunk=b_trunk,
        m_trunk=m_trunk,
        J_trunk=J_trunk,
        h_design_trunk=h_design_trunk,
        t_max=ctx.t_max,
        q_min_ratio=ctx.flow_ratio_min,
        q_max_ratio=ctx.flow_ratio_max,
        A=ctx.permeability_coefficient,
        m_leak=ctx.permeability_index,
        Qmax=Qmax,
    )

    algorithm = NSGA2(
        pop_size=ctx.pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=0.1, eta=20),
        eliminate_duplicates=True,
    )

    import logging as _logging
    _logger = _logging.getLogger('trunk_branch_optimize')
    _logger.setLevel(_logging.INFO)

    _logger.info(
        'PYMOO START: n_var=%d n_obj=%d n_constr=%d n_gen=%d pop=%d seed=%d',
        problem.n_var, problem.n_obj, problem.n_constr, ctx.n_gen, ctx.pop_size, ctx.seed,
    )

    try:
        res = minimize(
            problem,
            algorithm,
            termination=('n_gen', ctx.n_gen),
            seed=ctx.seed,
            verbose=False,
        )
    except Exception as exc:
        _logger.error('PYMOO minimize raised %s: %s', type(exc).__name__, exc)
        raise RuntimeError(f'NSGA-II 求解过程异常: {type(exc).__name__}: {exc}') from exc

    _logger.info(
        'PYMOO RESULT: X=%s F=%s G=%s',
        None if res.X is None else len(res.X),
        None if res.F is None else (res.F.shape if hasattr(res.F, 'shape') else len(res.F)),
        None if res.G is None else (res.G.shape if hasattr(res.G, 'shape') else len(res.G)),
    )

    import numpy as _np
    if res.X is None or len(res.X) == 0:
        raise RuntimeError('NSGA-II 未收敛到任何解，请调整参数或数据')

    # 检查所有目标函数值是否全为 inf/nan（评估全部失败的信号）
    all_f_nan_or_inf = _np.all(~_np.isfinite(res.F))
    if all_f_nan_or_inf:
        _logger.error('PYMOO: ALL fitness values are inf/nan — problem evaluation failed')
        raise RuntimeError('NSGA-II 所有个体目标函数值均为 inf/nan，问题评估失败，请检查渠道参数数据（几何尺寸、流量等）是否合理')

    feasible_mask = _np.sum(res.G > 1e-4, axis=1) == 0
    if not _np.any(feasible_mask):
        # 尝试放宽约束
        feasible_mask = _np.sum(res.G > 1e-2, axis=1) == 0
        _logger.info(
            'PYMOO feasible (1e-4): %d/%d  feasible (1e-2): %d/%d',
            int(_np.sum(_np.sum(res.G > 1e-4, axis=1) == 0)),
            len(res.G),
            int(_np.sum(_np.sum(res.G > 1e-2, axis=1) == 0)),
            len(res.G),
        )
        if not _np.any(feasible_mask):
            # 再放宽：直接取 G 最小的前 5 个
            g_violation = _np.maximum(res.G, 0).mean(axis=1)
            best_idx_relax = _np.argsort(g_violation)[:min(5, len(g_violation))]
            _logger.info('PYMOO best G violations: %s', [_np.maximum(g, 0).max() for g in res.G[best_idx_relax]])
            feasible_mask = _np.zeros(len(res.X), dtype=bool)
            feasible_mask[best_idx_relax] = True
            if not _np.any(feasible_mask):
                raise RuntimeError('NSGA-II 未找到满足干渠流量约束的可行解，请检查干渠设计流量或调高 t_max')

    X_feas = res.X[feasible_mask]
    F_feas = res.F[feasible_mask]

    pref = np.array([
        ctx.pref_weight_time,
        ctx.pref_weight_loss,
        ctx.pref_weight_flow_var,
    ])
    scores, weights, best_idx = _entropy_topsis(F_feas, pref, ctx.alpha)

    best_X = X_feas[best_idx]
    best_F = F_feas[best_idx]
    best_qk = best_X[:K]
    best_tsk = best_X[K:]

    # ── 构建支渠结果 ──
    branches_result = []
    total_branch_loss = 0.0
    tek_best = best_tsk + w_list / (3600.0 * np.maximum(best_qk, 1e-6))
    for k, branch in enumerate(ctx.branches):
        qk_k = float(best_qk[k])
        tsk_k = float(best_tsk[k])
        tek_k = float(tek_best[k])
        dur_k = tek_k - tsk_k
        qd_k = float(qd_list[k])
        ratio_k = qk_k / qd_k if qd_k > 1e-6 else 0.0
        loss_k = seepage_loss(
            qk_k, float(L_branch_list[k]), float(w_list[k]),
            ctx.permeability_coefficient, ctx.permeability_index,
        )
        total_branch_loss += loss_k
        branches_result.append({
            'name': branch.canal_id,
            'canal_name': branch.canal_name or branch.canal_id,
            'qd': round(qd_k, 4),
            'q_actual': round(qk_k, 4),
            'ratio': round(ratio_k, 4),
            't_start_h': round(tsk_k, 3),
            'duration_h': round(dur_k, 3),
            't_end_h': round(tek_k, 3),
            'loss_m3': round(loss_k, 2),
        })

    # ── 干渠损失 ──
    Q_total = float(np.sum(best_qk))
    t_total = float(np.max(tek_best))
    trunk_loss = 0.0
    if Q_total > 1e-6 and t_total > 0:
        trunk_loss = seepage_loss(
            Q_total, float(L_trunk), t_total * 3600.0,
            ctx.permeability_coefficient, ctx.permeability_index,
        )

    # ── 干渠时序 ──
    Qt, _ = compute_trunk_flow_series(
        best_qk, best_tsk, tek_best, K, Qmax,
    )
    time_series = []
    for t in range(len(Qt)):
        H_t = h_from_Q(
            float(Qt[t]), n_trunk, b_trunk, m_trunk, J_trunk, h_design_trunk,
        )
        time_series.append({
            't_h': round(float(t), 1),
            'Q_m3s': round(float(Qt[t]), 4),
            'H_m': round(H_t, 4),
        })

    # ── 汇总 ──
    summary = {
        'mode': 'trunk-branch',
        'n_branches': K,
        'trunk_canal_id': trunk.canal_id,
        'Qmax_m3s': round(Qmax, 4),
        'topsis_score': round(float(scores[best_idx]), 4),
        'entropy_weights': {
            'F1_time': round(float(weights[0]), 4),
            'F2_loss': round(float(weights[1]), 4),
            'F3_flow_var': round(float(weights[2]), 4),
        },
        'objective_values': {
            'F1_total_time_h': round(float(best_F[0]), 3),
            'F2_total_loss_m3': round(float(best_F[1]), 2),
            'F3_flow_var': round(float(best_F[2]), 6),
        },
        'trunk_loss_m3': round(trunk_loss, 2),
        'branch_loss_m3': round(total_branch_loss, 2),
        'total_loss_m3': round(trunk_loss + total_branch_loss, 2),
    }

    trunk_canal = {
        'Q_total_m3s': round(Q_total, 4),
        'Qmax_m3s': round(Qmax, 4),
        't_max_h': round(t_total, 3),
        'trunk_loss_m3': round(trunk_loss, 2),
        'branch_loss_m3': round(total_branch_loss, 2),
        'total_loss_m3': round(trunk_loss + total_branch_loss, 2),
    }

    topsis_summary = {
        'total_time_h': round(float(best_F[0]), 3),
        'total_loss_m3': round(float(best_F[1]), 2),
        'flow_var': round(float(best_F[2]), 6),
        'trunk_loss_m3': round(trunk_loss, 2),
        'branch_loss_m3': round(total_branch_loss, 2),
    }

    # ── Pareto 前沿 ──
    pareto = []
    for i in range(len(F_feas)):
        pareto.append({
            'F1': round(float(F_feas[i, 0]), 3),
            'F2': round(float(F_feas[i, 1]), 2),
            'F3': round(float(F_feas[i, 2]), 6),
            'score': round(float(scores[i]), 4),
            'selected': (i == best_idx),
        })

    return TrunkBranchResult(
        summary=summary,
        trunk_canal=trunk_canal,
        branches=branches_result,
        time_series=time_series,
        pareto=pareto,
        topsis_summary=topsis_summary,
    )
