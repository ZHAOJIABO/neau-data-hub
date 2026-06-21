"""
支斗轮续灌优化模型（NSGA-II）。

算法逻辑参考「支斗优化配水.py」：
- 输入：1条 level-3 支渠（upper）+ K条 level-4 斗渠（laterals）
- 决策变量：
  - 前 K 维：斗渠分组编号（0 ~ n_groups-1）
  - 后 K 维：斗渠流量比例（flow_ratio_min ~ flow_ratio_max）
- 目标函数（最小化）：
  - F1: 总输水损失 = 组间（支渠）损失 + 组内（斗渠）损失
  - F2: 组间流量差异 max(|Q_design - Q_group|)
  - F3: 组内时间差异 max(t_max_group - t_min_group)
- 约束：
  - G1: 总时间 <= t_max
  - G2: max(Q_group) <= Q_branch_design
  - G3: min(Q_group) >= 0.6 * Q_branch_design
- 选解：熵权法 + TOPSIS

数据源：module_irrigation.model.canals_data.CanalRecord
"""

from __future__ import annotations

import logging
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

from module_irrigation.model.canals_data import CanalRecord

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
# 渗漏损失
# =============================================================================


def seepage_loss(q: float, L: float, w: float,
                 A: float, m_leak: float) -> float:
    """单条渠道渗漏损失 F = 0.36 * A * q^(1-m) * L * t / 100。"""
    if q <= 0 or L <= 0 or w <= 0:
        return 0.0
    t = w / (3600.0 * q)
    return 0.36 * A * (q ** (1.0 - m_leak)) * L * t / 100.0


# =============================================================================
# 优化问题类
# =============================================================================


