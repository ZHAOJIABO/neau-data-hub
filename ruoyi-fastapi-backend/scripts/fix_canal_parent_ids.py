"""一次性脚本：把 agri_canal_base 表的 parent_id 校正到真实存在的渠段。

策略：
1. 读取所有渠段
2. 用 canals_data.infer_canal_parent + build_topology 推断正确的父
3. UPDATE 库里 parent_id
4. 验证

回滚思路：调用方应先备份 agri_canal_base 表（CREATE TABLE _bak AS SELECT * FROM agri_canal_base;）。
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, update
from config.database import AsyncSessionLocal
from module_agriculture.entity.do.canal_do import CanalBase
from module_irrigation.model.canals_data import build_parent_map


async def main():
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(CanalBase).order_by(CanalBase.canal_id))).scalars().all()
        print(f'总渠段数: {len(rows)}')

        records = [
            {
                'canal_id': r.canal_id,
                'parent_id': r.parent_id,
                'level': r.level,
            }
            for r in rows
        ]

        # 用 build_parent_map 推断（垃圾 parent_id 会被自动忽略）
        new_parents = build_parent_map(records, parent_ids=None)
        print(f'\n推断后的 parent map 样例 (前 20):')
        for cid in list(new_parents.keys())[:20]:
            print(f'  {cid} -> {new_parents[cid]!r}')

        # 找出需要 UPDATE 的行
        updates: list[tuple[str, str | None]] = []
        for r in rows:
            new_pid = new_parents.get(r.canal_id)
            cur_pid = (r.parent_id or '').strip() or None
            if cur_pid != new_pid:
                updates.append((r.canal_id, new_pid))

        print(f'\n需要更新的行数: {len(updates)}')

        if not updates:
            print('没有差异，无需 UPDATE。')
            return

        # 实际执行 UPDATE
        for cid, new_pid in updates:
            await session.execute(
                update(CanalBase).where(CanalBase.canal_id == cid).values(parent_id=new_pid)
            )
        await session.commit()
        print(f'已 UPDATE {len(updates)} 行。')

        # 复检
        rows2 = (await session.execute(select(CanalBase).order_by(CanalBase.canal_id))).scalars().all()
        ids2 = {r.canal_id for r in rows2}
        bad = [r.canal_id for r in rows2 if r.parent_id and r.parent_id not in ids2]
        print(f'\n复检孤儿渠段数: {len(bad)}')

        # 关键路径
        for cid in ('G', 'Z1', 'Z2', '1-D1', '1-D2', '1-1-N1'):
            r = next((x for x in rows2 if x.canal_id == cid), None)
            if r:
                children = [x.canal_id for x in rows2 if x.parent_id == cid]
                print(f'  {cid}: parent_id={r.parent_id!r}, 子数={len(children)}')


if __name__ == '__main__':
    asyncio.run(main())
