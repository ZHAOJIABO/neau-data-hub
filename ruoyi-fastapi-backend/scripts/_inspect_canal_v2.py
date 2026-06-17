"""一次性查 v2 / 老 base 表的列与行数，确认迁移状态。"""
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text
from config.database import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as s:
        # v2 表列
        print('=== agri_canal_v2 columns ===')
        for row in (
            await s.execute(
                text(
                    "SELECT column_name, data_type, numeric_precision, numeric_scale "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'agri_canal_v2' "
                    "ORDER BY ordinal_position"
                )
            )
        ).fetchall():
            print(f'  {row.column_name:30s} {row.data_type:25s} {row.numeric_precision or "-"} {row.numeric_scale or "-"}')

        # v2 行数
        cnt_v2 = (await s.execute(text('SELECT count(*) FROM agri_canal_v2'))).scalar()
        print(f'\n  agri_canal_v2 row count: {cnt_v2}')

        # 老 base 表存在？
        exists = (
            await s.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_name = 'agri_canal_base'"
                )
            )
        ).scalar()
        print(f'\n=== agri_canal_base exists: {bool(exists)}')
        if exists:
            cnt_base = (await s.execute(text('SELECT count(*) FROM agri_canal_base'))).scalar()
            print(f'  agri_canal_base row count: {cnt_base}')


if __name__ == '__main__':
    asyncio.run(main())
