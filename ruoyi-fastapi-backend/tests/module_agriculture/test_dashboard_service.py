from unittest.mock import AsyncMock, patch

import pytest

from module_agriculture.service.dashboard_service import DashboardService


class FakeRedis:
    def __init__(self, value=None):
        self.value = value
        self.set_calls = []

    async def get(self, key):
        return self.value

    async def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))


class TestDashboardServiceCache:

    @pytest.mark.asyncio
    async def test_get_stats_uses_cached_value_without_querying_db(self):
        redis = FakeRedis('{"stationCount": 3, "weatherStats": {}, "soilStats": {}, "cropCount": 4}')

        with patch.object(DashboardService, '_query_stats', new_callable=AsyncMock) as query_stats:
            result = await DashboardService.get_stats_services(AsyncMock(), redis)

        assert result['stationCount'] == 3
        assert result['cropCount'] == 4
        query_stats.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_stats_writes_query_result_to_cache(self):
        redis = FakeRedis()
        stats = {'stationCount': 1, 'weatherStats': {}, 'soilStats': {}, 'cropCount': 2}

        with patch.object(DashboardService, '_query_stats', new_callable=AsyncMock, return_value=stats):
            result = await DashboardService.get_stats_services(AsyncMock(), redis)

        assert result == stats
        assert len(redis.set_calls) == 1
        assert redis.set_calls[0][0] == DashboardService.STATS_CACHE_KEY
        assert redis.set_calls[0][2] == DashboardService.STATS_CACHE_TTL_SECONDS
