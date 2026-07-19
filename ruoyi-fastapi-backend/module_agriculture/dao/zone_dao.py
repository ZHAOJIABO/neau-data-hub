"""
灌区分区基础数据 DAO。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.zone_do import IrrigationZone
from module_agriculture.entity.vo.zone_vo import IrrigationZonePageQueryModel
from utils.page_util import PageUtil


class IrrigationZoneDao:
    """灌区分区基础数据数据库操作层。"""

    @classmethod
    async def get_zone_list(
        cls, db: AsyncSession, query_object: IrrigationZonePageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(IrrigationZone)
            .where(
                IrrigationZone.zone_id.like(f'%{query_object.zone_id}%') if query_object.zone_id else True,
                IrrigationZone.zone_name.like(f'%{query_object.zone_name}%') if query_object.zone_name else True,
                IrrigationZone.irrigation_area_code == query_object.irrigation_area_code
                if query_object.irrigation_area_code
                else True,
                IrrigationZone.irrigation_area_name.like(f'%{query_object.irrigation_area_name}%')
                if query_object.irrigation_area_name
                else True,
                IrrigationZone.status == query_object.status if query_object.status else True,
            )
            .order_by(IrrigationZone.irrigation_area_code, IrrigationZone.sort_order, IrrigationZone.zone_id)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_zone_by_id(
        cls, db: AsyncSession, irrigation_area_code: str, zone_id: str
    ) -> IrrigationZone | None:
        result = await db.execute(
            select(IrrigationZone).where(
                IrrigationZone.irrigation_area_code == irrigation_area_code,
                IrrigationZone.zone_id == zone_id,
            )
        )
        return result.scalars().first()

    @classmethod
    async def get_enabled_zones(cls, db: AsyncSession, irrigation_area_code: str) -> list[IrrigationZone]:
        result = await db.execute(
            select(IrrigationZone)
            .where(
                IrrigationZone.status == '0',
                IrrigationZone.irrigation_area_code == irrigation_area_code,
            )
            .order_by(IrrigationZone.sort_order, IrrigationZone.zone_id)
        )
        return list(result.scalars().all())

    @classmethod
    async def get_area_options(cls, db: AsyncSession) -> list[tuple[str, str]]:
        result = await db.execute(
            select(IrrigationZone.irrigation_area_code, IrrigationZone.irrigation_area_name)
            .distinct()
            .order_by(IrrigationZone.irrigation_area_code)
        )
        return [(str(code), str(name)) for code, name in result.all()]

    @classmethod
    async def add_zone(cls, db: AsyncSession, zone_data: dict) -> IrrigationZone:
        db_zone = IrrigationZone(**zone_data)
        db.add(db_zone)
        await db.flush()
        return db_zone

    @classmethod
    async def update_zone_by_id(
        cls, db: AsyncSession, irrigation_area_code: str, zone_id: str, zone_data: dict
    ) -> int:
        result = await db.execute(
            update(IrrigationZone)
            .where(
                IrrigationZone.irrigation_area_code == irrigation_area_code,
                IrrigationZone.zone_id == zone_id,
            )
            .values(**zone_data)
        )
        return int(result.rowcount or 0)

    @classmethod
    async def upsert_zone(cls, db: AsyncSession, zone_data: dict) -> tuple[IrrigationZone, bool]:
        existing = await cls.get_zone_by_id(db, zone_data['irrigation_area_code'], zone_data['zone_id'])
        if existing is None:
            return await cls.add_zone(db, zone_data), True
        for key, value in zone_data.items():
            setattr(existing, key, value)
        await db.flush()
        return existing, False

    @classmethod
    async def delete_zone_by_id(cls, db: AsyncSession, irrigation_area_code: str, zone_id: str) -> int:
        result = await db.execute(
            delete(IrrigationZone).where(
                IrrigationZone.irrigation_area_code == irrigation_area_code,
                IrrigationZone.zone_id == zone_id,
            )
        )
        return int(result.rowcount or 0)
