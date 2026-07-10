"""
灌区水土资源-水氮作物多目标优化配置模型（NSGA-II）。

决策变量：
- 不同分区、不同作物的种植面积；
- 不同分区、不同作物的地表水量、地下水量；
- 不同分区、不同作物的单位面积施氮量。

优化目标（均按最大化指标输出，求解时转换为最小化）：
- 单方水效益最高：净收益 / 总用水量；
- 公平性最大：各分区水分满足度越均衡越好；
- 用水效率最高：产量 / 总用水量；
- 氮肥利用效率最高：产量 / 总施氮量。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize


def _sanitize(obj: Any) -> Any:
    import math as _math

    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        obj = float(obj)
    if isinstance(obj, float):
        if _math.isnan(obj) or _math.isinf(obj):
            return None
        return obj
    return obj


def _normalize_weights(values: list[float], n: int) -> np.ndarray:
    weights = np.array(values if values else [1.0] * n, dtype=float)
    if len(weights) != n:
        weights = np.ones(n, dtype=float)
    weights = np.maximum(weights, 0.0)
    total = float(np.sum(weights))
    return weights / total if total > 1e-12 else np.full(n, 1.0 / n)


def _entropy_topsis_max(
    metrics: np.ndarray,
    pref_weights: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray, int]:
    """对最大化指标执行熵权-TOPSIS，返回 scores、混合权重、最佳行号。"""
    if metrics.ndim != 2 or len(metrics) == 0:
        raise ValueError('TOPSIS 指标矩阵为空')

    norm = (metrics - metrics.min(axis=0)) / (
        metrics.max(axis=0) - metrics.min(axis=0) + 1e-9
    )
    col_sum = np.sum(norm, axis=0)
    safe_sum = np.where(col_sum > 1e-12, col_sum, 1.0)
    p = norm / safe_sum
    entropy_raw = -np.sum(p * np.log(p + 1e-9), axis=0) / np.log(max(len(norm), 2))
    entropy = np.where(np.isfinite(entropy_raw), entropy_raw, 1.0)
    diversity = 1.0 - entropy
    if float(np.sum(diversity)) <= 1e-12:
        entropy_weights = np.full(metrics.shape[1], 1.0 / metrics.shape[1])
    else:
        entropy_weights = diversity / np.sum(diversity)

    weights = alpha * pref_weights + (1.0 - alpha) * entropy_weights
    weights = weights / np.sum(weights)

    ideal = norm.max(axis=0)
    nadir = norm.min(axis=0)
    d_pos = np.sqrt(np.sum(((norm - ideal) ** 2) * weights, axis=1))
    d_neg = np.sqrt(np.sum(((norm - nadir) ** 2) * weights, axis=1))
    scores = d_neg / (d_pos + d_neg + 1e-9)
    best_index = int(np.argmax(scores))
    return scores, weights, best_index


@dataclass
class ZoneConfig:
    zone_id: str
    zone_name: str
    land_area: float
    surface_water_available: float
    groundwater_available: float
    min_area: float = 0.0
    max_area: float | None = None

    @property
    def water_available(self) -> float:
        return self.surface_water_available + self.groundwater_available


@dataclass
class CropConfig:
    crop: str
    crop_name: str
    min_area_ratio: float
    max_area_ratio: float
    yield_kg_per_ha: float
    price_yuan_per_kg: float
    cost_yuan_per_ha: float
    water_quota_m3_per_ha: float
    nitrogen_max_kg_ha: float
    nitrogen_min_kg_ha: float = 0.0
    nitrogen_productivity_coeff: float = 1.0
    water_productivity_coeff: float = 1.0
    nitrogen_cost_yuan_per_kg: float = 1.0

    @property
    def effective_nitrogen_min(self) -> float:
        return min(max(0.0, self.nitrogen_min_kg_ha), self.nitrogen_max_kg_ha)


@dataclass
class StageConfig:
    stage: str
    stage_name: str
    min_water_mm: float
    max_water_mm: float
    demand_water_mm: float
    yield_response_weight: float


@dataclass
class WaterSoilResourceContext:
    zones: list[ZoneConfig]
    crops: list[CropConfig]
    stages: list[StageConfig]
    total_water_available: float | None
    pop_size: int
    n_gen: int
    seed: int
    pref_weight_benefit: float
    pref_weight_fairness: float
    pref_weight_efficiency: float
    pref_weight_nitrogen_efficiency: float
    alpha: float


@dataclass
class WaterSoilResourceResult:
    summary: dict
    allocation: list[dict]
    stage_water: list[dict]
    zone_summary: list[dict]
    crop_summary: list[dict]
    pareto: list[dict]
    topsis_summary: dict

    def to_dict(self) -> dict:
        return _sanitize({
            'summary': self.summary,
            'allocation': self.allocation,
            'stage_water': self.stage_water,
            'zone_summary': self.zone_summary,
            'crop_summary': self.crop_summary,
            'pareto': self.pareto,
            'topsis_summary': self.topsis_summary,
        })


class WaterSoilResourceSampling(Sampling):
    """Generate agronomically plausible individuals inside the easy constraints."""

    def _do(self, problem, n_samples, **kwargs):
        rng = np.random.default_rng(kwargs.get('seed', None))
        samples = []
        for _ in range(n_samples):
            samples.append(problem.random_feasible_vector(rng))
        return np.asarray(samples, dtype=float)


class WaterSoilResourceRepair(Repair):
    """Project NSGA-II individuals back to the water-soil feasible region."""

    def _do(self, problem, X, **kwargs):
        X = np.asarray(X, dtype=float)
        one_dim = X.ndim == 1
        if one_dim:
            X = X.reshape(1, -1)
        repaired = np.asarray([problem.repair_vector(x) for x in X], dtype=float)
        return repaired[0] if one_dim else repaired


class WaterSoilResourceProblem(ElementwiseProblem):
    """14 分区水土资源-水氮作物配置 NSGA-II 问题。"""

    def __init__(
        self,
        zones: list[ZoneConfig],
        crops: list[CropConfig],
        total_water_available: float | None,
    ):
        self.zones = zones
        self.crops = crops
        self.z_count = len(zones)
        self.c_count = len(crops)
        self.cell_count = self.z_count * self.c_count
        self.total_water_available = total_water_available

        area_xl: list[float] = []
        area_xu: list[float] = []
        surface_xl: list[float] = []
        surface_xu: list[float] = []
        groundwater_xl: list[float] = []
        groundwater_xu: list[float] = []
        nitrogen_xl: list[float] = []
        nitrogen_xu: list[float] = []

        for zone in zones:
            zone_max_area = zone.land_area if zone.max_area is None else min(zone.max_area, zone.land_area)
            for crop in crops:
                max_crop_area = max(0.0, zone_max_area * crop.max_area_ratio)
                max_water = max_crop_area * crop.water_quota_m3_per_ha * 1.2
                area_xl.append(max(0.0, zone.land_area * crop.min_area_ratio))
                area_xu.append(max_crop_area)
                surface_xl.append(0.0)
                surface_xu.append(min(zone.surface_water_available, max_water))
                groundwater_xl.append(0.0)
                groundwater_xu.append(min(zone.groundwater_available, max_water))
                nitrogen_xl.append(crop.effective_nitrogen_min)
                nitrogen_xu.append(max(0.0, crop.nitrogen_max_kg_ha))

        xl = np.array(area_xl + surface_xl + groundwater_xl + nitrogen_xl, dtype=float)
        xu = np.array(area_xu + surface_xu + groundwater_xu + nitrogen_xu, dtype=float)

        n_zone_constraints = self.z_count * 6
        n_crop_constraints = self.z_count * self.c_count * 3
        n_water_constraints = 1 if total_water_available is not None else 0
        super().__init__(
            n_var=self.cell_count * 4,
            n_obj=4,
            n_ieq_constr=n_zone_constraints + n_crop_constraints + n_water_constraints,
            xl=xl,
            xu=xu,
        )

    def _decode(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        end_area = self.cell_count
        end_surface = end_area + self.cell_count
        end_ground = end_surface + self.cell_count
        areas = x[:end_area].reshape((self.z_count, self.c_count))
        surface_water = x[end_area:end_surface].reshape((self.z_count, self.c_count))
        groundwater = x[end_surface:end_ground].reshape((self.z_count, self.c_count))
        nitrogen = x[end_ground:].reshape((self.z_count, self.c_count))
        return areas, surface_water, groundwater, nitrogen

    def _evaluate_solution(self, x: np.ndarray) -> dict[str, Any]:
        areas, surface_water, groundwater, nitrogen = self._decode(x)
        total_crop_water = surface_water + groundwater

        zone_surface = np.sum(surface_water, axis=1)
        zone_groundwater = np.sum(groundwater, axis=1)
        zone_water = zone_surface + zone_groundwater
        zone_demand = np.zeros(self.z_count)
        zone_nitrogen = np.zeros(self.z_count)
        zone_benefit = np.zeros(self.z_count)

        crop_area = np.zeros(self.c_count)
        crop_yield = np.zeros(self.c_count)
        crop_benefit = np.zeros(self.c_count)
        crop_surface = np.zeros(self.c_count)
        crop_groundwater = np.zeros(self.c_count)
        crop_nitrogen = np.zeros(self.c_count)

        total_yield = 0.0
        total_benefit = 0.0
        total_demand = 0.0
        total_nitrogen = 0.0

        for z_idx, zone in enumerate(self.zones):
            for c_idx, crop in enumerate(self.crops):
                area = float(areas[z_idx, c_idx])
                water_m3 = float(total_crop_water[z_idx, c_idx])
                nitrogen_kg_ha = float(nitrogen[z_idx, c_idx])
                nitrogen_kg = area * nitrogen_kg_ha
                demand_m3 = area * crop.water_quota_m3_per_ha

                water_factor = min(water_m3 / max(demand_m3, 1e-6), 1.2) if area > 1e-9 else 0.0
                nitrogen_factor = min(
                    nitrogen_kg_ha / max(crop.nitrogen_max_kg_ha, 1e-6),
                    1.2,
                ) if area > 1e-9 else 0.0
                yield_factor = 0.65 * water_factor + 0.35 * nitrogen_factor * crop.nitrogen_productivity_coeff
                yield_factor = min(max(yield_factor, 0.0), 1.2)

                production = area * crop.yield_kg_per_ha * yield_factor * crop.water_productivity_coeff
                water_cost = 0.025 * float(surface_water[z_idx, c_idx]) + 0.05 * float(groundwater[z_idx, c_idx])
                nitrogen_cost = nitrogen_kg * crop.nitrogen_cost_yuan_per_kg
                benefit = production * crop.price_yuan_per_kg - area * crop.cost_yuan_per_ha - water_cost - nitrogen_cost

                zone_demand[z_idx] += demand_m3
                zone_nitrogen[z_idx] += nitrogen_kg
                zone_benefit[z_idx] += benefit
                crop_area[c_idx] += area
                crop_yield[c_idx] += production
                crop_benefit[c_idx] += benefit
                crop_surface[c_idx] += float(surface_water[z_idx, c_idx])
                crop_groundwater[c_idx] += float(groundwater[z_idx, c_idx])
                crop_nitrogen[c_idx] += nitrogen_kg
                total_yield += production
                total_benefit += benefit
                total_demand += demand_m3
                total_nitrogen += nitrogen_kg

        total_water = float(np.sum(zone_water))
        zone_satisfaction = np.divide(
            zone_water,
            np.maximum(zone_demand, 1e-6),
            out=np.zeros_like(zone_water),
            where=zone_demand > 1e-6,
        )
        active = zone_demand > 1e-6
        if np.any(active):
            sat_active = np.clip(zone_satisfaction[active], 0.0, 1.2)
            fairness = 1.0 / (1.0 + float(np.std(sat_active) / (np.mean(sat_active) + 1e-9)))
        else:
            fairness = 0.0

        unit_water_benefit = total_benefit / max(total_water, 1e-6)
        water_efficiency = total_yield / max(total_water, 1e-6)
        nitrogen_efficiency = total_yield / max(total_nitrogen, 1e-6)

        return {
            'areas': areas,
            'surface_water': surface_water,
            'groundwater': groundwater,
            'nitrogen': nitrogen,
            'zone_surface': zone_surface,
            'zone_groundwater': zone_groundwater,
            'zone_water': zone_water,
            'zone_demand': zone_demand,
            'zone_satisfaction': zone_satisfaction,
            'zone_nitrogen': zone_nitrogen,
            'zone_benefit': zone_benefit,
            'crop_area': crop_area,
            'crop_yield': crop_yield,
            'crop_benefit': crop_benefit,
            'crop_surface': crop_surface,
            'crop_groundwater': crop_groundwater,
            'crop_nitrogen': crop_nitrogen,
            'total_water': total_water,
            'total_surface_water': float(np.sum(surface_water)),
            'total_groundwater': float(np.sum(groundwater)),
            'total_demand': total_demand,
            'total_nitrogen': total_nitrogen,
            'total_yield': total_yield,
            'total_benefit': total_benefit,
            'unit_water_benefit': unit_water_benefit,
            'fairness': fairness,
            'water_efficiency': water_efficiency,
            'nitrogen_efficiency': nitrogen_efficiency,
        }

    def _evaluate(self, x, out, *args, **kwargs):
        metrics = self._evaluate_solution(x)

        out['F'] = [
            -float(metrics['unit_water_benefit']),
            -float(metrics['fairness']),
            -float(metrics['water_efficiency']),
            -float(metrics['nitrogen_efficiency']),
        ]

        constraints: list[float] = []
        areas = metrics['areas']
        surface_water = metrics['surface_water']
        groundwater = metrics['groundwater']
        nitrogen = metrics['nitrogen']
        for z_idx, zone in enumerate(self.zones):
            zone_area = float(np.sum(areas[z_idx, :]))
            zone_max_area = zone.land_area if zone.max_area is None else min(zone.max_area, zone.land_area)
            constraints.append(zone_area - zone_max_area)
            constraints.append(max(0.0, zone.min_area) - zone_area)
            constraints.append(float(metrics['zone_surface'][z_idx]) - zone.surface_water_available)
            constraints.append(float(metrics['zone_groundwater'][z_idx]) - zone.groundwater_available)
            constraints.append(float(metrics['zone_water'][z_idx]) - zone.water_available)
            constraints.append(float(metrics['zone_demand'][z_idx]) * 0.55 - float(metrics['zone_water'][z_idx]))
            for c_idx, crop in enumerate(self.crops):
                constraints.append(areas[z_idx, c_idx] - zone.land_area * crop.max_area_ratio)
                constraints.append(
                    float(surface_water[z_idx, c_idx] + groundwater[z_idx, c_idx])
                    - float(areas[z_idx, c_idx]) * crop.water_quota_m3_per_ha * 1.2
                )
                constraints.append(float(nitrogen[z_idx, c_idx]) - crop.nitrogen_max_kg_ha)

        if self.total_water_available is not None:
            constraints.append(float(metrics['total_water']) - self.total_water_available)

        out['G'] = constraints

    def random_feasible_vector(self, rng: np.random.Generator) -> np.ndarray:
        areas = np.zeros((self.z_count, self.c_count), dtype=float)
        surface_water = np.zeros_like(areas)
        groundwater = np.zeros_like(areas)
        nitrogen = np.zeros_like(areas)

        for z_idx, zone in enumerate(self.zones):
            zone_max_area = zone.land_area if zone.max_area is None else min(zone.max_area, zone.land_area)
            min_area = min(max(zone.min_area, 0.0), zone_max_area)
            target_area = rng.uniform(max(min_area, zone_max_area * 0.55), zone_max_area)
            crop_pref = rng.dirichlet(np.ones(self.c_count))
            zone_areas = target_area * crop_pref
            for c_idx, crop in enumerate(self.crops):
                zone_areas[c_idx] = min(zone_areas[c_idx], zone_max_area * crop.max_area_ratio)
            area_sum = float(np.sum(zone_areas))
            if area_sum > zone_max_area:
                zone_areas *= zone_max_area / max(area_sum, 1e-9)
            areas[z_idx, :] = zone_areas

            demand = np.array([
                areas[z_idx, c_idx] * self.crops[c_idx].water_quota_m3_per_ha
                for c_idx in range(self.c_count)
            ], dtype=float)
            water_ratio = rng.uniform(0.62, 1.05, size=self.c_count)
            cell_water = np.minimum(demand * water_ratio, demand * 1.2)
            available = max(zone.water_available, 1e-9)
            if float(np.sum(cell_water)) > available:
                cell_water *= available / max(float(np.sum(cell_water)), 1e-9)
            surface_share = min(0.85, max(0.0, zone.surface_water_available / available))
            surface_water[z_idx, :] = cell_water * surface_share
            groundwater[z_idx, :] = cell_water - surface_water[z_idx, :]

            for c_idx, crop in enumerate(self.crops):
                nitrogen[z_idx, c_idx] = rng.uniform(crop.effective_nitrogen_min, crop.nitrogen_max_kg_ha)

        return self.encode(areas, surface_water, groundwater, nitrogen)

    def encode(
        self,
        areas: np.ndarray,
        surface_water: np.ndarray,
        groundwater: np.ndarray,
        nitrogen: np.ndarray,
    ) -> np.ndarray:
        return np.concatenate([
            areas.reshape(-1),
            surface_water.reshape(-1),
            groundwater.reshape(-1),
            nitrogen.reshape(-1),
        ])

    def repair_vector(self, x: np.ndarray) -> np.ndarray:
        areas, surface_water, groundwater, nitrogen = self._decode(np.asarray(x, dtype=float).copy())
        areas = np.clip(areas, 0.0, np.inf)
        surface_water = np.clip(surface_water, 0.0, np.inf)
        groundwater = np.clip(groundwater, 0.0, np.inf)

        for z_idx, zone in enumerate(self.zones):
            zone_max_area = zone.land_area if zone.max_area is None else min(zone.max_area, zone.land_area)
            for c_idx, crop in enumerate(self.crops):
                areas[z_idx, c_idx] = min(
                    areas[z_idx, c_idx],
                    zone_max_area * crop.max_area_ratio,
                )
                nitrogen[z_idx, c_idx] = float(np.clip(
                    nitrogen[z_idx, c_idx],
                    crop.effective_nitrogen_min,
                    crop.nitrogen_max_kg_ha,
                ))

            area_sum = float(np.sum(areas[z_idx, :]))
            if area_sum > zone_max_area:
                areas[z_idx, :] *= zone_max_area / max(area_sum, 1e-9)
                area_sum = zone_max_area
            if zone.min_area > 0 and 0 < area_sum < zone.min_area:
                scale = min(zone_max_area / max(area_sum, 1e-9), zone.min_area / max(area_sum, 1e-9))
                areas[z_idx, :] *= scale

            demand = np.array([
                areas[z_idx, c_idx] * self.crops[c_idx].water_quota_m3_per_ha
                for c_idx in range(self.c_count)
            ], dtype=float)
            max_cell_water = demand * 1.2
            cell_water = np.minimum(surface_water[z_idx, :] + groundwater[z_idx, :], max_cell_water)
            min_zone_water = float(np.sum(demand) * 0.55)
            max_zone_water = min(float(np.sum(max_cell_water)), zone.water_available)
            current_water = float(np.sum(cell_water))
            if current_water < min_zone_water and max_zone_water > current_water:
                deficit = min(min_zone_water, max_zone_water) - current_water
                capacity = np.maximum(max_cell_water - cell_water, 0.0)
                cap_sum = float(np.sum(capacity))
                if cap_sum > 1e-9:
                    cell_water += capacity / cap_sum * min(deficit, cap_sum)
            water_sum = float(np.sum(cell_water))
            if water_sum > max_zone_water:
                cell_water *= max_zone_water / max(water_sum, 1e-9)

            source_total = float(np.sum(surface_water[z_idx, :] + groundwater[z_idx, :]))
            if source_total > 1e-9:
                surface_ratio = np.divide(
                    surface_water[z_idx, :],
                    surface_water[z_idx, :] + groundwater[z_idx, :],
                    out=np.full(self.c_count, 0.8),
                    where=(surface_water[z_idx, :] + groundwater[z_idx, :]) > 1e-9,
                )
            else:
                surface_ratio = np.full(self.c_count, 0.8)
            surface_water[z_idx, :] = cell_water * surface_ratio
            groundwater[z_idx, :] = cell_water - surface_water[z_idx, :]

            surface_sum = float(np.sum(surface_water[z_idx, :]))
            if surface_sum > zone.surface_water_available:
                excess = surface_sum - zone.surface_water_available
                surface_water[z_idx, :] *= zone.surface_water_available / max(surface_sum, 1e-9)
                groundwater[z_idx, :] += self._spread_by_capacity(
                    excess,
                    cell_water - groundwater[z_idx, :],
                )

            ground_sum = float(np.sum(groundwater[z_idx, :]))
            if ground_sum > zone.groundwater_available:
                excess = ground_sum - zone.groundwater_available
                groundwater[z_idx, :] *= zone.groundwater_available / max(ground_sum, 1e-9)
                surface_water[z_idx, :] += self._spread_by_capacity(
                    excess,
                    cell_water - surface_water[z_idx, :],
                )

            total_after_source = surface_water[z_idx, :] + groundwater[z_idx, :]
            over_cell = total_after_source > max_cell_water
            if np.any(over_cell):
                ratio = np.divide(
                    max_cell_water,
                    total_after_source,
                    out=np.ones_like(total_after_source),
                    where=total_after_source > 1e-9,
                )
                surface_water[z_idx, over_cell] *= ratio[over_cell]
                groundwater[z_idx, over_cell] *= ratio[over_cell]

        return np.clip(self.encode(areas, surface_water, groundwater, nitrogen), self.xl, self.xu)

    @staticmethod
    def _spread_by_capacity(amount: float, capacity: np.ndarray) -> np.ndarray:
        capacity = np.maximum(capacity, 0.0)
        cap_sum = float(np.sum(capacity))
        if amount <= 0 or cap_sum <= 1e-9:
            return np.zeros_like(capacity)
        return capacity / cap_sum * min(amount, cap_sum)


def _build_result(
    ctx: WaterSoilResourceContext,
    problem: WaterSoilResourceProblem,
    x: np.ndarray,
    metrics: dict[str, Any],
    pareto_metrics: np.ndarray,
    scores: np.ndarray,
    weights: np.ndarray,
    selected_index: int,
) -> WaterSoilResourceResult:
    areas = metrics['areas']
    surface_water = metrics['surface_water']
    groundwater = metrics['groundwater']
    nitrogen = metrics['nitrogen']

    allocation: list[dict] = []
    stage_water: list[dict] = []
    for z_idx, zone in enumerate(ctx.zones):
        for c_idx, crop in enumerate(ctx.crops):
            area = float(areas[z_idx, c_idx])
            surface = float(surface_water[z_idx, c_idx])
            ground = float(groundwater[z_idx, c_idx])
            total_water = surface + ground
            nitrogen_kg_ha = float(nitrogen[z_idx, c_idx])
            total_nitrogen = area * nitrogen_kg_ha
            allocation.append({
                'zone_id': zone.zone_id,
                'zone_name': zone.zone_name,
                'crop': crop.crop,
                'crop_name': crop.crop_name,
                'area_ha': round(area, 4),
                'surface_water_m3': round(surface, 2),
                'groundwater_m3': round(ground, 2),
                'total_water_m3': round(total_water, 2),
                'nitrogen_kg_ha': round(nitrogen_kg_ha, 4),
                'total_nitrogen_kg': round(total_nitrogen, 2),
                'water_quota_m3_per_ha': round(crop.water_quota_m3_per_ha, 2),
                'nitrogen_max_kg_ha': round(crop.nitrogen_max_kg_ha, 2),
            })
            stage_water.append({
                'zone_id': zone.zone_id,
                'zone_name': zone.zone_name,
                'crop': crop.crop,
                'crop_name': crop.crop_name,
                'stage': 'season',
                'stage_name': '全生育期',
                'surface_water_m3': round(surface, 2),
                'groundwater_m3': round(ground, 2),
                'water_amount_m3': round(total_water, 2),
                'water_depth_mm': round(total_water / max(area * 10.0, 1e-6), 3),
                'demand_water_m3': round(area * crop.water_quota_m3_per_ha, 2),
                'satisfaction': round(total_water / max(area * crop.water_quota_m3_per_ha, 1e-6), 4),
                'nitrogen_kg_ha': round(nitrogen_kg_ha, 4),
                'total_nitrogen_kg': round(total_nitrogen, 2),
            })

    zone_summary = []
    for z_idx, zone in enumerate(ctx.zones):
        zone_summary.append({
            'zone_id': zone.zone_id,
            'zone_name': zone.zone_name,
            'land_area_ha': round(zone.land_area, 4),
            'allocated_area_ha': round(float(np.sum(areas[z_idx, :])), 4),
            'surface_water_available_m3': round(zone.surface_water_available, 2),
            'groundwater_available_m3': round(zone.groundwater_available, 2),
            'water_available_m3': round(zone.water_available, 2),
            'surface_water_used_m3': round(float(metrics['zone_surface'][z_idx]), 2),
            'groundwater_used_m3': round(float(metrics['zone_groundwater'][z_idx]), 2),
            'water_used_m3': round(float(metrics['zone_water'][z_idx]), 2),
            'water_demand_m3': round(float(metrics['zone_demand'][z_idx]), 2),
            'total_nitrogen_kg': round(float(metrics['zone_nitrogen'][z_idx]), 2),
            'net_benefit_yuan': round(float(metrics['zone_benefit'][z_idx]), 2),
            'satisfaction': round(float(metrics['zone_satisfaction'][z_idx]), 4),
        })

    crop_summary = []
    for c_idx, crop in enumerate(ctx.crops):
        total_water = float(metrics['crop_surface'][c_idx] + metrics['crop_groundwater'][c_idx])
        total_nitrogen = float(metrics['crop_nitrogen'][c_idx])
        crop_summary.append({
            'crop': crop.crop,
            'crop_name': crop.crop_name,
            'area_ha': round(float(metrics['crop_area'][c_idx]), 4),
            'yield_kg': round(float(metrics['crop_yield'][c_idx]), 2),
            'net_benefit_yuan': round(float(metrics['crop_benefit'][c_idx]), 2),
            'surface_water_m3': round(float(metrics['crop_surface'][c_idx]), 2),
            'groundwater_m3': round(float(metrics['crop_groundwater'][c_idx]), 2),
            'total_water_m3': round(total_water, 2),
            'total_nitrogen_kg': round(total_nitrogen, 2),
            'water_efficiency_kg_per_m3': round(float(metrics['crop_yield'][c_idx]) / max(total_water, 1e-6), 6),
            'nitrogen_efficiency_kg_per_kg': round(float(metrics['crop_yield'][c_idx]) / max(total_nitrogen, 1e-6), 6),
        })

    pareto = []
    for i in range(len(pareto_metrics)):
        pareto.append({
            'unit_water_benefit_yuan_per_m3': round(float(pareto_metrics[i, 0]), 6),
            'fairness': round(float(pareto_metrics[i, 1]), 6),
            'water_efficiency_kg_per_m3': round(float(pareto_metrics[i, 2]), 6),
            'nitrogen_efficiency_kg_per_kg': round(float(pareto_metrics[i, 3]), 6),
            'score': round(float(scores[i]), 6),
            'selected': i == selected_index,
        })

    summary = {
        'mode': 'water-soil-resource',
        'n_zones': len(ctx.zones),
        'n_crops': len(ctx.crops),
        'n_stages': 1,
        'total_area_ha': round(float(np.sum(areas)), 4),
        'total_surface_water_m3': round(float(metrics['total_surface_water']), 2),
        'total_groundwater_m3': round(float(metrics['total_groundwater']), 2),
        'total_water_m3': round(float(metrics['total_water']), 2),
        'total_demand_m3': round(float(metrics['total_demand']), 2),
        'total_nitrogen_kg': round(float(metrics['total_nitrogen']), 2),
        'total_yield_kg': round(float(metrics['total_yield']), 2),
        'total_benefit_yuan': round(float(metrics['total_benefit']), 2),
        'objective_values': {
            'unit_water_benefit_yuan_per_m3': round(float(metrics['unit_water_benefit']), 6),
            'fairness': round(float(metrics['fairness']), 6),
            'water_efficiency_kg_per_m3': round(float(metrics['water_efficiency']), 6),
            'nitrogen_efficiency_kg_per_kg': round(float(metrics['nitrogen_efficiency']), 6),
        },
        'topsis_score': round(float(scores[selected_index]), 6),
        'entropy_weights': {
            'unit_water_benefit': round(float(weights[0]), 6),
            'fairness': round(float(weights[1]), 6),
            'water_efficiency': round(float(weights[2]), 6),
            'nitrogen_efficiency': round(float(weights[3]), 6),
        },
    }

    topsis_summary = {
        'selected_index': int(selected_index),
        'unit_water_benefit_yuan_per_m3': round(float(metrics['unit_water_benefit']), 6),
        'fairness': round(float(metrics['fairness']), 6),
        'water_efficiency_kg_per_m3': round(float(metrics['water_efficiency']), 6),
        'nitrogen_efficiency_kg_per_kg': round(float(metrics['nitrogen_efficiency']), 6),
        'decision_vector': [round(float(v), 6) for v in x],
    }

    return WaterSoilResourceResult(
        summary=summary,
        allocation=allocation,
        stage_water=stage_water,
        zone_summary=zone_summary,
        crop_summary=crop_summary,
        pareto=pareto,
        topsis_summary=topsis_summary,
    )


def solve_water_soil_resource(ctx: WaterSoilResourceContext) -> WaterSoilResourceResult:
    """执行灌区水土资源-水氮作物多目标优化配置。"""
    if not ctx.zones:
        raise ValueError('分区列表不能为空')
    if not ctx.crops:
        raise ValueError('作物列表不能为空')
    for zone in ctx.zones:
        if zone.land_area <= 0:
            raise ValueError(f'分区 {zone.zone_id} 的 land_area 必须大于 0')
        if zone.water_available <= 0:
            raise ValueError(f'分区 {zone.zone_id} 的水量上限必须大于 0')
    for crop in ctx.crops:
        if crop.water_quota_m3_per_ha <= 0:
            raise ValueError(f'作物 {crop.crop} 的 water_quota_m3_per_ha 必须大于 0')
        if crop.nitrogen_max_kg_ha <= 0:
            raise ValueError(f'作物 {crop.crop} 的 nitrogen_max_kg_ha 必须大于 0')

    problem = WaterSoilResourceProblem(
        zones=ctx.zones,
        crops=ctx.crops,
        total_water_available=ctx.total_water_available,
    )
    algorithm = NSGA2(
        pop_size=max(10, int(ctx.pop_size)),
        sampling=WaterSoilResourceSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=0.1, eta=20),
        repair=WaterSoilResourceRepair(),
        eliminate_duplicates=True,
    )
    res = minimize(
        problem,
        algorithm,
        termination=('n_gen', max(1, int(ctx.n_gen))),
        seed=int(ctx.seed),
        verbose=False,
    )

    pop = getattr(res, 'pop', None)
    raw_x = pop.get('X') if pop is not None else None
    raw_g = pop.get('G') if pop is not None else None
    if raw_x is None or len(raw_x) == 0:
        raw_x = res.X
        raw_g = res.G
    if raw_x is None or len(raw_x) == 0:
        raise RuntimeError('NSGA-II 未收敛到任何解，请调整分区水量、面积约束或算法参数')
    raw_x = np.asarray(raw_x, dtype=float)
    if raw_x.ndim == 1:
        raw_x = raw_x.reshape(1, -1)
    raw_g = np.asarray(raw_g, dtype=float) if raw_g is not None else np.zeros((len(raw_x), 0))
    if raw_g.ndim == 1:
        raw_g = raw_g.reshape(1, -1)

    feasible_mask = np.sum(raw_g > 1e-4, axis=1) == 0
    if not np.any(feasible_mask):
        violation = np.maximum(raw_g, 0.0).sum(axis=1)
        best_violation = float(np.min(violation)) if len(violation) else 0.0
        raise RuntimeError(f'NSGA-II 未找到可行解，最小约束违约量为 {best_violation:.4f}，请检查面积、水量或施氮约束')

    x_feas = raw_x[feasible_mask]
    metrics_store = [problem._evaluate_solution(x) for x in x_feas]
    pareto_metrics = np.array([
        [
            item['unit_water_benefit'],
            item['fairness'],
            item['water_efficiency'],
            item['nitrogen_efficiency'],
        ]
        for item in metrics_store
    ], dtype=float)

    pref = _normalize_weights([
        ctx.pref_weight_benefit,
        ctx.pref_weight_fairness,
        ctx.pref_weight_efficiency,
        ctx.pref_weight_nitrogen_efficiency,
    ], 4)
    scores, weights, best_idx = _entropy_topsis_max(pareto_metrics, pref, ctx.alpha)
    return _build_result(
        ctx=ctx,
        problem=problem,
        x=x_feas[best_idx],
        metrics=metrics_store[best_idx],
        pareto_metrics=pareto_metrics,
        scores=scores,
        weights=weights,
        selected_index=best_idx,
    )
