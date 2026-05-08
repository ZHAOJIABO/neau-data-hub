from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, Numeric, String

from config.database import Base


class WeatherTemperature(Base):
    """
    每日温度表
    """

    __tablename__ = 'weather_temperature'
    __table_args__ = {'comment': '每日温度'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, comment='气象站编码')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    tmax = Column(Numeric(6, 2), nullable=True, comment='日最高温度(℃)')
    tmin = Column(Numeric(6, 2), nullable=True, comment='日最低温度(℃)')
    tmean = Column(Numeric(6, 2), nullable=True, comment='日平均温度(℃)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class WeatherHumidity(Base):
    """
    每日相对湿度表
    """

    __tablename__ = 'weather_humidity'
    __table_args__ = {'comment': '每日相对湿度'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, comment='气象站编码')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    rh_mean = Column(Numeric(6, 2), nullable=True, comment='日平均相对湿度(%)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class WeatherPrecipitation(Base):
    """
    每日降水量表
    """

    __tablename__ = 'weather_precipitation'
    __table_args__ = {'comment': '每日降水量'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, comment='气象站编码')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    precipitation = Column(Numeric(8, 2), nullable=True, comment='日降水量(mm)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class WeatherSunshine(Base):
    """
    每日日照时数表
    """

    __tablename__ = 'weather_sunshine'
    __table_args__ = {'comment': '每日日照时数'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, comment='气象站编码')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    sunshine_hours = Column(Numeric(6, 2), nullable=True, comment='日照时数(h)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class WeatherWind(Base):
    """
    每日风速表
    """

    __tablename__ = 'weather_wind'
    __table_args__ = {'comment': '每日风速'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, comment='气象站编码')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    wind_speed = Column(Numeric(6, 2), nullable=True, comment='日平均风速(m/s)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')


class WeatherEt0(Base):
    """
    每日ET0参考蒸散量表
    """

    __tablename__ = 'weather_et0'
    __table_args__ = {'comment': '每日ET0参考蒸散量'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    stcd = Column(String(10), nullable=False, comment='气象站编码')
    obs_date = Column(Date, nullable=False, comment='观测日期')
    tmean = Column(Numeric(6, 2), nullable=True, comment='日平均温度(℃)')
    precip = Column(Numeric(8, 2), nullable=True, comment='日降水量(mm)')
    et0 = Column(Numeric(8, 6), nullable=True, comment='参考蒸散量ET0(mm/d)')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
