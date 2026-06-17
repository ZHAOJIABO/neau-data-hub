"""
渠系数据管理接口（农业数据-渠系数据）。

路由前缀：/agriculture/canal
鉴权：登录用户（PreAuthDependency）
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body, File, Path, Query, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import CrudResponseModel, DataResponseModel, PageResponseModel, ResponseBaseModel
from module_agriculture.entity.vo.canal_vo import (
    CanalBaseCreateModel,
    CanalBaseModel,
    CanalBasePageQueryModel,
    CanalBaseUpdateModel,
)
from module_agriculture.service.canal_service import CanalService
from utils.log_util import logger
from utils.response_util import ResponseUtil

canal_controller = APIRouterPro(
    prefix='/agriculture/canal',
    order_num=25,
    tags=['农业数据-渠系数据'],
    dependencies=[PreAuthDependency()],
)


@canal_controller.get(
    '/list',
    summary='渠系基础数据分页列表',
    description='按渠段编号 / 名称 / 级别查询渠系基础数据',
    response_model=PageResponseModel,
)
async def get_canal_list(
    request: Request,
    query: Annotated[CanalBasePageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await CanalService.get_canal_list_services(query_db, query, is_page=True)
    logger.info('获取渠系数据列表成功')
    return ResponseUtil.success(model_content=result)


@canal_controller.get(
    '/topology',
    summary='渠系拓扑（节点 / 边 / 根）',
    description='返回 roots / nodes / edges 结构，供前端拓扑图渲染',
    response_model=DataResponseModel[dict],
)
async def get_canal_topology(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    data = await CanalService.get_topology_services(query_db)
    return ResponseUtil.success(data=data)


@canal_controller.get(
    '/{canal_id}',
    summary='渠系基础数据详情',
    response_model=DataResponseModel[CanalBaseModel],
)
async def get_canal_detail(
    request: Request,
    canal_id: Annotated[str, Path(description='渠段编号')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    data = await CanalService.get_canal_detail_services(query_db, canal_id)
    logger.info(f'获取渠段 {canal_id} 详情成功')
    return ResponseUtil.success(data=data)


@canal_controller.post(
    '',
    summary='新增渠系基础数据',
    response_model=ResponseBaseModel,
)
async def create_canal(
    request: Request,
    payload: Annotated[CanalBaseCreateModel, Body(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await CanalService.create_canal_services(query_db, payload)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@canal_controller.put(
    '',
    summary='更新渠系基础数据',
    response_model=ResponseBaseModel,
)
async def update_canal(
    request: Request,
    payload: Annotated[CanalBaseUpdateModel, Body(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await CanalService.update_canal_services(query_db, payload)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@canal_controller.delete(
    '/{ids}',
    summary='批量删除渠系基础数据',
    description='按业务主键 canal_id 批量删除，逗号分隔',
    response_model=ResponseBaseModel,
)
async def delete_canal(
    request: Request,
    ids: Annotated[str, Path(description='渠段编号列表，逗号分隔')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await CanalService.delete_canal_services(query_db, ids)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@canal_controller.post(
    '/import',
    summary='从 CSV 导入渠系数据',
    description='上传渠系 CSV 文件，按 canal_id upsert',
    response_model=CrudResponseModel,
)
async def import_canal_csv(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await CanalService.import_from_csv_services(query_db, file)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message, data=result.result)
