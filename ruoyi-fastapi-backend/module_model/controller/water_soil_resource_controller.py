"""
灌区水土资源多目标优化配置接口。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body
from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_model.entity.vo.water_soil_resource_vo import WaterSoilResourceOptimizeRequest
from module_model.service.water_soil_resource_service import WaterSoilResourceService
from utils.log_util import logger
from utils.response_util import ResponseUtil

water_soil_resource_controller = APIRouterPro(
    prefix='/api/v1/irrigation/water-soil-resource',
    order_num=25,
    tags=['灌区水土资源优化配置'],
    dependencies=[irrigation_api_key_dependency()],
)


@water_soil_resource_controller.post(
    '/optimize',
    summary='灌区水土资源多目标优化配置（NSGA-II）：14分区作物面积、水量与施氮量',
    response_model=None,
)
async def optimize_water_soil_resource(
    payload: Annotated[
        WaterSoilResourceOptimizeRequest,
        Body(description='灌区水土资源多目标优化配置 JSON 请求体'),
    ],
) -> JSONResponse:
    """优化不同分区、不同作物的种植面积、地表水量、地下水量和施氮量。"""
    logger.info(
        'water-soil-resource optimize request: zones=%s, crops=%s, pop=%s, gen=%s, seed=%s',
        len(payload.zones),
        len(payload.crops),
        payload.pop_size,
        payload.n_gen,
        payload.seed,
    )
    data = await WaterSoilResourceService.run_optimize(
        zones=[item.model_dump() for item in payload.zones],
        crops=[item.model_dump() for item in payload.crops],
        stages=[item.model_dump() for item in payload.stages],
        total_water_available=payload.total_water_available,
        pop_size=payload.pop_size,
        n_gen=payload.n_gen,
        seed=payload.seed,
        pref_weight_benefit=payload.pref_weight_benefit,
        pref_weight_fairness=payload.pref_weight_fairness,
        pref_weight_efficiency=payload.pref_weight_efficiency,
        pref_weight_nitrogen_efficiency=payload.pref_weight_nitrogen_efficiency,
        alpha=payload.alpha,
    )
    return ResponseUtil.success(data=data)
