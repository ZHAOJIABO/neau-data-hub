"""
灌区分区数据管理服务。
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
from module_agriculture.dao.zone_dao import IrrigationZoneDao
from module_agriculture.entity.vo.zone_vo import (
    DEFAULT_IRRIGATION_AREA_CODE,
    DEFAULT_IRRIGATION_AREA_NAME,
    IrrigationAreaModel,
    IrrigationZoneCreateModel,
    IrrigationZoneModel,
    IrrigationZonePageQueryModel,
    IrrigationZoneUpdateModel,
)
from utils.common_util import CamelCaseUtil


class IrrigationZoneService:
    """灌区分区数据业务逻辑层。"""

    @classmethod
    async def get_zone_list_services(
        cls, query_db: AsyncSession, query_object: IrrigationZonePageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await IrrigationZoneDao.get_zone_list(query_db, query_object, is_page)

    @classmethod
    async def get_zone_detail_services(cls, query_db: AsyncSession, zone_id: str) -> IrrigationZoneModel:
        area_code, clean_zone_id = cls._split_zone_key(zone_id)
        record = await IrrigationZoneDao.get_zone_by_id(query_db, area_code, clean_zone_id)
        if record is None:
            raise ServiceException(message=f'分区不存在: {area_code}/{clean_zone_id}')
        return IrrigationZoneModel(**CamelCaseUtil.transform_result(record))

    @classmethod
    async def create_zone_services(
        cls, query_db: AsyncSession, payload: IrrigationZoneCreateModel
    ) -> CrudResponseModel:
        existing = await IrrigationZoneDao.get_zone_by_id(
            query_db, payload.irrigation_area_code, payload.zone_id
        )
        if existing is not None:
            raise ServiceException(message=f'分区编号已存在: {payload.irrigation_area_code}/{payload.zone_id}')
        zone_data = cls._normalize_payload(payload.model_dump(exclude={'id', 'created_at', 'updated_at'}))
        try:
            await IrrigationZoneDao.add_zone(query_db, zone_data)
            await query_db.commit()
        except IntegrityError as exc:
            await query_db.rollback()
            raise ServiceException(message=f'分区编号已存在: {payload.zone_id}') from exc
        return CrudResponseModel(is_success=True, message='新增成功')

    @classmethod
    async def update_zone_services(
        cls, query_db: AsyncSession, payload: IrrigationZoneUpdateModel
    ) -> CrudResponseModel:
        existing = await IrrigationZoneDao.get_zone_by_id(
            query_db, payload.irrigation_area_code, payload.zone_id
        )
        if existing is None:
            raise ServiceException(message=f'分区不存在: {payload.irrigation_area_code}/{payload.zone_id}')
        zone_data = cls._normalize_payload(payload.model_dump(exclude={'id', 'zone_id', 'created_at', 'updated_at'}))
        await IrrigationZoneDao.update_zone_by_id(
            query_db, payload.irrigation_area_code, payload.zone_id, zone_data
        )
        await query_db.commit()
        return CrudResponseModel(is_success=True, message='更新成功')

    @classmethod
    async def delete_zone_services(cls, query_db: AsyncSession, ids: str) -> CrudResponseModel:
        zone_ids = [i.strip() for i in ids.split(',') if i.strip()]
        if not zone_ids:
            raise ServiceException(message='分区编号不能为空')
        try:
            deleted = 0
            for raw_id in zone_ids:
                area_code, zid = cls._split_zone_key(raw_id)
                deleted += await IrrigationZoneDao.delete_zone_by_id(query_db, area_code, zid)
            await query_db.commit()
        except Exception:
            await query_db.rollback()
            raise
        if deleted == 0:
            raise ServiceException(message='未找到可删除的分区')
        return CrudResponseModel(is_success=True, message=f'已删除 {deleted} 条')

    @classmethod
    async def list_area_options_services(cls, query_db: AsyncSession) -> list[dict[str, str]]:
        rows = await IrrigationZoneDao.get_area_options(query_db)
        if not rows:
            rows = [(DEFAULT_IRRIGATION_AREA_CODE, DEFAULT_IRRIGATION_AREA_NAME)]
        options = [
            IrrigationAreaModel(irrigation_area_code=code, irrigation_area_name=name).model_dump()
            for code, name in rows
        ]
        if not any(item['irrigation_area_code'] == DEFAULT_IRRIGATION_AREA_CODE for item in options):
            options.insert(
                0,
                IrrigationAreaModel(
                    irrigation_area_code=DEFAULT_IRRIGATION_AREA_CODE,
                    irrigation_area_name=DEFAULT_IRRIGATION_AREA_NAME,
                ).model_dump(),
            )
        return options

    @classmethod
    async def list_enabled_services(
        cls, query_db: AsyncSession, irrigation_area_code: str = DEFAULT_IRRIGATION_AREA_CODE
    ) -> list[dict[str, Any]]:
        records = await IrrigationZoneDao.get_enabled_zones(query_db, irrigation_area_code)
        return [cls._record_to_api(rec) for rec in records]

    @classmethod
    async def list_enabled_for_water_soil(
        cls, query_db: AsyncSession, irrigation_area_code: str = DEFAULT_IRRIGATION_AREA_CODE
    ) -> list[dict[str, Any]]:
        records = await IrrigationZoneDao.get_enabled_zones(query_db, irrigation_area_code)
        if not records:
            raise ServiceException(message=f'未维护灌区 {irrigation_area_code} 的启用分区数据')
        return [cls._record_to_model(rec, include_area_bounds=True) for rec in records]

    @classmethod
    async def list_enabled_for_water_right(
        cls, query_db: AsyncSession, irrigation_area_code: str = DEFAULT_IRRIGATION_AREA_CODE
    ) -> list[dict[str, Any]]:
        records = await IrrigationZoneDao.get_enabled_zones(query_db, irrigation_area_code)
        if not records:
            raise ServiceException(message=f'未维护灌区 {irrigation_area_code} 的启用分区数据')
        return [cls._record_to_model(rec, include_area_bounds=False) for rec in records]

    @classmethod
    async def zone_name_map(
        cls, query_db: AsyncSession, irrigation_area_code: str = DEFAULT_IRRIGATION_AREA_CODE
    ) -> dict[str, str]:
        records = await IrrigationZoneDao.get_enabled_zones(query_db, irrigation_area_code)
        return {rec.zone_id: rec.zone_name for rec in records}

    @classmethod
    async def import_from_csv_services(cls, query_db: AsyncSession, file: UploadFile) -> CrudResponseModel:
        content = await file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ServiceException(message='CSV 文件必须使用 UTF-8 编码') from exc

        reader = csv.DictReader(io.StringIO(text))
        required = {'zone_id', 'zone_name', 'land_area'}
        fieldnames = set(reader.fieldnames or [])
        missing = required - fieldnames
        if missing:
            raise ServiceException(message=f'CSV 缺少必填列: {", ".join(sorted(missing))}')

        inserted = 0
        updated = 0
        try:
            for row in reader:
                if not row.get('zone_id'):
                    continue
                data = cls._normalize_payload(
                    {
                        'zone_id': row.get('zone_id', '').strip(),
                        'irrigation_area_code': (
                            row.get('irrigation_area_code') or DEFAULT_IRRIGATION_AREA_CODE
                        ).strip(),
                        'irrigation_area_name': (
                            row.get('irrigation_area_name') or DEFAULT_IRRIGATION_AREA_NAME
                        ).strip(),
                        'zone_name': row.get('zone_name', '').strip(),
                        'land_area': cls._to_float(row.get('land_area')),
                        'surface_water_available': cls._to_float(row.get('surface_water_available'), 0.0),
                        'groundwater_available': cls._to_float(row.get('groundwater_available'), 0.0),
                        'min_area': cls._to_optional_float(row.get('min_area')),
                        'max_area': cls._to_optional_float(row.get('max_area')),
                        'sort_order': int(cls._to_float(row.get('sort_order'), 0.0)),
                        'status': (row.get('status') or '0').strip(),
                        'remark': row.get('remark') or None,
                    }
                )
                IrrigationZoneCreateModel(**data)
                _, is_new = await IrrigationZoneDao.upsert_zone(query_db, data)
                inserted += 1 if is_new else 0
                updated += 0 if is_new else 1
            await query_db.commit()
        except Exception:
            await query_db.rollback()
            raise
        return CrudResponseModel(
            is_success=True,
            message='导入成功',
            result={'inserted': inserted, 'updated': updated},
        )

    @staticmethod
    def _normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
        if data.get('min_area') is None and data.get('land_area') is not None:
            data['min_area'] = round(float(data['land_area']) * 0.75, 4)
        if data.get('max_area') is None and data.get('land_area') is not None:
            data['max_area'] = float(data['land_area'])
        if data.get('status') is None:
            data['status'] = '0'
        if data.get('sort_order') is None:
            data['sort_order'] = 0
        if not data.get('irrigation_area_code'):
            data['irrigation_area_code'] = DEFAULT_IRRIGATION_AREA_CODE
        if not data.get('irrigation_area_name'):
            data['irrigation_area_name'] = DEFAULT_IRRIGATION_AREA_NAME
        return data

    @staticmethod
    def _record_to_api(record: Any) -> dict[str, Any]:
        return {
            'id': record.id,
            'irrigation_area_code': record.irrigation_area_code,
            'irrigation_area_name': record.irrigation_area_name,
            'zone_id': record.zone_id,
            'zone_name': record.zone_name,
            'land_area': float(record.land_area),
            'surface_water_available': float(record.surface_water_available or 0.0),
            'groundwater_available': float(record.groundwater_available or 0.0),
            'min_area': float(record.min_area) if record.min_area is not None else None,
            'max_area': float(record.max_area) if record.max_area is not None else None,
            'sort_order': int(record.sort_order or 0),
            'status': record.status,
            'remark': record.remark,
            'created_at': record.created_at,
            'updated_at': record.updated_at,
        }

    @classmethod
    def _record_to_model(cls, record: Any, include_area_bounds: bool) -> dict[str, Any]:
        data = {
            'irrigation_area_code': record.irrigation_area_code,
            'irrigation_area_name': record.irrigation_area_name,
            'zone_id': record.zone_id,
            'zone_name': record.zone_name,
            'land_area': float(record.land_area),
            'surface_water_available': float(record.surface_water_available or 0.0),
            'groundwater_available': float(record.groundwater_available or 0.0),
        }
        if include_area_bounds:
            min_area = float(record.min_area) if record.min_area is not None else round(data['land_area'] * 0.75, 4)
            max_area = float(record.max_area) if record.max_area is not None else data['land_area']
            data.update({'min_area': min_area, 'max_area': max_area})
        return data

    @staticmethod
    def _split_zone_key(raw_id: str) -> tuple[str, str]:
        if ':' in raw_id:
            area_code, zone_id = raw_id.split(':', 1)
            return area_code.strip() or DEFAULT_IRRIGATION_AREA_CODE, zone_id.strip()
        return DEFAULT_IRRIGATION_AREA_CODE, raw_id.strip()

    @staticmethod
    def _to_float(value: Any, default: float | None = None) -> float:
        if value in (None, ''):
            if default is None:
                raise ServiceException(message='CSV 数值字段不能为空')
            return default
        return float(value)

    @staticmethod
    def _to_optional_float(value: Any) -> float | None:
        if value in (None, ''):
            return None
        return float(value)
