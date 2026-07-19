"""
灌区农业水效评价接口。

支持多时段历史数据横向对比，采用熵权-TOPSIS 法综合评价各分区用水效率。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_agriculture.service.zone_service import IrrigationZoneService
from module_model.entity.vo.water_efficiency_evaluate_vo import WaterEfficiencyEvaluateRequest
from module_model.service.water_efficiency_evaluate_service import WaterEfficiencyEvaluateService
from utils.log_util import logger
from utils.response_util import ResponseUtil

water_efficiency_evaluate_controller = APIRouterPro(
    prefix='/api/v1/irrigation/water-efficiency',
    order_num=26,
    tags=['灌区农业水效评价'],
    dependencies=[irrigation_api_key_dependency()],
)


@water_efficiency_evaluate_controller.post(
    '/evaluate',
    summary='灌区农业水效综合评价（熵权-TOPSIS，支持多时段对比）',
    response_model=None,
)
async def evaluate_water_efficiency(
    payload: Annotated[
        WaterEfficiencyEvaluateRequest,
        Body(description='灌区农业水效评价 JSON 请求体'),
    ],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> JSONResponse:
    """
    对灌区各分区历史用水效率进行综合评价，支持多时段横向对比。

    评价方法：熵权-TOPSIS 综合评价法。
    - 各时段独立执行评价，保证排名可比性
    - 权重由熵权法定权，可选混入用户主观权重
    - 输出各分区得分、排名、等级及详细指标
    """
    logger.info(
        'water-efficiency evaluate request: periods=%s, n_zones=%s, alpha=%s',
        len(payload.periods),
        sum(len(p.zones) for p in payload.periods),
        payload.alpha,
    )

    zone_names = await IrrigationZoneService.zone_name_map(query_db, payload.irrigation_area_code)
    periods = []
    for period in payload.periods:
        period_data = period.model_dump()
        for zone in period_data['zones']:
            if not zone.get('zone_name') and zone.get('zone_id') in zone_names:
                zone['zone_name'] = zone_names[zone['zone_id']]
        periods.append(period_data)

    data = WaterEfficiencyEvaluateService.run_evaluate(
        periods=periods,
        indicator_weights=payload.indicator_weights,
        alpha=payload.alpha,
        grade_thresholds=payload.grade_thresholds,
    )
    return ResponseUtil.success(data=data)
