import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module_agriculture.service.data_asset_service import DataAssetService


class TestDataAssetServiceUploadValidation:

    @pytest.mark.asyncio
    async def test_reject_unsafe_filename(self):
        db = AsyncMock()
        file = MagicMock()
        file.filename = '../evil.tif'
        with pytest.raises(Exception, match='文件名不合法'):
            await DataAssetService.upload_asset_services(db, file, None, None, None, None)

    @pytest.mark.asyncio
    async def test_reject_unsupported_extension(self):
        db = AsyncMock()
        file = MagicMock()
        file.filename = 'malware.exe'
        with pytest.raises(Exception, match='不支持的文件类型'):
            await DataAssetService.upload_asset_services(db, file, None, None, None, None)

    @pytest.mark.asyncio
    async def test_reject_empty_filename(self):
        db = AsyncMock()
        file = MagicMock()
        file.filename = ''
        with pytest.raises(Exception, match='文件名不合法'):
            await DataAssetService.upload_asset_services(db, file, None, None, None, None)


class TestDataAssetServiceDeletePolicy:

    @pytest.mark.asyncio
    async def test_delete_import_only_soft_deletes(self):
        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.source_type = 'import'
        mock_asset.storage_path = None

        db = AsyncMock()
        with patch(
            'module_agriculture.service.data_asset_service.DataAssetDao.soft_delete_assets',
            return_value=[mock_asset],
        ):
            result = await DataAssetService.delete_asset_services(db, '1')
            assert result.is_success

    @pytest.mark.asyncio
    async def test_delete_upload_removes_file(self, tmp_path):
        test_file = tmp_path / 'test.tif'
        test_file.write_bytes(b'\x00' * 100)

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.source_type = 'upload'
        mock_asset.storage_path = str(test_file)

        db = AsyncMock()
        with (
            patch(
                'module_agriculture.service.data_asset_service.DataAssetDao.soft_delete_assets',
                return_value=[mock_asset],
            ),
            patch(
                'module_agriculture.service.data_asset_service.DataAssetSettings.UPLOAD_ROOT',
                str(tmp_path),
            ),
        ):
            result = await DataAssetService.delete_asset_services(db, '1')
            assert result.is_success
            assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_refuses_outside_upload_root(self, tmp_path):
        outside_dir = tmp_path / 'outside'
        outside_dir.mkdir()
        test_file = outside_dir / 'important.tif'
        test_file.write_bytes(b'\x00' * 100)

        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.source_type = 'upload'
        mock_asset.storage_path = str(test_file)

        db = AsyncMock()
        upload_root = tmp_path / 'managed'
        upload_root.mkdir()

        with (
            patch(
                'module_agriculture.service.data_asset_service.DataAssetDao.soft_delete_assets',
                return_value=[mock_asset],
            ),
            patch(
                'module_agriculture.service.data_asset_service.DataAssetSettings.UPLOAD_ROOT',
                str(upload_root),
            ),
        ):
            result = await DataAssetService.delete_asset_services(db, '1')
            assert result.is_success
            assert test_file.exists()


class TestDataAssetServiceDownload:

    @pytest.mark.asyncio
    async def test_download_missing_asset(self):
        db = AsyncMock()
        with patch(
            'module_agriculture.service.data_asset_service.DataAssetDao.get_data_asset_by_id',
            return_value=None,
        ):
            with pytest.raises(Exception, match='数据资产不存在'):
                await DataAssetService.resolve_download_services(db, 999)
