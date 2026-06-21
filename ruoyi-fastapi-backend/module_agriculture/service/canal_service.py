"""
渠系数据管理服务：CRUD + CSV 导入 + 拓扑。
"""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from exceptions.exception import ServiceException
from module_agriculture.dao.canal_dao import CanalDao
from module_agriculture.entity.vo.canal_vo import (
    CanalBaseCreateModel,
    CanalBaseModel,
    CanalBasePageQueryModel,
    CanalBaseUpdateModel,
)
from utils.common_util import CamelCaseUtil


# 渠系拓扑节点用于前端的字段裁剪
_TOPOLOGY_FIELDS = (
    'canal_id',
    'canal_name',
    'level',
    'length',
    'design_flow',
    'water_demand',
)


class CanalService:
    """
    渠系数据业务逻辑层。
    """

    @classmethod
    async def get_canal_list_services(
        cls, query_db: AsyncSession, query_object: CanalBasePageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await CanalDao.get_canal_list(query_db, query_object, is_page)

    @classmethod
    async def get_canal_detail_services(cls, query_db: AsyncSession, canal_id: str) -> CanalBaseModel:
        record = await CanalDao.get_canal_by_canal_id(query_db, canal_id)
        if record is None:
            raise ServiceException(message=f'渠段不存在: {canal_id}')
        return CanalBaseModel(**CamelCaseUtil.transform_result(record))

    @classmethod
    async def create_canal_services(
        cls, query_db: AsyncSession, payload: CanalBaseCreateModel
    ) -> CrudResponseModel:
        existing = await CanalDao.get_canal_by_canal_id(query_db, payload.canal_id)
        if existing is not None:
            raise ServiceException(message=f'渠段编号已存在: {payload.canal_id}')
        canal_data = payload.model_dump()
        try:
            await CanalDao.add_canal(query_db, canal_data)
            await query_db.commit()
        except IntegrityError as exc:
            await query_db.rollback()
            raise ServiceException(message=f'渠段编号已存在: {payload.canal_id}') from exc
        return CrudResponseModel(is_success=True, message='新增成功')

    @classmethod
    async def update_canal_services(
        cls, query_db: AsyncSession, payload: CanalBaseUpdateModel
    ) -> CrudResponseModel:
        existing = await CanalDao.get_canal_by_canal_id(query_db, payload.canal_id)
        if existing is None:
            raise ServiceException(message=f'渠段不存在: {payload.canal_id}')
        canal_data = payload.model_dump(exclude={'canal_id'})
        await CanalDao.update_canal_by_canal_id(query_db, payload.canal_id, canal_data)
        await query_db.commit()
        return CrudResponseModel(is_success=True, message='更新成功')

    @classmethod
    async def delete_canal_services(cls, query_db: AsyncSession, ids: str) -> CrudResponseModel:
        canal_ids = [i.strip() for i in ids.split(',') if i.strip()]
        if not canal_ids:
            raise ServiceException(message='渠段编号不能为空')
        try:
            deleted = 0
            for cid in canal_ids:
                deleted += await CanalDao.delete_canal_by_canal_id(query_db, cid)
            await query_db.commit()
        except Exception:
            await query_db.rollback()
            raise
        if deleted == 0:
            raise ServiceException(message='未找到可删除的渠段')
        return CrudResponseModel(is_success=True, message=f'已删除 {deleted} 条')

    # ----------------------- 启动期辅助 -----------------------

    @classmethod
    async def list_all_for_runtime(cls, query_db: AsyncSession) -> list[dict[str, Any]]:
        """
        启动期加载到 CanalsData 单例时使用的全量接口。

        全灌区共享的常量（渠床透水指数/系数、μ/σs/ε）不在 `CanalBase` 内，模型求解时由调用方传入。
        """
        records = await CanalDao.get_all_canals(query_db)
        result: list[dict[str, Any]] = []
        for rec in records:
            result.append(
                {
                    'canal_id': rec.canal_id,
                    'canal_name': rec.canal_name or '',
                    'level': rec.level or '',
                    'length': float(rec.length or 0.0),
                    'design_flow': float(rec.design_flow or 0.0),
                    'bottom_width': float(rec.bottom_width or 0.0),
                    'slope': float(rec.slope or 0.0),
                    'side_slope': float(rec.side_slope or 0.0),
                    'roughness': float(rec.roughness or 0.0),
                    'water_demand': float(rec.water_demand or 0.0),
                    'position': float(rec.position or 0.0),
                }
            )
        return result
