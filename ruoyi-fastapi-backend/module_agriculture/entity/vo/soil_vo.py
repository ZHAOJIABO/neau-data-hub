from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class SoilSensorModel(BaseModel):
    """
    传感器监测数据pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    device_name: str | None = Field(default=None, description='设备序列号')
    depth_cm: int | None = Field(default=None, description='监测深度(cm)')
    temperature: Decimal | None = Field(default=None, description='温度(℃)')
    humidity: Decimal | None = Field(default=None, description='湿度(%)')
    conductivity: Decimal | None = Field(default=None, description='电导率(μs/cm)')
    obs_time: datetime | None = Field(default=None, description='上报时间')
    created_at: datetime | None = Field(default=None, description='创建时间')


class SoilSensorPageQueryModel(BaseModel):
    """
    传感器监测数据分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    device_name: str | None = Field(default=None, description='设备序列号')
    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class SoilParameterModel(BaseModel):
    """
    土壤水文参数pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    source: str | None = Field(default=None, description='来源(k/k1/k2)')
    fid: int | None = Field(default=None, description='FID')
    grid_id: int | None = Field(default=None, description='网格ID')
    grid_no: int | None = Field(default=None, description='网格编号')
    crop: int | None = Field(default=None, description='作物类型')
    oc_0_5: Decimal | None = Field(default=None, description='有机碳')
    sand_0_5: Decimal | None = Field(default=None, description='砂粒')
    clay_0_5: Decimal | None = Field(default=None, description='粘粒')
    silt_0_5: Decimal | None = Field(default=None, description='粉粒')
    bulk_density: Decimal | None = Field(default=None, description='容重')
    k_value: Decimal | None = Field(default=None, description='K值')
    moisture_content: Decimal | None = Field(default=None, description='含水量')
    saturated_moisture_content: Decimal | None = Field(default=None, description='饱和含水量')
    saturated_matrix_potential: Decimal | None = Field(default=None, description='饱和基质势')
    campbell: Decimal | None = Field(default=None, description='Campbell参数')
    field_capacity: Decimal | None = Field(default=None, description='田间持水量')
    wilting_coefficient: Decimal | None = Field(default=None, description='凋萎系数')
    saturated_hydraulic_conductivity: Decimal | None = Field(default=None, description='饱和导水率')
    thermal_conductivity: Decimal | None = Field(default=None, description='热导率')
    specific_heat_capacity: Decimal | None = Field(default=None, description='比热容')
    steady_state_infiltration_rate: Decimal | None = Field(default=None, description='稳渗率')
    dem: Decimal | None = Field(default=None, description='高程')
    created_at: datetime | None = Field(default=None, description='创建时间')


class SoilParameterPageQueryModel(BaseModel):
    """
    土壤水文参数分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    source: str | None = Field(default=None, description='来源(k/k1/k2)')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class SoilGroundTempModel(BaseModel):
    """
    地温数据pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    obs_date: date | None = Field(default=None, description='观测日期')
    depth_cm: int | None = Field(default=None, description='深度(cm)')
    temperature: Decimal | None = Field(default=None, description='地温(℃)')
    created_at: datetime | None = Field(default=None, description='创建时间')


class SoilGroundTempPageQueryModel(BaseModel):
    """
    地温数据分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    start_date: str | None = Field(default=None, description='开始日期')
    end_date: str | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class SoilThicknessModel(BaseModel):
    """
    黑土厚度pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    point_id: str | None = Field(default=None, description='监测点编号')
    point_x: Decimal | None = Field(default=None, description='经度')
    point_y: Decimal | None = Field(default=None, description='纬度')
    black_soil_depth_cm: int | None = Field(default=None, description='黑土厚度(cm)')
    created_at: datetime | None = Field(default=None, description='创建时间')


class SoilThicknessPageQueryModel(BaseModel):
    """
    黑土厚度分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class SoilLayerStatsModel(BaseModel):
    """
    分层统计pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    layer_depth: str | None = Field(default=None, description='土层深度')
    max_value: Decimal | None = Field(default=None, description='最大值')
    min_value: Decimal | None = Field(default=None, description='最小值')
    mean_value: Decimal | None = Field(default=None, description='均值')
    std_dev: Decimal | None = Field(default=None, description='标准偏差')
    cv: Decimal | None = Field(default=None, description='变异系数')
    created_at: datetime | None = Field(default=None, description='创建时间')


class SoilLayerStatsPageQueryModel(BaseModel):
    """
    分层统计分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
