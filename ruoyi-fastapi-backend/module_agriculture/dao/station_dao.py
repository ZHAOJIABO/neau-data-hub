from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.station_do import Station
from module_agriculture.entity.vo.station_vo import StationModel, StationPageQueryModel
from utils.page_util import PageUtil


class StationDao:
    """
    站点管理数据库操作层
    """

    @classmethod
    async def get_station_list(
        cls, db: AsyncSession, query_object: StationPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(Station)
            .where(
                Station.stcd.like(f'%{query_object.stcd}%') if query_object.stcd else True,
                Station.name.like(f'%{query_object.name}%') if query_object.name else True,
            )
            .order_by(Station.id)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_station_by_id(cls, db: AsyncSession, station_id: int) -> Station | None:
        return (await db.execute(select(Station).where(Station.id == station_id))).scalars().first()

    @classmethod
    async def add_station(cls, db: AsyncSession, station: StationModel) -> Station:
        db_station = Station(**station.model_dump(exclude_unset=True, exclude={'id', 'created_at'}))
        db.add(db_station)
        await db.flush()
        return db_station

    @classmethod
    async def edit_station(cls, db: AsyncSession, station: dict) -> None:
        station_obj = await cls.get_station_by_id(db, station['id'])
        if station_obj:
            for key, value in station.items():
                if key != 'id' and hasattr(station_obj, key):
                    setattr(station_obj, key, value)

    @classmethod
    async def delete_station(cls, db: AsyncSession, ids: list[int]) -> None:
        await db.execute(delete(Station).where(Station.id.in_(ids)))
