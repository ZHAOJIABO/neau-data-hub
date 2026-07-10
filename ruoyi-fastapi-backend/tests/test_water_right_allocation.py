"""
灌区初始水权分配 + 水权交易市场博弈模型测试。

覆盖范围：
1. 按面积均分初始水权
2. 边际产值自动计算
3. 全局拍卖 LP 出清（市场出清、贸易对、价格区间）
4. Stackelberg 嵌套求解
5. VO 模型校验（异常路径）
6. Service 异步调用
"""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from pydantic import ValidationError

from module_model.entity.vo.water_soil_resource_vo import DEFAULT_WATER_SOIL_ZONES
from module_model.entity.vo.water_right_allocation_vo import (
    WaterRightAllocationRequest,
    WaterRightCropInputModel,
    WaterRightMarketInputModel,
    WaterRightZoneInputModel,
)
from module_model.model.water_right_allocation_model import (
    WaterRightAllocationResult,
    WaterRightContext,
    WaterRightCrop,
    WaterRightMarketConfig,
    WaterRightZone,
    allocate_initial_rights_by_area,
    build_context,
    compute_fairness_index,
    compute_marginal_value,
    solve_auction_clearing,
    solve_water_right_allocation,
)
from module_model.service.water_right_allocation_service import WaterRightAllocationService


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------

def _make_zones(n: int = 4) -> list[dict[str, Any]]:
    """构造 n 个分区，需求差异显著以触发贸易。"""
    out = []
    base = DEFAULT_WATER_SOIL_ZONES[:n]
    for i, item in enumerate(base):
        out.append({
            'zone_id': item['zone_id'],
            'zone_name': item['zone_name'],
            'land_area': float(item['land_area']),
            'surface_water_available': float(item['surface_water_available']),
            'groundwater_available': float(item['groundwater_available']),
            # 高需求分区（前 2 个）
            'water_demand_m3': float(item['land_area']) * 9000.0 * (1.5 if i < 2 else 0.5),
            'crop_mix': {'rice': 0.6, 'corn': 0.4} if i < 2 else {'soybean': 0.7, 'corn': 0.3},
            'water_saving_potential_m3': float(item['land_area']) * 1500.0 if i >= 2 else 0.0,
        })
    return out


def _make_crops() -> list[dict[str, Any]]:
    return [
        {
            'crop': 'rice',
            'crop_name': '水稻',
            'yield_kg_per_ha': 7500.0,
            'price_yuan_per_kg': 2.6,
            'cost_yuan_per_ha': 8000.0,
            'water_quota_m3_per_ha': 9000.0,
        },
        {
            'crop': 'corn',
            'crop_name': '玉米',
            'yield_kg_per_ha': 9000.0,
            'price_yuan_per_kg': 2.2,
            'cost_yuan_per_ha': 6000.0,
            'water_quota_m3_per_ha': 6000.0,
        },
        {
            'crop': 'soybean',
            'crop_name': '大豆',
            'yield_kg_per_ha': 3000.0,
            'price_yuan_per_kg': 4.8,
            'cost_yuan_per_ha': 4500.0,
            'water_quota_m3_per_ha': 4500.0,
        },
    ]


def _make_market(**overrides: Any) -> dict[str, Any]:
    market = {
        'initial_total_water_m3': 4.0e7,
        'reserve_price_yuan_per_m3': 1.5,
        'price_floor': 0.5,
        'price_ceiling': 8.0,
        'transaction_cost_rate': 0.05,
        'fairness_weight': 0.3,
        'saving_incentive_weight': 0.2,
        'min_self_use_ratio': 0.0,
    }
    market.update(overrides)
    return market


# ---------------------------------------------------------------------------
# 1. 初始水权按面积均分
# ---------------------------------------------------------------------------

