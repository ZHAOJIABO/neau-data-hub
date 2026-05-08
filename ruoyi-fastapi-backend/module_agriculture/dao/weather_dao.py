from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.weather_do import (
    WeatherHumidity,
    WeatherPrecipitation,
    WeatherTemperature,
)
from module_agriculture.entity.vo.weather_vo import (
    WeatherHumidityPageQueryModel,
    WeatherOverviewPageQueryModel,
    WeatherPrecipitationPageQueryModel,
    WeatherTemperatureModel,
    WeatherTemperaturePageQueryModel,
)
from utils.page_util import PageUtil


class WeatherDao:
    """
    气象数据数据库操作层
    """

    @classmethod
    async def get_temperature_list(
        cls, db: AsyncSession, query_object: WeatherTemperaturePageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(WeatherTemperature)
            .where(
                WeatherTemperature.stcd == query_object.stcd if query_object.stcd else True,
                WeatherTemperature.obs_date >= query_object.start_date if query_object.start_date else True,
                WeatherTemperature.obs_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(WeatherTemperature.obs_date.desc())
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def add_temperature(cls, db: AsyncSession, data: WeatherTemperatureModel) -> WeatherTemperature:
        db_obj = WeatherTemperature(**data.model_dump(exclude_unset=True, exclude={'id', 'created_at'}))
        db.add(db_obj)
        await db.flush()
        return db_obj

    @classmethod
    async def delete_temperature(cls, db: AsyncSession, ids: list[int]) -> None:
        await db.execute(delete(WeatherTemperature).where(WeatherTemperature.id.in_(ids)))

    @classmethod
    async def get_humidity_list(
        cls, db: AsyncSession, query_object: WeatherHumidityPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(WeatherHumidity)
            .where(
                WeatherHumidity.stcd == query_object.stcd if query_object.stcd else True,
                WeatherHumidity.obs_date >= query_object.start_date if query_object.start_date else True,
                WeatherHumidity.obs_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(WeatherHumidity.obs_date.desc())
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_precipitation_list(
        cls, db: AsyncSession, query_object: WeatherPrecipitationPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(WeatherPrecipitation)
            .where(
                WeatherPrecipitation.stcd == query_object.stcd if query_object.stcd else True,
                WeatherPrecipitation.obs_date >= query_object.start_date if query_object.start_date else True,
                WeatherPrecipitation.obs_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(WeatherPrecipitation.obs_date.desc())
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_overview_list(
        cls, db: AsyncSession, query_object: WeatherOverviewPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """查询气象综合视图"""
        conditions = []
        if query_object.stcd:
            conditions.append(f"stcd = '{query_object.stcd}'")
        if query_object.start_date:
            conditions.append(f"obs_date >= '{query_object.start_date}'")
        if query_object.end_date:
            conditions.append(f"obs_date <= '{query_object.end_date}'")

        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        count_sql = text(f'SELECT COUNT(*) FROM v_weather_daily WHERE {where_clause}')
        total = (await db.execute(count_sql)).scalar()

        offset = (query_object.page_num - 1) * query_object.page_size
        data_sql = text(
            f'SELECT station_name, stcd, obs_date, tmax, tmin, tmean, rh_mean, precipitation, sunshine_hours, wind_speed '
            f'FROM v_weather_daily WHERE {where_clause} ORDER BY obs_date DESC '
            f'LIMIT {query_object.page_size} OFFSET {offset}'
        )
        result = await db.execute(data_sql)
        rows = []
        for row in result:
            rows.append({
                'stationName': row[0],
                'stcd': row[1],
                'obsDate': str(row[2]) if row[2] else None,
                'tmax': float(row[3]) if row[3] is not None else None,
                'tmin': float(row[4]) if row[4] is not None else None,
                'tmean': float(row[5]) if row[5] is not None else None,
                'rhMean': float(row[6]) if row[6] is not None else None,
                'precipitation': float(row[7]) if row[7] is not None else None,
                'sunshineHours': float(row[8]) if row[8] is not None else None,
                'windSpeed': float(row[9]) if row[9] is not None else None,
            })

        import math

        has_next = math.ceil(total / query_object.page_size) > query_object.page_num if total else False

        if is_page:
            return PageModel(
                rows=rows,
                pageNum=query_object.page_num,
                pageSize=query_object.page_size,
                total=total,
                hasNext=has_next,
            )
        return rows
