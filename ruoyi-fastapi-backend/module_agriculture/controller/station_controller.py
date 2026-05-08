from typing import Annotated

from fastapi import Path, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_agriculture.entity.vo.station_vo import DeleteStationModel, StationModel, StationPageQueryModel
from module_agriculture.service.station_service import StationService
from utils.log_util import logger
from utils.response_util import ResponseUtil

station_controller = APIRouterPro(
    prefix='/agriculture/station', order_num=23, tags=['农业数据-站点管理'], dependencies=[PreAuthDependency()]
)


@station_controller.get(
    '/list',
    summary='获取站点分页列表',
    description='用于获取监测站点的分页列表',
    response_model=PageResponseModel,
)
async def get_station_list(
    request: Request,
    query: Annotated[StationPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await StationService.get_station_list_services(query_db, query, is_page=True)
    logger.info('获取站点列表成功')
    return ResponseUtil.success(model_content=result)


@station_controller.get(
    '/{station_id}',
    summary='获取站点详情',
    description='用于获取指定站点的详细信息',
    response_model=DataResponseModel[StationModel],
)
async def get_station_detail(
    request: Request,
    station_id: Annotated[int, Path(description='站点ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await StationService.station_detail_services(query_db, station_id)
    logger.info(f'获取站点{station_id}详情成功')
    return ResponseUtil.success(data=result)


@station_controller.post(
    '',
    summary='新增站点',
    description='用于新增监测站点',
    response_model=ResponseBaseModel,
)
async def add_station(
    request: Request,
    station: StationModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await StationService.add_station_services(query_db, station)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@station_controller.put(
    '',
    summary='编辑站点',
    description='用于编辑监测站点',
    response_model=ResponseBaseModel,
)
async def edit_station(
    request: Request,
    station: StationModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await StationService.edit_station_services(query_db, station)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@station_controller.delete(
    '/{ids}',
    summary='删除站点',
    description='用于删除监测站点',
    response_model=ResponseBaseModel,
)
async def delete_station(
    request: Request,
    ids: Annotated[str, Path(description='需要删除的站点ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await StationService.delete_station_services(query_db, ids)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)
