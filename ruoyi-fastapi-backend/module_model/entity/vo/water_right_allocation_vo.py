"""
灌区初始水权分配模型 JSON 入参。

模型：灌区管理单位（Leader）与 14 个分区（Followers）的 Stackelberg 主从博弈，
下层通过线性规划在拍卖机制下全局最优出清。

收益函数采用线性简化：分区 z 的边际产值 ρ_z（元/m³），
其值由前端按作物结构预先计算并传入：

    ρ_z = Σ_c  share_{z,c} * (Y_c_max * P_c) / Q_c
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

class WaterRightZoneInputModel(BaseModel):
    """水权交易市场中的分区 Agent 入参。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    zone_id: str = Field(description='分区编号')
    zone_name: Optional[str] = Field(default=None, description='分区名称')
    land_area: float = Field(gt=0, description='可配置耕地面积 (ha)')
    surface_water_available: float = Field(ge=0, description='地表水可供水量 (m³)')
    groundwater_available: float = Field(ge=0, description='地下水可供水量 (m³)')

    crop_mix: dict[str, float] = Field(
        default_factory=dict,
        description='作物种植比例，例如 {"rice": 0.6, "corn": 0.4}；留空时按默认作物均匀分配',
    )
    marginal_value: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            '分区单位水的边际产值 ρ_z (元/m³)，由前端按 ρ_z = '
            'Σ_c share_c * (Y_c_max * P_c) / Q_c 计算；'
            '为空时由模型根据 crops + crop_mix 自动计算'
        ),
    )
    water_demand_m3: Optional[float] = Field(
        default=None,
        ge=0,
        description='分区理论需水量 (m³)，留空时按土地面积与作物定额估算',
    )
    max_purchase_m3: Optional[float] = Field(
        default=None,
        ge=0,
        description='分区最大可购入水权 (m³)，留空时按需水量上限推断',
    )
    water_saving_potential_m3: float = Field(
        default=0.0,
        ge=0,
        description='分区理论节水潜力 (m³)，用于上层的节水激励目标',
    )

    @model_validator(mode='after')
    def _validate_zone(self) -> 'WaterRightZoneInputModel':
        if self.crop_mix:
            total = sum(self.crop_mix.values())
            if total <= 0:
                raise ValueError(f'分区 {self.zone_id} 的 crop_mix 加总必须为正数')
            normalized = {k: v / total for k, v in self.crop_mix.items()}
            self.crop_mix = normalized
        return self


class WaterRightCropInputModel(BaseModel):
    """线性化收益函数下的作物参数。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    crop: str = Field(description='作物编码')
    crop_name: Optional[str] = Field(default=None, description='作物名称')
    yield_kg_per_ha: float = Field(gt=0, description='充分水条件下单位面积产量 (kg/ha)')
    price_yuan_per_kg: float = Field(gt=0, description='作物单价 (元/kg)')
    cost_yuan_per_ha: float = Field(default=0.0, ge=0, description='单位面积种植成本 (元/ha)')
    water_quota_m3_per_ha: float = Field(default=8000.0, gt=0, description='作物季节灌溉定额 (m³/ha)')

    @property
    def marginal_value(self) -> float:
        """单位水的边际产值（元/m³），用于线性规划目标系数。"""
        quota = max(self.water_quota_m3_per_ha, 1e-9)
        return max(0.0, self.yield_kg_per_ha * self.price_yuan_per_kg / quota)


class WaterRightMarketInputModel(BaseModel):
    """Stackelberg + 拍卖市场机制参数。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    mode: Literal['water-right-allocation'] = 'water-right-allocation'
    allocation_method: Literal['area'] = 'area'
    initial_total_water_m3: float = Field(gt=0, description='全灌区可分配初始水权总量 (m³)')
    reserve_price_yuan_per_m3: float = Field(default=1.0, ge=0, description='拍卖底价 / 保留价 τ')
    price_floor: float = Field(default=0.5, ge=0, description='均衡价格下限')
    price_ceiling: float = Field(default=10.0, gt=0, description='均衡价格上限')
    transaction_cost_rate: float = Field(default=0.05, ge=0, le=0.5, description='交易费率')
    fairness_weight: float = Field(default=0.3, ge=0, le=1, description='上层目标中公平性权重 η')
    saving_incentive_weight: float = Field(default=0.2, ge=0, le=1, description='上层目标中节水激励权重 γ')
    min_self_use_ratio: float = Field(default=0.0, ge=0, le=1, description='分区最低自用比例')
    big_m: float = Field(
        default=1.0e10,
        gt=0,
        description='MILP 线性化中买/卖二选一约束的大 M 常量',
    )

    @model_validator(mode='after')
    def _validate_market(self) -> 'WaterRightMarketInputModel':
        if self.price_floor >= self.price_ceiling:
            raise ValueError('price_floor 必须小于 price_ceiling')
        if not (self.price_floor <= self.reserve_price_yuan_per_m3 <= self.price_ceiling):
            raise ValueError('reserve_price 必须落在 [price_floor, price_ceiling] 区间内')
        return self


class WaterRightAllocationRequest(BaseModel):
    """灌区初始水权分配 + Stackelberg + 拍卖 LP 出清请求。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    irrigation_area_code: str = Field(default='chahayang', description='灌区编码')
    zones: List[WaterRightZoneInputModel] = Field(
        default_factory=list,
        description='灌区分区 Agent 列表；为空时由接口从数据库加载启用分区',
    )
    crops: List[WaterRightCropInputModel] = Field(
        default_factory=list,
        description='线性化作物参数，前端必须传入',
    )
    market: WaterRightMarketInputModel = Field(
        default_factory=WaterRightMarketInputModel,
        description='Stackelberg + 拍卖市场参数',
    )

    @model_validator(mode='after')
    def _validate_request(self) -> 'WaterRightAllocationRequest':
        if not self.crops:
            raise ValueError('作物列表 crops 不能为空，前端必须传入作物配置')
        seen = set()
        for zone in self.zones:
            if zone.zone_id in seen:
                raise ValueError(f'分区编号 {zone.zone_id} 重复')
            seen.add(zone.zone_id)
        return self
