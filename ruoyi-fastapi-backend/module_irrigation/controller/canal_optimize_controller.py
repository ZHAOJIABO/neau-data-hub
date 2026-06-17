"""
渠系优化配水接口（NSGA-III 多目标优化）：

- POST /api/v1/irrigation/canal/optimize/full      全渠系三级顺序配水优化

返回结构化 JSON（无 ZIP），由前端 ECharts 直接渲染。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Body
from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_irrigation.entity.vo.canal_model_vo import FullOptimizeStandardRequest

from module_irrigation.service.canal_optimize_service import CanalOptimizeService
from utils.log_util import logger
from utils.response_util import ResponseUtil

canal_optimize_controller = APIRouterPro(
    prefix='/api/v1/irrigation/canal/optimize',
    order_num=24,
    tags=['渠系优化配水'],
    dependencies=[irrigation_api_key_dependency()],
)


def _canal_records_from_payload(payload) -> list[dict]:
    return [item.model_dump() for item in payload.canals]


def _parent_ids_from_payload(payload) -> dict[str, str | None] | None:
    if payload.topology is None:
        return None
    return {item.canal_id: item.parent_id for item in payload.topology}


@canal_optimize_controller.post(
    '/full',
    summary='全渠系三级顺序配水优化（NSGA-III）',
    response_model=None,
)
async def optimize_full(
    payload: Annotated[
        FullOptimizeStandardRequest,
        Body(description='全渠系三级优化标准 JSON 请求体'),
    ],
) -> JSONResponse:
    """全渠系三级顺序配水优化：干-支连续配水 + 支-斗轮灌分组。"""
    canal_count = len(payload.canals)
    logger.info(
        'canal optimize full request: main={}, canals={}, pop={}, gen={}, seed={}',
        payload.main_canal_id,
        canal_count,
        payload.pop_size,
        payload.n_gen,
        payload.seed,
    )
    data = await CanalOptimizeService.run_full(
        main_canal_id=payload.main_canal_id,
        t_max=payload.t_max,
        flow_ratio_min=payload.flow_ratio_min,
        flow_ratio_max=payload.flow_ratio_max,
        min_groups=payload.min_groups,
        max_groups=payload.max_groups,
        pop_size=payload.pop_size,
        n_gen=payload.n_gen,
        seed=payload.seed,
        permeability_index=payload.permeability_index,
        permeability_coefficient=payload.permeability_coefficient,
        pref_weight_time=payload.pref_weight_time,
        pref_weight_loss=payload.pref_weight_loss,
        pref_weight_flow_var=payload.pref_weight_flow_var,
        alpha=payload.alpha,
        canal_records=_canal_records_from_payload(payload),
        parent_ids=_parent_ids_from_payload(payload),
    )
    return ResponseUtil.success(data=data)
