from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from module_agriculture.dao.weather_dao import WeatherDao
from module_agriculture.entity.vo.weather_vo import (
    WeatherHumidityPageQueryModel,
    WeatherOverviewPageQueryModel,
    WeatherPrecipitationPageQueryModel,
    WeatherTemperatureModel,
    WeatherTemperaturePageQueryModel,
)


class WeatherService:
    """
    气象数据服务层
    """

    @classmethod
    async def get_overview_list_services(
        cls, query_db: AsyncSession, query_object: WeatherOverviewPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await WeatherDao.get_overview_list(query_db, query_object, is_page)

    @classmethod
    async def get_temperature_list_services(
        cls, query_db: AsyncSession, query_object: WeatherTemperaturePageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await WeatherDao.get_temperature_list(query_db, query_object, is_page)

    @classmethod
    async def add_temperature_services(cls, query_db: AsyncSession, data: WeatherTemperatureModel) -> CrudResponseModel:
        try:
            await WeatherDao.add_temperature(query_db, data)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def delete_temperature_services(cls, query_db: AsyncSession, ids: str) -> CrudResponseModel:
        try:
            id_list = [int(i) for i in ids.split(',')]
            await WeatherDao.delete_temperature(query_db, id_list)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def get_humidity_list_services(
        cls, query_db: AsyncSession, query_object: WeatherHumidityPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await WeatherDao.get_humidity_list(query_db, query_object, is_page)

    @classmethod
    async def get_precipitation_list_services(
        cls, query_db: AsyncSession, query_object: WeatherPrecipitationPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await WeatherDao.get_precipitation_list(query_db, query_object, is_page)
