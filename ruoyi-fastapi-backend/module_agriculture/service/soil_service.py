from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.dao.soil_dao import SoilDao
from module_agriculture.entity.vo.soil_vo import (
    SoilGroundTempPageQueryModel,
    SoilLayerStatsPageQueryModel,
    SoilParameterPageQueryModel,
    SoilSensorPageQueryModel,
    SoilThicknessPageQueryModel,
)


class SoilService:
    """
    土壤数据服务层
    """

    @classmethod
    async def get_sensor_list_services(
        cls, query_db: AsyncSession, query_object: SoilSensorPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await SoilDao.get_sensor_list(query_db, query_object, is_page)

    @classmethod
    async def get_parameter_list_services(
        cls, query_db: AsyncSession, query_object: SoilParameterPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await SoilDao.get_parameter_list(query_db, query_object, is_page)

    @classmethod
    async def get_ground_temp_list_services(
        cls, query_db: AsyncSession, query_object: SoilGroundTempPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await SoilDao.get_ground_temp_list(query_db, query_object, is_page)

    @classmethod
    async def get_thickness_list_services(
        cls, query_db: AsyncSession, query_object: SoilThicknessPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await SoilDao.get_thickness_list(query_db, query_object, is_page)

    @classmethod
    async def get_layer_stats_list_services(
        cls, query_db: AsyncSession, query_object: SoilLayerStatsPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await SoilDao.get_layer_stats_list(query_db, query_object, is_page)
