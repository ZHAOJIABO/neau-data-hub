from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class WaterFertilizerRegulationModel(BaseModel):
    """
    水肥调控时序数据响应模型。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    id: str | None = Field(default=None, description='主键ID')
    daily_effective_rainfall: Decimal | None = Field(default=None, description='日有效降雨(mm)')
    daily_max_crop_evapotranspiration: Decimal | None = Field(default=None, description='日最大作物蒸散发量(mm)')
    daily_min_crop_evapotranspiration: Decimal | None = Field(default=None, description='日最小作物蒸散发量(mm)')
    max_water_storage_depth: Decimal | None = Field(default=None, description='最大蓄水深度(mm)')
    max_suitable_water_depth: Decimal | None = Field(default=None, description='最大适宜水深(mm)')
    min_suitable_water_depth: Decimal | None = Field(default=None, description='最小适宜水深(mm)')
    record_time: date | None = Field(default=None, description='记录日期')
    create_by: str | None = Field(default=None, description='创建人')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新人')
    update_time: datetime | None = Field(default=None, description='更新时间')


class WaterFertilizerRegulationPageQueryModel(BaseModel):
    """
    水肥调控时序数据分页查询模型。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    start_date: date | None = Field(default=None, description='开始日期')
    end_date: date | None = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, ge=1, description='当前页码')
    page_size: int = Field(default=10, ge=1, le=500, description='每页记录数')

    @model_validator(mode='after')
    def validate_date_range(self) -> 'WaterFertilizerRegulationPageQueryModel':
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('开始日期不能晚于结束日期')
        return self


class WaterFertilizerOptimizeRequest(BaseModel):
    """
    水肥调控 NSGA-III 优化请求。
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    yield_max: float = Field(gt=0, description='最大产量(kg/hm²)')
    max_irrigation: float = Field(gt=0, description='每日最大灌溉量(mm)')
    water_efficiency: float = Field(gt=0, description='水分利用效率')
    paddy_water: float = Field(ge=0, description='泡田期净灌溉水量(mm)')
    leakage: float = Field(ge=0, description='深层渗漏量(mm)')
    b0: float = Field(description='产量响应函数系数b0')
    b1: float = Field(description='产量响应函数系数b1')
    b2: float = Field(description='产量响应函数系数b2')
    c: float = Field(description='产量响应函数系数c')
    nitrogen_base: float = Field(ge=0, description='播种前含氮量(kg/hm²)')
    nitrogen_optimal: float = Field(gt=0, description='最优施氮量(kg/hm²)')
    nitrogen_max: float = Field(gt=0, description='最大施氮量(kg/hm²)')
    nitrogen_min: float = Field(ge=0, description='最小施氮量(kg/hm²)')
    population_size: int = Field(default=80, ge=20, le=600, description='种群大小')
    generations: int = Field(default=60, ge=1, le=2000, description='进化代数')
    start_date: date = Field(description='开始日期')
    end_date: date = Field(description='结束日期')

    @model_validator(mode='after')
    def validate_bounds(self) -> 'WaterFertilizerOptimizeRequest':
        if self.start_date > self.end_date:
            raise ValueError('开始日期不能晚于结束日期')
        if self.nitrogen_min > self.nitrogen_max:
            raise ValueError('最小施氮量不能大于最大施氮量')
        if self.nitrogen_optimal > self.nitrogen_max:
            raise ValueError('最优施氮量不能大于最大施氮量')
        return self
