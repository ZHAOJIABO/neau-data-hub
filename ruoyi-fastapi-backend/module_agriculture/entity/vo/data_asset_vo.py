from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class DataAssetModel(BaseModel):

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    asset_type: str | None = Field(default=None, description='资产类型')
    data_category: str | None = Field(default=None, description='数据分类')
    region_name: str | None = Field(default=None, description='区域名称')
    asset_name: str | None = Field(default=None, description='数据名称')
    variable_name: str | None = Field(default=None, description='变量名称')
    obs_date: date | None = Field(default=None, description='观测日期')
    file_format: str | None = Field(default=None, description='文件格式')
    relative_path: str | None = Field(default=None, description='相对路径')
    original_filename: str | None = Field(default=None, description='原始文件名')
    storage_path: str | None = Field(default=None, description='存储路径')
    size_bytes: int | None = Field(default=None, description='文件大小(字节)')
    checksum: str | None = Field(default=None, description='SHA-256校验和')
    source_type: str | None = Field(default=None, description='来源类型')
    upload_user_id: int | None = Field(default=None, description='上传用户ID')
    crs: str | None = Field(default=None, description='坐标参考系')
    bbox: dict | None = Field(default=None, description='边界框')
    raster_width: int | None = Field(default=None, description='栅格宽度')
    raster_height: int | None = Field(default=None, description='栅格高度')
    raster_count: int | None = Field(default=None, description='波段数')
    raster_dtype: str | None = Field(default=None, description='栅格数据类型')
    resolution_x: float | None = Field(default=None, description='X方向分辨率')
    resolution_y: float | None = Field(default=None, description='Y方向分辨率')
    nodata_value: float | None = Field(default=None, description='无数据值')
    extra_metadata: dict | None = Field(default=None, description='扩展元数据')
    created_at: datetime | None = Field(default=None, description='创建时间')
    updated_at: datetime | None = Field(default=None, description='更新时间')
    deleted_at: datetime | None = Field(default=None, description='软删除时间')


class DataAssetPageQueryModel(BaseModel):

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
    asset_name: str | None = Field(default=None, description='文件名称')
    relative_path: str | None = Field(default=None, description='相对路径')
    asset_type: str | None = Field(default=None, description='资产类型')
    file_format: str | None = Field(default=None, description='文件格式')
    data_category: str | None = Field(default=None, description='数据分类')
    region_name: str | None = Field(default=None, description='区域名称')
    variable_name: str | None = Field(default=None, description='变量名称')
    obs_date_begin: date | None = Field(default=None, description='观测日期起')
    obs_date_end: date | None = Field(default=None, description='观测日期止')


class DeleteDataAssetModel(BaseModel):

    model_config = ConfigDict(alias_generator=to_camel)

    ids: str = Field(description='需要删除的资产ID')
