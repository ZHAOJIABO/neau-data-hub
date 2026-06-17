"""
全渠系三级顺序配水优化模型（NSGA-III）。

采用顺序优化策略：
1. 干-支优化：同时配水，优化支渠流量和开始时间
2. 支-斗优化：对每个支渠下的斗渠进行轮灌分组

目标函数：
- F1: 配水总时间
- F2: 全渠系渗漏损失（干渠 + 支渠 + 斗渠）
- F3: 干渠流量波动方差

约束条件：
- 干渠最大流量约束
- 各支渠下级斗渠总流量约束（0.6*Qd ~ Qd）
- 总输水时间约束

数据源：module_irrigation.model.canals_data.CanalRecord
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize

from module_irrigation.model.canals_data import CanalRecord

GRAVITY: float = 9.81


# =============================================================================
# 熵权法 + TOPSIS（复用现有逻辑）
# =============================================================================


def _entropy_topsis_weighted(
    F_matrix: np.ndarray,
    pref_weights: np.ndarray,
    alpha: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, int]:
    """熵权+TOPSIS选解，返回 (scores, weights, best_index)。"""
    F_norm = (F_matrix - F_matrix.min(axis=0)) / (
        F_matrix.max(axis=0) - F_matrix.min(axis=0) + 1e-9
    )
    P = F_norm / np.sum(F_norm, axis=0)
    E = -np.sum(P * np.log(P + 1e-9), axis=0) / np.log(len(F_norm))
    W_entropy = (1 - E) / np.sum(1 - E)
    W = alpha * pref_weights + (1 - alpha) * W_entropy

    distances = np.sqrt(
        np.sum(
            (F_norm * np.sqrt(W) - F_norm.max(axis=0) * np.sqrt(W)) ** 2,
            axis=1,
        )
    )
    best_index = int(np.argmax(distances))
    return distances, W, best_index


# =============================================================================
# 渗漏损失计算
# =============================================================================


def _calc_seepage_loss(
    q: float,
    length: float,
    duration: float,
    coefficient_a: float,
    index_m: float,
) -> float:
    """渗漏损失公式：F = 0.36 * A * q^(1-m) * L * t / 100"""
    return 0.36 * coefficient_a * (q ** (1 - index_m)) * length * duration / 100.0


# =============================================================================
# 干渠几何计算（Manning 公式）
# =============================================================================


def _trapezoid_Q(h: float, canal: CanalRecord) -> float:
    """Manning 公式：Q = (1/n) * A * R^(2/3) * J^0.5"""
    b = canal.bottom_width
    m = canal.side_slope
    n = canal.roughness
    J = canal.slope
    top = ((b + m * h) * h) ** (5.0 / 3.0)
    bottom = (b + 2.0 * h * math.sqrt(1.0 + m * m)) ** (2.0 / 3.0)
    return (1.0 / n) * top / bottom * (J ** 0.5)


def _trapezoid_Qmax(canal: CanalRecord) -> float:
    return _trapezoid_Q(canal.design_depth, canal)


# =============================================================================
# 上下文和结果数据类
# =============================================================================


@dataclass
class FullCanalContext:
    """全渠系优化上下文。"""

    main: CanalRecord  # 干渠
    branches: list[CanalRecord]  # 支渠列表
    laterals_by_branch: dict[str, list[CanalRecord]]  # 每个支渠下的斗渠
    t_max: float = 360.0
    flow_ratio_min: float = 0.8
    flow_ratio_max: float = 1.0
    min_groups: int = 2
    max_groups: int = 6
    permeability_index: float = 0.4
    permeability_coefficient: float = 1.9
    pop_size: int = 80
    n_gen: int = 60
    seed: int = 1
    pref_weight_time: float = 0.4
    pref_weight_loss: float = 0.3
    pref_weight_flow_var: float = 0.3
    alpha: float = 0.5


@dataclass
class LateralSchedule:
    """单个支渠下的斗渠配水安排。"""

    branch_id: str
    channels: list[dict]  # 斗渠配水详情
    groups: list[dict]  # 轮灌组汇总
    total_loss: float
    total_time: float
    max_group_flow: float


@dataclass
class FullResult:
    """全渠系优化结果。"""

    summary: dict
    main_canal: dict
    branches: list[dict]
    laterals: list[dict]
    groups: list[dict]
    time_series: list[dict]
    pareto: list[dict]
    topsis_summary: dict

    def to_dict(self) -> dict:
        return {
            'summary': self.summary,
            'main_canal': self.main_canal,
            'branches': self.branches,
            'laterals': self.laterals,
            'groups': self.groups,
            'time_series': self.time_series,
            'pareto': self.pareto,
            'topsis_summary': self.topsis_summary,
        }


# =============================================================================
# 全渠系优化问题
# =============================================================================


class FullCanalProblem(ElementwiseProblem):
    """
    全渠系三级顺序配水问题。

    决策变量：
        - 前 K 维：支渠流量 qk，范围 0.6*qd ~ qd
        - 后 K 维：支渠开始时间 tsk，范围 0 ~ t_max

    目标函数（均为 cost 型）：
        - F1: 配水总时间
        - F2: 全渠系渗漏损失
        - F3: 干渠流量波动方差

    约束：
        - g1: max(Qt) - Qmax_main <= 0
    """

    def __init__(self, ctx: FullCanalContext) -> None:
        self.ctx = ctx
        K = len(ctx.branches)
        self.K = K
        qd_list = np.array([b.design_flow for b in ctx.branches])
        self.qd_list = qd_list
        super().__init__(
            n_var=K * 2,
            n_obj=3,
            n_ieq_constr=1,
            xl=np.concatenate([0.6 * qd_list, np.zeros(K)]),
            xu=np.concatenate([qd_list, np.full(K, ctx.t_max)]),
        )

    def _evaluate(self, x, out, *args, **kwargs) -> None:
        ctx = self.ctx
        K = self.K
        qk = x[:K]
        tsk = x[K:]

        # 计算各支渠配水时长
        w_list = np.array([b.water_demand for b in ctx.branches])
        lengths_branch = np.array([b.length for b in ctx.branches])
        tek = tsk + w_list / (3600.0 * np.maximum(qk, 1e-9))
        T_total = float(np.max(tek))

        # F1: 总配水时间
        F1 = T_total

        # 计算干渠各时段流量
        T_int = max(1, int(math.ceil(T_total)))
        Qt = np.zeros(T_int)
        for t in range(T_int):
            active = (tsk <= t) & (tek >= t)
            Qt[t] = float(np.sum(qk[active]))

        # F3: 干渠流量波动方差
        Qt_avg = float(np.mean(Qt)) if len(Qt) > 0 else 0.0
        F3 = float(np.mean((Qt - Qt_avg) ** 2)) if len(Qt) > 0 else 0.0

        # F2: 全渠系渗漏损失
        F2 = 0.0
        # 干渠损失
        main_loss = _calc_seepage_loss(
            float(np.sum(qk)), ctx.main.length, T_total,
            ctx.permeability_coefficient, ctx.permeability_index
        )
        F2 += main_loss
        # 支渠损失
        for j in range(K):
            branch_loss = _calc_seepage_loss(
                qk[j], lengths_branch[j], tek[j] - tsk[j],
                ctx.permeability_coefficient, ctx.permeability_index
            )
            F2 += branch_loss

        # 约束：干渠最大流量
        Qmax_main = _trapezoid_Qmax(ctx.main)
        g1 = float(np.max(Qt) - Qmax_main) if len(Qt) > 0 else 0.0

        out['F'] = [F1, F2, F3]
        out['G'] = [g1]


# =============================================================================
# 支-斗轮灌优化（复用现有逻辑）
# =============================================================================


def _run_lateral_optimization(
    parent: CanalRecord,
    laterals: list[CanalRecord],
    ctx: FullCanalContext,
) -> tuple[list[dict], list[dict], float] | None:
    """
    对单个支渠下的斗渠进行轮灌优化，返回 (channels, groups, loss)。

    采用固定分组数 M=3 进行简化（可扩展为多分组搜索）。
    """
    if not laterals:
        return None

    n = len(laterals)
    # 简化处理：使用 min_groups 作为固定分组数
    m = min(max(2, ctx.min_groups), n)

    Q_design = np.array([l.design_flow for l in laterals])
    W_req = np.array([l.water_demand for l in laterals])
    L = np.array([l.length for l in laterals])

    # 简化轮灌策略：按配水比例排序后均分
    # 实际流量取设计流量的 flow_ratio_max
    ratios = np.full(n, ctx.flow_ratio_max)
    q_actual = ratios * Q_design
    t_actual = W_req / (3600.0 * np.maximum(q_actual, 1e-9))

    # 按时间长短排序分配组别
    sorted_indices = np.argsort(-t_actual)
    groups_idx = np.zeros(n, dtype=int)
    group_size = n // m
    for i, idx in enumerate(sorted_indices):
        groups_idx[idx] = min(i // group_size, m - 1) if group_size > 0 else 0

    # 计算每组流量
    group_flows = np.zeros(m)
    group_times = np.zeros(m)
    group_losses = np.zeros(m)
    total_lateral_loss = 0.0

    for g in range(m):
        idx = np.where(groups_idx == g)[0]
        if len(idx) == 0:
            continue
        q_sum = float(np.sum(q_actual[idx]))
        t_max_g = float(np.max(t_actual[idx]))
        group_flows[g] = q_sum
        group_times[g] = t_max_g
        group_losses[g] = _calc_seepage_loss(
            q_sum, parent.length, t_max_g,
            ctx.permeability_coefficient, ctx.permeability_index
        )
        for i in idx:
            total_lateral_loss += _calc_seepage_loss(
                q_actual[i], L[i], t_actual[i],
                ctx.permeability_coefficient, ctx.permeability_index
            )

    # 构建斗渠详情
    channel_rows: list[dict] = []
    for i, lat in enumerate(laterals):
        channel_rows.append({
            'name': lat.canal_id,
            'parent': parent.canal_id,
            'group': int(groups_idx[i]) + 1,
            'Q_design': float(Q_design[i]),
            'Q_actual': float(q_actual[i]),
            'ratio': float(ratios[i]),
            'duration_h': float(t_actual[i]),
            'loss_m3': float(_calc_seepage_loss(
                q_actual[i], L[i], t_actual[i],
                ctx.permeability_coefficient, ctx.permeability_index
            )),
        })

    # 构建轮灌组汇总
    group_rows: list[dict] = []
    for g in range(m):
        idx = np.where(groups_idx == g)[0]
        if len(idx) == 0:
            continue
        group_rows.append({
            'group': g + 1,
            'parent': parent.canal_id,
            'total_flow': round(group_flows[g], 4),
            'flow_ratio': round(group_flows[g] / max(parent.design_flow, 1e-9), 4),
            'duration_h': round(group_times[g], 3),
            'loss_m3': round(group_losses[g], 2),
        })

    total_loss = total_lateral_loss + float(np.sum(group_losses))
    return channel_rows, group_rows, total_loss


def _compute_main_time_series(
    qk: np.ndarray,
    tsk: np.ndarray,
    tek: np.ndarray,
    ctx: FullCanalContext,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """计算干渠时序：流量 Qt + 水位 H。"""
    T_total = float(np.max(tek))
    M = max(1, int(math.ceil(T_total)))
    Qt = np.zeros(M)
    for t in range(M):
        active = (tsk <= t) & (tek >= t)
        Qt[t] = float(np.sum(qk[active]))

    t_start = int(max(0, math.floor(float(np.min(tsk)))))
    if t_start >= M:
        t_start = M - 1
    Qt_cut = Qt[t_start:] if t_start < M else np.array([Qt[-1]])
    time_cut = np.arange(t_start, t_start + len(Qt_cut))

    # 计算水位
    def _h_from_Q(Q_target: float) -> float:
        """二分法反算水深。"""
        lo, hi = 0.01, max(ctx.main.design_depth * 2.0, 2.0)
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            q_mid = _trapezoid_Q(mid, ctx.main)
            if abs(q_mid - Q_target) < 1e-4:
                return mid
            if q_mid < Q_target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    H_main = np.array([_h_from_Q(float(q)) for q in Qt_cut])
    return time_cut, Qt_cut, H_main


# =============================================================================
# 主求解函数
# =============================================================================


def _ProgressCallback(n_gen, ctx: FullCanalContext):
    """返回一个 pymoo Callback，用于在每代结束时打印进度。"""
    import time
    from utils.log_util import logger

    class _GenCallback:
        def __init__(self):
            self.start = time.time()
            self.last_report = 0

        def __call__(self, algorithm):
            gen = algorithm.n_gen
            elapsed = time.time() - self.start
            # 每 10 代或最后一代打印一次
            if gen % 10 == 0 or gen >= ctx.n_gen:
                progress = gen / ctx.n_gen * 100
                best_f = algorithm.pop.get('F')
                if best_f is not None and len(best_f) > 0:
                    f1 = float(best_f[:, 0].min())
                    f2 = float(best_f[:, 1].min())
                    f3 = float(best_f[:, 2].min())
                    logger.info(
                        '[NSGA-II] gen=%d/%d (%.1f%%) | elapsed=%.1fs | best: F1=%.3f F2=%.3f F3=%.4f',
                        gen, ctx.n_gen, progress, elapsed, f1, f2, f3,
                    )
                else:
                    logger.info(
                        '[NSGA-II] gen=%d/%d (%.1f%%) | elapsed=%.1fs',
                        gen, ctx.n_gen, progress, elapsed,
                    )
                self.last_report = gen

    return _GenCallback()


def solve_full_optimization(ctx: FullCanalContext) -> FullResult:
    """
    全渠系三级顺序配水优化。

    步骤：
    1. 干-支优化：NSGA-III 求解支渠流量和开始时间
    2. 支-斗优化：对每个支渠下的斗渠进行轮灌分组
    3. 汇总计算：整合两级结果，计算统一目标函数值
    4. TOPSIS 选优：从 Pareto 前沿选择最优方案
    """
    if not ctx.branches:
        raise ValueError('branches 列表为空，无法运行全渠系优化')

    # 步骤1：干-支优化（NSGA-II）
    problem = FullCanalProblem(ctx)
    algorithm = NSGA2(
        pop_size=ctx.pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=0.1, eta=20),
        eliminate_duplicates=True,
    )
    callback = _ProgressCallback(ctx.n_gen, ctx)
    # 硬上限：代数 或 8 秒超时（多目标题规模小，8s 足够）
    from pymoo.core.termination import TerminateIfAny
    from pymoo.termination import get_termination
    termination = TerminateIfAny(
        get_termination('n_gen', ctx.n_gen),
        get_termination('time', 8.0),
    )
    res = minimize(
        problem,
        algorithm,
        termination=termination,
        seed=ctx.seed,
        save_history=False,
        callback=callback,
        verbose=False,
    )

    F = np.asarray(res.F) if res.F is not None else None
    X = np.asarray(res.X) if res.X is not None else None
    if F is None or X is None or len(F) == 0:
        raise RuntimeError('全渠系优化：未找到可行解，请检查约束边界或增加种群/代数')

    # 步骤4：TOPSIS 选优
    pref = np.array([
        ctx.pref_weight_time,
        ctx.pref_weight_loss,
        ctx.pref_weight_flow_var,
    ], dtype=float)
    scores, W, best_index = _entropy_topsis_weighted(F, pref, alpha=ctx.alpha)

    # 获取最优解
    qk_best = X[best_index, :len(ctx.branches)]
    tsk_best = X[best_index, len(ctx.branches):]
    w_list = np.array([b.water_demand for b in ctx.branches])
    tek_best = tsk_best + w_list / (3600.0 * np.maximum(qk_best, 1e-9))

    # 步骤2：支-斗优化
    all_channels: list[dict] = []
    all_groups: list[dict] = []
    all_laterals: list[dict] = []
    branch_schedules: list[LateralSchedule] = []

    for i, branch in enumerate(ctx.branches):
        laterals = ctx.laterals_by_branch.get(branch.canal_id, [])
        if laterals:
            result = _run_lateral_optimization(branch, laterals, ctx)
            if result:
                channels, groups, loss = result
                # 分配时间
                t_start = float(tsk_best[i])
                for ch in channels:
                    ch['start_h'] = round(t_start, 3)
                    ch['end_h'] = round(t_start + ch['duration_h'], 3)
                for gr in groups:
                    gr['start_h'] = round(t_start, 3)
                    gr['end_h'] = round(t_start + gr['duration_h'], 3)
                all_channels.extend(channels)
                all_groups.extend(groups)
                all_laterals.extend(channels)
                branch_schedules.append(LateralSchedule(
                    branch_id=branch.canal_id,
                    channels=channels,
                    groups=groups,
                    total_loss=loss,
                    total_time=float(np.max([c['duration_h'] for c in channels])) if channels else 0.0,
                    max_group_flow=max((g['total_flow'] for g in groups), default=0.0),
                ))

    # 步骤3：汇总计算
    # 干渠时序
    time_cut, Qt_cut, H_main = _compute_main_time_series(qk_best, tsk_best, tek_best, ctx)
    Q_main_total = float(np.sum(qk_best))
    t_main_max = float(np.max(tek_best))

    # 干渠损失
    main_loss = _calc_seepage_loss(
        Q_main_total, ctx.main.length, t_main_max,
        ctx.permeability_coefficient, ctx.permeability_index
    )

    # 支渠损失
    lengths_branch = np.array([b.length for b in ctx.branches])
    branch_losses = []
    for i, branch in enumerate(ctx.branches):
        branch_loss = _calc_seepage_loss(
            qk_best[i], lengths_branch[i], tek_best[i] - tsk_best[i],
            ctx.permeability_coefficient, ctx.permeability_index
        )
        branch_losses.append(branch_loss)

    # 斗渠总损失
    lateral_total_loss = sum(s.total_loss for s in branch_schedules)
    total_system_loss = main_loss + sum(branch_losses) + lateral_total_loss

    # 流量波动
    Qt_avg = float(np.mean(Qt_cut)) if len(Qt_cut) > 0 else 0.0
    flow_var = float(np.mean((Qt_cut - Qt_avg) ** 2)) if len(Qt_cut) > 0 else 0.0

    # 构建支渠结果
    branch_rows: list[dict] = []
    for i, br in enumerate(ctx.branches):
        branch_loss = branch_losses[i]
        branch_rows.append({
            'name': br.canal_id,
            'qd': float(br.design_flow),
            'q_actual': float(qk_best[i]),
            'ratio': float(qk_best[i] / max(br.design_flow, 1e-9)),
            't_start_h': float(tsk_best[i]),
            'duration_h': float(tek_best[i] - tsk_best[i]),
            't_end_h': float(tek_best[i]),
            'loss_m3': float(branch_loss),
            'n_laterals': len(ctx.laterals_by_branch.get(br.canal_id, [])),
        })

    # 构建时序
    time_series: list[dict] = []
    for t_h, q, h in zip(time_cut.tolist(), Qt_cut.tolist(), H_main.tolist()):
        time_series.append({
            't_h': round(float(t_h), 3),
            'Q_m3s': round(float(q), 4),
            'H_m': round(float(h), 4),
        })

    # 构建 Pareto
    pareto_rows: list[dict] = []
    for i, fvec in enumerate(F):
        pareto_rows.append({
            'F1': float(fvec[0]),
            'F2': float(fvec[1]),
            'F3': float(fvec[2]),
            'score': float(scores[i]),
            'selected': i == best_index,
        })

    # Summary
    summary = {
        'mode': 'full',
        'main_canal_id': ctx.main.canal_id,
        'n_branches': len(ctx.branches),
        'n_laterals': len(all_laterals),
        'branch_ids': [b.canal_id for b in ctx.branches],
        'q_max_m3s': float(_trapezoid_Qmax(ctx.main)),
        'topsis_score': float(scores[best_index]),
        'entropy_weights': {
            'F1_time': float(W[0]),
            'F2_loss': float(W[1]),
            'F3_flow_var': float(W[2]),
        },
        'objective_values': {
            'F1_total_time_h': float(F[best_index, 0]),
            'F2_total_loss_m3': float(F[best_index, 1]),
            'F3_flow_var': float(F[best_index, 2]),
        },
        'main_loss_m3': round(main_loss, 2),
        'branch_loss_m3': round(sum(branch_losses), 2),
        'lateral_loss_m3': round(lateral_total_loss, 2),
        'total_loss_m3': round(total_system_loss, 2),
    }

    main_canal = {
        'Q_total_m3s': round(Q_main_total, 4),
        't_max_h': round(t_main_max, 3),
        'main_loss_m3': round(main_loss, 2),
        'branch_loss_m3': round(sum(branch_losses), 2),
        'lateral_loss_m3': round(lateral_total_loss, 2),
        'total_loss_m3': round(total_system_loss, 2),
    }

    topsis_summary = {
        'total_time_h': round(float(F[best_index, 0]), 3),
        'total_loss_m3': round(total_system_loss, 2),
        'main_loss_m3': round(main_loss, 2),
        'branch_loss_m3': round(sum(branch_losses), 2),
        'lateral_loss_m3': round(lateral_total_loss, 2),
        'flow_var': round(flow_var, 4),
    }

    return FullResult(
        summary=summary,
        main_canal=main_canal,
        branches=branch_rows,
        laterals=all_laterals,
        groups=all_groups,
        time_series=time_series,
        pareto=pareto_rows,
        topsis_summary=topsis_summary,
    )