class BranchLateralProblem(ElementwiseProblem):
    """支斗轮续灌 NSGA-II 问题。

    决策变量布局：
    - 前 K 维：斗渠分组编号（连续值，用 floor 映射到整数）
    - 后 K 维：斗渠流量比例（flow_ratio_min ~ flow_ratio_max）

    目标函数（最小化）：
    - F1: 总输水损失（支渠段 + 各斗渠）
    - F2: 组间流量差异 max(|Q_design - Q_group|)
    - F3: 组内时间差异 max(t_max_group - t_min_group)

    约束（<= 0 即满足）：
    - G1: 总时间 <= t_max
    - G2: max(Q_group) <= Q_branch_design
    - G3: min(Q_group) >= 0.6 * Q_branch_design
    """

    def __init__(
        self,
        lateral_qd: np.ndarray,
        lateral_w: np.ndarray,
        lateral_L: np.ndarray,
        Q_branch_design: float,
        L_branch: float,
        t_max: float,
        flow_ratio_min: float,
        flow_ratio_max: float,
        n_groups: int,
        A: float,
        m_leak: float,
    ):
        self.K = len(lateral_qd)
        self.lateral_qd = lateral_qd
        self.lateral_w = lateral_w
        self.lateral_L = lateral_L
        self.Q_branch_design = Q_branch_design
        self.L_branch = L_branch
        self.t_max = t_max
        self.flow_ratio_min = flow_ratio_min
        self.flow_ratio_max = flow_ratio_max
        self.n_groups = n_groups
        self.A = A
        self.m_leak = m_leak

        # 分组变量 x[0:K] ∈ [0,1)，流量比例 x[K:] ∈ [0,1]
        super().__init__(n_var=self.K * 2, n_obj=3, n_ieq_constr=3, xl=0.0, xu=1.0)

    def _evaluate(self, x, out, *args, **kwargs):
        # ── 解码 ──
        groups = np.floor(x[:self.K] * self.n_groups).astype(int)
        groups = np.clip(groups, 0, self.n_groups - 1)
        ratios = self.flow_ratio_min + (self.flow_ratio_max - self.flow_ratio_min) * x[self.K:]
        ratios = np.clip(ratios, self.flow_ratio_min, self.flow_ratio_max)

        # 斗渠实际流量
        q_actual = ratios * self.lateral_qd

        # 斗渠配水历时
        t_actual = np.zeros(self.K)
        for k in range(self.K):
            if q_actual[k] > 1e-6:
                t_actual[k] = self.lateral_w[k] / (3600.0 * q_actual[k])

        # ── 按组聚合 ──
        group_flows = np.zeros(self.n_groups)
        group_times = np.zeros(self.n_groups)
        group_losses_U = 0.0
        max_time_diff_sum = 0.0
        valid_groups_mask = np.zeros(self.n_groups, dtype=bool)

        for g_id in range(self.n_groups):
            indices = np.where(groups == g_id)[0]
            if len(indices) == 0:
                continue
            valid_groups_mask[g_id] = True

            q_sum = float(np.sum(q_actual[indices]))
            group_flows[g_id] = q_sum

            t_max_g = float(np.max(t_actual[indices]))
            group_times[g_id] = t_max_g

            if len(indices) > 1:
                t_min_g = float(np.min(t_actual[indices]))
                diff = t_max_g - t_min_g
                if diff > max_time_diff_sum:
                    max_time_diff_sum = diff

            # 支渠段在该组的损失（用组内总流量近似）
            if q_sum > 1e-6 and t_max_g > 0:
                F_u = seepage_loss(
                    q_sum, self.L_branch, t_max_g * 3600.0,
                    self.A, self.m_leak,
                )
                group_losses_U += F_u

        # 斗渠渗漏损失
        lateral_losses = 0.0
        for k in range(self.K):
            if q_actual[k] > 1e-6:
                lateral_losses += seepage_loss(
                    q_actual[k], float(self.lateral_L[k]),
                    float(self.lateral_w[k]), self.A, self.m_leak,
                )

        # ── 目标函数 ──
        F1 = group_losses_U + lateral_losses

        if np.any(valid_groups_mask):
            valid_flows = group_flows[valid_groups_mask]
            diffs = self.Q_branch_design - valid_flows
            F2 = float(np.max(np.abs(diffs)))
        else:
            F2 = 1e10

        F3 = max_time_diff_sum

        # ── 约束 ──
        g = []
        total_time = float(np.sum(group_times))
        g.append(total_time - self.t_max)

        if np.any(valid_groups_mask):
            current_flows = group_flows[valid_groups_mask]
            g.append(float(np.max(current_flows) - self.Q_branch_design))
            g.append(float(0.6 * self.Q_branch_design - float(np.min(current_flows))))
        else:
            g.extend([100.0, 100.0])

        out["F"] = [F1, F2, F3]
        out["G"] = g


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class BranchLateralContext:
    """支斗轮续灌优化上下文。"""
    branch: CanalRecord               # level-3 支渠
    laterals: list[CanalRecord]      # level-4 斗渠列表
    t_max: float
    flow_ratio_min: float
    flow_ratio_max: float
    min_groups: int
    max_groups: int
    permeability_index: float          # m
    permeability_coefficient: float   # A
    pop_size: int
    n_gen: int
    seed: int
    pref_weight_time: float
    pref_weight_loss: float
    pref_weight_flow_var: float
    alpha: float


@dataclass
class BranchLateralResult:
    """支斗轮续灌优化结果。"""
    summary: dict
    branch_canal: dict
    groups: list[dict]
    laterals: list[dict]
    pareto: list[dict]
    topsis_summary: dict

    def to_dict(self) -> dict:
        return _sanitize({
            'summary': self.summary,
            'branch_canal': self.branch_canal,
            'groups': self.groups,
            'laterals': self.laterals,
            'pareto': self.pareto,
            'topsis_summary': self.topsis_summary,
        })


# =============================================================================
# 核心求解函数
# =============================================================================


