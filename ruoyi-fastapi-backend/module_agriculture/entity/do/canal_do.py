"""
渠系基础数据 ORM（v2）。

设计原则：字段名不带单位、不带数字后缀；
- `length` = 渠段长度 (m)
- `design_flow` = 设计流量 (m³/s)
- `design_depth` = 设计水深 (m)
- `top_width` = 渠顶宽 (m)
- `bottom_width` = 渠底宽 (m)
- `slope` = 纵坡（小数或 1/N）
- `side_slope` = 边坡系数 m（1:m 中的 m）
- `roughness` = Manning n
- `gate_height` / `gate_width` = 闸门 (m)
- `min_gate_opening` / `max_gate_opening` = 闸门开度 (m)
- `water_demand` = 单次灌水需水量 (m³)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String

from config.database import Base


class CanalBase(Base):
    """
    渠系基础数据表（干/支/斗/农渠参数、闸门、需水量）。

    canal_id 为主键，命名形如 `1` / `1-1` / `1-1-1` / `1-1-1-1`。
    全灌区共享的常量（渠床土壤透水指数/系数、闸门流量系数 μ、淹没系数 σs、侧收缩系数 ε）
    不在此表内。
    """

    __tablename__ = 'agri_canal_v2'
    __table_args__ = {'comment': '渠系基础数据 v2（canal_id 主键）'}

    canal_id = Column(String(64), primary_key=True, nullable=False, comment='渠段编号（主键）')
    canal_name = Column(String(100), nullable=True, comment='渠段名称')
    parent_id = Column(
        String(64), ForeignKey('agri_canal_v2.canal_id', ondelete='SET NULL'),
        nullable=True, comment='父渠段编号（FK self）'
    )
    level = Column(String(8), nullable=True, comment='级别：1 干 / 2 支 / 3 斗 / 4 农')
    length = Column(Numeric(12, 3), nullable=True, comment='渠段长度 (m)')
    design_flow = Column(Numeric(12, 4), nullable=True, comment='设计流量 (m³/s)')
    design_depth = Column(Numeric(8, 4), nullable=True, comment='设计水深 (m)')
    top_width = Column(Numeric(10, 4), nullable=True, comment='设计渠顶宽 (m)')
    bottom_width = Column(Numeric(10, 4), nullable=True, comment='设计渠底宽 (m)')
    slope = Column(Numeric(14, 10), nullable=True, comment='设计纵坡')
    side_slope = Column(Numeric(8, 4), nullable=True, comment='边坡系数 (1:m 中的 m)')
    roughness = Column(Numeric(8, 5), nullable=True, comment='糙率 Manning n')
    gate_height = Column(Numeric(8, 4), nullable=True, comment='闸门高度 (m)')
    gate_width = Column(Numeric(8, 4), nullable=True, comment='闸门宽度 (m)')
    min_gate_opening = Column(Numeric(8, 4), nullable=True, comment='闸门最小开度 (m)')
    max_gate_opening = Column(Numeric(8, 4), nullable=True, comment='闸门最大开度 (m)')
    water_demand = Column(Numeric(18, 4), nullable=True, comment='单次灌水需水量 (m³)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间'
    )
