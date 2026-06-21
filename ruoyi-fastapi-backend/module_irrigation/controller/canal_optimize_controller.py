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
from module_irrigation.entity.vo.canal_model_vo import (
    BranchLateralOptimizeRequest,
    TrunkBranchOptimizeRequest,
)

from module_irrigation.service.canal_optimize_service import CanalOptimizeService
from utils.log_util import logger
from utils.response_util import ResponseUtil

canal_optimize_controller = APIRouterPro(
    prefix='/api/v1/irrigation/canal/optimize',
    order_num=24,
    tags=['渠系优化配水'],
    dependencies=[irrigation_api_key_dependency()],
)

@canal_optimize_controller.post(
    '/trunk-branch',
    summary='干支优化（NSGA-II）：选一条 level-2 干渠与其 level-3 支渠子网',
    response_model=None,
)
async def optimize_trunk_branch(
    payload: Annotated[
        TrunkBranchOptimizeRequest,
        Body(description='干支优化 JSON 请求体'),
    ],
) -> JSONResponse:
    """干支优化：选一条 level-2 干渠 + 其 level-3 支渠子网，NSGA-II 三目标优化配水。"""
    canal_count = len(payload.canals)
    logger.info(
        'trunk-branch optimize request: canals=%s, trunk=%s, t_max=%s, pop=%s, gen=%s, seed=%s',
        canal_count,
        payload.trunk_canal_id,
        payload.t_max,
        payload.pop_size,
        payload.n_gen,
        payload.seed,
    )
    data = await CanalOptimizeService.run_trunk_branch(
        trunk_canal_id=payload.trunk_canal_id,
        canal_records=[item.model_dump() for item in payload.canals],
        topology=[item.model_dump() for item in payload.topology] if payload.topology else None,
        t_max=payload.t_max,
        flow_ratio_min=payload.flow_ratio_min,
        flow_ratio_max=payload.flow_ratio_max,
        pop_size=payload.pop_size,
        n_gen=payload.n_gen,
        seed=payload.seed,
        permeability_index=payload.permeability_index,
        permeability_coefficient=payload.permeability_coefficient,
        pref_weight_time=payload.pref_weight_time,
        pref_weight_loss=payload.pref_weight_loss,
        pref_weight_flow_var=payload.pref_weight_flow_var,
        alpha=payload.alpha,
    )
    return ResponseUtil.success(data=data)


@canal_optimize_controller.post(
    '/branch-lateral',
    summary='支斗轮续灌优化（NSGA-II）：选一条 level-3 支渠与其 level-4 斗渠子网',
    response_model=None,
)
async def optimize_branch_lateral(
    payload: Annotated[
        BranchLateralOptimizeRequest,
        Body(description='支斗轮续灌优化 JSON 请求体'),
    ],
) -> JSONResponse:
    """支斗轮续灌优化：选一条 level-3 支渠 + 其 level-4 斗渠子网，NSGA-II 组间轮灌组内续灌。"""
    canal_count = len(payload.canals)
    logger.info(
        'branch-lateral optimize request: canals=%s, branch=%s, groups=[%s,%s], t_max=%s, pop=%s, gen=%s, seed=%s',
        canal_count,
        payload.branch_canal_id,
        payload.min_groups,
        payload.max_groups,
        payload.t_max,
        payload.pop_size,
        payload.n_gen,
        payload.seed,
    )
    data = await CanalOptimizeService.run_branch_lateral(
        branch_canal_id=payload.branch_canal_id,
        canal_records=[item.model_dump() for item in payload.canals],
        topology=[item.model_dump() for item in payload.topology] if payload.topology else None,
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
    )
    return ResponseUtil.success(data=data)
