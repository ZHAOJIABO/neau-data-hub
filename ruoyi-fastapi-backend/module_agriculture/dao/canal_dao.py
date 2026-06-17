"""
渠系基础数据 DAO。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.canal_do import CanalBase
from module_agriculture.entity.vo.canal_vo import CanalBasePageQueryModel
from utils.page_util import PageUtil


class CanalDao:
    """
    渠系基础数据数据库操作层。
    """

    @classmethod
    async def get_canal_list(
        cls, db: AsyncSession, query_object: CanalBasePageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(CanalBase)
            .where(
                CanalBase.canal_id == query_object.canal_id if query_object.canal_id else True,
                CanalBase.canal_name.like(f'%{query_object.canal_name}%')
                if query_object.canal_name
                else True,
                CanalBase.level == query_object.level if query_object.level else True,
            )
            .order_by(CanalBase.canal_id)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_canal_by_canal_id(cls, db: AsyncSession, canal_id: str) -> CanalBase | None:
        result = await db.execute(select(CanalBase).where(CanalBase.canal_id == canal_id))
        return result.scalars().first()

    @classmethod
    async def get_all_canals(cls, db: AsyncSession) -> list[CanalBase]:
        result = await db.execute(select(CanalBase).order_by(CanalBase.canal_id))
        return list(result.scalars().all())

    @classmethod
    async def count_canals(cls, db: AsyncSession) -> int:
        result = await db.execute(select(func.count('*')).select_from(CanalBase))
        return int(result.scalar() or 0)

    @classmethod
    async def add_canal(cls, db: AsyncSession, canal_data: dict) -> CanalBase:
        db_canal = CanalBase(**canal_data)
        db.add(db_canal)
        await db.flush()
        return db_canal

    @classmethod
    async def update_canal_by_canal_id(
        cls, db: AsyncSession, canal_id: str, canal_data: dict
    ) -> int:
        result = await db.execute(
            update(CanalBase).where(CanalBase.canal_id == canal_id).values(**canal_data)
        )
        return int(result.rowcount or 0)

    @classmethod
    async def upsert_canal(cls, db: AsyncSession, canal_data: dict) -> tuple[CanalBase, bool]:
        """
        按 canal_id 唯一键 upsert；返回 (对象, 是否新建)。
        """
        existing = await cls.get_canal_by_canal_id(db, canal_data['canal_id'])
        if existing is None:
            return await cls.add_canal(db, canal_data), True
        for key, value in canal_data.items():
            setattr(existing, key, value)
        await db.flush()
        return existing, False

    @classmethod
    async def delete_canal_by_canal_id(cls, db: AsyncSession, canal_id: str) -> int:
        result = await db.execute(delete(CanalBase).where(CanalBase.canal_id == canal_id))
        return int(result.rowcount or 0)
