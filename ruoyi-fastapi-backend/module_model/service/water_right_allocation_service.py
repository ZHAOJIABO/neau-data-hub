"""
灌区初始水权分配 + 水权交易市场博弈服务。
"""

from __future__ import annotations

import asyncio
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial
from typing import Any

from exceptions.exception import ServiceException
from module_model.model.water_right_allocation_model import (
    WaterRightContext,
    WaterRightAllocationResult,
    build_context,
    solve_water_right_allocation,
)


def _water_right_allocation_worker(
    zones: list[dict[str, Any]],
    crops: list[dict[str, Any]],
    market: dict[str, Any],
) -> dict[str, Any]:
    """进程级入口：执行水权分配与博弈求解。"""
    ctx = build_context(
        zone_inputs=zones,
        crop_inputs=crops,
        market_input=market,
    )
    try:
        result: WaterRightAllocationResult = solve_water_right_allocation(ctx)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise ServiceException(message=str(exc)) from exc
    return result.to_dict()


class WaterRightAllocationService:
    """灌区初始水权分配 + Stackelberg 主从博弈 + 拍卖 LP 出清。"""

    @classmethod
    async def run_allocation(
        cls,
        zones: list[dict[str, Any]],
        crops: list[dict[str, Any]],
        market: dict[str, Any],
    ) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        func = partial(
            _water_right_allocation_worker,
            zones,
            crops,
            market,
        )
        # Windows 下 ProcessPoolExecutor 使用 spawn，需要 __main__ 保护。
        # 在 FastAPI server 进程中正常可用；但若直接脚本调用且未加
        # `if __name__ == '__main__':`，则降级为 ThreadPoolExecutor。
        use_process = sys.platform != 'win32' or __name__ != '__main__'
        executor: Any
        if use_process:
            executor = ProcessPoolExecutor(max_workers=1)
        else:
            executor = ThreadPoolExecutor(max_workers=1)
        try:
            result = await loop.run_in_executor(executor, func)
        finally:
            executor.shutdown(wait=True)
        return result