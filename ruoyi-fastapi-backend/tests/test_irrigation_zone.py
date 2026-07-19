"""
灌区分区数据入库与模型运行时加载测试。
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from exceptions.exception import ServiceException
from module_agriculture.entity.vo.zone_vo import IrrigationZoneCreateModel
from module_agriculture.service.zone_service import IrrigationZoneService


def _record(zone_id: str, status: str = '0', sort_order: int = 1):
    return SimpleNamespace(
        id=1,
        irrigation_area_code='chahayang',
        irrigation_area_name='查哈阳灌区',
        zone_id=zone_id,
        zone_name=f'分区{zone_id}',
        land_area=100.0,
        surface_water_available=1000.0,
        groundwater_available=200.0,
        min_area=None,
        max_area=None,
        sort_order=sort_order,
        status=status,
        remark=None,
        created_at=None,
        updated_at=None,
    )


class IrrigationZoneVoTests(unittest.TestCase):
    def test_area_range_validation(self):
        with self.assertRaises(ValidationError):
            IrrigationZoneCreateModel(
                zoneId='Z99',
                zoneName='测试分区',
                landArea=100.0,
                surfaceWaterAvailable=10.0,
                groundwaterAvailable=10.0,
                minArea=90.0,
                maxArea=80.0,
            )

    def test_negative_water_is_rejected(self):
        with self.assertRaises(ValidationError):
            IrrigationZoneCreateModel(
                zoneId='Z99',
                zoneName='测试分区',
                landArea=100.0,
                surfaceWaterAvailable=-1.0,
                groundwaterAvailable=10.0,
            )

    def test_empty_irrigation_area_code_is_rejected(self):
        with self.assertRaises(ValidationError):
            IrrigationZoneCreateModel(
                irrigationAreaCode='',
                irrigationAreaName='测试灌区',
                zoneId='Z99',
                zoneName='测试分区',
                landArea=100.0,
            )


class IrrigationZoneRuntimeLoaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_water_soil_loader_fills_area_bounds(self):
        with patch(
            'module_agriculture.service.zone_service.IrrigationZoneDao.get_enabled_zones',
            new=AsyncMock(return_value=[_record('Z02'), _record('Z01')]),
        ):
            rows = await IrrigationZoneService.list_enabled_for_water_soil(AsyncMock(), 'chahayang')
        self.assertEqual([row['zone_id'] for row in rows], ['Z02', 'Z01'])
        self.assertEqual(rows[0]['irrigation_area_code'], 'chahayang')
        self.assertEqual(rows[0]['min_area'], 75.0)
        self.assertEqual(rows[0]['max_area'], 100.0)

    async def test_water_right_loader_excludes_area_bounds(self):
        with patch(
            'module_agriculture.service.zone_service.IrrigationZoneDao.get_enabled_zones',
            new=AsyncMock(return_value=[_record('Z01')]),
        ):
            rows = await IrrigationZoneService.list_enabled_for_water_right(AsyncMock(), 'chahayang')
        self.assertEqual(rows[0]['zone_id'], 'Z01')
        self.assertNotIn('min_area', rows[0])
        self.assertNotIn('max_area', rows[0])

    async def test_empty_enabled_zones_raise_clear_error(self):
        with patch(
            'module_agriculture.service.zone_service.IrrigationZoneDao.get_enabled_zones',
            new=AsyncMock(return_value=[]),
        ):
            with self.assertRaises(ServiceException) as ctx:
                await IrrigationZoneService.list_enabled_for_water_soil(AsyncMock(), 'unknown')
        self.assertIn('未维护灌区 unknown 的启用分区数据', str(ctx.exception.message))

    async def test_zone_name_map(self):
        with patch(
            'module_agriculture.service.zone_service.IrrigationZoneDao.get_enabled_zones',
            new=AsyncMock(return_value=[_record('Z01'), _record('Z02')]),
        ):
            mapping = await IrrigationZoneService.zone_name_map(AsyncMock(), 'chahayang')
        self.assertEqual(mapping['Z01'], '分区Z01')

    async def test_area_options_include_default_when_empty(self):
        with patch(
            'module_agriculture.service.zone_service.IrrigationZoneDao.get_area_options',
            new=AsyncMock(return_value=[]),
        ):
            rows = await IrrigationZoneService.list_area_options_services(AsyncMock())
        self.assertEqual(rows[0]['irrigation_area_code'], 'chahayang')


if __name__ == '__main__':
    unittest.main()
