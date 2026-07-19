"""
灌区分区基础数据 ORM。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Numeric, String, Text, UniqueConstraint

from config.database import Base


class IrrigationZone(Base):
    """灌区分区基础数据表。"""

    __tablename__ = 'agri_irrigation_zone'
    __table_args__ = (
        UniqueConstraint('irrigation_area_code', 'zone_id', name='uk_agri_irrigation_zone_area_zone'),
        {'comment': '灌区分区基础数据'},
    )

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    irrigation_area_code = Column(String(64), nullable=False, default='chahayang', comment='灌区编码')
    irrigation_area_name = Column(String(100), nullable=False, default='查哈阳灌区', comment='灌区名称')
    zone_id = Column(String(32), nullable=False, comment='分区编号')
    zone_name = Column(String(100), nullable=False, comment='分区名称')
    land_area = Column(Numeric(14, 4), nullable=False, comment='可配置耕地面积 (ha)')
    surface_water_available = Column(Numeric(18, 4), nullable=False, default=0, comment='地表水可供水量 (m³)')
    groundwater_available = Column(Numeric(18, 4), nullable=False, default=0, comment='地下水可供水量 (m³)')
    min_area = Column(Numeric(14, 4), nullable=True, comment='分区最小种植面积 (ha)')
    max_area = Column(Numeric(14, 4), nullable=True, comment='分区最大种植面积 (ha)')
    sort_order = Column(Numeric(8, 0), nullable=False, default=0, comment='排序')
    status = Column(String(1), nullable=False, default='0', comment='状态（0启用 1停用）')
    remark = Column(Text, nullable=True, comment='备注')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')
