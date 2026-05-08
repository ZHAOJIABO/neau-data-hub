from typing import Annotated

from fastapi import Path, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.db_seesion import DBSessionDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import PageResponseModel, ResponseBaseModel
from module_agriculture.entity.vo.weather_vo import (
    DeleteWeatherModel,
    WeatherHumidityPageQueryModel,
    WeatherOverviewPageQueryModel,
    WeatherPrecipitationPageQueryModel,
    WeatherTemperatureModel,
    WeatherTemperaturePageQueryModel,
)
from module_agriculture.service.weather_service import WeatherService
from utils.log_util import logger
from utils.response_util import ResponseUtil

weather_controller = APIRouterPro(
    prefix='/agriculture/weather', order_num=20, tags=['农业数据-气象数据'], dependencies=[PreAuthDependency()]
)


@weather_controller.get(
    '/overview/list',
    summary='获取气象综合数据列表',
    description='用于获取气象综合视图的分页数据',
    response_model=PageResponseModel,
)
async def get_weather_overview_list(
    request: Request,
    query: Annotated[WeatherOverviewPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WeatherService.get_overview_list_services(query_db, query, is_page=True)
    logger.info('获取气象综合数据成功')
    return ResponseUtil.success(model_content=result)


@weather_controller.get(
    '/temperature/list',
    summary='获取温度数据分页列表',
    description='用于获取每日温度数据的分页列表',
    response_model=PageResponseModel,
)
async def get_weather_temperature_list(
    request: Request,
    query: Annotated[WeatherTemperaturePageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WeatherService.get_temperature_list_services(query_db, query, is_page=True)
    logger.info('获取温度数据成功')
    return ResponseUtil.success(model_content=result)


@weather_controller.post(
    '/temperature',
    summary='新增温度数据',
    description='用于新增一条温度记录',
    response_model=ResponseBaseModel,
)
async def add_weather_temperature(
    request: Request,
    data: WeatherTemperatureModel,
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WeatherService.add_temperature_services(query_db, data)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@weather_controller.delete(
    '/temperature/{ids}',
    summary='删除温度数据',
    description='用于删除温度记录',
    response_model=ResponseBaseModel,
)
async def delete_weather_temperature(
    request: Request,
    ids: Annotated[str, Path(description='需要删除的记录ID')],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WeatherService.delete_temperature_services(query_db, ids)
    logger.info(result.message)
    return ResponseUtil.success(msg=result.message)


@weather_controller.get(
    '/humidity/list',
    summary='获取湿度数据分页列表',
    description='用于获取每日湿度数据的分页列表',
    response_model=PageResponseModel,
)
async def get_weather_humidity_list(
    request: Request,
    query: Annotated[WeatherHumidityPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WeatherService.get_humidity_list_services(query_db, query, is_page=True)
    logger.info('获取湿度数据成功')
    return ResponseUtil.success(model_content=result)


@weather_controller.get(
    '/precipitation/list',
    summary='获取降水数据分页列表',
    description='用于获取每日降水数据的分页列表',
    response_model=PageResponseModel,
)
async def get_weather_precipitation_list(
    request: Request,
    query: Annotated[WeatherPrecipitationPageQueryModel, Query()],
    query_db: Annotated[AsyncSession, DBSessionDependency()],
) -> Response:
    result = await WeatherService.get_precipitation_list_services(query_db, query, is_page=True)
    logger.info('获取降水数据成功')
    return ResponseUtil.success(model_content=result)
