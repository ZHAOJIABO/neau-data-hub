from sqlalchemy import Column, Date, DateTime, Numeric, String

from config.database import Base


class WaterFertilizerRegulation(Base):
    """
    水肥调控时序数据表。
    """

    __tablename__ = 'water_fertilizer_regulation'
    __table_args__ = {'comment': '水肥调控数据表'}

    id = Column(String, primary_key=True, nullable=False, comment='主键ID')
    daily_effective_rainfall = Column(Numeric, nullable=False, comment='日有效降雨(mm)')
    daily_max_crop_evapotranspiration = Column(Numeric, nullable=False, comment='日最大作物蒸散发量(mm)')
    daily_min_crop_evapotranspiration = Column(Numeric, nullable=False, comment='日最小作物蒸散发量(mm)')
    max_water_storage_depth = Column(Numeric, nullable=False, comment='最大蓄水深度(mm)')
    max_suitable_water_depth = Column(Numeric, nullable=False, comment='最大适宜水深(mm)')
    min_suitable_water_depth = Column(Numeric, nullable=False, comment='最小适宜水深(mm)')
    record_time = Column(Date, nullable=False, comment='记录日期')
    create_by = Column(String, nullable=True, comment='创建人')
    create_time = Column(DateTime, nullable=True, comment='创建时间')
    update_by = Column(String, nullable=True, comment='更新人')
    update_time = Column(DateTime, nullable=True, comment='更新时间')
