"""
灌区分区数据管理接口（农业数据-分区数据）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body, File, Path, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import CrudResponseModel, DataResponseModel, PageResponseModel, ResponseBaseModel
from module_agriculture.entity.vo.zone_vo import (
    DEFAULT_IRRIGATION_AREA_CODE,
    IrrigationZoneCreateModel,
    IrrigationZoneModel,
    IrrigationZonePageQueryModel,
    IrrigationZoneUpdateModel,
)
from module_agriculture.service.zone_service import IrrigationZoneService
from utils.log_util import logger
from utils.response_util import ResponseUtil

zone_controller = APIRouterPro(
    prefix='/agriculture/zone',
    order_num=24,
    tags=['农业数据-分区数据'],
    dependencies=[PreAuthDependency()],
)


@zone_controller.get('/list', summary='灌区分区分页列表', response_model=PageResponseModel)
async def get_zone_list(
    request: Request,
    query: Annotated[IrrigationZonePageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await IrrigationZoneService.get_zone_list_services(query_db, query, is_page=True)
    logger.info('获取分区数据列表成功')
    return ResponseUtil.success(model_content=result)


@zone_controller.get('/areas', summary='灌区选项列表', response_model=DataResponseModel[list])
async def get_irrigation_areas(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    data = await IrrigationZoneService.list_area_options_services(query_db)
    return ResponseUtil.success(data=data)


@zone_controller.get('/enabled', summary='启用分区列表', response_model=DataResponseModel[list])
async def get_enabled_zones(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    irrigation_area_code: Annotated[
        str, Query(alias='irrigationAreaCode', description='灌区编码')
    ] = DEFAULT_IRRIGATION_AREA_CODE,
) -> Response:
    data = await IrrigationZoneService.list_enabled_services(query_db, irrigation_area_code)
    return ResponseUtil.success(data=data)


@zone_controller.get('/{zone_id}', summary='分区详情', response_model=DataResponseModel[IrrigationZoneModel])
async def get_zone_detail(
    request: Request,
    zone_id: Annotated[str, Path(description='分区编号')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    data = await IrrigationZoneService.get_zone_detail_services(query_db, zone_id)
    logger.info(f'获取分区 {zone_id} 详情成功')
    return ResponseUtil.success(data=data)


@zone_controller.post('', summary='新增分区', response_model=ResponseBaseModel)
async def create_zone(
    request: Request,
    payload: Annotated[IrrigationZoneCreateModel, Body(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await IrrigationZoneService.create_zone_services(query_db, payload)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@zone_controller.put('', summary='更新分区', response_model=ResponseBaseModel)
async def update_zone(
    request: Request,
    payload: Annotated[IrrigationZoneUpdateModel, Body(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await IrrigationZoneService.update_zone_services(query_db, payload)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@zone_controller.delete('/{ids}', summary='删除分区', response_model=ResponseBaseModel)
async def delete_zone(
    request: Request,
    ids: Annotated[str, Path(description='分区编号列表，逗号分隔')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await IrrigationZoneService.delete_zone_services(query_db, ids)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@zone_controller.post('/import', summary='从 CSV 导入分区数据', response_model=CrudResponseModel)
async def import_zone_csv(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await IrrigationZoneService.import_from_csv_services(query_db, file)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message, data=result.result)
