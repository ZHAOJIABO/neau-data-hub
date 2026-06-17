"""
全渠系逐分钟水动力学仿真服务：异步执行，返回结构化 JSON。
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from exceptions.exception import ServiceException
from module_irrigation.model.canal_full_hydro import (
    DEFAULT_DESIGN_FLOW_RATIO_MIN,
    DEFAULT_H_SAFETY_MARGIN_M,
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
        design_flow_ratio_min: float = DEFAULT_DESIGN_FLOW_RATIO_MIN,
        h_safety_margin_m: float = DEFAULT_H_SAFETY_MARGIN_M,
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
            design_flow_ratio_min,
            h_safety_margin_m,
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
        design_flow_ratio_min: float,
        h_safety_margin_m: float,
        downstream_h_mode: str,
        fixed_downstream_h: Optional[float],
    ) -> dict[str, Any]:
        parent_ids: Optional[dict[str, Optional[str]]] = None
        if topology:
            parent_ids = {item['canal_id']: item.get('parent_id') for item in topology}
        elif canals:
            # Extract parent_id from canals payload when topology is not provided
            parent_ids = {
                c['canal_id']: c.get('parent_id')
                for c in canals
                if c.get('canal_id') and c.get('parent_id')
            }

        ctx = FullHydroContext(
            main_canal_id=main_canal_id or '1',
            records=canals,
            parent_ids=parent_ids,
            sim_duration_min=int(sim_duration_min),
            dt_sec=int(dt_sec),
            dx_m=float(dx_m),
            design_flow_ratio_min=float(design_flow_ratio_min),
            h_safety_margin_m=float(h_safety_margin_m),
            downstream_h_mode=downstream_h_mode,
            fixed_downstream_h=fixed_downstream_h,
        )
        try:
            result: FullHydroResult = solve_full_hydro(ctx)
        except (KeyError, ValueError, TypeError) as exc:
            raise ServiceException(message=str(exc)) from exc
        return result.to_dict()
