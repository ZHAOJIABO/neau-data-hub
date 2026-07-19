from typing import Annotated

from fastapi import Body, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from common.vo import PageResponseModel
from module_model.entity.vo.water_fertilizer_vo import (
    WaterFertilizerOptimizeRequest,
    WaterFertilizerRegulationPageQueryModel,
)
from module_model.service.water_fertilizer_service import WaterFertilizerService
from utils.log_util import logger
from utils.response_util import ResponseUtil

water_fertilizer_controller = APIRouterPro(
    prefix='/api/v1/irrigation/water-fertilizer',
    order_num=27,
    tags=['水肥调控模型'],
    dependencies=[irrigation_api_key_dependency()],
)


@water_fertilizer_controller.get(
    '/regulation/summary',
    summary='获取水肥调控时序数据日期范围',
    response_model=None,
)
async def get_water_fertilizer_regulation_summary(
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    data = await WaterFertilizerService.get_regulation_summary_services(query_db)
    return ResponseUtil.success(data=data)


@water_fertilizer_controller.get(
    '/regulation/list',
    summary='获取水肥调控时序数据列表',
    response_model=PageResponseModel,
)
async def get_water_fertilizer_regulation_list(
    query: Annotated[WaterFertilizerRegulationPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WaterFertilizerService.get_regulation_list_services(query_db, query, is_page=True)
    logger.info(
        'water-fertilizer regulation list request: start={}, end={}, page={}, size={}',
        query.start_date,
        query.end_date,
        query.page_num,
        query.page_size,
    )
    return ResponseUtil.success(model_content=result)


@water_fertilizer_controller.post(
    '/optimize',
    summary='水肥调控多目标优化（NSGA-III）：逐日灌溉量与施氮量推荐',
    response_model=None,
)
async def optimize_water_fertilizer(
    payload: Annotated[
        WaterFertilizerOptimizeRequest,
        Body(description='水肥调控 NSGA-III 优化 JSON 请求体'),
    ],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    logger.info(
        'water-fertilizer optimize request: range={}~{}, pop={}, gen={}',
        payload.start_date,
        payload.end_date,
        payload.population_size,
        payload.generations,
    )
    data = await WaterFertilizerService.run_optimize_services(query_db, payload)
    return ResponseUtil.success(data=data)
