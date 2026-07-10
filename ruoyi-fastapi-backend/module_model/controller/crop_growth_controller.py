from typing import Annotated

from fastapi import Body, Response

from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from module_model.entity.vo.crop_growth_vo import RiceGrowthSimulationRequest
from module_model.service.crop_growth_service import CropGrowthService
from utils.log_util import logger
from module_model.model.pcse_growth_util import CropGrowthSimulationError
from utils.response_util import ResponseUtil

crop_growth_controller = APIRouterPro(
    prefix='/agriculture/crop-growth',
    order_num=25,
    tags=['模型平台-作物生长模拟'],
    dependencies=[PreAuthDependency()],
)


@crop_growth_controller.post(
    '/rice/simulate',
    summary='水稻逐日作物生长模拟',
    description='基于 PCSE/WOFOST 与 NASA POWER 气象数据模拟水稻每日生长指标',
    response_model=None,
)
async def simulate_rice_growth(
    payload: Annotated[RiceGrowthSimulationRequest, Body(description='水稻作物生长模拟参数')],
) -> Response:
    try:
        result = await CropGrowthService.simulate_rice_growth(payload)
        logger.info(
            '水稻作物生长模拟完成: lat={}, lon={}, days={}',
            payload.latitude,
            payload.longitude,
            result.summary.simulation_days,
        )
        return ResponseUtil.success(data=result.model_dump(by_alias=True))
    except CropGrowthSimulationError as exc:
        logger.warning('水稻作物生长模拟失败: {}', exc)
        return ResponseUtil.failure(msg=str(exc))
    except Exception as exc:
        logger.exception('水稻作物生长模拟接口异常: {}', exc)
        return ResponseUtil.error(msg=f'水稻作物生长模拟接口异常: {exc}')
