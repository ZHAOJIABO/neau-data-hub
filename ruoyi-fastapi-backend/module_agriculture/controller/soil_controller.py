from typing import Annotated

from fastapi import Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import PageResponseModel
from module_agriculture.entity.vo.soil_vo import (
    SoilGroundTempPageQueryModel,
    SoilLayerStatsPageQueryModel,
    SoilParameterPageQueryModel,
    SoilSensorPageQueryModel,
    SoilThicknessPageQueryModel,
)
from module_agriculture.service.soil_service import SoilService
from utils.log_util import logger
from utils.response_util import ResponseUtil

soil_controller = APIRouterPro(
    prefix='/agriculture/soil', order_num=21, tags=['农业数据-土壤数据'], dependencies=[PreAuthDependency()]
)


@soil_controller.get(
    '/sensor/list',
    summary='获取传感器监测数据列表',
    description='用于获取传感器监测数据的分页列表',
    response_model=PageResponseModel,
)
async def get_soil_sensor_list(
    request: Request,
    query: Annotated[SoilSensorPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await SoilService.get_sensor_list_services(query_db, query, is_page=True)
    logger.info('获取传感器监测数据成功')
    return ResponseUtil.success(model_content=result)


@soil_controller.get(
    '/parameter/list',
    summary='获取土壤参数数据列表',
    description='用于获取土壤水文参数的分页列表',
    response_model=PageResponseModel,
)
async def get_soil_parameter_list(
    request: Request,
    query: Annotated[SoilParameterPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await SoilService.get_parameter_list_services(query_db, query, is_page=True)
    logger.info('获取土壤参数数据成功')
    return ResponseUtil.success(model_content=result)


@soil_controller.get(
    '/ground-temp/list',
    summary='获取地温数据列表',
    description='用于获取分层地温数据的分页列表',
    response_model=PageResponseModel,
)
async def get_soil_ground_temp_list(
    request: Request,
    query: Annotated[SoilGroundTempPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await SoilService.get_ground_temp_list_services(query_db, query, is_page=True)
    logger.info('获取地温数据成功')
    return ResponseUtil.success(model_content=result)


@soil_controller.get(
    '/thickness/list',
    summary='获取黑土厚度数据列表',
    description='用于获取监测点黑土厚度的分页列表',
    response_model=PageResponseModel,
)
async def get_soil_thickness_list(
    request: Request,
    query: Annotated[SoilThicknessPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await SoilService.get_thickness_list_services(query_db, query, is_page=True)
    logger.info('获取黑土厚度数据成功')
    return ResponseUtil.success(model_content=result)


@soil_controller.get(
    '/layer-stats/list',
    summary='获取分层统计数据列表',
    description='用于获取各土层含水量统计的分页列表',
    response_model=PageResponseModel,
)
async def get_soil_layer_stats_list(
    request: Request,
    query: Annotated[SoilLayerStatsPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await SoilService.get_layer_stats_list_services(query_db, query, is_page=True)
    logger.info('获取分层统计数据成功')
    return ResponseUtil.success(model_content=result)
