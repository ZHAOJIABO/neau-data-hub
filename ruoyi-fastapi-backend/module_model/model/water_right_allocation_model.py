"""
灌区初始水权分配 + 水权交易市场博弈模型（Stackelberg 主从博弈 + 全局拍卖 LP 出清）。

模型结构
--------
1. 上层（Leader，灌区管理单位）：
   - 决策：按面积均分初始水权 R_z；设定拍卖底价 τ
   - 目标：灌区整体社会福利 + 公平性 + 节水激励

2. 下层（Followers，14 个分区 Agent）：
   - 决策：u_z（自用水量）、b_z（购入量）、s_z（售出量）
   - 目标：自身农业净收益 + 交易净收益最大化
   - 约束：水量平衡 u_z + b_z - s_z = R_z；买/卖二选一

3. 市场出清：
   - Σb_z = Σs_z（全局拍卖 LP）
   - 在保留价区间内寻找均衡价格 p*

收益函数采用线性简化：
   B_z(u_z) = ρ_z * u_z
   其中 ρ_z（元/m³）由作物结构和市场价格计算得到
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import linprog


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _sanitize(obj: Any) -> Any:
    """替换 NaN/Inf 为 None，确保 JSON 可序列化。"""
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
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


# ---------------------------------------------------------------------------
# dataclass 配置
# ---------------------------------------------------------------------------

@dataclass
class WaterRightZone:
    """求解用的分区 Agent 配置。"""
    zone_id: str
    zone_name: str
    land_area: float
    surface_water: float
    groundwater: float
    water_demand: float
    marginal_value: float
    crop_mix: dict[str, float]
    max_purchase_m3: float
    water_saving_potential: float
    min_self_use_ratio: float

    @property
    def water_available(self) -> float:
        return self.surface_water + self.groundwater

    @property
    def self_use_floor(self) -> float:
        return self.water_demand * self.min_self_use_ratio

    @property
    def self_use_ceiling(self) -> float:
        return self.water_demand + self.max_purchase_m3


@dataclass
class WaterRightCrop:
    """线性化的作物参数。"""
    crop: str
    crop_name: str
    yield_kg_per_ha: float
    price_yuan_per_kg: float
    cost_yuan_per_ha: float
    water_quota_m3_per_ha: float

    @property
    def marginal_value(self) -> float:
        quota = max(self.water_quota_m3_per_ha, 1e-9)
        return max(0.0, self.yield_kg_per_ha * self.price_yuan_per_kg / quota)


@dataclass
class WaterRightMarketConfig:
    """Stackelberg + 拍卖市场参数。"""
    initial_total_water: float
    reserve_price: float
    price_floor: float
    price_ceiling: float
    transaction_cost_rate: float
    fairness_weight: float
    saving_incentive_weight: float
    min_self_use_ratio: float
    big_m: float


# ---------------------------------------------------------------------------
# 上下文与结果
# ---------------------------------------------------------------------------

@dataclass
class WaterRightContext:
    """求解上下文。"""
    zones: list[WaterRightZone]
    crops: list[WaterRightCrop]
    market: WaterRightMarketConfig
    initial_rights: np.ndarray
    crop_lookup: dict[str, WaterRightCrop] = field(default_factory=dict)


@dataclass
class LeaderIteration:
    """Stackelberg 上层迭代记录。"""
    iteration: int
    reserve_price: float
    clearing_price: float
    total_buy_m3: float
    total_sell_m3: float
    excess_m3: float
    leader_objective: float
    social_welfare: float
    fairness_index: float


@dataclass
class AuctionClearing:
    """下层 LP 出清结果。"""
    clearing_price: float
    total_buy_m3: float
    total_sell_m3: float
    excess_m3: float
    trade_pairs: list[dict]
    zone_outcomes: list[dict]


@dataclass
class WaterRightAllocationResult:
    """完整求解结果。"""
    summary: dict
    initial_allocation: list[dict]
    equilibrium: dict
    zone_outcomes: list[dict]
    trade_flows: list[dict]
    crop_summary: list[dict]
    leader_history: list[LeaderIteration]
    metrics: dict

    def to_dict(self) -> dict:
        return _sanitize({
            'summary': self.summary,
            'initial_allocation': self.initial_allocation,
            'equilibrium': self.equilibrium,
            'zone_outcomes': self.zone_outcomes,
            'trade_flows': self.trade_flows,
            'crop_summary': self.crop_summary,
            'leader_history': [
                {
                    'iteration': it.iteration,
                    'reserve_price': it.reserve_price,
                    'clearing_price': it.clearing_price,
                    'total_buy_m3': it.total_buy_m3,
                    'total_sell_m3': it.total_sell_m3,
                    'excess_m3': it.excess_m3,
                    'leader_objective': it.leader_objective,
                    'social_welfare': it.social_welfare,
                    'fairness_index': it.fairness_index,
                }
                for it in self.leader_history
            ],
            'metrics': self.metrics,
        })


# ---------------------------------------------------------------------------
# 初始水权分配（按面积均分）
# ---------------------------------------------------------------------------

def allocate_initial_rights_by_area(
    zones: list[WaterRightZone],
    total_water: float,
) -> np.ndarray:
    """R_z = total_water * A_z / ΣA。

    注意：仅当 total_water <= Σ min(demand_z, available_z) 时有意义；
    超出部分会自动通过下层 LP 在市场上被售出。
    """
    if total_water <= 0:
        raise ValueError('全灌区可分配水量 initial_total_water_m3 必须大于 0')
    if not zones:
        raise ValueError('分区列表为空')
    areas = np.array([z.land_area for z in zones], dtype=float)
    total_area = float(np.sum(areas))
    if total_area <= 0:
        raise ValueError('分区总面积必须大于 0')
    return total_water * areas / total_area


# ---------------------------------------------------------------------------
# 边际产值计算（前端未传入时）
# ---------------------------------------------------------------------------

def compute_marginal_value(
    zone: WaterRightZone,
    crop_lookup: dict[str, WaterRightCrop],
    crops: list[WaterRightCrop],
) -> float:
    """ρ_z = Σ_c share_c * (Y_c * P_c) / Q_c。"""
    if not zone.crop_mix:
        # 平均分配到所有作物
        if not crops:
            return 0.0
        share = 1.0 / len(crops)
        return float(sum(share * crop.marginal_value for crop in crops))
    total = 0.0
    for crop_code, share in zone.crop_mix.items():
        crop = crop_lookup.get(crop_code)
        if crop is None:
            continue
        total += share * crop.marginal_value
    return float(total)


# ---------------------------------------------------------------------------
# 下层：全局拍卖 LP 出清
# ---------------------------------------------------------------------------

def solve_auction_clearing(
    ctx: WaterRightContext,
    reserve_price: float,
) -> AuctionClearing:
    """求解下层 LP，给定市场出清价格 p。

    决策变量 x ∈ R^{3n}:
        x[0:n]    = u_z (自用水量)
        x[n:2n]   = b_z (购入量)
        x[2n:3n]  = s_z (售出量)

    目标（maximize，等价 minimize）: Σρ_z u_z - (1+tx)*p*Σb_z + (1-tx)*p*Σs_z

    约束：
        (a) u_z + b_z - s_z = R_z       (n 个，水量平衡)
        (b) Σb_z - Σs_z = 0              (1 个，市场出清)
        (c) 0 <= u_z <= u_z_max
        (d) 0 <= b_z <= max_purchase_m3
        (e) 0 <= s_z <= R_z
        (f) u_z <= demand_z + b_z        (自用不超过需水+购入)
        (g) b_z + s_z <= max(R, max_buy) (买/卖互斥松弛)

    说明：保留价 τ 通过上层搜索传入（p = τ），
    上层再在候选价格集合上比较社会福利。
    """
    n = len(ctx.zones)
    rho = np.array([z.marginal_value for z in ctx.zones], dtype=float)
    R = np.asarray(ctx.initial_rights, dtype=float)
    demands = np.array([z.water_demand for z in ctx.zones], dtype=float)
    max_buys = np.array([z.max_purchase_m3 for z in ctx.zones], dtype=float)

    u_min = np.array([z.self_use_floor for z in ctx.zones], dtype=float)
    # u_z 的真正上界是 demand_z + max_buy_z（不等式约束 f 已强制）
    u_max = np.array(
        [max(z.water_demand + z.max_purchase_m3, z.water_demand, 1.0) for z in ctx.zones],
        dtype=float,
    )

    p = float(reserve_price)
    tx = float(ctx.market.transaction_cost_rate)

    # 目标（minimize）：-ρ·u + (1+tx)*p*b - (1-tx)*p*s
    c = np.zeros(3 * n)
    c[:n] = -rho
    c[n:2 * n] = (1.0 + tx) * p
    c[2 * n:3 * n] = -(1.0 - tx) * p

    # 等式约束
    A_eq = np.zeros((n + 1, 3 * n))
    b_eq = np.zeros(n + 1)
    for z in range(n):
        A_eq[z, z] = 1.0
        A_eq[z, n + z] = 1.0
        A_eq[z, 2 * n + z] = -1.0
        b_eq[z] = R[z]
    A_eq[n, n:2 * n] = 1.0
    A_eq[n, 2 * n:3 * n] = -1.0
    b_eq[n] = 0.0

    # 不等式约束（按行堆叠）：
    #  b_z + s_z <= max(R_z, max_buy_z)        -- 买/卖互斥松弛
    #  u_z <= 2*R_z + max_buy_z                 -- 自用上界（防 LP 异常放大）
    rows: list[np.ndarray] = []
    rhs: list[float] = []
    for z in range(n):
        cap = max(float(R[z]), float(max_buys[z]), 1.0)
        row = np.zeros(3 * n)
        row[n + z] = 1.0
        row[2 * n + z] = 1.0
        rows.append(row)
        rhs.append(cap)
        # u_z <= 2*R_z + max_buy_z (足够大但不失控)
        row = np.zeros(3 * n)
        row[z] = 1.0
        rows.append(row)
        rhs.append(2.0 * float(R[z]) + float(max_buys[z]))
    A_ub = np.asarray(rows, dtype=float)
    b_ub = np.asarray(rhs, dtype=float)

    # 变量边界（顺序：u_1..u_n, b_1..b_n, s_1..s_n）
    bounds: list[tuple[float, float]] = []
    for z in range(n):
        bounds.append((float(u_min[z]), 2.0 * float(R[z]) + float(max_buys[z])))  # u_z
    for z in range(n):
        bounds.append((0.0, float(max_buys[z])))                # b_z ≤ max_purchase
    for z in range(n):
        bounds.append((0.0, float(R[z])))                       # s_z ≤ R_z

    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method='highs',
    )

    if not res.success:
        raise RuntimeError(f'下层拍卖 LP 求解失败：{res.message}')

    x = res.x
    u_vec = x[:n]
    b_vec = x[n:2 * n]
    s_vec = x[2 * n:3 * n]
    p_star = p

    # 清理接近 0 的值
    b_vec = np.where(b_vec < 1e-3, 0.0, b_vec)
    s_vec = np.where(s_vec < 1e-3, 0.0, s_vec)

    total_buy = float(np.sum(b_vec))
    total_sell = float(np.sum(s_vec))

    # 计算贸易配对（贪心匹配：价差最小优先）
    trade_pairs = _match_trades(ctx.zones, b_vec, s_vec, p_star)

    # 分区结果
    zone_outcomes = []
    for z, zone in enumerate(ctx.zones):
        u_z = float(u_vec[z])
        b_z = float(b_vec[z])
        s_z = float(s_vec[z])
        gross_ag = rho[z] * u_z
        buy_cost = p_star * b_z
        sell_income = p_star * s_z
        tx_cost = ctx.market.transaction_cost_rate * p_star * (b_z + s_z)
        net_profit = gross_ag - buy_cost + sell_income - tx_cost
        zone_outcomes.append({
            'zone_id': zone.zone_id,
            'zone_name': zone.zone_name,
            'land_area_ha': round(zone.land_area, 4),
            'initial_right_m3': round(float(R[z]), 2),
            'self_used_m3': round(u_z, 2),
            'purchased_m3': round(b_z, 2),
            'sold_m3': round(s_z, 2),
            'final_used_m3': round(u_z, 2),
            'marginal_value_yuan_per_m3': round(rho[z], 6),
            'gross_agricultural_benefit_yuan': round(gross_ag, 2),
            'purchase_cost_yuan': round(buy_cost, 2),
            'sale_revenue_yuan': round(sell_income, 2),
            'transaction_cost_yuan': round(tx_cost, 2),
            'net_profit_yuan': round(net_profit, 2),
            'role': 'seller' if s_z > b_z + 1e-3 else ('buyer' if b_z > s_z + 1e-3 else 'self'),
        })

    return AuctionClearing(
        clearing_price=p_star,
        total_buy_m3=total_buy,
        total_sell_m3=total_sell,
        excess_m3=total_buy - total_sell,
        trade_pairs=trade_pairs,
        zone_outcomes=zone_outcomes,
    )


def _match_trades(
    zones: list[WaterRightZone],
    buy: np.ndarray,
    sell: np.ndarray,
    price: float,
) -> list[dict]:
    """贪心匹配买卖方生成贸易对记录。"""
    pairs: list[dict] = []
    sellers = [(i, float(sell[i])) for i in range(len(zones)) if sell[i] > 1e-3]
    buyers = [(i, float(buy[i])) for i in range(len(zones)) if buy[i] > 1e-3]
    s_idx = 0
    b_idx = 0
    while s_idx < len(sellers) and b_idx < len(buyers):
        si, sv = sellers[s_idx]
        bi, bv = buyers[b_idx]
        traded = min(sv, bv)
        if traded > 1e-3:
            pairs.append({
                'seller_zone_id': zones[si].zone_id,
                'seller_zone_name': zones[si].zone_name,
                'buyer_zone_id': zones[bi].zone_id,
                'buyer_zone_name': zones[bi].zone_name,
                'amount_m3': round(traded, 2),
                'price_yuan_per_m3': round(price, 6),
                'transaction_value_yuan': round(price * traded, 2),
            })
            sellers[s_idx] = (si, sv - traded)
            buyers[b_idx] = (bi, bv - traded)
        if sellers[s_idx][1] <= 1e-3:
            s_idx += 1
        if buyers[b_idx][1] <= 1e-3:
            b_idx += 1
    return pairs


# ---------------------------------------------------------------------------
# 上层：公平性、节水激励、Leader 目标
# ---------------------------------------------------------------------------

def compute_fairness_index(u_vec: np.ndarray) -> float:
    """1 - CV(u)，CV = σ/μ。CV >= 1 时取 0。"""
    if len(u_vec) == 0:
        return 0.0
    mean = float(np.mean(u_vec))
    if mean <= 1e-9:
        return 0.0
    cv = float(np.std(u_vec) / mean)
    return max(0.0, 1.0 - cv)


def compute_leader_objective(
    ctx: WaterRightContext,
    auction: AuctionClearing,
    u_vec: np.ndarray,
) -> tuple[float, float, float]:
    """返回 (leader_objective, social_welfare, fairness)。"""
    n = len(ctx.zones)
    rho = np.array([z.marginal_value for z in ctx.zones], dtype=float)
    total_social = float(np.sum(rho * u_vec))
    fairness = compute_fairness_index(u_vec)

    # 节水激励：Σ (R_z - u_z)^2 越低越好（用负值参与目标）
    saving_penalty = float(np.sum((ctx.initial_rights - u_vec) ** 2))

    leader = (
        total_social
        + ctx.market.fairness_weight * fairness * total_social
        - ctx.market.saving_incentive_weight * saving_penalty / max(np.sum(ctx.initial_rights) ** 2, 1.0)
    )
    return leader, total_social, fairness


# ---------------------------------------------------------------------------
# 主求解入口
# ---------------------------------------------------------------------------

def solve_water_right_allocation(ctx: WaterRightContext) -> WaterRightAllocationResult:
    """执行灌区初始水权分配 + Stackelberg + 拍卖 LP 出清。"""
    if not ctx.zones:
        raise ValueError('分区列表不能为空')
    if not ctx.crops:
        raise ValueError('作物列表不能为空')
    if ctx.market.initial_total_water <= 0:
        raise ValueError('全灌区可分配水量必须大于 0')

    # 补全 crop_lookup
    if not ctx.crop_lookup:
        ctx.crop_lookup = {crop.crop: crop for crop in ctx.crops}

    # 补全分区 marginal_value 和 water_demand
    for zone in ctx.zones:
        if zone.marginal_value <= 0:
            zone.marginal_value = compute_marginal_value(
                zone, ctx.crop_lookup, ctx.crops,
            )
        if zone.water_demand <= 0:
            zone.water_demand = _estimate_demand(zone, ctx.crop_lookup, ctx.crops)
        if zone.max_purchase_m3 <= 0:
            zone.max_purchase_m3 = max(zone.water_demand * 0.5, zone.water_available * 0.3)

    # Stackelberg 嵌套求解
    leader_history: list[LeaderIteration] = []
    best_result: AuctionClearing | None = None
    best_leader = -math.inf
    best_u_vec: np.ndarray | None = None

    # 上层价格搜索：以保留价 τ 为外层变量
    reserve_candidates = _generate_reserve_candidates(ctx.market)
    for it, tau in enumerate(reserve_candidates):
        auction = solve_auction_clearing(ctx, tau)
        u_vec = np.array([item['self_used_m3'] for item in auction.zone_outcomes], dtype=float)
        leader, social, fairness = compute_leader_objective(ctx, auction, u_vec)
        leader_history.append(LeaderIteration(
            iteration=it,
            reserve_price=tau,
            clearing_price=auction.clearing_price,
            total_buy_m3=auction.total_buy_m3,
            total_sell_m3=auction.total_sell_m3,
            excess_m3=auction.excess_m3,
            leader_objective=leader,
            social_welfare=social,
            fairness_index=fairness,
        ))
        if leader > best_leader:
            best_leader = leader
            best_result = auction
            best_u_vec = u_vec

    if best_result is None or best_u_vec is None:
        raise RuntimeError('Stackelberg 求解未能产生任何可行解')

    # 构造输出
    return _build_result(ctx, best_result, best_u_vec, leader_history)


def _estimate_demand(
    zone: WaterRightZone,
    crop_lookup: dict[str, WaterRightCrop],
    crops: list[WaterRightCrop],
) -> float:
    """根据作物结构估算理论需水量。"""
    if not zone.crop_mix and crops:
        avg_quota = float(np.mean([c.water_quota_m3_per_ha for c in crops]))
        return zone.land_area * avg_quota
    total = 0.0
    for crop_code, share in zone.crop_mix.items():
        crop = crop_lookup.get(crop_code)
        if crop is None:
            continue
        total += share * zone.land_area * crop.water_quota_m3_per_ha
    if total <= 0 and crops:
        avg_quota = float(np.mean([c.water_quota_m3_per_ha for c in crops]))
        total = zone.land_area * avg_quota
    return max(total, zone.water_available)


def _generate_reserve_candidates(market: WaterRightMarketConfig) -> list[float]:
    """在保留价可行区间内生成上层搜索候选。

    默认从底价开始，逐步接近上界，
    步长由区间宽度自适应生成（约 6 个候选点）。
    """
    lo = market.price_floor
    hi = market.price_ceiling
    span = hi - lo
    if span <= 0:
        return [market.reserve_price]
    n_steps = 6
    step = span / n_steps
    candidates = [lo + i * step for i in range(n_steps + 1)]
    candidates.append(market.reserve_price)
    # 去重排序
    return sorted(set(round(c, 6) for c in candidates))


# ---------------------------------------------------------------------------
# 结果封装
# ---------------------------------------------------------------------------

def _build_result(
    ctx: WaterRightContext,
    auction: AuctionClearing,
    u_vec: np.ndarray,
    history: list[LeaderIteration],
) -> WaterRightAllocationResult:
    n = len(ctx.zones)
    R = ctx.initial_rights
    rho = np.array([z.marginal_value for z in ctx.zones], dtype=float)
    p_star = auction.clearing_price

    initial_allocation: list[dict] = []
    for z, zone in enumerate(ctx.zones):
        initial_allocation.append({
            'zone_id': zone.zone_id,
            'zone_name': zone.zone_name,
            'land_area_ha': round(zone.land_area, 4),
            'initial_right_m3': round(float(R[z]), 2),
            'share_pct': round(float(R[z] / np.sum(R)), 6) if np.sum(R) > 0 else 0.0,
            'crop_mix': zone.crop_mix,
            'marginal_value_yuan_per_m3': round(zone.marginal_value, 6),
            'estimated_demand_m3': round(zone.water_demand, 2),
        })

    n_sellers = sum(1 for item in auction.zone_outcomes if item['role'] == 'seller')
    n_buyers = sum(1 for item in auction.zone_outcomes if item['role'] == 'buyer')

    equilibrium = {
        'clearing_price_yuan_per_m3': round(p_star, 6),
        'total_traded_m3': round(min(auction.total_buy_m3, auction.total_sell_m3), 2),
        'total_buy_m3': round(auction.total_buy_m3, 2),
        'total_sell_m3': round(auction.total_sell_m3, 2),
        'excess_m3': round(auction.excess_m3, 2),
        'n_sellers': n_sellers,
        'n_buyers': n_buyers,
        'n_self': n - n_sellers - n_buyers,
    }

    # 作物维度汇总
    crop_summary: list[dict] = []
    for crop in ctx.crops:
        crop_summary.append({
            'crop': crop.crop,
            'crop_name': crop.crop_name,
            'yield_kg_per_ha': round(crop.yield_kg_per_ha, 2),
            'price_yuan_per_kg': round(crop.price_yuan_per_kg, 4),
            'water_quota_m3_per_ha': round(crop.water_quota_m3_per_ha, 2),
            'marginal_value_yuan_per_m3': round(crop.marginal_value, 6),
        })

    total_ag = sum(item['gross_agricultural_benefit_yuan'] for item in auction.zone_outcomes)
    total_tx_cost = sum(item['transaction_cost_yuan'] for item in auction.zone_outcomes)
    total_profit = sum(item['net_profit_yuan'] for item in auction.zone_outcomes)
    fairness = compute_fairness_index(u_vec)
    total_water_saved = float(np.sum(np.maximum(R - u_vec, 0.0)))
    total_water_purchased = float(np.sum(np.maximum(u_vec - R, 0.0)))

    summary = {
        'mode': 'water-right-allocation',
        'allocation_method': 'area',
        'n_zones': n,
        'n_crops': len(ctx.crops),
        'initial_total_water_m3': round(float(np.sum(R)), 2),
        'clearing_price_yuan_per_m3': round(p_star, 6),
        'total_traded_m3': round(min(auction.total_buy_m3, auction.total_sell_m3), 2),
        'total_water_saved_m3': round(total_water_saved, 2),
        'total_water_purchased_m3': round(total_water_purchased, 2),
        'total_agricultural_benefit_yuan': round(total_ag, 2),
        'total_transaction_cost_yuan': round(total_tx_cost, 2),
        'total_social_welfare_yuan': round(total_ag - total_tx_cost, 2),
        'total_net_profit_yuan': round(total_profit, 2),
        'fairness_index': round(fairness, 6),
        'n_sellers': n_sellers,
        'n_buyers': n_buyers,
    }

    leader, social, fair = compute_leader_objective(ctx, auction, u_vec)
    metrics = {
        'leader_objective': round(leader, 6),
        'social_welfare': round(social, 6),
        'fairness_index': round(fair, 6),
        'price_floor': ctx.market.price_floor,
        'price_ceiling': ctx.market.price_ceiling,
        'fairness_weight': ctx.market.fairness_weight,
        'saving_incentive_weight': ctx.market.saving_incentive_weight,
    }

    return WaterRightAllocationResult(
        summary=summary,
        initial_allocation=initial_allocation,
        equilibrium=equilibrium,
        zone_outcomes=auction.zone_outcomes,
        trade_flows=auction.trade_pairs,
        crop_summary=crop_summary,
        leader_history=history,
        metrics=metrics,
    )


# ---------------------------------------------------------------------------
# 工厂函数：从字典构建 Context（供 service 层调用）
# ---------------------------------------------------------------------------

def build_context(
    zone_inputs: list[dict],
    crop_inputs: list[dict],
    market_input: dict,
) -> WaterRightContext:
    """从原始 dict 构造 WaterRightContext。"""
    crops = [
        WaterRightCrop(
            crop=str(item['crop']),
            crop_name=item.get('crop_name') or str(item['crop']),
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
        )
        for item in crop_inputs
    ]
    crop_lookup = {crop.crop: crop for crop in crops}

    zones: list[WaterRightZone] = []
    for item in zone_inputs:
        surface = float(
            item.get('surface_water_available')
            if item.get('surface_water_available') is not None
            else item.get('water_available')
            if item.get('water_available') is not None
            else 0.0
        )
        ground = float(item.get('groundwater_available') or 0.0)
        crop_mix = item.get('crop_mix') or {}
        if isinstance(crop_mix, dict):
            crop_mix = {str(k): float(v) for k, v in crop_mix.items()}
        else:
            crop_mix = {}
        zones.append(WaterRightZone(
            zone_id=str(item['zone_id']),
            zone_name=item.get('zone_name') or str(item['zone_id']),
            land_area=float(item['land_area']),
            surface_water=surface,
            groundwater=ground,
            water_demand=float(item.get('water_demand_m3') or 0.0),
            marginal_value=float(item.get('marginal_value') or 0.0),
            crop_mix=crop_mix,
            max_purchase_m3=float(item.get('max_purchase_m3') or 0.0),
            water_saving_potential=float(item.get('water_saving_potential_m3') or 0.0),
            min_self_use_ratio=float(item.get('min_self_use_ratio') or market_input.get('min_self_use_ratio') or 0.0),
        ))

    market = WaterRightMarketConfig(
        initial_total_water=float(market_input['initial_total_water_m3']),
        reserve_price=float(market_input.get('reserve_price_yuan_per_m3') or 1.0),
        price_floor=float(market_input.get('price_floor') or 0.5),
        price_ceiling=float(market_input.get('price_ceiling') or 10.0),
        transaction_cost_rate=float(market_input.get('transaction_cost_rate') or 0.05),
        fairness_weight=float(market_input.get('fairness_weight') or 0.3),
        saving_incentive_weight=float(market_input.get('saving_incentive_weight') or 0.2),
        min_self_use_ratio=float(market_input.get('min_self_use_ratio') or 0.0),
        big_m=float(market_input.get('big_m') or 1.0e10),
    )

    initial_rights = allocate_initial_rights_by_area(zones, market.initial_total_water)

    # 补全分区运行时参数（边际产值、需求、购买上限）
    crop_lookup = {crop.crop: crop for crop in crops}
    # 总富余水量（其他分区可能卖出的最大值），用于上限购买量估算
    total_surplus_candidate = float(sum(
        max(0.0, initial_rights[i] - z.water_demand) for i, z in enumerate(zones)
    ))
    # 平均分摊的富余量 + 自身需求的合理倍数
    avg_surplus_share = total_surplus_candidate / max(len(zones), 1)
    for idx, zone in enumerate(zones):
        if zone.marginal_value <= 0:
            zone.marginal_value = compute_marginal_value(zone, crop_lookup, crops)
        if zone.water_demand <= 0:
            zone.water_demand = _estimate_demand(zone, crop_lookup, crops)
        if zone.max_purchase_m3 <= 0:
            # 允许买到的量：足够消化其他分区的平均富余，
            # 同时覆盖自身需求缺口的一半
            own_deficit = max(0.0, zone.water_demand - initial_rights[idx])
            zone.max_purchase_m3 = max(
                own_deficit * 0.5,
                zone.water_available * 0.3,
                avg_surplus_share * 1.5,
            )
        # 保证分区能消化自身水权：max_purchase >= R - demand（允许卖后买回）
        surplus = max(0.0, initial_rights[idx] - zone.water_demand)
        zone.max_purchase_m3 = max(zone.max_purchase_m3, surplus + 1.0)

    return WaterRightContext(
        zones=zones,
        crops=crops,
        market=market,
        initial_rights=initial_rights,
        crop_lookup=crop_lookup,
    )