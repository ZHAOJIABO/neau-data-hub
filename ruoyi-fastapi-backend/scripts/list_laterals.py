"""列出所有斗渠（level=3）的 canal_id"""

import asyncio, sys
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
from sqlalchemy import select
from config.database import AsyncSessionLocal
from module_agriculture.entity.do.canal_do import CanalBase

async def main():
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(CanalBase).where(CanalBase.level == '3').order_by(CanalBase.canal_id)
        )).scalars().all()
        print(f'level=3 共 {len(rows)} 条:')
        for r in rows:
            print(f'  {r.canal_id} (parent_id={r.parent_id})')

if __name__ == '__main__':
    asyncio.run(main())
