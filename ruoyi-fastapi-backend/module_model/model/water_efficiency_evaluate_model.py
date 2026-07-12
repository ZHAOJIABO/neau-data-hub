"""
灌区农业水效评价模型核心算法。

评价方法：熵权-TOPSIS 综合评价法。
对每个历史时段独立执行评价，保证各时段排名具有可比性。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from module_model.entity.vo.water_efficiency_evaluate_vo import (
    DEFAULT_GRADE_LABELS,
    DEFAULT_GRADE_THRESHOLDS,
    WaterEfficiencyEvaluateRequest,
    WaterEfficiencyIndicatorResultModel,
    WaterEfficiencyPeriodInputModel,
    WaterEfficiencyPeriodResultModel,
    WaterEfficiencyZonePeriodInputModel,
)


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _camelize(value: Any) -> Any:
    """递归将 dict 键由 snake_case 转为 camelCase，列表元素递归处理。"""
    if isinstance(value, dict):
        return {_to_camel(k): _camelize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_camelize(v) for v in value]
    return value


def _to_camel(name: str) -> str:
    """snake_case -> camelCase，简单实现：第一个片段保持小写，后续片段首字母大写。"""
    parts = name.split('_')
    return parts[0] + ''.join(p[:1].upper() + p[1:] for p in parts[1:] if p)


def _sanitize(obj: Any) -> Any:
    """将 numpy 标量转换为 Python 原生类型，NaN/Inf 替换为 None。"""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        obj = float(obj)
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def _normalize_weights(values: list[float], n: int) -> np.ndarray:
    """归一化权重向量，非法值自动降级为等权。"""
    weights = np.array(values if values else [1.0] * n, dtype=float)
    if len(weights) != n:
        weights = np.ones(n, dtype=float)
    weights = np.maximum(weights, 0.0)
    total = float(np.sum(weights))
    return weights / total if total > 1e-12 else np.full(n, 1.0 / n)


# ---------------------------------------------------------------------------
# 指标定义
# ---------------------------------------------------------------------------

# 指标 ID 列表（固定顺序，与矩阵列对应）
INDICATOR_IDS: list[str] = [
    'iwue',
    'water_productivity_kg_m3',
    'benefit_yuan_per_m3',
    'irrigation_reliability',
    'field_efficiency',
    'surface_water_utilization',
    'groundwater_utilization',
    'groundwater_dependency',
]

# 指标元数据：ID -> (名称, 是否效益型)
# 效益型（True）：标准化后直接用，越大越好
# 成本型（False）：标准化后用 1 - norm，越大越好
INDICATOR_META: dict[str, tuple[str, bool]] = {
    'iwue': ('灌溉水利用系数 IWUE', True),
    'water_productivity_kg_m3': ('水分生产率 WUE', True),
    'benefit_yuan_per_m3': ('单方水净效益 BEC', True),
    'irrigation_reliability': ('灌溉保证率 IRS', True),
    'field_efficiency': ('田间水利用系数 FE', True),
    'surface_water_utilization': ('地表水利用率 SUR', True),
    'groundwater_utilization': ('地下水利用率 GWR', True),
    'groundwater_dependency': ('地下水依赖度 GWI', False),  # 越小越好
}


def _extract_indicator_values(zone: WaterEfficiencyZonePeriodInputModel) -> np.ndarray:
    """将分区的原始指标提取为固定顺序的 numpy 向量。"""
    values = []
    for iid in INDICATOR_IDS:
        values.append(getattr(zone, iid, 0.0))
    return np.array(values, dtype=float)


# ---------------------------------------------------------------------------
# 核心算法：熵权-TOPSIS
# ---------------------------------------------------------------------------

def _entropy_topsis(
    metrics: np.ndarray,
    pref_weights: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    对给定指标矩阵执行熵权-TOPSIS 评价。

    Parameters
    ----------
    metrics : np.ndarray, shape = (n_zones, n_indicators)
        原始指标矩阵，每行一个分区，每列一个指标。
    pref_weights : np.ndarray, shape = (n_indicators,)
        用户主观权重（预权重），已归一化。
    alpha : float
        混合系数，0=纯熵权，1=纯主观权重。

    Returns
    -------
    scores : np.ndarray, shape = (n_zones,)
        每个分区的 TOPSIS 相对贴近度（越大越好）。
    weights : np.ndarray, shape = (n_indicators,)
        最终混合权重。
    entropy_weights : np.ndarray, shape = (n_indicators,)
        熵权法客观权重。
    norm_mat : np.ndarray, shape = (n_zones, n_indicators)
        标准化后的指标矩阵（已统一为越大越好方向）。
    """
    n_zones, n_ind = metrics.shape

    # --- Step 1: 极差标准化（统一为越大越好） ---
    col_min = metrics.min(axis=0)
    col_max = metrics.max(axis=0)
    col_range = col_max - col_min

    # 避免除零：range < eps 时该列所有值相同，标准化后全为 0.5
    eps = 1e-12
    safe_range = np.where(col_range < eps, 1.0, col_range)

    norm_mat = (metrics - col_min) / safe_range

    # 对成本型指标取反（地下水依赖度：越小越好）
    cost_ids = [iid for iid, meta in INDICATOR_META.items() if not meta[1]]
    cost_indices = [INDICATOR_IDS.index(iid) for iid in cost_ids]
    norm_mat[:, cost_indices] = 1.0 - norm_mat[:, cost_indices]

    # --- Step 2: 熵权法计算客观权重 ---
    # 归一化概率矩阵
    p = norm_mat / (np.sum(norm_mat, axis=0, keepdims=True) + eps)

    # 熵值
    entropy_raw = -np.sum(p * np.log(p + eps), axis=0) / np.log(max(n_zones, 2))
    # 当某列全部相同时，p 全等，熵值最大(1)，多样性最小，熵权为 0
    entropy = np.where(np.isfinite(entropy_raw), entropy_raw, 1.0)

    # 信息熵冗余度 -> 权重
    diversity = 1.0 - entropy
    if float(np.sum(diversity)) <= eps:
        entropy_weights = np.full(n_ind, 1.0 / n_ind)
    else:
        entropy_weights = diversity / np.sum(diversity)

    # --- Step 3: 混合赋权 ---
    weights = alpha * pref_weights + (1.0 - alpha) * entropy_weights
    weights = weights / np.sum(weights)

    # --- Step 4: 加权标准化矩阵 ---
    weighted_norm = norm_mat * weights

    # --- Step 5: TOPSIS 计算贴近度 ---
    # 正理想解 A+：每列最大值（越大越好）
    # 负理想解 A-：每列最小值
    ideal = weighted_norm.max(axis=0)
    nadir = weighted_norm.min(axis=0)

    d_pos = np.sqrt(np.sum((weighted_norm - ideal) ** 2, axis=1))
    d_neg = np.sqrt(np.sum((weighted_norm - nadir) ** 2, axis=1))

    scores = d_neg / (d_pos + d_neg + eps)

    return scores, weights, entropy_weights, norm_mat


