from datetime import date, datetime

from module_agriculture.entity.vo.data_asset_vo import DataAssetModel, DataAssetPageQueryModel


class TestDataAssetModel:

    def test_camel_case_serialization(self):
        model = DataAssetModel(
            id=1,
            asset_type='raster',
            data_category='气象数据',
            region_name='浓江农场',
            asset_name='RAIN_2024-07-01',
            variable_name='RAIN',
            obs_date=date(2024, 7, 1),
            file_format='tif',
            relative_path='气象数据/浓江农场/RAIN_2024-07-01.tif',
            original_filename='RAIN_2024-07-01.tif',
            source_type='upload',
            size_bytes=1024000,
            deleted_at=None,
        )
        data = model.model_dump(by_alias=True)
        assert data['relativePath'] == '气象数据/浓江农场/RAIN_2024-07-01.tif'
        assert data['fileFormat'] == 'tif'
        assert data['sourceType'] == 'upload'
        assert data['deletedAt'] is None
        assert data['assetType'] == 'raster'
        assert data['originalFilename'] == 'RAIN_2024-07-01.tif'

    def test_optional_upload_fields(self):
        model = DataAssetModel(
            id=2,
            asset_type='vector',
            asset_name='边界',
            file_format='shp',
            relative_path='自然地理数据/boundary.shp',
        )
        data = model.model_dump(by_alias=True)
        assert data['originalFilename'] is None
        assert data['storagePath'] is None
        assert data['checksum'] is None
        assert data['sourceType'] is None
        assert data['uploadUserId'] is None
        assert data['deletedAt'] is None

    def test_page_query_filters(self):
        query = DataAssetPageQueryModel(
            asset_type='raster',
            data_category='气象数据',
            region_name='浓江农场',
            variable_name='RAIN',
            file_format='tif',
            asset_name='RAIN',
            obs_date_begin=date(2024, 1, 1),
            obs_date_end=date(2024, 12, 31),
        )
        assert query.asset_type == 'raster'
        assert query.data_category == '气象数据'
        assert query.region_name == '浓江农场'
        assert query.variable_name == 'RAIN'
        assert query.file_format == 'tif'
        assert query.obs_date_begin == date(2024, 1, 1)
        assert query.obs_date_end == date(2024, 12, 31)

    def test_from_attributes(self):
        class MockORM:
            id = 10
            asset_type = 'raster'
            data_category = '气象数据'
            region_name = '浓江农场'
            asset_name = 'RAIN'
            variable_name = 'RAIN'
            obs_date = date(2024, 7, 1)
            file_format = 'tif'
            relative_path = '气象数据/浓江农场/RAIN_2024-07-01.tif'
            original_filename = 'RAIN_2024-07-01.tif'
            storage_path = '/data/assets/2024/07/01/abc.tif'
            size_bytes = 2048
            checksum = 'abc123'
            source_type = 'upload'
            upload_user_id = 1
            crs = 'EPSG:4326'
            bbox = {'minx': 100, 'miny': 40, 'maxx': 110, 'maxy': 50}
            raster_width = 100
            raster_height = 100
            raster_count = 1
            raster_dtype = 'float32'
            resolution_x = 0.01
            resolution_y = 0.01
            nodata_value = -9999.0
            extra_metadata = {'driver': 'GTiff'}
            created_at = datetime(2024, 7, 1)
            updated_at = datetime(2024, 7, 1)
            deleted_at = None

        model = DataAssetModel.model_validate(MockORM)
        assert model.id == 10
        assert model.source_type == 'upload'
        assert model.checksum == 'abc123'
        assert model.deleted_at is None
