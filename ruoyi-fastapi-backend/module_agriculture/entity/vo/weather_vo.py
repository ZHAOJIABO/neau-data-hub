from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class WeatherTemperatureModel(BaseModel):
    """
    温度数据pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    stcd: str | None = Field(default=None, description='气象站编码')
    obs_date: date | None = Field(default=None, description='观测日期')
    tmax: Decimal | None = Field(default=None, description='日最高温度(℃)')
    tmin: Decimal | None = Field(default=None, description='日最低温度(℃)')
    tmean: Decimal | None = Field(default=None, description='日平均温度(℃)')
    created_at: datetime | None = Field(default=None, description='创建时间')


class WeatherTemperaturePageQueryModel(BaseModel):
    """
    温度数据分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    stcd: str | None = Field(default=None, description='气象站编码')
    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class WeatherHumidityModel(BaseModel):
    """
    湿度数据pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    stcd: str | None = Field(default=None, description='气象站编码')
    obs_date: date | None = Field(default=None, description='观测日期')
    rh_mean: Decimal | None = Field(default=None, description='日平均相对湿度(%)')
    created_at: datetime | None = Field(default=None, description='创建时间')


class WeatherHumidityPageQueryModel(BaseModel):
    """
    湿度数据分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    stcd: str | None = Field(default=None, description='气象站编码')
    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class WeatherPrecipitationModel(BaseModel):
    """
    降水数据pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    stcd: str | None = Field(default=None, description='气象站编码')
    obs_date: date | None = Field(default=None, description='观测日期')
    precipitation: Decimal | None = Field(default=None, description='日降水量(mm)')
    created_at: datetime | None = Field(default=None, description='创建时间')


class WeatherPrecipitationPageQueryModel(BaseModel):
    """
    降水数据分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    stcd: str | None = Field(default=None, description='气象站编码')
    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class WeatherOverviewModel(BaseModel):
    """
    气象综合视图数据模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    station_name: str | None = Field(default=None, description='站点名称')
    stcd: str | None = Field(default=None, description='气象站编码')
    obs_date: date | None = Field(default=None, description='观测日期')
    tmax: Decimal | None = Field(default=None, description='日最高温度(℃)')
    tmin: Decimal | None = Field(default=None, description='日最低温度(℃)')
    tmean: Decimal | None = Field(default=None, description='日平均温度(℃)')
    rh_mean: Decimal | None = Field(default=None, description='日平均相对湿度(%)')
    precipitation: Decimal | None = Field(default=None, description='日降水量(mm)')
    sunshine_hours: Decimal | None = Field(default=None, description='日照时数(h)')
    wind_speed: Decimal | None = Field(default=None, description='日平均风速(m/s)')


class WeatherOverviewPageQueryModel(BaseModel):
    """
    气象综合视图分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    stcd: str | None = Field(default=None, description='气象站编码')
    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class DeleteWeatherModel(BaseModel):
    """
    删除气象数据模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    ids: str = Field(description='需要删除的记录ID')
