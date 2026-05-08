from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String

from config.database import Base


class CropLeafArea(Base):
    """
    大豆叶面积指数表
    """

    __tablename__ = 'crop_leaf_area'
    __table_args__ = {'comment': '大豆叶面积指数'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    plot = Column(String(20), nullable=False, comment='小区编号')
    obs_date = Column(String(10), nullable=True, comment='观测日期(月.日格式)')
    plant_no = Column(Integer, nullable=True, comment='植株序号')
    density = Column(Integer, nullable=True, comment='密度(株)')
    leaf_area_1 = Column(Numeric(10, 6), nullable=True, comment='叶面积值1')
    leaf_area_2 = Column(Numeric(10, 6), nullable=True, comment='叶面积值2')
    leaf_area_3 = Column(Numeric(10, 6), nullable=True, comment='叶面积值3')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