def solve_branch_lateral(ctx: BranchLateralContext) -> BranchLateralResult:
    """执行支斗轮续灌优化。"""
    if not ctx.laterals:
        raise ValueError('斗渠列表为空，无法执行支斗轮续灌优化')

    K = len(ctx.laterals)
    lateral_qd = np.array([max(l.design_flow, 1e-6) for l in ctx.laterals])
    lateral_w = np.array([max(l.water_demand, 0.0) for l in ctx.laterals])
    lateral_L = np.array([max(l.length, 1.0) for l in ctx.laterals])

    branch = ctx.branch
    Q_branch_design = max(branch.design_flow, 1e-6)
    L_branch = max(branch.length, 1.0)

    # ── 对每个候选分组数分别求解，取 TOPSIS 最优 ──
    results_store: dict[int, dict] = {}
    best_score_global = -1.0
    best_M_global = ctx.min_groups
    best_X_global = None
    best_F_global = None
    best_weights_global = None
    best_scores_global = None

    pref = np.array([
        ctx.pref_weight_time,
        ctx.pref_weight_loss,
        ctx.pref_weight_flow_var,
    ])

    for n_groups in range(ctx.min_groups, ctx.max_groups + 1):
        problem = BranchLateralProblem(
            lateral_qd=lateral_qd,
            lateral_w=lateral_w,
            lateral_L=lateral_L,
            Q_branch_design=Q_branch_design,
            L_branch=L_branch,
            t_max=ctx.t_max,
            flow_ratio_min=ctx.flow_ratio_min,
            flow_ratio_max=ctx.flow_ratio_max,
            n_groups=n_groups,
            A=ctx.permeability_coefficient,
            m_leak=ctx.permeability_index,
        )

        algorithm = NSGA2(
            pop_size=ctx.pop_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=0.1, eta=20),
            eliminate_duplicates=True,
        )

        res = minimize(
            problem,
            algorithm,
            termination=('n_gen', ctx.n_gen),
            seed=ctx.seed,
            verbose=False,
        )

        if res.X is None or len(res.X) == 0:
            continue

        feasible_mask = np.sum(res.G > 1e-4, axis=1) == 0
        if not np.any(feasible_mask):
            feasible_mask = np.sum(res.G > 1e-2, axis=1) == 0
            if not np.any(feasible_mask):
                continue

        X_feas = res.X[feasible_mask]
        F_feas = res.F[feasible_mask]
        scores, weights, best_idx = _entropy_topsis(F_feas, pref, ctx.alpha)

        results_store[n_groups] = {
            'X_feas': X_feas,
            'F_feas': F_feas,
            'scores': scores,
            'weights': weights,
            'best_idx': best_idx,
        }

        if float(scores[best_idx]) > best_score_global:
            best_score_global = float(scores[best_idx])
            best_M_global = n_groups
            best_X_global = X_feas[best_idx]
            best_F_global = F_feas[best_idx]
            best_weights_global = weights
            best_scores_global = scores

    if best_X_global is None:
        raise RuntimeError(
            f'NSGA-II 未找到满足约束的可行解（候选分组数 {ctx.min_groups}~{ctx.max_groups}）'
        )

    # ── 解码最优解 ──
    best_X = best_X_global
    best_F = best_F_global
    best_M = best_M_global

    groups = np.floor(best_X[:K] * best_M).astype(int)
    groups = np.clip(groups, 0, best_M - 1)
    ratios = ctx.flow_ratio_min + (ctx.flow_ratio_max - ctx.flow_ratio_min) * best_X[K:]
    ratios = np.clip(ratios, ctx.flow_ratio_min, ctx.flow_ratio_max)

    q_actual = ratios * lateral_qd
    t_actual = np.zeros(K)
    for k in range(K):
        if q_actual[k] > 1e-6:
            t_actual[k] = lateral_w[k] / (3600.0 * q_actual[k])

    lateral_loss_total = 0.0
    laterals_result = []
    for k, lateral in enumerate(ctx.laterals):
        qk = float(q_actual[k])
        tk = float(t_actual[k])
        qd_k = float(lateral_qd[k])
        ratio_k = qk / qd_k if qd_k > 1e-6 else 0.0
        loss_k = seepage_loss(
            qk, float(lateral_L[k]), float(lateral_w[k]),
            ctx.permeability_coefficient, ctx.permeability_index,
        )
        lateral_loss_total += loss_k
        laterals_result.append({
            'Name': lateral.canal_id,
            'canal_name': lateral.canal_name or lateral.canal_id,
            'group': int(groups[k]) + 1,
            'Q_design': round(qd_k, 4),
            'Q_actual': round(qk, 4),
            'ratio': round(ratio_k, 4),
            'duration_h': round(tk, 3),
            'loss_m3': round(loss_k, 2),
        })

    # ── 构建轮灌组 ──
    groups_result = []
    group_flows = np.zeros(best_M)
    group_times = np.zeros(best_M)
    group_losses = np.zeros(best_M)
    current_time = 0.0

    for g_id in range(best_M):
        indices = np.where(groups == g_id)[0]
        if len(indices) == 0:
            continue

        q_sum = float(np.sum(q_actual[indices]))
        t_max_g = float(np.max(t_actual[indices]))
        t_min_g = float(np.min(t_actual[indices]))

        loss_g = seepage_loss(
            q_sum, L_branch, t_max_g * 3600.0,
            ctx.permeability_coefficient, ctx.permeability_index,
        )

        group_flows[g_id] = q_sum
        group_times[g_id] = t_max_g
        group_losses[g_id] = loss_g

        flow_ratio_g = q_sum / Q_branch_design if Q_branch_design > 1e-6 else 0.0

        groups_result.append({
            'group': g_id + 1,
            'total_flow': round(q_sum, 4),
            'flow_ratio': round(flow_ratio_g, 4),
            'start_h': round(current_time, 3),
            'duration_h': round(t_max_g, 3),
            'end_h': round(current_time + t_max_g, 3),
            'loss_m3': round(loss_g, 2),
            'n_laterals': len(indices),
        })

        current_time += t_max_g

    total_time = float(current_time)
    total_branch_loss = float(np.sum(group_losses))

    # ── 汇总 ──
    summary = {
        'mode': 'branch-lateral',
        'n_laterals': K,
        'branch_canal_id': branch.canal_id,
        'best_n_groups': best_M,
        'topsis_score': round(float(best_scores_global[results_store[best_M]['best_idx']]), 4),
        'entropy_weights': {
            'F1_time': round(float(best_weights_global[0]), 4),
            'F2_loss': round(float(best_weights_global[1]), 4),
            'F3_flow_var': round(float(best_weights_global[2]), 4),
        },
        'objective_values': {
            'F1_total_loss_m3': round(float(best_F[0]), 2),
            'F2_flow_diff': round(float(best_F[1]), 4),
            'F3_time_diff': round(float(best_F[2]), 3),
        },
        'branch_loss_m3': round(total_branch_loss, 2),
        'lateral_loss_m3': round(lateral_loss_total, 2),
        'total_loss_m3': round(total_branch_loss + lateral_loss_total, 2),
        'total_time_h': round(total_time, 3),
    }

    branch_canal = {
        'Q_design_m3s': round(Q_branch_design, 4),
        't_max_h': round(total_time, 3),
        'branch_loss_m3': round(total_branch_loss, 2),
        'lateral_loss_m3': round(lateral_loss_total, 2),
        'total_loss_m3': round(total_branch_loss + lateral_loss_total, 2),
    }

    topsis_summary = {
        'total_time_h': round(total_time, 3),
        'total_loss_m3': round(float(best_F[0]), 2),
        'flow_diff': round(float(best_F[1]), 4),
        'time_diff': round(float(best_F[2]), 3),
        'branch_loss_m3': round(total_branch_loss, 2),
        'lateral_loss_m3': round(lateral_loss_total, 2),
    }

    # ── Pareto 前沿 ──
    stored = results_store[best_M]
    pareto = []
    for i in range(len(stored['scores'])):
        pareto.append({
            'F1': round(float(stored['F_feas'][i, 0]), 2),
            'F2': round(float(stored['F_feas'][i, 1]), 4),
            'F3': round(float(stored['F_feas'][i, 2]), 3),
            'score': round(float(stored['scores'][i]), 4),
            'selected': (i == stored['best_idx']),
        })

    return BranchLateralResult(
        summary=summary,
        branch_canal=branch_canal,
        groups=groups_result,
        laterals=laterals_result,
        pareto=pareto,
        topsis_summary=topsis_summary,
    )
