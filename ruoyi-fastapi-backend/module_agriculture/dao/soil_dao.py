from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.soil_do import (
    SoilGroundTemperature,
    SoilLayerStats,
    SoilParameter,
    SoilSensorMonitor,
    SoilThickness,
)
from module_agriculture.entity.vo.soil_vo import (
    SoilGroundTempPageQueryModel,
    SoilLayerStatsPageQueryModel,
    SoilParameterPageQueryModel,
    SoilSensorPageQueryModel,
    SoilThicknessPageQueryModel,
)
from utils.page_util import PageUtil


class SoilDao:
    """
    土壤数据数据库操作层
    """

    @classmethod
    async def get_sensor_list(
        cls, db: AsyncSession, query_object: SoilSensorPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(SoilSensorMonitor)
            .where(
                SoilSensorMonitor.device_name.like(f'%{query_object.device_name}%')
                if query_object.device_name
                else True,
                SoilSensorMonitor.obs_time >= query_object.start_date if query_object.start_date else True,
                SoilSensorMonitor.obs_time <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(SoilSensorMonitor.obs_time.desc())
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_parameter_list(
        cls, db: AsyncSession, query_object: SoilParameterPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(SoilParameter)
            .where(
                SoilParameter.source == query_object.source if query_object.source else True,
            )
            .order_by(SoilParameter.id)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_ground_temp_list(
        cls, db: AsyncSession, query_object: SoilGroundTempPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(SoilGroundTemperature)
            .where(
                SoilGroundTemperature.obs_date >= query_object.start_date if query_object.start_date else True,
                SoilGroundTemperature.obs_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(SoilGroundTemperature.obs_date.desc(), SoilGroundTemperature.depth_cm)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_thickness_list(
        cls, db: AsyncSession, query_object: SoilThicknessPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = select(SoilThickness).order_by(SoilThickness.point_id)
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_layer_stats_list(
        cls, db: AsyncSession, query_object: SoilLayerStatsPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = select(SoilLayerStats).order_by(SoilLayerStats.id)
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)
