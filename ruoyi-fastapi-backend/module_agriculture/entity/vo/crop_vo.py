from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CropLeafAreaModel(BaseModel):
    """
    叶面积指数pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    plot: str | None = Field(default=None, description='小区编号')
    obs_date: str | None = Field(default=None, description='观测日期(月.日格式)')
    plant_no: int | None = Field(default=None, description='植株序号')
    density: int | None = Field(default=None, description='密度(株)')
    leaf_area_1: Decimal | None = Field(default=None, description='叶面积值1')
    leaf_area_2: Decimal | None = Field(default=None, description='叶面积值2')
    leaf_area_3: Decimal | None = Field(default=None, description='叶面积值3')
    created_at: datetime | None = Field(default=None, description='创建时间')


class CropLeafAreaPageQueryModel(BaseModel):
    """
    叶面积指数分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    plot: str | None = Field(default=None, description='小区编号')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
