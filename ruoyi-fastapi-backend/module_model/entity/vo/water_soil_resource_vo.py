"""
灌区水土资源-水氮作物多目标优化配置 JSON 入参模型。
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


DEFAULT_WATER_SOIL_ZONES = [
    {
        'zone_id': 'Z01',
        'zone_name': '红河',
        'land_area': 2865.02,
        'surface_water_available': 36259380.0,
        'groundwater_available': 4696734.0,
    },
    {
        'zone_id': 'Z02',
        'zone_name': '万发',
        'land_area': 3135.47,
        'surface_water_available': 39296070.0,
        'groundwater_available': 4873331.0,
    },
    {
        'zone_id': 'Z03',
        'zone_name': '金光',
        'land_area': 3398.08,
        'surface_water_available': 41055570.0,
        'groundwater_available': 5091537.0,
    },
    {
        'zone_id': 'Z04',
        'zone_name': '稻花香',
        'land_area': 3550.21,
        'surface_water_available': 30910780.0,
        'groundwater_available': 3833423.0,
    },
    {
        'zone_id': 'Z05',
        'zone_name': '发展',
        'land_area': 2672.96,
        'surface_water_available': 44974950.0,
        'groundwater_available': 5877602.0,
    },
    {
        'zone_id': 'Z06',
        'zone_name': '金星',
        'land_area': 3212.89,
        'surface_water_available': 39945480.0,
        'groundwater_available': 5253868.0,
    },
    {
        'zone_id': 'Z07',
        'zone_name': '太平湖',
        'land_area': 1761.67,
        'surface_water_available': 43645990.0,
        'groundwater_available': 5412790.0,
    },
    {
        'zone_id': 'Z08',
        'zone_name': '海洋',
        'land_area': 3889.15,
        'surface_water_available': 64301350.0,
        'groundwater_available': 8974380.0,
    },
    {
        'zone_id': 'Z09',
        'zone_name': '新立',
        'land_area': 3454.23,
        'surface_water_available': 19992150.0,
        'groundwater_available': 2979341.0,
    },
    {
        'zone_id': 'Z10',
        'zone_name': '丰收',
        'land_area': 3774.23,
        'surface_water_available': 37951930.0,
        'groundwater_available': 4006637.0,
    },
    {
        'zone_id': 'Z11',
        'zone_name': '二十八方',
        'land_area': 5560.37,
        'surface_water_available': 26396760.0,
        'groundwater_available': 3273614.0,
    },
    {
        'zone_id': 'Z12',
        'zone_name': '联合',
        'land_area': 1795.09,
        'surface_water_available': 42364060.0,
        'groundwater_available': 1153810.0,
    },
    {
        'zone_id': 'Z13',
        'zone_name': '金边',
        'land_area': 2139.52,
        'surface_water_available': 7026099.0,
        'groundwater_available': 871347.0,
    },
    {
        'zone_id': 'Z14',
        'zone_name': '长吉岗',
        'land_area': 5459.97,
        'surface_water_available': 33879440.0,
        'groundwater_available': 6701584.0,
    },
]

for _zone in DEFAULT_WATER_SOIL_ZONES:
    _zone['min_area'] = round(float(_zone['land_area']) * 0.75, 4)


class WaterSoilZoneInputModel(BaseModel):
    """灌区分区输入。"""

    zone_id: str = Field(description='分区编号')
    zone_name: Optional[str] = Field(default=None, description='分区名称')
    land_area: float = Field(gt=0, description='可配置耕地面积 (ha)')
    water_available: Optional[float] = Field(default=None, gt=0, description='兼容字段：可供总水量 (m³)')
    surface_water_available: Optional[float] = Field(default=None, ge=0, description='地表水可供水量 (m³)')
    groundwater_available: Optional[float] = Field(default=None, ge=0, description='地下水可供水量 (m³)')
    min_area: float = Field(default=0.0, ge=0, description='分区最小种植面积 (ha)')
    max_area: Optional[float] = Field(default=None, gt=0, description='分区最大种植面积 (ha)，默认等于 land_area')


class WaterSoilCropInputModel(BaseModel):
    """作物经济、产量、水氮参数。"""

    crop: Literal['rice', 'corn', 'soybean'] | str = Field(description='作物编码：rice/corn/soybean')
    crop_name: Optional[str] = Field(default=None, description='作物名称')
    min_area_ratio: float = Field(default=0.0, ge=0, le=1, description='每个分区内该作物最小面积比例')
    max_area_ratio: float = Field(default=1.0, ge=0, le=1, description='每个分区内该作物最大面积比例')
    yield_kg_per_ha: float = Field(gt=0, description='充分水氮条件下单位面积产量 (kg/ha)')
    price_yuan_per_kg: float = Field(gt=0, description='作物单价 (元/kg)')
    cost_yuan_per_ha: float = Field(default=0.0, ge=0, description='单位面积种植成本 (元/ha)')
    water_quota_m3_per_ha: float = Field(default=8000.0, gt=0, description='作物季节灌溉定额 (m³/ha)')
    nitrogen_max_kg_ha: float = Field(default=200.0, gt=0, description='单位面积施氮上限 (kg/ha)')
    nitrogen_min_kg_ha: float = Field(default=0.0, ge=0, description='单位面积施氮下限 (kg/ha)，用于避免零施氮导致氮效目标退化')
    nitrogen_productivity_coeff: float = Field(default=1.0, gt=0, description='氮肥生产效率修正系数')
    water_productivity_coeff: float = Field(default=1.0, gt=0, description='水分生产效率修正系数')
    nitrogen_cost_yuan_per_kg: float = Field(default=1.0, ge=0, description='氮肥成本 (元/kg)')


class WaterSoilStageInputModel(BaseModel):
    """兼容旧版生育期入参，新版统一按全生育期水氮配置。"""

    stage: str = Field(description='生育期编码')
    stage_name: Optional[str] = Field(default=None, description='生育期名称')
    min_water_mm: float = Field(default=0.0, ge=0, description='最小灌水深度 (mm)')
    max_water_mm: float = Field(gt=0, description='最大灌水深度 (mm)')
    demand_water_mm: float = Field(gt=0, description='需水深度 (mm)')
    yield_response_weight: float = Field(default=1.0, ge=0, description='产量响应权重')


class WaterSoilResourceOptimizeRequest(BaseModel):
    """灌区水土资源-水氮作物多目标优化配置请求。"""

    mode: Literal['water-soil-resource'] = 'water-soil-resource'
    zones: List[WaterSoilZoneInputModel] = Field(
        default_factory=lambda: [WaterSoilZoneInputModel(**item) for item in DEFAULT_WATER_SOIL_ZONES],
        description='灌区分区列表，默认内置14个管理区',
    )
    crops: List[WaterSoilCropInputModel] = Field(
        default_factory=lambda: [
            WaterSoilCropInputModel(
                crop='rice',
                crop_name='水稻',
                yield_kg_per_ha=9255.56,
                price_yuan_per_kg=3.16,
                cost_yuan_per_ha=8400,
                water_quota_m3_per_ha=8000,
                nitrogen_min_kg_ha=80,
                nitrogen_max_kg_ha=250,
                nitrogen_productivity_coeff=1.0,
                water_productivity_coeff=1.0,
            ),
            WaterSoilCropInputModel(
                crop='corn',
                crop_name='玉米',
                yield_kg_per_ha=5269.44,
                price_yuan_per_kg=2.25,
                cost_yuan_per_ha=7200,
                water_quota_m3_per_ha=1900,
                nitrogen_min_kg_ha=70,
                nitrogen_max_kg_ha=230,
                nitrogen_productivity_coeff=1.05,
                water_productivity_coeff=1.03,
            ),
            WaterSoilCropInputModel(
                crop='soybean',
                crop_name='大豆',
                yield_kg_per_ha=5945.0,
                price_yuan_per_kg=5.4,
                cost_yuan_per_ha=3000,
                water_quota_m3_per_ha=1700,
                nitrogen_min_kg_ha=40,
                nitrogen_max_kg_ha=180,
                nitrogen_productivity_coeff=1.08,
                water_productivity_coeff=1.05,
            ),
        ],
        description='作物参数列表，默认包含水稻、玉米、大豆',
    )
    stages: List[WaterSoilStageInputModel] = Field(
        default_factory=list,
        description='兼容旧版字段；新版结果按全生育期输出',
    )
    total_water_available: Optional[float] = Field(default=None, gt=0, description='灌区总可供水量 (m³)，为空则只约束各分区水源')
    pop_size: int = Field(default=120, ge=10, description='NSGA-II 种群规模')
    n_gen: int = Field(default=100, ge=1, description='NSGA-II 迭代代数')
    seed: int = Field(default=1, ge=0, description='随机种子')
    pref_weight_benefit: float = Field(default=0.35, ge=0, description='先验权重：单方水效益')
    pref_weight_fairness: float = Field(default=0.25, ge=0, description='先验权重：公平性')
    pref_weight_efficiency: float = Field(default=0.25, ge=0, description='先验权重：用水效率')
    pref_weight_nitrogen_efficiency: float = Field(default=0.15, ge=0, description='先验权重：氮肥利用效率')
    alpha: float = Field(default=0.5, ge=0, le=1, description='先验权重与熵权混合系数')
