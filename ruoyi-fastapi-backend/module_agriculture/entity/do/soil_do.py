from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Integer, Numeric, String

from config.database import Base


class SoilParameter(Base):
    """
    土壤水文参数表(k/k1/k2)
    """

    __tablename__ = 'soil_parameter'
    __table_args__ = {'comment': '土壤水文参数(k/k1/k2)'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    source = Column(String(10), nullable=False, comment='来源(k/k1/k2)')
    fid = Column(Integer, nullable=True, comment='FID')
    grid_id = Column(Integer, nullable=True, comment='网格ID')
    grid_no = Column(Integer, nullable=True, comment='网格编号')
    crop = Column(Integer, nullable=True, comment='作物类型')
    oc_0_5 = Column(Numeric(12, 4), nullable=True, comment='有机碳')
    sand_0_5 = Column(Numeric(12, 4), nullable=True, comment='砂粒')
    clay_0_5 = Column(Numeric(12, 4), nullable=True, comment='粘粒')
    silt_0_5 = Column(Numeric(12, 4), nullable=True, comment='粉粒')
    bulk_density = Column(Numeric(8, 4), nullable=True, comment='容重')
    k_value = Column(Numeric(12, 6), nullable=True, comment='K值')
    moisture_content = Column(Numeric(8, 4), nullable=True, comment='含水量')
    saturated_moisture_content = Column(Numeric(8, 6), nullable=True, comment='饱和含水量')
    saturated_matrix_potential = Column(Numeric(12, 6), nullable=True, comment='饱和基质势')
    campbell = Column(Numeric(12, 5), nullable=True, comment='Campbell参数')
    field_capacity = Column(Numeric(8, 6), nullable=True, comment='田间持水量')
    wilting_coefficient = Column(Numeric(8, 6), nullable=True, comment='凋萎系数')
    saturated_hydraulic_conductivity = Column(Numeric(12, 6), nullable=True, comment='饱和导水率')
    thermal_conductivity = Column(Numeric(8, 6), nullable=True, comment='热导率')
    specific_heat_capacity = Column(Numeric(8, 6), nullable=True, comment='比热容')
    steady_state_infiltration_rate = Column(Numeric(12, 6), nullable=True, comment='稳渗率')
    dem = Column(Numeric(10, 6), nullable=True, comment='高程')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class SoilSensorMonitor(Base):
    """
    传感器监测数据表
    """

    __tablename__ = 'soil_sensor_monitor'
    __table_args__ = {'comment': '传感器监测数据(每2小时)'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    device_name = Column(String(50), nullable=False, comment='设备序列号')
    depth_cm = Column(Integer, nullable=False, comment='监测深度(cm)')
    temperature = Column(Numeric(6, 2), nullable=True, comment='温度(℃)')
    humidity = Column(Numeric(8, 3), nullable=True, comment='湿度(%)')
    conductivity = Column(Numeric(10, 2), nullable=True, comment='电导率(μs/cm)')
    obs_time = Column(DateTime, nullable=False, comment='上报时间')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class SoilGroundTemperature(Base):
    """
    分层地温表
    """

    __tablename__ = 'soil_ground_temperature'
    __table_args__ = {'comment': '分层地温(10-200cm)'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    depth_cm = Column(Integer, nullable=False, comment='深度(cm)')
    temperature = Column(Numeric(6, 2), nullable=True, comment='地温(℃)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class SoilLayerStats(Base):
    """
    各土层含水量统计表
    """

    __tablename__ = 'soil_layer_stats'
    __table_args__ = {'comment': '各土层含水量统计'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    layer_depth = Column(String(20), nullable=False, comment='土层深度')
    max_value = Column(Numeric(10, 6), nullable=True, comment='最大值')
    min_value = Column(Numeric(10, 6), nullable=True, comment='最小值')
    mean_value = Column(Numeric(10, 6), nullable=True, comment='均值')
    std_dev = Column(Numeric(10, 6), nullable=True, comment='标准偏差')
    cv = Column(Numeric(10, 6), nullable=True, comment='变异系数')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class SoilThickness(Base):
    """
    监测点黑土厚度表
    """

    __tablename__ = 'soil_thickness'
    __table_args__ = {'comment': '监测点黑土厚度'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    point_id = Column(String(20), nullable=False, comment='监测点编号')
    point_x = Column(Numeric(12, 6), nullable=False, comment='经度')
    point_y = Column(Numeric(12, 6), nullable=False, comment='纬度')
    black_soil_depth_cm = Column(Integer, nullable=False, comment='黑土厚度(cm)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