# ---------------------------------------------------------------------------
# 分级
# ---------------------------------------------------------------------------

def _assign_grade(score: float, thresholds: dict[str, float]) -> str:
    """根据得分和阈值确定等级。"""
    thresholds = thresholds or DEFAULT_GRADE_THRESHOLDS
    if score >= thresholds.get('excellent', 0.8):
        return DEFAULT_GRADE_LABELS.get('excellent', '优秀')
    if score >= thresholds.get('good', 0.6):
        return DEFAULT_GRADE_LABELS.get('good', '良好')
    if score >= thresholds.get('qualified', 0.4):
        return DEFAULT_GRADE_LABELS.get('qualified', '合格')
    return DEFAULT_GRADE_LABELS.get('unqualified', '不合格')


# ---------------------------------------------------------------------------
# 主体：单时段评价
# ---------------------------------------------------------------------------

def evaluate_single_period(
    period: WaterEfficiencyPeriodInputModel,
    pref_weights: np.ndarray | None,
    alpha: float,
    grade_thresholds: dict[str, float] | None,
) -> WaterEfficiencyPeriodResultModel:
    """
    对单个历史时段执行水效综合评价。

    Parameters
    ----------
    period : WaterEfficiencyPeriodInputModel
        时段输入数据。
    pref_weights : np.ndarray or None
        用户主观权重（已归一化），None 时完全使用熵权。
    alpha : float
        混合系数。
    grade_thresholds : dict or None
        分级阈值。

    Returns
    -------
    WaterEfficiencyPeriodResultModel
    """
    n_zones = len(period.zones)
    n_ind = len(INDICATOR_IDS)

    # --- 构建指标矩阵 ---
    metrics = np.zeros((n_zones, n_ind), dtype=float)
    original_values: list[dict[str, float]] = []
    for i, zone in enumerate(period.zones):
        metrics[i, :] = _extract_indicator_values(zone)
        row_dict: dict[str, float] = {}
        for iid in INDICATOR_IDS:
            row_dict[iid] = float(getattr(zone, iid, 0.0))
        original_values.append(row_dict)

    # --- 预处理权重 ---
    if pref_weights is not None:
        pref_weights = _normalize_weights(pref_weights.tolist(), n_ind)
    else:
        pref_weights = np.full(n_ind, 1.0 / n_ind)

    # --- 熵权-TOPSIS 评价 ---
    scores, final_weights, entropy_w, norm_mat = _entropy_topsis(metrics, pref_weights, alpha)

    # --- 排名（降序，1=最优）---
    ranks = np.argsort(np.argsort(-scores)) + 1  # 两次 argsort 取得降序排名，1=最高分

    # --- 构建正负理想解（原始标准化矩阵，非加权）---
    ideal_raw = metrics.max(axis=0)
    nadir_raw = metrics.min(axis=0)
    ideal_dict: dict[str, float] = {}
    nadir_dict: dict[str, float] = {}
    for idx, iid in enumerate(INDICATOR_IDS):
        ideal_dict[iid] = float(ideal_raw[idx])
        nadir_dict[iid] = float(nadir_raw[idx])

    # --- 组装各分区结果 ---
    zone_results: list[WaterEfficiencyIndicatorResultModel] = []
    grade_thresholds = grade_thresholds or DEFAULT_GRADE_THRESHOLDS

    # 标准化矩阵（统一越大越好）需要在成本型指标处反转后取每列极值
    # _entropy_topsis 已处理 norm_mat，此处 norm_mat 已是正向化后的
    norm_col_min = norm_mat.min(axis=0)
    norm_col_max = norm_mat.max(axis=0)

    for i, zone in enumerate(period.zones):
        # 标准化值（统一越大越好方向）
        norm_dict: dict[str, float] = {}
        for idx, iid in enumerate(INDICATOR_IDS):
            norm_dict[iid] = float(norm_mat[i, idx])

        # 加权值
        weighted_dict: dict[str, float] = {}
        for idx, iid in enumerate(INDICATOR_IDS):
            weighted_dict[iid] = float(norm_mat[i, idx] * final_weights[idx])

        score = float(scores[i])
        rank = int(ranks[i])
        grade = _assign_grade(score, grade_thresholds)

        zone_results.append(
            WaterEfficiencyIndicatorResultModel(
                zone_id=zone.zone_id,
                zone_name=zone.zone_name or zone.zone_id,
                original=original_values[i],
                normalized=norm_dict,
                weighted=weighted_dict,
                score=round(score, 6),
                rank=rank,
                grade=grade,
            )
        )

    # 按 rank 升序排列
    zone_results.sort(key=lambda x: x.rank)

    # --- 时段统计 ---
    score_list = scores.tolist()
    max_idx = int(np.argmax(scores))
    min_idx = int(np.argmin(scores))
    period_summary: dict[str, Any] = {
        'n_zones': n_zones,
        'mean_score': round(float(np.mean(scores)), 6),
        'std_score': round(float(np.std(scores)), 6),
        'max_score': round(float(np.max(scores)), 6),
        'min_score': round(float(np.min(scores)), 6),
        'best_zone_id': period.zones[max_idx].zone_id,
        'best_zone_name': period.zones[max_idx].zone_name or period.zones[max_idx].zone_id,
        'worst_zone_id': period.zones[min_idx].zone_id,
        'worst_zone_name': period.zones[min_idx].zone_name or period.zones[min_idx].zone_id,
        'grade_distribution': {
            'excellent': int(np.sum(scores >= grade_thresholds.get('excellent', 0.8))),
            'good': int(np.sum((scores >= grade_thresholds.get('good', 0.6)) & (scores < grade_thresholds.get('excellent', 0.8)))),
            'qualified': int(np.sum((scores >= grade_thresholds.get('qualified', 0.4)) & (scores < grade_thresholds.get('good', 0.6)))),
            'unqualified': int(np.sum(scores < grade_thresholds.get('qualified', 0.4))),
        },
    }

    return WaterEfficiencyPeriodResultModel(
        period_id=period.period_id,
        period_label=period.period_label or period.period_id,
        n_zones=n_zones,
        zone_results=zone_results,
        topsis_ideal=ideal_dict,
        topsis_negative=nadir_dict,
        indicator_weights={iid: round(float(final_weights[idx]), 6) for idx, iid in enumerate(INDICATOR_IDS)},
        entropy_weights={iid: round(float(entropy_w[idx]), 6) for idx, iid in enumerate(INDICATOR_IDS)},
        summary=period_summary,
    )