class InitialAllocationTest(unittest.TestCase):
    def test_initial_rights_sum_to_total_water(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        R = ctx.initial_rights
        total = float(R.sum())
        self.assertAlmostEqual(total, 4.0e7, delta=1.0)

    def test_initial_rights_proportional_to_land_area(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        R = ctx.initial_rights
        areas = np.array([z.land_area for z in ctx.zones])
        # R_i / R_j == area_i / area_j
        ratios = R / areas
        self.assertAlmostEqual(float(ratios.std()), 0.0, places=4)


import numpy as np  # noqa: E402  在测试类之后导入保持文件顶部整洁


# ---------------------------------------------------------------------------
# 2. 边际产值计算
# ---------------------------------------------------------------------------

class MarginalValueTest(unittest.TestCase):
    def test_crop_marginal_value_matches_definition(self):
        crop = WaterRightCrop(
            crop='rice',
            crop_name='水稻',
            yield_kg_per_ha=7500.0,
            price_yuan_per_kg=2.6,
            cost_yuan_per_ha=8000.0,
            water_quota_m3_per_ha=9000.0,
        )
        expected = 7500.0 * 2.6 / 9000.0
        self.assertAlmostEqual(crop.marginal_value, expected, places=6)

    def test_zone_marginal_value_weighted_by_crop_mix(self):
        from module_model.model.water_right_allocation_model import compute_marginal_value
        zones = _make_zones(2)
        crops = _make_crops()
        ctx = build_context(zones, crops, _make_market())
        # 第一个分区：rice 60% + corn 40%
        zone0 = ctx.zones[0]
        # build_context 不自动填充 marginal_value，需要显式调用 compute_marginal_value
        rho = compute_marginal_value(zone0, ctx.crop_lookup, ctx.crops)
        expected = 0.6 * ctx.crop_lookup['rice'].marginal_value + \
                   0.4 * ctx.crop_lookup['corn'].marginal_value
        self.assertAlmostEqual(rho, expected, places=6)


# ---------------------------------------------------------------------------
# 3. 全局拍卖 LP 出清
# ---------------------------------------------------------------------------

class AuctionClearingTest(unittest.TestCase):
    def test_market_clearing_balances_buy_and_sell(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        auction = solve_auction_clearing(ctx, ctx.market.reserve_price)
        # 买/卖近似相等（LP 严格出清）
        self.assertLess(abs(auction.total_buy_m3 - auction.total_sell_m3), 1.0)

    def test_trade_pairs_generated_for_active_zones(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        auction = solve_auction_clearing(ctx, ctx.market.reserve_price)
        # 至少有一个分区参与交易（不论买卖）
        active = [item for item in auction.zone_outcomes if item['role'] != 'self']
        self.assertGreater(len(active), 0)

    def test_clearing_price_within_bounds(self):
        zones = _make_zones(4)
        market = _make_market(price_floor=0.5, price_ceiling=8.0)
        ctx = build_context(zones, _make_crops(), market)
        auction = solve_auction_clearing(ctx, ctx.market.reserve_price)
        self.assertGreaterEqual(auction.clearing_price, market['price_floor'] - 1e-6)
        self.assertLessEqual(auction.clearing_price, market['price_ceiling'] + 1e-6)

    def test_zone_water_balance_holds(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        auction = solve_auction_clearing(ctx, ctx.market.reserve_price)
        R = ctx.initial_rights
        for i, item in enumerate(auction.zone_outcomes):
            # u + b - s ≈ R
            lhs = item['self_used_m3'] + item['purchased_m3'] - item['sold_m3']
            self.assertAlmostEqual(lhs, R[i], delta=1.0)

    def test_clearing_with_higher_reserve_price_reduces_trade(self):
        """价格足够高时，缺水方买水不划算，交易量下降。"""
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        auction_low = solve_auction_clearing(ctx, reserve_price=0.5)
        auction_high = solve_auction_clearing(ctx, reserve_price=8.0)
        # 高价下交易量应该 ≤ 低价下交易量（卖方收入高但买方成本高）
        self.assertLessEqual(auction_high.total_buy_m3, auction_low.total_buy_m3 + 1.0)


# ---------------------------------------------------------------------------
# 4. Stackelberg 完整求解
# ---------------------------------------------------------------------------

class StackelbergSolveTest(unittest.TestCase):
    def test_full_solve_returns_valid_result(self):
        zones = _make_zones(4)
        crops = _make_crops()
        market = _make_market()
        ctx = build_context(zones, crops, market)
        result = solve_water_right_allocation(ctx)
        self.assertIsInstance(result, WaterRightAllocationResult)
        self.assertEqual(result.summary['n_zones'], 4)
        self.assertEqual(result.summary['n_crops'], 3)
        # 初始水权总和等于输入
        self.assertAlmostEqual(
            result.summary['initial_total_water_m3'], 4.0e7, delta=1.0
        )

    def test_leader_history_records_iterations(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        result = solve_water_right_allocation(ctx)
        # 至少迭代 5 次（5 个保留价候选）
        self.assertGreaterEqual(len(result.leader_history), 5)
        for it in result.leader_history:
            self.assertGreaterEqual(it.reserve_price, ctx.market.price_floor)
            self.assertLessEqual(it.reserve_price, ctx.market.price_ceiling)

    def test_fairness_index_is_unit_interval(self):
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        result = solve_water_right_allocation(ctx)
        fair = result.summary['fairness_index']
        self.assertGreaterEqual(fair, 0.0)
        self.assertLessEqual(fair, 1.0)

    def test_to_dict_is_json_safe(self):
        import json
        zones = _make_zones(4)
        ctx = build_context(zones, _make_crops(), _make_market())
        result = solve_water_right_allocation(ctx)
        d = result.to_dict()
        # 必须可被 json.dumps 序列化
        json.dumps(d)


# ---------------------------------------------------------------------------
# 5. VO 校验
# ---------------------------------------------------------------------------

class ValidationTest(unittest.TestCase):
    def test_default_zones_are_reused(self):
        req = WaterRightAllocationRequest(
            crops=[WaterRightCropInputModel(**c) for c in _make_crops()],
            market=WaterRightMarketInputModel(initial_total_water_m3=4.0e7),
        )
        # 默认继承水土资源模型 14 分区
        self.assertEqual(len(req.zones), len(DEFAULT_WATER_SOIL_ZONES))

    def test_crops_must_be_non_empty(self):
        with self.assertRaises(ValidationError):
            WaterRightAllocationRequest(zones=[])

    def test_market_price_floor_must_be_less_than_ceiling(self):
        with self.assertRaises(ValidationError):
            WaterRightMarketInputModel(
                initial_total_water_m3=1.0e7,
                price_floor=5.0,
                price_ceiling=3.0,
            )

    def test_market_reserve_price_must_be_within_bounds(self):
        with self.assertRaises(ValidationError):
            WaterRightMarketInputModel(
                initial_total_water_m3=1.0e7,
                reserve_price_yuan_per_m3=20.0,
                price_floor=0.5,
                price_ceiling=10.0,
            )

    def test_zone_id_must_be_unique(self):
        zones = _make_zones(2)
        zones[1]['zone_id'] = zones[0]['zone_id']
        with self.assertRaises(ValidationError):
            WaterRightAllocationRequest(
                zones=[WaterRightZoneInputModel(**z) for z in zones],
                crops=[WaterRightCropInputModel(**c) for c in _make_crops()],
            )

    def test_crop_mix_is_normalized(self):
        z = _make_zones(1)[0]
        z['crop_mix'] = {'rice': 2.0, 'corn': 2.0}  # 总和=4
        mz = WaterRightZoneInputModel(**z)
        s = sum(mz.crop_mix.values())
        self.assertAlmostEqual(s, 1.0, places=6)


# ---------------------------------------------------------------------------
# 6. Service 异步入口
# ---------------------------------------------------------------------------

class ServiceTest(unittest.TestCase):
    def test_run_allocation_async(self):
        async def _run():
            return await WaterRightAllocationService.run_allocation(
                zones=_make_zones(4),
                crops=_make_crops(),
                market=_make_market(),
            )
        data = asyncio.run(_run())
        self.assertEqual(data['summary']['n_zones'], 4)
        self.assertIn('equilibrium', data)
        self.assertIn('zone_outcomes', data)
        self.assertIn('trade_flows', data)

    def test_run_allocation_with_all_14_zones(self):
        async def _run():
            return await WaterRightAllocationService.run_allocation(
                zones=_make_zones(14),
                crops=_make_crops(),
                market=_make_market(),
            )
        data = asyncio.run(_run())
        self.assertEqual(data['summary']['n_zones'], 14)


# ---------------------------------------------------------------------------
# 7. 公平性度量工具
# ---------------------------------------------------------------------------

class FairnessTest(unittest.TestCase):
    def test_uniform_vector_has_fairness_one(self):
        v = np.array([10.0, 10.0, 10.0, 10.0])
        self.assertAlmostEqual(compute_fairness_index(v), 1.0, places=6)

    def test_extreme_vector_has_low_fairness(self):
        v = np.array([100.0, 1.0, 1.0, 1.0])
        fair = compute_fairness_index(v)
        self.assertLess(fair, 0.5)

    def test_zero_mean_returns_zero(self):
        v = np.array([0.0, 0.0, 0.0, 0.0])
        self.assertEqual(compute_fairness_index(v), 0.0)


if __name__ == '__main__':
    unittest.main()