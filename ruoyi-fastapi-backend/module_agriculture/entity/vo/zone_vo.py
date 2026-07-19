"""
灌区分区基础数据 pydantic 模型。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


DEFAULT_IRRIGATION_AREA_CODE = 'chahayang'
DEFAULT_IRRIGATION_AREA_NAME = '查哈阳灌区'


class IrrigationZoneModel(BaseModel):
    """灌区分区基础数据响应模型。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    id: int | None = Field(default=None, description='主键ID')
    irrigation_area_code: str | None = Field(
        default=DEFAULT_IRRIGATION_AREA_CODE, description='灌区编码'
    )
    irrigation_area_name: str | None = Field(
        default=DEFAULT_IRRIGATION_AREA_NAME, description='灌区名称'
    )
    zone_id: str | None = Field(default=None, description='分区编号')
    zone_name: str | None = Field(default=None, description='分区名称')
    land_area: float | None = Field(default=None, gt=0, description='可配置耕地面积 (ha)')
    surface_water_available: float | None = Field(default=0.0, ge=0, description='地表水可供水量 (m³)')
    groundwater_available: float | None = Field(default=0.0, ge=0, description='地下水可供水量 (m³)')
    min_area: float | None = Field(default=None, ge=0, description='分区最小种植面积 (ha)')
    max_area: float | None = Field(default=None, gt=0, description='分区最大种植面积 (ha)')
    sort_order: int | None = Field(default=0, ge=0, description='排序')
    status: str | None = Field(default='0', description='状态（0启用 1停用）')
    remark: str | None = Field(default=None, description='备注')
    created_at: datetime | None = Field(default=None, description='创建时间')
    updated_at: datetime | None = Field(default=None, description='更新时间')

    @model_validator(mode='after')
    def validate_area_range(self) -> 'IrrigationZoneModel':
        if self.max_area is not None and self.min_area is not None and self.max_area < self.min_area:
            raise ValueError('max_area 必须大于或等于 min_area')
        if self.status not in (None, '0', '1'):
            raise ValueError('status 只能为 0 或 1')
        if self.irrigation_area_code is not None and not self.irrigation_area_code.strip():
            raise ValueError('irrigation_area_code 不能为空')
        return self


class IrrigationZonePageQueryModel(BaseModel):
    """灌区分区分页查询模型。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    irrigation_area_code: str | None = Field(default=None, description='灌区编码（精确）')
    irrigation_area_name: str | None = Field(default=None, description='灌区名称（模糊）')
    zone_id: str | None = Field(default=None, description='分区编号（模糊）')
    zone_name: str | None = Field(default=None, description='分区名称（模糊）')
    status: str | None = Field(default=None, description='状态（0启用 1停用）')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class IrrigationZoneCreateModel(IrrigationZoneModel):
    """灌区分区新增模型。"""

    irrigation_area_code: str = Field(default=DEFAULT_IRRIGATION_AREA_CODE, description='灌区编码')
    irrigation_area_name: str = Field(default=DEFAULT_IRRIGATION_AREA_NAME, description='灌区名称')
    zone_id: str = Field(description='分区编号')
    zone_name: str = Field(description='分区名称')
    land_area: float = Field(gt=0, description='可配置耕地面积 (ha)')
    surface_water_available: float = Field(default=0.0, ge=0, description='地表水可供水量 (m³)')
    groundwater_available: float = Field(default=0.0, ge=0, description='地下水可供水量 (m³)')


class IrrigationZoneUpdateModel(IrrigationZoneCreateModel):
    """灌区分区更新模型（按 zone_id 定位）。"""


class IrrigationAreaModel(BaseModel):
    """灌区选项模型。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    irrigation_area_code: str = Field(description='灌区编码')
    irrigation_area_name: str = Field(description='灌区名称')
