from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text

from config.database import Base


class Station(Base):
    """
    监测站信息表
    """

    __tablename__ = 'station'
    __table_args__ = {'comment': '监测站信息'}

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, unique=True, comment='气象站编码')
    name = Column(String(50), nullable=False, comment='站点名称')
    latitude = Column(Numeric(8, 4), nullable=True, comment='纬度')
    longitude = Column(Numeric(8, 4), nullable=True, comment='经度')
    altitude = Column(Numeric(8, 2), nullable=True, comment='海拔(m)')
    description = Column(Text, nullable=True, comment='描述')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
