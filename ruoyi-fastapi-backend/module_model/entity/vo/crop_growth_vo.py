from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class RiceGrowthSiteParamsModel(BaseModel):
    """
    WOFOST 站点水文参数。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    ifunrn: float = Field(default=0, description='是否根据雨量计算非入渗率')
    notinf: float = Field(default=0.0, ge=0, le=1, description='最大非入渗雨量比例')
    ssi: float = Field(default=0.0, ge=0, description='初始地表储水深度(cm)')
    ssmax: float = Field(default=0.0, ge=0, description='地表最大储水深度(cm)')
    wav: float = Field(default=20.0, ge=0, description='初始土壤总含水量(cm)')
    smlim: float = Field(default=0.4, ge=0, le=1, description='初始根区最大含水量')


class RiceGrowthSimulationRequest(BaseModel):
    """
    水稻作物生长模拟请求。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    longitude: float = Field(description='经度')
    latitude: float = Field(description='纬度')
    simulation_start_date: str = Field(description='模拟开始日期 YYYY-MM-DD')
    plant_start_date: str = Field(description='作物开始日期 YYYY-MM-DD')
    plant_end_date: str = Field(description='作物结束/收获日期 YYYY-MM-DD')
    irrigation_end_date: str = Field(description='灌溉结束日期 YYYY-MM-DD')
    soil_moisture_threshold: float = Field(default=0.32, gt=0, lt=1, description='土壤水分触发阈值')
    irrigation_efficiency: float = Field(default=0.75, gt=0, le=1, description='灌溉效率')
    single_irrigation_amount: float = Field(default=3.0, ge=0, description='单次灌溉水层(cm)')
    site: RiceGrowthSiteParamsModel = Field(default_factory=RiceGrowthSiteParamsModel, description='站点参数')
    variety_name: str = Field(default='Rice_IR72_WS', description='rice.crop 中的水稻品种名')

    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if value < -180 or value > 180:
            raise ValueError('经度必须在 -180 到 180 之间')
        return value

    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if value < -90 or value > 90:
            raise ValueError('纬度必须在 -90 到 90 之间')
        return value


class RiceGrowthDailyResult(BaseModel):
    """
    水稻逐日模拟结果。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    day: str = Field(description='日期')
    dvs: float | None = Field(default=None, description='发育阶段')
    lai: float | None = Field(default=None, description='叶面积指数')
    tagp: float | None = Field(default=None, description='地上部总干物质')
    twso: float | None = Field(default=None, description='贮藏器官干物质')
    twlv: float | None = Field(default=None, description='叶干物质')
    twst: float | None = Field(default=None, description='茎干物质')
    twrt: float | None = Field(default=None, description='根干物质')
    tra: float | None = Field(default=None, description='实际蒸腾')
    rd: float | None = Field(default=None, description='根深')
    sm: float | None = Field(default=None, description='土壤含水量')
    wwlow: float | None = Field(default=None, description='根区水量')
    rftra: float | None = Field(default=None, description='蒸腾胁迫因子')
    rirr: float | None = Field(default=None, description='当日实际施加灌溉量(cm)')
    totirr: float | None = Field(default=None, description='累计实际施加灌溉量(cm)')


class RiceGrowthSummary(BaseModel):
    """
    水稻模拟汇总。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    simulation_days: int = Field(description='模拟天数')
    final_yield: float | None = Field(default=None, description='最终产量指标(TWSO)')
    final_lai: float | None = Field(default=None, description='最终 LAI')
    max_lai: float | None = Field(default=None, description='最大 LAI')
    final_tagp: float | None = Field(default=None, description='最终地上部总干物质')
    total_irrigation: float = Field(default=0.0, description='累计灌溉量')
    irrigation_count: int = Field(default=0, description='灌溉事件次数')
    variety_name: str = Field(description='使用的水稻品种名')
    weather_source: str = Field(default='NASA POWER', description='气象数据源')


class RiceGrowthSimulationResponse(BaseModel):
    """
    水稻作物生长模拟响应。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    summary: RiceGrowthSummary = Field(description='汇总结果')
    daily_results: list[RiceGrowthDailyResult] = Field(description='逐日模拟结果')
