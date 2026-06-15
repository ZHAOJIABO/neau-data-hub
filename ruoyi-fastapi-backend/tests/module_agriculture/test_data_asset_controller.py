import pytest


class TestDataAssetControllerEndpoints:
    """Endpoint shape verification tests (contract-level, no live DB)."""

    def test_list_endpoint_exists(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        paths = [route.path for route in data_asset_controller.routes]
        assert '/list' in paths

    def test_detail_endpoint_exists(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        paths = [route.path for route in data_asset_controller.routes]
        assert '/{asset_id}' in paths

    def test_upload_endpoint_exists(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        paths = [route.path for route in data_asset_controller.routes]
        assert '/upload' in paths

    def test_download_endpoint_exists(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        paths = [route.path for route in data_asset_controller.routes]
        assert '/download/{asset_id}' in paths

    def test_delete_endpoint_exists(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        paths = [route.path for route in data_asset_controller.routes]
        assert '/{ids}' in paths

    def test_router_prefix(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        assert data_asset_controller.prefix == '/agriculture/dataAsset'

    def test_router_has_auth_dependency(self):
        from module_agriculture.controller.data_asset_controller import data_asset_controller
        assert len(data_asset_controller.dependencies) > 0
