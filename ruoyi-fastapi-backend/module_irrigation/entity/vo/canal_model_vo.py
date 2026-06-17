"""
对外开放渠系模型的标准 JSON 入参模型。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InflowSeriesPointModel(BaseModel):
    """入流时序点。"""

    time_min: float = Field(ge=0, description='时间 (min)')
    q_m3s: float = Field(ge=0, description='入流流量 (m3/s)')


class CanalInputModel(BaseModel):
    """单条渠段输入。"""

    model_config = ConfigDict(populate_by_name=True)

    canal_id: str = Field(description='渠段编号，如 G、Z1、1-D1')
    canal_name: Optional[str] = Field(default=None, description='渠段名称')
    parent_id: Optional[str] = Field(default=None, description='父渠段编号；未传时按 canal_id 命名规则推断')
    level: Optional[str] = Field(default=None, description='渠段级别：1=干 2=支 3=斗 4=农 或 main/branch/lateral/farm')
    length: float = Field(default=0.0, ge=0, description='渠段长度 (m)')
    design_flow: float = Field(default=0.0, ge=0, description='设计流量 (m³/s)')
    design_depth: float = Field(default=0.0, ge=0, description='设计水深 (m)')
    top_width: float = Field(default=0.0, ge=0, description='设计渠顶宽 (m)')
    bottom_width: float = Field(default=0.0, ge=0, description='设计渠底宽 (m)')
    slope: float = Field(default=0.0, ge=0, description='设计纵坡')
    side_slope: float = Field(default=0.0, ge=0, description='边坡系数 (1:m)')
    roughness: float = Field(default=0.0, ge=0, description='糙率 Manning n')
    gate_height: float = Field(default=0.0, ge=0, description='闸门高度 (m)')
    gate_width: float = Field(default=0.0, ge=0, description='闸门宽度 (m)')
    min_gate_opening: float = Field(default=0.0, ge=0, description='闸门最小开度 (m)')
    max_gate_opening: float = Field(default=0.0, ge=0, description='闸门最大开度 (m)')
    water_demand: float = Field(default=0.0, ge=0, description='单次配水需水量 (m³)')
    inflow_series: Optional[List[InflowSeriesPointModel]] = Field(
        default=None,
        description='该渠段上游入流时序 (time_min, q_m3s)；未传时按恒定设计流量入流',
    )


class CanalTopologyItemModel(BaseModel):
    """显式拓扑关系。"""

    canal_id: str = Field(description='渠段编号')
    parent_id: Optional[str] = Field(default=None, description='父渠段编号；根渠段填 null')


class FullOptimizeStandardRequest(BaseModel):
    """全渠系三级顺序配水优化标准 JSON 请求。"""

    main_canal_id: str = Field(default='1', description='干渠编号（默认 1）')
    canals: List[CanalInputModel] = Field(description='渠系完整数据列表（干+支+斗渠），必填')
    topology: Optional[List[CanalTopologyItemModel]] = Field(default=None, description='可选显式父子拓扑')
    t_max: float = Field(default=360.0, gt=0, description='总输水时间上限 (h)')
    flow_ratio_min: float = Field(default=0.8, gt=0, description='斗渠配水流量/设计流量下限')
    flow_ratio_max: float = Field(default=1.0, gt=0, description='斗渠配水流量/设计流量上限')
    min_groups: int = Field(default=2, ge=2, description='斗渠轮灌候选最小分组数')
    max_groups: int = Field(default=6, ge=2, description='斗渠轮灌候选最大分组数')
    pop_size: int = Field(default=80, ge=10, description='NSGA-III 种群规模')
    n_gen: int = Field(default=60, ge=1, description='NSGA-III 迭代代数')
    seed: int = Field(default=1, ge=0, description='随机种子')
    permeability_index: float = Field(default=0.4, ge=0, description='渠床土壤透水指数')
    permeability_coefficient: float = Field(default=1.9, ge=0, description='渠床土壤透水系数')
    pref_weight_time: float = Field(default=0.4, ge=0, description='先验权重：总输水时间')
    pref_weight_loss: float = Field(default=0.3, ge=0, description='先验权重：全渠系渗漏损失')
    pref_weight_flow_var: float = Field(default=0.3, ge=0, description='先验权重：干渠流量波动')
    alpha: float = Field(default=0.5, ge=0, le=1, description='先验权重与熵权混合系数')


class FullHydroStandardRequest(BaseModel):
    """全渠系逐分钟水动力学仿真标准 JSON 请求。"""

    main_canal_id: str = Field(default='1', description='干渠编号（默认 1）')
    canals: List[CanalInputModel] = Field(
        description='全渠系渠道数据（干+支+斗+农），每条必须带 inflow_series',
    )
    topology: Optional[List[CanalTopologyItemModel]] = Field(
        default=None, description='可选显式父子拓扑；未传时按 canal_id 命名规则推断',
    )
    sim_duration_min: int = Field(default=60, ge=1, le=1440, description='仿真时长 (min)，最大 24h')
    dt_sec: int = Field(default=30, ge=30, le=60, description='时间步长 (s)')
    dx_m: float = Field(default=200.0, gt=0, description='空间步长 (m)，仅作参考')
    design_flow_ratio_min: float = Field(
        default=0.6, gt=0, le=1.0,
        description='流量下限比（相对设计流量 Q_design）：0<Q<ratio*Q_design 视为 v_silt，'
                    'Q>Q_design 视为 v_scour。v_max 已取消，由设计流量隐含。',
    )
    h_safety_margin_m: float = Field(
        default=0.3, gt=0, le=1.0,
        description='水深安全余量 (m)：h_max = design_depth + h_safety_margin，'
                    'h>h_max 视为 h_over',
    )
    downstream_h_mode: str = Field(
        default='normal',
        description='末级渠段下游水位模式：normal=各渠段按正常水深，design=设计水深，fixed=fixed_downstream_h',
    )
    fixed_downstream_h: Optional[float] = Field(default=None, ge=0, description='下游固定水位 (m)，仅 downstream_h_mode=fixed 时使用')
