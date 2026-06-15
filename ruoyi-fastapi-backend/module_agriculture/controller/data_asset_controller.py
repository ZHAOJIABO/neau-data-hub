from typing import Annotated
from urllib.parse import quote

from fastapi import File, Form, Path, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_agriculture.entity.vo.data_asset_vo import DataAssetModel, DataAssetPageQueryModel
from module_agriculture.service.data_asset_service import DataAssetService
from utils.log_util import logger
from utils.response_util import ResponseUtil
from utils.upload_util import UploadUtil

data_asset_controller = APIRouterPro(
    prefix='/agriculture/dataAsset', order_num=24, tags=['农业数据-数据资产管理'], dependencies=[PreAuthDependency()]
)


@data_asset_controller.get(
    '/list',
    summary='获取数据资产分页列表',
    description='用于获取数据资产的分页列表',
    response_model=PageResponseModel,
)
async def get_data_asset_list(
    request: Request,
    query: Annotated[DataAssetPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await DataAssetService.get_data_asset_list_services(query_db, query, is_page=True)
    logger.info('获取数据资产列表成功')
    return ResponseUtil.success(model_content=result)


@data_asset_controller.get(
    '/download/{asset_id}',
    summary='下载数据资产',
    description='通过资产ID下载数据文件',
    response_class=StreamingResponse,
)
async def download_data_asset(
    request: Request,
    asset_id: Annotated[int, Path(description='资产ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    filepath, download_name = await DataAssetService.resolve_download_services(query_db, asset_id)
    logger.info(f'下载数据资产{asset_id}')
    encoded_name = quote(download_name)
    return ResponseUtil.streaming(
        data=UploadUtil.generate_file(filepath),
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@data_asset_controller.get(
    '/{asset_id}',
    summary='获取数据资产详情',
    description='用于获取指定数据资产的详细信息',
    response_model=DataResponseModel[DataAssetModel],
)
async def get_data_asset_detail(
    request: Request,
    asset_id: Annotated[int, Path(description='资产ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await DataAssetService.data_asset_detail_services(query_db, asset_id)
    logger.info(f'获取数据资产{asset_id}详情成功')
    return ResponseUtil.success(data=result)


@data_asset_controller.post(
    '/upload',
    summary='上传数据资产',
    description='上传GeoTIFF或Shapefile ZIP文件作为数据资产',
    response_model=ResponseBaseModel,
)
async def upload_data_asset(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    data_category: Annotated[str | None, Form(alias='dataCategory')] = None,
    region_name: Annotated[str | None, Form(alias='regionName')] = None,
    variable_name: Annotated[str | None, Form(alias='variableName')] = None,
) -> Response:
    user_id = current_user.user.user_id if current_user and current_user.user else None
    result = await DataAssetService.upload_asset_services(
        query_db, file, data_category, region_name, variable_name, user_id
    )
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message, data=result.result)


@data_asset_controller.delete(
    '/{ids}',
    summary='删除数据资产',
    description='用于删除数据资产（支持批量）',
    response_model=ResponseBaseModel,
)
async def delete_data_asset(
    request: Request,
    ids: Annotated[str, Path(description='需要删除的资产ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await DataAssetService.delete_asset_services(query_db, ids)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)
