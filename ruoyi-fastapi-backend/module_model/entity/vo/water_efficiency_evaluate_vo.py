"""
灌区农业水效评价模型 JSON 入参与响应模型。

评价方法：熵权-TOPSIS 综合评价法，支持多时段历史数据横向对比。
所有指标由前端表格直接输入（原始统计值），后端不做派生计算。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class WaterEfficiencyZoneInputModel(BaseModel):
    """分区基础信息。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    zone_id: str = Field(description='分区编号')
    zone_name: Optional[str] = Field(default=None, description='分区名称')


class WaterEfficiencyZonePeriodInputModel(WaterEfficiencyZoneInputModel):
    """分区在某一历史时段的原始评价指标（前端已统计好的值）。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    # 用水效率类（越大越好）
    iwue: float = Field(
        default=0.0,
        ge=0,
        description='灌溉水利用系数 IWUE：作物有效利用水量 / 毛取水量',
    )
    water_productivity_kg_m3: float = Field(
        default=0.0,
        ge=0,
        description='水分生产率 WUE：作物产量(kg) / 灌溉水量(m³)',
    )
    benefit_yuan_per_m3: float = Field(
        default=0.0,
        ge=0,
        description='单方水净效益 BEC：净收益(元) / 灌溉水量(m³)',
    )

    # 灌溉质量类（越大越好）
    irrigation_reliability: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description='灌溉保证率 IRS：满足需水的灌溉次数 / 总灌溉次数',
    )
    field_efficiency: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description='田间水利用系数 FE：田间有效水量 / 田间取水量',
    )

    # 资源配置类（适中，标准化时采用偏离度处理）
    surface_water_utilization: float = Field(
        default=0.0,
        ge=0,
        le=2,
        description='地表水利用率 SUR：实际使用地表水量 / 可供地表水量',
    )
    groundwater_utilization: float = Field(
        default=0.0,
        ge=0,
        le=2,
        description='地下水利用率 GWR：实际使用地下水量 / 可供地下水量',
    )

    # 资源压力类（越小越好）
    groundwater_dependency: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description='地下水依赖度 GWI：地下水用量 / 总用水量',
    )


class WaterEfficiencyPeriodInputModel(BaseModel):
    """单个历史时段的完整数据。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    period_id: str = Field(description='时段编号，如 2024Q1、2024 年度')
    period_label: Optional[str] = Field(default=None, description='时段展示名称')
    zones: List[WaterEfficiencyZonePeriodInputModel] = Field(
        default_factory=list,
        description='该时段内各分区的原始评价指标',
    )

    @model_validator(mode='after')
    def _validate_zones(self) -> 'WaterEfficiencyPeriodInputModel':
        if not self.zones:
            raise ValueError(f'时段 {self.period_id} 的 zones 不能为空')
        seen: set[str] = set()
        for z in self.zones:
            if z.zone_id in seen:
                raise ValueError(f'时段 {self.period_id} 中分区编号 {z.zone_id} 重复')
            seen.add(z.zone_id)
        return self


