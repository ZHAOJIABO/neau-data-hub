from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.data_asset_do import DataAsset
from module_agriculture.entity.vo.data_asset_vo import DataAssetPageQueryModel
from utils.page_util import PageUtil


class DataAssetDao:

    @classmethod
    async def get_data_asset_list(
        cls, db: AsyncSession, query_object: DataAssetPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(DataAsset)
            .where(
                DataAsset.deleted_at.is_(None),
                DataAsset.asset_name.like(f'%{query_object.asset_name}%') if query_object.asset_name else True,
                DataAsset.relative_path.like(f'%{query_object.relative_path}%') if query_object.relative_path else True,
                DataAsset.asset_type == query_object.asset_type if query_object.asset_type else True,
                DataAsset.file_format == query_object.file_format if query_object.file_format else True,
                DataAsset.data_category == query_object.data_category if query_object.data_category else True,
                DataAsset.region_name == query_object.region_name if query_object.region_name else True,
                DataAsset.variable_name == query_object.variable_name if query_object.variable_name else True,
                DataAsset.obs_date >= query_object.obs_date_begin if query_object.obs_date_begin else True,
                DataAsset.obs_date <= query_object.obs_date_end if query_object.obs_date_end else True,
            )
            .order_by(DataAsset.id.desc())
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_data_asset_by_id(cls, db: AsyncSession, asset_id: int) -> DataAsset | None:
        result = await db.execute(
            select(DataAsset).where(DataAsset.id == asset_id, DataAsset.deleted_at.is_(None))
        )
        return result.scalars().first()

    @classmethod
    async def get_data_asset_by_path(cls, db: AsyncSession, relative_path: str) -> DataAsset | None:
        result = await db.execute(
            select(DataAsset).where(DataAsset.relative_path == relative_path, DataAsset.deleted_at.is_(None))
        )
        return result.scalars().first()

    @classmethod
    async def add_data_asset(cls, db: AsyncSession, asset_data: dict) -> DataAsset:
        db_asset = DataAsset(**asset_data)
        db.add(db_asset)
        await db.flush()
        return db_asset

    @classmethod
    async def soft_delete_assets(cls, db: AsyncSession, ids: list[int]) -> list[DataAsset]:
        from datetime import datetime
        result = await db.execute(
            select(DataAsset).where(DataAsset.id.in_(ids), DataAsset.deleted_at.is_(None))
        )
        assets = list(result.scalars().all())
        if assets:
            await db.execute(
                update(DataAsset)
                .where(DataAsset.id.in_([a.id for a in assets]))
                .values(deleted_at=datetime.now())
            )
        return assets
