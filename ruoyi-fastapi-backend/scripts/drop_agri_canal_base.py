"""Drop 老 agri_canal_base 表（迁移已完成：v2 行数 = base 行数 = 91，列名已重命名）。

操作前再次校验：
1) v2 与 base 行数一致；
2) v2 与 base 的 canal_name 集合一致（旧表 v2 用不同 canal_id 编号，
   见 migrate_canal_v2._build_new_canal_id；canal_name 是迁移保留字段）；
3) v2 与 base 的 level 分布一致（1 干 / 2 支 / 3 斗 / 4 农 数量相等）。

任意校验失败则拒绝 drop。Drop 之后保留一份 metadata 备份表 _bak_agri_canal_base_meta（仅 DDL + count），便于审计。
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text
from config.database import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as s:
        # 1) base 表存在？
        exists = (
            await s.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables WHERE table_name = 'agri_canal_base'"
                )
            )
        ).scalar()
        if not exists:
            print('agri_canal_base 不存在，无需 drop。')
            return

        cnt_base = (await s.execute(text('SELECT count(*) FROM agri_canal_base'))).scalar()
        cnt_v2 = (await s.execute(text('SELECT count(*) FROM agri_canal_v2'))).scalar()
        print(f'行数: v2={cnt_v2}, base={cnt_base}')
        if cnt_v2 != cnt_base:
            raise SystemExit(f'行数不一致，拒绝 drop：v2={cnt_v2}, base={cnt_base}')

        # 2) v2 与 base 的 canal_name 集合一致（迁移保留字段，canal_id 编码已重排）
        base_names = {
            r[0]
            for r in (
                await s.execute(text('SELECT canal_name FROM agri_canal_base'))
            ).fetchall()
        }
        v2_names = {
            r[0]
            for r in (
                await s.execute(text('SELECT canal_name FROM agri_canal_v2'))
            ).fetchall()
        }
        missing_in_v2 = base_names - v2_names
        extra_in_v2 = v2_names - base_names
        if missing_in_v2 or extra_in_v2:
            raise SystemExit(
                f'canal_name 集合不一致：base→v2 缺失 {missing_in_v2}, v2→base 多余 {extra_in_v2}'
            )

        # 3) v2 与 base 的 level 分布一致
        level_dist_base = dict(
            (
                await s.execute(
                    text('SELECT level, count(*) FROM agri_canal_base GROUP BY level')
                )
            ).fetchall()
        )
        level_dist_v2 = dict(
            (
                await s.execute(
                    text('SELECT level, count(*) FROM agri_canal_v2 GROUP BY level')
                )
            ).fetchall()
        )
        if level_dist_base != level_dist_v2:
            raise SystemExit(
                f'level 分布不一致：base={level_dist_base}, v2={level_dist_v2}'
            )

        # 4) 备份元信息
        await s.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS _bak_agri_canal_base_meta (
                    dropped_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    row_count  INTEGER NOT NULL,
                    note       TEXT
                )
                """
            )
        )
        await s.execute(
            text(
                """
                INSERT INTO _bak_agri_canal_base_meta (row_count, note)
                VALUES (:cnt, :note)
                """
            ),
            {'cnt': cnt_base, 'note': 'dropped by drop_agri_canal_base.py'},
        )

        # 5) drop
        await s.execute(text('DROP TABLE agri_canal_base'))
        await s.commit()
        print(f'\n✅ agri_canal_base 已 drop（{cnt_base} 行），备份在 _bak_agri_canal_base_meta')


if __name__ == '__main__':
    asyncio.run(main())