# ---------------------------------------------------------------------------
# 主体：多时段评价入口
# ---------------------------------------------------------------------------

def evaluate_water_efficiency(
    request: WaterEfficiencyEvaluateRequest,
) -> dict[str, Any]:
    """
    对多时段历史数据执行水效综合评价。

    Parameters
    ----------
    request : WaterEfficiencyEvaluateRequest
        评价请求。

    Returns
    -------
    dict
        评价结果，兼容 JSON 序列化。
    """
    n_ind = len(INDICATOR_IDS)

    # 预处理用户主观权重
    pref_weights: np.ndarray | None = None
    if request.indicator_weights:
        raw_weights: list[float] = []
        for iid in INDICATOR_IDS:
            raw_weights.append(request.indicator_weights.get(iid, 1.0))
        pref_weights = _normalize_weights(raw_weights, n_ind)

    # 各时段独立评价
    period_results: list[WaterEfficiencyPeriodResultModel] = []
    for period in request.periods:
        result = evaluate_single_period(
            period=period,
            pref_weights=pref_weights,
            alpha=request.alpha,
            grade_thresholds=request.grade_thresholds,
        )
        period_results.append(result)

    # 按 period_id 升序排列
    period_results.sort(key=lambda x: x.period_id)

    # 总体统计
    all_zones_count = sum(r.n_zones for r in period_results)
    total_excellent = sum(r.summary.get('grade_distribution', {}).get('excellent', 0) for r in period_results)
    total_good = sum(r.summary.get('grade_distribution', {}).get('good', 0) for r in period_results)
    total_qualified = sum(r.summary.get('grade_distribution', {}).get('qualified', 0) for r in period_results)
    total_unqualified = sum(r.summary.get('grade_distribution', {}).get('unqualified', 0) for r in period_results)

    overall_summary: dict[str, Any] = {
        'n_periods': len(period_results),
        'total_zones': all_zones_count,
        'period_ids': [p.period_id for p in request.periods],
        'grade_distribution': {
            'excellent': total_excellent,
            'good': total_good,
            'qualified': total_qualified,
            'unqualified': total_unqualified,
        },
        'alpha': request.alpha,
        'use_preference_weights': pref_weights is not None,
    }

    return _sanitize(_camelize({
        'summary': overall_summary,
        'period_results': [r.model_dump(by_alias=True) for r in period_results],
        'indicator_info': {
            iid: meta[0] for iid, meta in INDICATOR_META.items()
        },
    }))
