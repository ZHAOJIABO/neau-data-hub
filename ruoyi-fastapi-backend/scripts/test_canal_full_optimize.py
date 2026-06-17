"""渠系全渠系三级 NSGA-III 优化 — 独立验证脚本

绕过 HTTP 层，直接调 CanalOptimizeService.run_full()，
确认 canal_full_optimize.py 的 termination 修复 + elapsed 修复生效。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

# 让脚本能 import 到项目模块
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from module_irrigation.service.canal_optimize_service import CanalOptimizeService  # noqa: E402


async def main() -> int:
    print('=' * 70)
    print(' 渠系全渠系三级 NSGA-III 优化 — 单元验证')
    print('=' * 70)

    # 1) 从数据库加载渠段数据到 CanalsData 单例
    from sqlalchemy import select
    from config.database import AsyncSessionLocal
    from module_agriculture.entity.do.canal_do import CanalBase
    from module_irrigation.model.canals_data import CanalsData

    async with AsyncSessionLocal() as session:
        objs = (await session.execute(select(CanalBase).order_by(CanalBase.canal_id))).scalars().all()
        records = [
            {
                'canal_id': o.canal_id,
                'canal_name': o.canal_name,
                'parent_id': o.parent_id,
                'level': o.level,
                'length': float(o.length) if o.length is not None else 0.0,
                'design_flow': float(o.design_flow) if o.design_flow is not None else 0.0,
                'design_depth': float(o.design_depth) if o.design_depth is not None else 0.0,
                'top_width': float(o.top_width) if o.top_width is not None else 0.0,
                'bottom_width': float(o.bottom_width) if o.bottom_width is not None else 0.0,
                'slope': float(o.slope) if o.slope is not None else 0.0,
                'side_slope': float(o.side_slope) if o.side_slope is not None else 0.0,
                'roughness': float(o.roughness) if o.roughness is not None else 0.0,
                'gate_height': float(o.gate_height) if o.gate_height is not None else 0.0,
                'gate_width': float(o.gate_width) if o.gate_width is not None else 0.0,
                'min_gate_opening': float(o.min_gate_opening) if o.min_gate_opening is not None else 0.0,
                'max_gate_opening': float(o.max_gate_opening) if o.max_gate_opening is not None else 0.0,
                'water_demand': float(o.water_demand) if o.water_demand is not None else 0.0,
            }
            for o in objs
        ]
    CanalsData.load_from_records(records)
    print(f' 加载渠段数: {len(records)}')

    t0 = time.time()
    data = await CanalOptimizeService.run_full(
        main_canal_id='1',
        t_max=360.0,
        pop_size=80,
        n_gen=60,
        seed=1,
    )
    # FullResult.to_dict() 是嵌套结构，摘出关键字段
    summary = data.get('summary') or {}
    elapsed = time.time() - t0
    print(f'\n 耗时: {elapsed:.2f}s')
    print(f' summary: {json.dumps(summary, ensure_ascii=False)}')
    print(f' branches 数: {len(data.get("branches") or [])}')
    print(f' laterals 数: {len(data.get("laterals") or [])}')
    print(f' groups 数: {len(data.get("groups") or [])}')
    print(f' time_series 数: {len(data.get("time_series") or [])}')
    print(f' pareto 数: {len(data.get("pareto") or [])}')
    if data.get('main_canal'):
        mc = data['main_canal']
        print(f' main_canal: {json.dumps(mc, ensure_ascii=False)[:400]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
