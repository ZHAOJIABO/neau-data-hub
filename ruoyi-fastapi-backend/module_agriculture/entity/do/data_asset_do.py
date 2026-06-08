from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from config.database import Base


class DataAsset(Base):

    __tablename__ = 'data_asset'
    __table_args__ = {'comment': '非表格空间/文件数据资产索引'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    asset_type = Column(String(20), nullable=False, comment='资产类型 raster/vector/file')
    data_category = Column(String(50), nullable=True, comment='数据分类')
    region_name = Column(String(50), nullable=True, comment='区域名称')
    asset_name = Column(String(200), nullable=False, comment='数据名称')
    variable_name = Column(String(50), nullable=True, comment='变量名称')
    obs_date = Column(DateTime, nullable=True, comment='观测日期')
    file_format = Column(String(20), nullable=False, comment='文件格式')
    relative_path = Column(Text, nullable=False, unique=True, comment='相对路径')
    original_filename = Column(String(255), nullable=True, comment='原始文件名')
    storage_path = Column(Text, nullable=True, comment='受管存储路径')
    size_bytes = Column(BigInteger, nullable=True, comment='文件大小(字节)')
    checksum = Column(String(64), nullable=True, comment='SHA-256校验和')
    source_type = Column(String(20), nullable=False, default='import', comment='来源类型 import/upload')
    upload_user_id = Column(BigInteger, nullable=True, comment='上传用户ID')
    crs = Column(Text, nullable=True, comment='坐标参考系')
    bbox = Column(JSONB, nullable=True, comment='边界框')
    raster_width = Column(Integer, nullable=True, comment='栅格宽度')
    raster_height = Column(Integer, nullable=True, comment='栅格高度')
    raster_count = Column(Integer, nullable=True, comment='波段数')
    raster_dtype = Column(String(50), nullable=True, comment='栅格数据类型')
    resolution_x = Column(Float, nullable=True, comment='X方向分辨率')
    resolution_y = Column(Float, nullable=True, comment='Y方向分辨率')
    nodata_value = Column(Float, nullable=True, comment='无数据值')
    extra_metadata = Column(JSONB, nullable=True, comment='扩展元数据')
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    deleted_at = Column(DateTime, nullable=True, comment='软删除时间')