class WaterEfficiencyEvaluateRequest(BaseModel):
    """灌区农业水效评价请求，支持多时段横向对比。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    irrigation_area_code: str = Field(default='chahayang', description='灌区编码')
    periods: List[WaterEfficiencyPeriodInputModel] = Field(
        min_length=1,
        description='历史时段列表，至少传入 1 个时段',
    )
    indicator_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description=(
            '用户主观权重字典，键为指标英文缩写，值为 0~1 之间的权重值。'
            '支持的键：iwue, water_productivity_kg_m3, benefit_yuan_per_m3, '
            'irrigation_reliability, field_efficiency, surface_water_utilization, '
            'groundwater_utilization, groundwater_dependency。'
            '为空时完全采用熵权法定权'
        ),
    )
    alpha: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description='先验权重与熵权混合系数，0=纯熵权，1=纯主观权重，0.5=各占一半',
    )
    grade_thresholds: Optional[Dict[str, float]] = Field(
        default=None,
        description='分级阈值，如 {"excellent": 0.8, "good": 0.6, "qualified": 0.4}，为空时使用默认值',
    )

    @model_validator(mode='after')
    def _validate_periods(self) -> 'WaterEfficiencyEvaluateRequest':
        if not self.periods:
            raise ValueError('periods 不能为空，至少传入 1 个时段')
        period_ids = [p.period_id for p in self.periods]
        if len(period_ids) != len(set(period_ids)):
            raise ValueError(f'period_id 不可重复，当前传入: {period_ids}')
        return self


class WaterEfficiencyIndicatorResultModel(BaseModel):
    """单个分区在单一时段内的指标详细结果。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    zone_id: str = Field(description='分区编号')
    zone_name: Optional[str] = Field(default=None, description='分区名称')

    # 原始值
    original: Dict[str, float] = Field(description='各指标原始输入值')
    # 标准化值（统一为越大越好的方向）
    normalized: Dict[str, float] = Field(description='各指标标准化后的值')
    # 加权值
    weighted: Dict[str, float] = Field(description='各指标加权后的值')
    # 最终得分
    score: float = Field(description='TOPSIS 相对贴近度得分')
    # 排名
    rank: int = Field(description='该时段内排名（1=最优）')
    # 等级
    grade: str = Field(description='等级：excellent/good/qualified/unqualified 或中文优秀/良好/合格/不合格')


class WaterEfficiencyPeriodResultModel(BaseModel):
    """单个历史时段的评价结果汇总。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    period_id: str = Field(description='时段编号')
    period_label: Optional[str] = Field(default=None, description='时段展示名称')
    n_zones: int = Field(description='该时段参与评价的分区数量')

    # 各分区评价结果
    zone_results: List[WaterEfficiencyIndicatorResultModel] = Field(
        description='各分区评价结果列表，按 rank 升序排列',
    )

    # TOPSIS 正负理想解
    topsis_ideal: Dict[str, float] = Field(description='正理想解向量')
    topsis_negative: Dict[str, float] = Field(description='负理想解向量')

    # 最终采用的混合权重
    indicator_weights: Dict[str, float] = Field(description='各指标最终权重（混合赋权后）')

    # 熵权法客观权重
    entropy_weights: Dict[str, float] = Field(description='各指标熵权法定权结果')

    # 时段整体统计
    summary: Dict[str, Any] = Field(
        description='该时段评价统计摘要：平均分、最高分区、最低分区等',
    )


class WaterEfficiencyEvaluateResponse(BaseModel):
    """灌区农业水效评价响应，支持多时段对比。"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    # 总体摘要
    summary: Dict[str, Any] = Field(
        description='总体统计摘要：参与时段数、总分区数、各等级分布等',
    )
    # 各时段独立评价结果
    period_results: List[WaterEfficiencyPeriodResultModel] = Field(
        description='各时段评价结果列表，按 period_id 升序排列',
    )
    # 指标权重配置
    indicator_info: Dict[str, str] = Field(
        description='各指标中英文名称对照，供前端展示使用',
    )


# 默认指标中英文对照
DEFAULT_INDICATOR_INFO: Dict[str, str] = {
    'iwue': '灌溉水利用系数 (IWUE)',
    'water_productivity_kg_m3': '水分生产率 WUE (kg/m³)',
    'benefit_yuan_per_m3': '单方水净效益 BEC (元/m³)',
    'irrigation_reliability': '灌溉保证率 IRS',
    'field_efficiency': '田间水利用系数 FE',
    'surface_water_utilization': '地表水利用率 SUR',
    'groundwater_utilization': '地下水利用率 GWR',
    'groundwater_dependency': '地下水依赖度 GWI',
}

# 默认分级阈值
# 注：基于熵权-TOPSIS 的贴近度分布特性，14 个分区综合得分通常落在 [0.25, 0.78] 区间，
# 故将「优秀」阈值设为 0.7、「良好」0.5、「合格」0.3，与典型分布匹配。
DEFAULT_GRADE_THRESHOLDS: Dict[str, float] = {
    'excellent': 0.7,
    'good': 0.5,
    'qualified': 0.3,
}

# 默认等级中文映射
DEFAULT_GRADE_LABELS: Dict[str, str] = {
    'excellent': '优秀',
    'good': '良好',
    'qualified': '合格',
    'unqualified': '不合格',
}
