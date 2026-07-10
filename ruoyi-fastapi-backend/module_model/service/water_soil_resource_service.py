"""
灌区水土资源多目标优化配置服务。
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import Any

from exceptions.exception import ServiceException
from module_model.entity.vo.water_soil_resource_vo import DEFAULT_WATER_SOIL_ZONES
from module_model.model.water_soil_resource_optimize import (
    CropConfig,
    StageConfig,
    WaterSoilResourceContext,
    WaterSoilResourceResult,
    ZoneConfig,
    solve_water_soil_resource,
)


def _water_soil_resource_worker(
    zones: list[dict[str, Any]],
    crops: list[dict[str, Any]],
    stages: list[dict[str, Any]],
    total_water_available: float | None,
    pop_size: int,
    n_gen: int,
    seed: int,
    pref_weight_benefit: float,
    pref_weight_fairness: float,
    pref_weight_efficiency: float,
    pref_weight_nitrogen_efficiency: float,
    alpha: float,
) -> dict[str, Any]:
    """进程级入口：执行灌区水土资源多目标优化配置。"""
    if not zones:
        zones = list(DEFAULT_WATER_SOIL_ZONES)
    zone_configs = [
        ZoneConfig(
            zone_id=str(item['zone_id']),
            zone_name=item.get('zone_name') or str(item['zone_id']),
            land_area=float(item['land_area']),
            surface_water_available=float(
                item.get('surface_water_available')
                if item.get('surface_water_available') is not None
                else item.get('water_available')
                if item.get('water_available') is not None
                else 0.0
            ),
            groundwater_available=float(item.get('groundwater_available') or 0.0),
            min_area=float(item.get('min_area') or 0.0),
            max_area=(float(item['max_area']) if item.get('max_area') is not None else None),
        )
        for item in zones
    ]
    crop_configs = [
        CropConfig(
            crop=str(item['crop']),
            crop_name=item.get('crop_name') or str(item['crop']),
            min_area_ratio=float(item.get('min_area_ratio') or 0.0),
            max_area_ratio=float(item.get('max_area_ratio') if item.get('max_area_ratio') is not None else 1.0),
            yield_kg_per_ha=float(item['yield_kg_per_ha']),
            price_yuan_per_kg=float(item['price_yuan_per_kg']),
            cost_yuan_per_ha=float(item.get('cost_yuan_per_ha') or 0.0),
            water_quota_m3_per_ha=float(
                item.get('water_quota_m3_per_ha')
                if item.get('water_quota_m3_per_ha') is not None
                else item.get('water_quota')
                if item.get('water_quota') is not None
                else 8000.0
            ),
            nitrogen_max_kg_ha=float(item.get('nitrogen_max_kg_ha') or item.get('nitrogen_max') or 200.0),
            nitrogen_min_kg_ha=float(item.get('nitrogen_min_kg_ha') or item.get('nitrogen_min') or 0.0),
            nitrogen_productivity_coeff=float(item.get('nitrogen_productivity_coeff') or 1.0),
            water_productivity_coeff=float(item.get('water_productivity_coeff') or 1.0),
            nitrogen_cost_yuan_per_kg=float(item.get('nitrogen_cost_yuan_per_kg') or 1.0),
        )
        for item in crops
    ]
    stage_configs = [
        StageConfig(
            stage=str(item['stage']),
            stage_name=item.get('stage_name') or str(item['stage']),
            min_water_mm=float(item.get('min_water_mm') or 0.0),
            max_water_mm=float(item['max_water_mm']),
            demand_water_mm=float(item['demand_water_mm']),
            yield_response_weight=float(item.get('yield_response_weight') or 0.0),
        )
        for item in stages
    ]
    ctx = WaterSoilResourceContext(
        zones=zone_configs,
        crops=crop_configs,
        stages=stage_configs,
        total_water_available=total_water_available,
        pop_size=max(10, int(pop_size)),
        n_gen=max(1, int(n_gen)),
        seed=int(seed),
        pref_weight_benefit=float(pref_weight_benefit),
        pref_weight_fairness=float(pref_weight_fairness),
        pref_weight_efficiency=float(pref_weight_efficiency),
        pref_weight_nitrogen_efficiency=float(pref_weight_nitrogen_efficiency),
        alpha=float(alpha),
    )
    try:
        result: WaterSoilResourceResult = solve_water_soil_resource(ctx)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise ServiceException(message=str(exc)) from exc
    return result.to_dict()


class WaterSoilResourceService:
    """灌区水土资源配置：面积 + 地表水 + 地下水 + 施氮量，NSGA-II 四目标优化。"""

    @classmethod
    async def run_optimize(
        cls,
        zones: list[dict[str, Any]],
        crops: list[dict[str, Any]],
        stages: list[dict[str, Any]],
        total_water_available: float | None = None,
        pop_size: int = 120,
        n_gen: int = 100,
        seed: int = 1,
        pref_weight_benefit: float = 0.4,
        pref_weight_fairness: float = 0.3,
        pref_weight_efficiency: float = 0.3,
        pref_weight_nitrogen_efficiency: float = 0.15,
        alpha: float = 0.5,
    ) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(
                pool,
                partial(
                    _water_soil_resource_worker,
                    zones,
                    crops,
                    stages,
                    total_water_available,
                    pop_size,
                    n_gen,
                    seed,
                    pref_weight_benefit,
                    pref_weight_fairness,
                    pref_weight_efficiency,
                    pref_weight_nitrogen_efficiency,
                    alpha,
                ),
            )
        return result
