from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class StationModel(BaseModel):
    """
    站点信息pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    stcd: str | None = Field(default=None, description='气象站编码')
    name: str | None = Field(default=None, description='站点名称')
    latitude: Decimal | None = Field(default=None, description='纬度')
    longitude: Decimal | None = Field(default=None, description='经度')
    altitude: Decimal | None = Field(default=None, description='海拔(m)')
    description: str | None = Field(default=None, description='描述')
    created_at: datetime | None = Field(default=None, description='创建时间')


class StationPageQueryModel(StationModel):
    """
    站点分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class DeleteStationModel(BaseModel):
    """
    删除站点模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    ids: str = Field(description='需要删除的站点ID')
