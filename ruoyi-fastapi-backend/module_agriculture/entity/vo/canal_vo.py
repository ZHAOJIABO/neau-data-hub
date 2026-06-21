"""
渠系数据 pydantic 模型（响应 / 查询 / 新增 / 更新）。

字段与 agri_canal 表（canal.csv）完全一致。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CanalBaseModel(BaseModel):
    """
    渠系基础数据响应模型。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    canal_id: str | None = Field(default=None, description='渠段编号（主键）')
    canal_name: str | None = Field(default=None, description='渠段名称')
    parent_id: str | None = Field(default=None, description='父渠段编号')
    level: str | None = Field(default=None, description='级别：1 干 / 2 支 / 3 斗 / 4 农')
    length: float | None = Field(default=None, description='渠段长度 (m)')
    design_flow: float | None = Field(default=None, description='设计流量 (m\u00b3/s)')
    bottom_width: float | None = Field(default=None, description='渠底宽 (m)')
    slope: float | None = Field(default=None, description='坡降')
    side_slope: float | None = Field(default=None, description='边坡系数 (1:m)')
    roughness: float | None = Field(default=None, description='糙率 Manning n')
    water_demand: float | None = Field(default=None, description='单次灌水需水量 (m\u00b3)')
    position: float | None = Field(default=None, description='桩号/位置 (m)')
    latitude: float | None = Field(default=None, description='纬度')
    longitude: float | None = Field(default=None, description='经度')
    created_at: datetime | None = Field(default=None, description='创建时间')
    updated_at: datetime | None = Field(default=None, description='更新时间')


class CanalBasePageQueryModel(BaseModel):
    """
    渠系基础数据分页查询模型。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    canal_id: str | None = Field(default=None, description='渠段编号（精确）')
    canal_name: str | None = Field(default=None, description='渠段名称（模糊）')
    level: str | None = Field(default=None, description='级别：1 干 / 2 支 / 3 斗 / 4 农（精确）')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class CanalBaseCreateModel(BaseModel):
    """
    渠系基础数据新增模型。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    canal_id: str = Field(description='渠段编号')
    canal_name: str | None = Field(default=None, description='渠段名称')
    parent_id: str | None = Field(default=None, description='父渠段编号')
    level: str | None = Field(default=None, description='级别：1 干 / 2 支 / 3 斗 / 4 农')
    length: float | None = Field(default=None, description='渠段长度 (m)')
    design_flow: float | None = Field(default=None, description='设计流量 (m\u00b3/s)')
    bottom_width: float | None = Field(default=None, description='渠底宽 (m)')
    slope: float | None = Field(default=None, description='坡降')
    side_slope: float | None = Field(default=None, description='边坡系数 (1:m)')
    roughness: float | None = Field(default=None, description='糙率 Manning n')
    water_demand: float | None = Field(default=None, description='单次灌水需水量 (m\u00b3)')
    position: float | None = Field(default=None, description='桩号/位置 (m)')
    latitude: float | None = Field(default=None, description='纬度')
    longitude: float | None = Field(default=None, description='经度')


class CanalBaseUpdateModel(BaseModel):
    """
    渠系基础数据更新模型（按 canal_id 定位）。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    canal_id: str = Field(description='渠段编号')
    canal_name: str | None = Field(default=None, description='渠段名称')
    parent_id: str | None = Field(default=None, description='父渠段编号')
    level: str | None = Field(default=None, description='级别：1 干 / 2 支 / 3 斗 / 4 农')
    length: float | None = Field(default=None, description='渠段长度 (m)')
    design_flow: float | None = Field(default=None, description='设计流量 (m\u00b3/s)')
    bottom_width: float | None = Field(default=None, description='渠底宽 (m)')
    slope: float | None = Field(default=None, description='坡降')
    side_slope: float | None = Field(default=None, description='边坡系数 (1:m)')
    roughness: float | None = Field(default=None, description='糙率 Manning n')
    water_demand: float | None = Field(default=None, description='单次灌水需水量 (m\u00b3)')
    position: float | None = Field(default=None, description='桩号/位置 (m)')
    latitude: float | None = Field(default=None, description='纬度')
    longitude: float | None = Field(default=None, description='经度')
