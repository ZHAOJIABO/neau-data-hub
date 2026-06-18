"""
两级渠段（父 + 子）水动力学仿真服务：异步执行，返回结构化 JSON。
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from exceptions.exception import ServiceException
from module_irrigation.model.canal_full_hydro import (
    SubtreeHydroContext,
    SubtreeHydroResult,
    solve_subtree_hydro,
)
from utils.log_util import logger


class CanalFullHydroService:
    """两级渠段水动力学仿真服务：参数校验 + 异步求解。"""

    @classmethod
    async def run_subtree(
        cls,
        canals: list[dict[str, Any]],
        sim_duration_min: int = 60,
        dt_sec: int = 30,
        dx_m: float = 50.0,
    ) -> dict[str, Any]:
        if not canals:
            raise ServiceException(message='canals 不能为空')

        def _norm(v: Any) -> Optional[str]:
            return str(v) if v is not None else None

        parent_ids: Optional[dict[str, Optional[str]]] = {
            str(c['canal_id']): _norm(c.get('parent_id'))
            for c in canals
            if c.get('canal_id') is not None
        }
        all_ids = set(parent_ids.keys())
        root_ids = [cid for cid, pid in parent_ids.items() if pid not in all_ids]
        if root_ids:
            root = min(root_ids, key=lambda x: (len(x), x))
        else:
            root = min(all_ids, key=lambda x: (len(x), x))
        logger.info(
            'run_subtree: canals_count={}, canal_ids={}, root={}, root_ids={}',
            len(canals),
            [str(c.get('canal_id')) for c in canals],
            root,
            root_ids,
        )
        ctx = SubtreeHydroContext(
            main_canal_id=root,
            records=canals,
            parent_ids=parent_ids,
            sim_duration_min=int(sim_duration_min),
            dt_sec=int(dt_sec),
            dx_m=float(dx_m),
        )
        try:
            result: SubtreeHydroResult = solve_subtree_hydro(ctx)
        except (KeyError, ValueError, TypeError) as exc:
            logger.error('run_subtree failed: {}', exc)
            raise ServiceException(message=str(exc)) from exc
        return result.to_dict()
