import hashlib
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from config.env import DataAssetSettings
from exceptions.exception import ServiceException
from module_agriculture.dao.data_asset_dao import DataAssetDao
from module_agriculture.entity.vo.data_asset_vo import DataAssetModel, DataAssetPageQueryModel
from utils.common_util import CamelCaseUtil
from utils.data_asset_util import (
    RASTER_EXTS,
    build_asset_record,
    extract_shapefile_zip,
    is_safe_filename,
    is_supported_upload_extension,
    read_raster_metadata,
    read_vector_metadata,
    validate_shapefile_zip,
)


class DataAssetService:

    @classmethod
    async def get_data_asset_list_services(
        cls, query_db: AsyncSession, query_object: DataAssetPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        return await DataAssetDao.get_data_asset_list(query_db, query_object, is_page)

    @classmethod
    async def data_asset_detail_services(cls, query_db: AsyncSession, asset_id: int) -> DataAssetModel:
        asset = await DataAssetDao.get_data_asset_by_id(query_db, asset_id)
        if not asset:
            raise ServiceException(message='数据资产不存在')
        result = DataAssetModel(**CamelCaseUtil.transform_result(asset))
        return result

    @classmethod
    async def upload_asset_services(
        cls,
        query_db: AsyncSession,
        file: UploadFile,
        data_category: str | None,
        region_name: str | None,
        variable_name: str | None,
        user_id: int | None,
    ) -> CrudResponseModel:
        filename = file.filename or ''
        if not is_safe_filename(filename):
            raise ServiceException(message='文件名不合法')
        if not is_supported_upload_extension(filename):
            raise ServiceException(message='不支持的文件类型，仅支持 .tif/.tiff/.zip')

        _, ext = os.path.splitext(filename)
        lower_ext = ext.lower()

        now = datetime.now()
        date_path = now.strftime('%Y/%m/%d')
        storage_name = f'{uuid.uuid4().hex}{ext}'
        storage_dir = os.path.join(DataAssetSettings.UPLOAD_ROOT, date_path)
        os.makedirs(storage_dir, exist_ok=True)
        storage_path = os.path.join(storage_dir, storage_name)

        sha256 = hashlib.sha256()
        size_bytes = 0
        try:
            async with aiofiles.open(storage_path, 'wb') as f:
                while True:
                    chunk = await file.read(1024 * 1024 * 10)
                    if not chunk:
                        break
                    sha256.update(chunk)
                    size_bytes += len(chunk)
                    await f.write(chunk)
        except Exception as e:
            if os.path.exists(storage_path):
                os.remove(storage_path)
            raise ServiceException(message=f'文件写入失败: {e}')

        if size_bytes == 0:
            os.remove(storage_path)
            raise ServiceException(message='上传文件为空')

        checksum = sha256.hexdigest()
        relative_path = f'assets/{date_path}/{storage_name}'

        try:
            if lower_ext == '.zip':
                validate_shapefile_zip(storage_path)
                tmp_dir = tempfile.mkdtemp()
                shp_path = extract_shapefile_zip(storage_path, tmp_dir)
                metadata = read_vector_metadata(shp_path)
                asset_type = 'vector'
                file_format = 'shp'
                metadata['extra_metadata'] = metadata.get('extra_metadata', {})
                metadata['extra_metadata']['source_zip'] = filename
            elif lower_ext in RASTER_EXTS:
                metadata = read_raster_metadata(storage_path)
                asset_type = 'raster'
                file_format = lower_ext.lstrip('.')
            else:
                metadata = {'extra_metadata': {}}
                asset_type = 'file'
                file_format = lower_ext.lstrip('.')
        except ValueError as e:
            os.remove(storage_path)
            raise ServiceException(message=str(e))
        except Exception as e:
            metadata = {'extra_metadata': {'metadata_error': str(e)}}
            asset_type = 'raster' if lower_ext in RASTER_EXTS else 'file'
            file_format = lower_ext.lstrip('.')

        stem = os.path.splitext(filename)[0]
        asset_record = {
            'asset_type': asset_type,
            'data_category': data_category,
            'region_name': region_name,
            'asset_name': stem,
            'variable_name': variable_name,
            'file_format': file_format,
            'relative_path': relative_path,
            'original_filename': filename,
            'storage_path': storage_path,
            'size_bytes': size_bytes,
            'checksum': checksum,
            'source_type': 'upload',
            'upload_user_id': user_id,
            'crs': metadata.get('crs'),
            'bbox': metadata.get('bbox'),
            'raster_width': metadata.get('raster_width'),
            'raster_height': metadata.get('raster_height'),
            'raster_count': metadata.get('raster_count'),
            'raster_dtype': metadata.get('raster_dtype'),
            'resolution_x': metadata.get('resolution_x'),
            'resolution_y': metadata.get('resolution_y'),
            'nodata_value': metadata.get('nodata_value'),
            'extra_metadata': metadata.get('extra_metadata'),
        }

        try:
            db_asset = await DataAssetDao.add_data_asset(query_db, asset_record)
            await query_db.commit()
            result = DataAssetModel(**CamelCaseUtil.transform_result(db_asset))
            return CrudResponseModel(is_success=True, result=result, message='上传成功')
        except Exception as e:
            await query_db.rollback()
            if os.path.exists(storage_path):
                os.remove(storage_path)
            raise e

    @classmethod
    async def resolve_download_services(cls, query_db: AsyncSession, asset_id: int) -> tuple[str, str]:
        asset = await DataAssetDao.get_data_asset_by_id(query_db, asset_id)
        if not asset:
            raise ServiceException(message='数据资产不存在')

        if asset.storage_path and os.path.isfile(asset.storage_path):
            filepath = asset.storage_path
        elif asset.relative_path:
            candidate = os.path.join(DataAssetSettings.DATA_DIR, asset.relative_path)
            if os.path.isfile(candidate):
                filepath = candidate
            else:
                raise ServiceException(message='文件不存在或已被移除')
        else:
            raise ServiceException(message='文件路径无效')

        real_path = os.path.realpath(filepath)
        allowed_roots = [
            os.path.realpath(DataAssetSettings.UPLOAD_ROOT),
            os.path.realpath(DataAssetSettings.DATA_DIR),
        ]
        if not any(real_path.startswith(root) for root in allowed_roots):
            raise ServiceException(message='文件路径不在允许范围内')

        download_name = asset.original_filename or os.path.basename(asset.relative_path)
        return filepath, download_name

    @classmethod
    async def delete_asset_services(cls, query_db: AsyncSession, ids: str) -> CrudResponseModel:
        try:
            id_list = [int(i) for i in ids.split(',')]
        except ValueError:
            raise ServiceException(message='ID格式不合法')

        try:
            assets = await DataAssetDao.soft_delete_assets(query_db, id_list)
            if not assets:
                raise ServiceException(message='未找到可删除的资产')

            for asset in assets:
                if asset.source_type == 'upload' and asset.storage_path:
                    real_path = os.path.realpath(asset.storage_path)
                    upload_root = os.path.realpath(DataAssetSettings.UPLOAD_ROOT)
                    if real_path.startswith(upload_root) and os.path.isfile(real_path):
                        os.remove(real_path)

            await query_db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except ServiceException:
            await query_db.rollback()
            raise
        except Exception as e:
            await query_db.rollback()
            raise e
