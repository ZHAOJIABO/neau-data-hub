"""
渠系模型核心：梯形断面水力工具与静态校核。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from module_model.model.canals_data import CanalRecord

# 全灌区常量：重力加速度（m/s²）
GRAVITY: float = 9.81

# 全灌区常量：闸门水力计算默认值（由调用方在 API 入参中显式传入；此处仅供单元测试/未指定时使用）
DEFAULT_DISCHARGE_COEFF: float = 0.6
DEFAULT_SUBMERGENCE_COEFF: float = 0.6
DEFAULT_LATERAL_CONTRACTION: float = 0.0
DEFAULT_PERMEABILITY_INDEX: float = 0.0
DEFAULT_PERMEABILITY_COEFFICIENT: float = 1.0


# ---------------------------------------------------------------------------
# 通用断面水力（梯形）
# ---------------------------------------------------------------------------

def area_topwidth(h: float, b: float, m: float) -> tuple[float, float]:
    A = (b + m * h) * h
    T = b + 2.0 * m * h
    return A, T


def wetted_perimeter(h: float, b: float, m: float) -> float:
    if h <= 0:
        return 0.0
    return b + 2.0 * h * math.sqrt(1.0 + m * m)


def hydraulic_radius(h: float, b: float, m: float) -> float:
    if h <= 0:
        return 0.0
    A, _ = area_topwidth(h, b, m)
    P = wetted_perimeter(h, b, m)
    return A / P if P > 0 else 0.0


def manning_normal_depth(Q: float, b: float, m: float, n: float, S0: float) -> float:
    if Q <= 0 or n <= 0 or S0 <= 0:
        return 0.0
    Sf = math.sqrt(S0)

    def residual(h: float) -> float:
        A, _ = area_topwidth(h, b, m)
        R = hydraulic_radius(h, b, m)
        return (A * (R ** (2.0 / 3.0)) / n) * Sf - Q

    lo, hi = 1e-4, 50.0
    if residual(lo) > 0:
        return lo
    if residual(hi) < 0:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = residual(mid)
        if r > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


def critical_depth(Q: float, b: float, m: float) -> float:
    if Q <= 0:
        return 0.0
    rhs = Q * Q / GRAVITY

    def residual(h: float) -> float:
        A, T = area_topwidth(h, b, m)
        return (A ** 3) / max(T, 1e-9) - rhs

    lo, hi = 1e-4, 50.0
    if residual(hi) < 0:
        return hi
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = residual(mid)
        if r > 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# 静态校核
# ---------------------------------------------------------------------------

@dataclass
class StaticCheckResult:
    canal_id: str
    design_flow: float
    normal_h: float
    critical_h: float
    safe_q_min: float
    safe_q_max: float
    head_loss: float
    seepage_l_per_km: float
    safe: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'canal_id': self.canal_id,
            'design_flow': self.design_flow,
            'normal_h': self.normal_h,
            'critical_h': self.critical_h,
            'safe_q_min': self.safe_q_min,
            'safe_q_max': self.safe_q_max,
            'head_loss': self.head_loss,
            'seepage_l_per_km': self.seepage_l_per_km,
            'safe': self.safe,
            'notes': list(self.notes),
        }


def _manning_discharge(h: float, rec: CanalRecord) -> float:
    A, _ = area_topwidth(h, rec.bottom_width, rec.side_slope)
    R = hydraulic_radius(h, rec.bottom_width, rec.side_slope)
    Sf = math.sqrt(rec.slope)
    if rec.roughness <= 0 or R <= 0:
        return 0.0
    return (A * (R ** (2.0 / 3.0)) / rec.roughness) * Sf


def _seepage_per_km(
    rec: CanalRecord,
    k: float,
    permeability_index: float = DEFAULT_PERMEABILITY_INDEX,
    permeability_coefficient_a: float = DEFAULT_PERMEABILITY_COEFFICIENT,
) -> float:
    if permeability_index <= 0:
        return 0.0
    A, _ = area_topwidth(rec.design_depth, rec.bottom_width, rec.side_slope)
    return k * permeability_coefficient_a * math.sqrt(rec.slope) * permeability_index * A


def static_check(
    canal_id: str,
    k_seepage: float = 1.0,
    permeability_index: float = DEFAULT_PERMEABILITY_INDEX,
    permeability_coefficient_a: float = DEFAULT_PERMEABILITY_COEFFICIENT,
    canal_record: CanalRecord | None = None,
) -> StaticCheckResult:
    from module_model.model.canals_data import CanalsData

    rec = canal_record if canal_record is not None else CanalsData.canal(canal_id)
    Qd = rec.design_flow
    h_n = manning_normal_depth(Qd, rec.bottom_width, rec.side_slope, rec.roughness, rec.slope)
    h_c = critical_depth(Qd, rec.bottom_width, rec.side_slope)
    h_safe_max = rec.design_depth + 0.2
    Q_max = _manning_discharge(h_safe_max, rec)
    Q_min = max(0.05 * Qd, 1e-3)
    head_loss = rec.slope * rec.length
    seepage = _seepage_per_km(
        rec, k_seepage, permeability_index, permeability_coefficient_a
    )

    notes: list[str] = []
    safe = True
    if h_n > h_safe_max - 1e-6:
        notes.append('设计水深 + 超高已不满足正常水深')
        safe = False
    if h_c > rec.design_depth:
        notes.append('临界水深大于设计水深（陡坡/小流量易致急流）')
    if Q_max < Qd - 1e-3:
        notes.append('安全过流能力低于设计流量')
        safe = False
    if 0 < h_n < 0.1 * rec.design_depth:
        notes.append('设计流量下正常水深过小，可能存在不淤风险')

    return StaticCheckResult(
        canal_id=canal_id,
        design_flow=Qd,
        normal_h=h_n,
        critical_h=h_c,
        safe_q_min=Q_min,
        safe_q_max=Q_max,
        head_loss=head_loss,
        seepage_l_per_km=seepage,
        safe=safe,
        notes=notes,
    )
