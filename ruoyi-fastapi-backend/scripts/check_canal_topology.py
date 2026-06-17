"""检查 agri_canal_base 表的支渠/斗渠拓扑关系。"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from config.database import AsyncSessionLocal
from module_agriculture.entity.do.canal_do import CanalBase


async def main():
    async with AsyncSessionLocal() as session:
        # 1) 全部 91 条
        all_rows = (await session.execute(select(CanalBase).order_by(CanalBase.canal_id))).scalars().all()
        print(f'总渠段数: {len(all_rows)}')

        # 2) level 分布
        from collections import Counter
        level_counter = Counter((r.level or '<NULL>') for r in all_rows)
        print(f'\nlevel 分布: {dict(level_counter)}')

        # 3) 找 Z1/Z2
        z_rows = [r for r in all_rows if r.canal_id in ('Z1', 'Z2')]
        print(f'\nZ1/Z2 记录:')
        for r in z_rows:
            print(f'  {r.canal_id}: level={r.level!r}, parent_id={r.parent_id!r}')

        # 4) 找 Z1/Z2 的 parent_id 链
        all_ids = {r.canal_id for r in all_rows}
        for z in z_rows:
            child_ids = [r.canal_id for r in all_rows if r.parent_id == z.canal_id]
            print(f'\n  {z.canal_id} 的子渠段数: {len(child_ids)}')
            print(f'  子列表: {child_ids[:20]}{"..." if len(child_ids) > 20 else ""}')

        # 5) 找所有 level=2/3 的
        print('\n按 level 分组:')
        for lv in sorted(set(r.level for r in all_rows)):
            ids = [r.canal_id for r in all_rows if r.level == lv]
            print(f'  level={lv!r}: {len(ids)} 条 — 样例 {ids[:8]}')

        # 6) 检查所有 parent_id 是否指向真实存在的 canal_id
        print('\nparent_id 完整性检查:')
        bad = []
        for r in all_rows:
            if r.parent_id is not None and r.parent_id not in all_ids:
                bad.append((r.canal_id, r.level, r.parent_id))
        print(f'  孤儿渠段数: {len(bad)}')
        for cid, lv, pid in bad[:15]:
            print(f'    {cid} (level={lv}) -> parent_id={pid!r} (不存在)')

        # 7) 干渠 G 的 parent_id 是什么？
        g = next((r for r in all_rows if r.canal_id == 'G'), None)
        if g:
            print(f'\n  干渠 G: parent_id={g.parent_id!r}, level={g.level!r}')

        # 8) 所有不同的 parent_id 值
        from collections import Counter
        pid_counter = Counter((r.parent_id or '<NULL>') for r in all_rows)
        print(f'\n  parent_id 频次: {dict(pid_counter)}')


if __name__ == '__main__':
    asyncio.run(main())
