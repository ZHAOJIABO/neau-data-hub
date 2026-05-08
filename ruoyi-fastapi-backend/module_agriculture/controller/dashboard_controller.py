from typing import Annotated

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import ResponseBaseModel
from module_agriculture.service.dashboard_service import DashboardService
from utils.log_util import logger
from utils.response_util import ResponseUtil

dashboard_controller = APIRouterPro(
    prefix='/agriculture/dashboard', order_num=19, tags=['农业数据-数据概览'], dependencies=[PreAuthDependency()]
)


@dashboard_controller.get(
    '/stats',
    summary='获取数据概览统计',
    description='用于获取农业数据各模块的统计概览',
    response_model=ResponseBaseModel,
)
async def get_dashboard_stats(
    request: Request,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await DashboardService.get_stats_services(query_db)
    logger.info('获取数据概览统计成功')
    return ResponseUtil.success(data=result)
