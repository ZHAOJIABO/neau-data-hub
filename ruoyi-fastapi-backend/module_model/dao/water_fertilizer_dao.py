from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_model.entity.do.water_fertilizer_do import WaterFertilizerRegulation
from module_model.entity.vo.water_fertilizer_vo import WaterFertilizerRegulationPageQueryModel
from utils.page_util import PageUtil


class WaterFertilizerDao:
    """
    水肥调控数据数据库操作层。
    """

    @classmethod
    async def get_regulation_list(
        cls,
        db: AsyncSession,
        query_object: WaterFertilizerRegulationPageQueryModel,
        is_page: bool = False,
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(WaterFertilizerRegulation)
            .where(
                WaterFertilizerRegulation.record_time >= query_object.start_date if query_object.start_date else True,
                WaterFertilizerRegulation.record_time <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(WaterFertilizerRegulation.record_time)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size, is_page)

    @classmethod
    async def get_regulation_summary(cls, db: AsyncSession) -> dict[str, Any]:
        result = (
            await db.execute(
                select(
                    func.count(WaterFertilizerRegulation.id).label('total'),
                    func.min(WaterFertilizerRegulation.record_time).label('start_date'),
                    func.max(WaterFertilizerRegulation.record_time).label('end_date'),
                )
            )
        ).mappings().first()
        return dict(result or {'total': 0, 'start_date': None, 'end_date': None})
