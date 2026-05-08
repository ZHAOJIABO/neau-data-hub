from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.entity.do.crop_do import CropLeafArea
from module_agriculture.entity.vo.crop_vo import CropLeafAreaPageQueryModel
from utils.page_util import PageUtil


class CropDao:
    """
    作物数据数据库操作层
    """

    @classmethod
    async def get_leaf_area_list(
        cls, db: AsyncSession, query_object: CropLeafAreaPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(CropLeafArea)
            .where(
                CropLeafArea.plot.like(f'%{query_object.plot}%') if query_object.plot else True,
            )
            .order_by(CropLeafArea.id)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)
