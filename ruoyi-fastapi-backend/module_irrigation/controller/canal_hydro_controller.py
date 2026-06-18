"""
两级渠段（父+子）水动力学接口：

  POST /api/v1/irrigation/canal/hydro/subtree/standard
      两级渠段逐分钟水动力学仿真（父渠道 + 直接下级子渠道）
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body
from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_irrigation.entity.vo.canal_model_vo import SubtreeHydroRequest
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
    '/subtree/standard',
    summary='两级渠段逐分钟水动力学仿真',
)
async def canal_hydro_subtree_standard(
    payload: Annotated[
        SubtreeHydroRequest,
        Body(description='两级渠段水动力学仿真 JSON 请求体：1 父渠道 + ≥1 子渠道'),
    ],
) -> JSONResponse:
    """前端选择某条父渠道，将该父渠道及其直接下级子渠道传入；
    后端只仿真这两级，每条子渠段按其 design_flow 恒定入流（未传 inflow_series 时）；
    返回 (t, canal_id, x, Q, h, V) 时空序列供 ECharts 展示。"""
    canal_count = len(payload.canals)
    logger.info(
        'canal subtree hydro request: canals={}, sim_duration_min={}, dt_sec={}',
        canal_count,
        payload.sim_duration_min,
        payload.dt_sec,
    )
    canals_payload = [c.model_dump() for c in payload.canals]
    data = await CanalFullHydroService.run_subtree(
        canals=canals_payload,
        sim_duration_min=payload.sim_duration_min,
        dt_sec=payload.dt_sec,
        dx_m=payload.dx_m,
    )
    return ResponseUtil.success(data=data)
