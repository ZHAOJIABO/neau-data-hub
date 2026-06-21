"""
渠系基础数据 ORM（与 canal.csv 字段完全一致）。

表名：agri_canal
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Numeric, String

from config.database import Base


class CanalBase(Base):
    """
    渠系基础数据表。

    字段与 canal.csv 完全一致。
    """

    __tablename__ = 'agri_canal'
    __table_args__ = {'comment': '渠系基础数据（与 canal.csv 字段一致）'}

    canal_id = Column(String(64), primary_key=True, nullable=False, comment='渠段编号（主键）')
    canal_name = Column(String(200), nullable=True, comment='渠段名称')
    parent_id = Column(String(64), nullable=True, comment='父渠段编号')
    level = Column(String(8), nullable=True, comment='级别：1 干 / 2 支 / 3 斗 / 4 农')
    length = Column(Numeric(12, 3), nullable=True, comment='渠段长度 (m)')
    design_flow = Column(Numeric(12, 4), nullable=True, comment='设计流量 (m\u00b3/s)')
    bottom_width = Column(Numeric(10, 4), nullable=True, comment='渠底宽 (m)')
    slope = Column(Numeric(14, 10), nullable=True, comment='坡降')
    side_slope = Column(Numeric(8, 4), nullable=True, comment='边坡系数 (1:m)')
    roughness = Column(Numeric(8, 5), nullable=True, comment='糙率 Manning n')
    water_demand = Column(Numeric(18, 4), nullable=True, comment='单次灌水需水量 (m\u00b3)')
    position = Column(Numeric(12, 3), nullable=True, comment='桩号/位置 (m)')
    latitude = Column(Numeric(12, 8), nullable=True, comment='纬度')
    longitude = Column(Numeric(12, 8), nullable=True, comment='经度')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间'
    )
