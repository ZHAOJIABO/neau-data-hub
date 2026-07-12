"""
灌区农业水效评价服务。

对灌区各分区历史用水效率进行综合评价，支持多时段横向对比。
评价方法：熵权-TOPSIS 综合评价法。
"""

from __future__ import annotations

from typing import Any

from exceptions.exception import ServiceException
from module_model.entity.vo.water_efficiency_evaluate_vo import (
    WaterEfficiencyEvaluateRequest,
    WaterEfficiencyPeriodInputModel,
)
from module_model.model.water_efficiency_evaluate_model import evaluate_water_efficiency


class WaterEfficiencyEvaluateService:
    """灌区农业水效评价：熵权-TOPSIS 多指标综合评价，支持多时段对比。"""

    @classmethod
    def run_evaluate(
        cls,
        periods: list[dict[str, Any]],
        indicator_weights: dict[str, float] | None = None,
        alpha: float = 0.5,
        grade_thresholds: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        执行水效综合评价。

        Parameters
        ----------
        periods : list[dict]
            时段数据列表，每个 dict 对应一个时段的结构化数据。
        indicator_weights : dict or None
            用户主观权重，键为指标英文缩写，值为 0~1 之间的权重。
        alpha : float
            先验权重与熵权混合系数，0=纯熵权，1=纯主观权重。
        grade_thresholds : dict or None
            分级阈值，如 {"excellent": 0.8, "good": 0.6, "qualified": 0.4}。

        Returns
        -------
        dict
            评价结果字典，可直接序列化为 JSON 响应。
        """
        try:
            period_models = [
                WaterEfficiencyPeriodInputModel.model_validate(p)
                for p in periods
            ]
            request = WaterEfficiencyEvaluateRequest(
                periods=period_models,
                indicator_weights=indicator_weights,
                alpha=alpha,
                grade_thresholds=grade_thresholds,
            )
            return evaluate_water_efficiency(request)
        except (KeyError, ValueError, TypeError) as exc:
            raise ServiceException(message=f'农业水效评价参数错误: {exc}') from exc
