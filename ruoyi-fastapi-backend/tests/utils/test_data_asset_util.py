import os
import tempfile
import zipfile
from datetime import date

import pytest

from utils.data_asset_util import (
    classify_asset_path,
    is_safe_filename,
    is_supported_upload_extension,
    read_raster_metadata,
    validate_shapefile_zip,
)


class TestClassifyAssetPath:

    def test_weather_raster(self, tmp_path):
        data_dir = str(tmp_path)
        subdir = tmp_path / '气象数据' / '浓江农场'
        subdir.mkdir(parents=True)
        filepath = subdir / 'RAIN_2024-07-01.tif'
        filepath.write_bytes(b'\x00' * 100)

        result = classify_asset_path(data_dir, str(filepath))

        assert result['asset_type'] == 'raster'
        assert result['data_category'] == '气象数据'
        assert result['region_name'] == '浓江农场'
        assert result['variable_name'] == 'RAIN'
        assert result['obs_date'] == date(2024, 7, 1)
        assert result['file_format'] == 'tif'
        assert result['relative_path'] == '气象数据/浓江农场/RAIN_2024-07-01.tif'

    def test_dem_file(self, tmp_path):
        data_dir = str(tmp_path)
        subdir = tmp_path / '自然地理数据' / '鹤北小流域'
        subdir.mkdir(parents=True)
        filepath = subdir / 'DEM_30m.tif'
        filepath.write_bytes(b'\x00' * 50)

        result = classify_asset_path(data_dir, str(filepath))

        assert result['variable_name'] == 'DEM'
        assert result['region_name'] == '鹤北小流域'
        assert result['data_category'] == '自然地理数据'

    def test_land_use_file(self, tmp_path):
        data_dir = str(tmp_path)
        subdir = tmp_path / '土地利用' / '鹤北小流域'
        subdir.mkdir(parents=True)
        filepath = subdir / 'TDLY_2020.tif'
        filepath.write_bytes(b'\x00' * 50)

        result = classify_asset_path(data_dir, str(filepath))

        assert result['variable_name'] == '土地利用'


class TestReadRasterMetadata:

    def test_missing_rasterio(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'rasterio':
                raise ImportError('mocked')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', mock_import)
        result = read_raster_metadata('/fake/path.tif')
        assert 'metadata_warning' in result['extra_metadata']

    def test_file_not_found(self):
        result = read_raster_metadata('/nonexistent/file.tif')
        assert result['extra_metadata'].get('metadata_error') or result['extra_metadata'].get('metadata_warning')


class TestValidateShapefileZip:

    def test_valid_zip(self, tmp_path):
        zip_path = str(tmp_path / 'test.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('boundary.shp', b'\x00' * 10)
            zf.writestr('boundary.shx', b'\x00' * 10)
            zf.writestr('boundary.dbf', b'\x00' * 10)
            zf.writestr('boundary.prj', 'GEOGCS')

        shp_name, members = validate_shapefile_zip(zip_path)
        assert shp_name == 'boundary.shp'
        assert len(members) == 4

    def test_no_shp_file(self, tmp_path):
        zip_path = str(tmp_path / 'bad.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('data.dbf', b'\x00')

        with pytest.raises(ValueError, match='未找到.shp主文件'):
            validate_shapefile_zip(zip_path)

    def test_multiple_shp_files(self, tmp_path):
        zip_path = str(tmp_path / 'multi.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('a.shp', b'\x00')
            zf.writestr('b.shp', b'\x00')

        with pytest.raises(ValueError, match='多个.shp文件'):
            validate_shapefile_zip(zip_path)

    def test_unsafe_path(self, tmp_path):
        zip_path = str(tmp_path / 'unsafe.zip')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('../evil.shp', b'\x00')

        with pytest.raises(ValueError, match='不安全路径'):
            validate_shapefile_zip(zip_path)

    def test_not_zip(self, tmp_path):
        bad_file = tmp_path / 'fake.zip'
        bad_file.write_bytes(b'not a zip')

        with pytest.raises(ValueError, match='不是有效的ZIP'):
            validate_shapefile_zip(str(bad_file))


class TestFilenameValidation:

    def test_safe_filenames(self):
        assert is_safe_filename('RAIN_2024-07-01.tif')
        assert is_safe_filename('boundary.zip')

    def test_unsafe_filenames(self):
        assert not is_safe_filename('')
        assert not is_safe_filename('../evil.tif')
        assert not is_safe_filename('/etc/passwd')
        assert not is_safe_filename('..\\evil.tif')
        assert not is_safe_filename('.hidden')

    def test_supported_extensions(self):
        assert is_supported_upload_extension('data.tif')
        assert is_supported_upload_extension('data.tiff')
        assert is_supported_upload_extension('data.zip')
        assert not is_supported_upload_extension('data.exe')
        assert not is_supported_upload_extension('data.shp')
        assert not is_supported_upload_extension('data.pdf')
