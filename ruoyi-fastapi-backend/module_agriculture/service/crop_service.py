from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_agriculture.dao.crop_dao import CropDao
from module_agriculture.entity.vo.crop_vo import CropLeafAreaPageQueryModel


class CropService:
    """
    作物数据服务层
    """

    @classmethod
    async def get_leaf_area_list_services(
        cls, query_db: AsyncSession, query_object: CropLeafAreaPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await CropDao.get_leaf_area_list(query_db, query_object, is_page)
