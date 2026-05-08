from typing import Annotated

from fastapi import Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import PageResponseModel
from module_agriculture.entity.vo.crop_vo import CropLeafAreaPageQueryModel
from module_agriculture.service.crop_service import CropService
from utils.log_util import logger
from utils.response_util import ResponseUtil

crop_controller = APIRouterPro(
    prefix='/agriculture/crop', order_num=22, tags=['农业数据-作物数据'], dependencies=[PreAuthDependency()]
)


@crop_controller.get(
    '/leaf-area/list',
    summary='获取叶面积指数数据列表',
    description='用于获取大豆叶面积指数的分页列表',
    response_model=PageResponseModel,
)
async def get_crop_leaf_area_list(
    request: Request,
    query: Annotated[CropLeafAreaPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await CropService.get_leaf_area_list_services(query_db, query, is_page=True)
    logger.info('获取叶面积指数数据成功')
    return ResponseUtil.success(model_content=result)
