"""
全渠系逐分钟水动力学仿真服务：异步执行，返回结构化 JSON。
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from exceptions.exception import ServiceException
from module_irrigation.model.canal_full_hydro import (
    FullHydroContext,
    FullHydroResult,
    solve_full_hydro,
)


class CanalFullHydroService:
    """全渠系水动力学仿真服务：参数校验 + 异步求解。"""

    @classmethod
    async def run_full(
        cls,
        main_canal_id: str = '1',
        canals: Optional[list[dict[str, Any]]] = None,
        topology: Optional[list[dict[str, Any]]] = None,
        sim_duration_min: int = 60,
        dt_sec: int = 30,
        dx_m: float = 200.0,
        v_max: float = 1.5,
        v_min: float = 0.3,
        downstream_h_mode: str = 'normal',
        fixed_downstream_h: Optional[float] = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            cls._run_full_sync,
            main_canal_id,
            canals or [],
            topology,
            sim_duration_min,
            dt_sec,
            dx_m,
            v_max,
            v_min,
            downstream_h_mode,
            fixed_downstream_h,
        )

    @classmethod
    def _run_full_sync(
        cls,
        main_canal_id: str,
        canals: list[dict[str, Any]],
        topology: Optional[list[dict[str, Any]]],
        sim_duration_min: int,
        dt_sec: int,
        dx_m: float,
        v_max: float,
        v_min: float,
        downstream_h_mode: str,
        fixed_downstream_h: Optional[float],
    ) -> dict[str, Any]:
        parent_ids: Optional[dict[str, Optional[str]]] = None
        if topology:
            parent_ids = {item['canal_id']: item.get('parent_id') for item in topology}

        ctx = FullHydroContext(
            main_canal_id=main_canal_id or '1',
            records=canals,
            parent_ids=parent_ids,
            sim_duration_min=int(sim_duration_min),
            dt_sec=int(dt_sec),
            dx_m=float(dx_m),
            v_max=float(v_max),
            v_min=float(v_min),
            downstream_h_mode=downstream_h_mode,
            fixed_downstream_h=fixed_downstream_h,
        )
        try:
            result: FullHydroResult = solve_full_hydro(ctx)
        except (KeyError, ValueError, TypeError) as exc:
            raise ServiceException(message=str(exc)) from exc
        return result.to_dict()
