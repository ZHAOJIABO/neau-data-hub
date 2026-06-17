"""
全渠系水动力学接口：

  POST /api/v1/irrigation/canal/hydro/full/standard
      全渠系逐分钟水动力学仿真（节点连续耦合）
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body
from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_irrigation.entity.vo.canal_model_vo import FullHydroStandardRequest
from module_irrigation.service.canal_full_hydro_service import CanalFullHydroService
from utils.log_util import logger
from utils.response_util import ResponseUtil


canal_hydro_controller = APIRouterPro(
    prefix='/api/v1/irrigation/canal/hydro',
    order_num=22,
    tags=['渠系水动力学'],
    dependencies=[irrigation_api_key_dependency()],
)


@canal_hydro_controller.post(
    '/full/standard',
    summary='全渠系逐分钟水动力学仿真（节点连续耦合）',
)
async def canal_hydro_full_standard(
    payload: Annotated[
        FullHydroStandardRequest,
        Body(description='全渠系逐分钟水动力学仿真标准 JSON 请求体'),
    ],
) -> JSONResponse:
    """前端传入完整渠系数据（每条渠段必带 inflow_series）与仿真参数；后端按拓扑
    逐条做圣维南仿真并通过节点流量/水位连续条件接力，最终返回全渠系时空序列
    (t, canal_id, x, Q, h, V) 供前端动态展示。"""
    canal_count = len(payload.canals)
    logger.info(
        'canal full hydro request: main={}, canals={}, sim_duration_min={}, dt_sec={}, downstream_h_mode={}',
        payload.main_canal_id,
        canal_count,
        payload.sim_duration_min,
        payload.dt_sec,
        payload.downstream_h_mode,
    )
    topology_payload = None
    if payload.topology:
        topology_payload = [t.model_dump() for t in payload.topology]
    canals_payload = [c.model_dump() for c in payload.canals]

    data = await CanalFullHydroService.run_full(
        main_canal_id=payload.main_canal_id,
        canals=canals_payload,
        topology=topology_payload,
        sim_duration_min=payload.sim_duration_min,
        dt_sec=payload.dt_sec,
        dx_m=payload.dx_m,
        v_max=payload.v_max,
        v_min=payload.v_min,
        downstream_h_mode=payload.downstream_h_mode,
        fixed_downstream_h=payload.fixed_downstream_h,
    )
    return ResponseUtil.success(data=data)
