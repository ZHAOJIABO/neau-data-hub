from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from module_agriculture.dao.station_dao import StationDao
from module_agriculture.entity.vo.station_vo import StationModel, StationPageQueryModel
from utils.common_util import CamelCaseUtil


class StationService:
    """
    站点管理服务层
    """

    @classmethod
    async def get_station_list_services(
        cls, query_db: AsyncSession, query_object: StationPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await StationDao.get_station_list(query_db, query_object, is_page)

    @classmethod
    async def station_detail_services(cls, query_db: AsyncSession, station_id: int) -> StationModel:
        station = await StationDao.get_station_by_id(query_db, station_id)
        result = StationModel(**CamelCaseUtil.transform_result(station)) if station else StationModel()
        return result

    @classmethod
    async def add_station_services(cls, query_db: AsyncSession, station: StationModel) -> CrudResponseModel:
        try:
            await StationDao.add_station(query_db, station)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def edit_station_services(cls, query_db: AsyncSession, station: StationModel) -> CrudResponseModel:
        edit_data = station.model_dump(exclude_unset=True)
        try:
            await StationDao.edit_station(query_db, edit_data)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='更新成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def delete_station_services(cls, query_db: AsyncSession, ids: str) -> CrudResponseModel:
        try:
            id_list = [int(i) for i in ids.split(',')]
            await StationDao.delete_station(query_db, id_list)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except Exception as e:
            await query_db.rollback()
            raise e
