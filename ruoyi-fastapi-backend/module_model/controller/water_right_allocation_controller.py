"""
灌区初始水权分配 + 水权交易市场博弈接口。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body
from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_model.entity.vo.water_right_allocation_vo import WaterRightAllocationRequest
from module_model.service.water_right_allocation_service import WaterRightAllocationService
from utils.log_util import logger
from utils.response_util import ResponseUtil

water_right_allocation_controller = APIRouterPro(
    prefix='/api/v1/irrigation/water-right-allocation',
    order_num=26,
    tags=['灌区水权分配与市场博弈'],
    dependencies=[irrigation_api_key_dependency()],
)


@water_right_allocation_controller.post(
    '/solve',
    summary='灌区初始水权分配 + Stackelberg 博弈 + 拍卖 LP 出清',
    response_model=None,
)
async def solve_water_right_allocation(
    payload: Annotated[
        WaterRightAllocationRequest,
        Body(description='水权分配与市场博弈 JSON 请求体'),
    ],
) -> JSONResponse:
    """按面积均分初始水权，下层通过拍卖 LP 全局最优出清。"""
    logger.info(
        'water-right-allocation solve request: zones=%s, crops=%s, total_water=%s',
        len(payload.zones),
        len(payload.crops),
        payload.market.initial_total_water_m3,
    )
    market_dict = payload.market.model_dump(by_alias=False)
    data = await WaterRightAllocationService.run_allocation(
        zones=[item.model_dump(by_alias=False) for item in payload.zones],
        crops=[item.model_dump(by_alias=False) for item in payload.crops],
        market=market_dict,
    )
    return ResponseUtil.success(data=data)