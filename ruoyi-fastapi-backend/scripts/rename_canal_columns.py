"""把 agri_canal_v2 表的列重命名为不带单位/数字的简洁名。

旧 -> 新：
  length_m            -> length
  design_q_m3s        -> design_flow
  design_depth_m      -> design_depth
  design_top_width_m  -> top_width
  design_bottom_width_m -> bottom_width
  design_slope        -> slope
  side_slope_m        -> side_slope
  manning_n           -> roughness
  gate_height_m       -> gate_height
  gate_width_m        -> gate_width
  min_gate_opening_m  -> min_gate_opening
  max_gate_opening_m  -> max_gate_opening
  water_demand_m3     -> water_demand
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text
from config.database import AsyncSessionLocal


RENAME_MAP = [
    ('length_m', 'length'),
    ('design_q_m3s', 'design_flow'),
    ('design_depth_m', 'design_depth'),
    ('design_top_width_m', 'top_width'),
    ('design_bottom_width_m', 'bottom_width'),
    ('design_slope', 'slope'),
    ('side_slope_m', 'side_slope'),
    ('manning_n', 'roughness'),
    ('gate_height_m', 'gate_height'),
    ('gate_width_m', 'gate_width'),
    ('min_gate_opening_m', 'min_gate_opening'),
    ('max_gate_opening_m', 'max_gate_opening'),
    ('water_demand_m3', 'water_demand'),
]


async def main():
    async with AsyncSessionLocal() as session:
        # 查列存在性
        result = await session.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'agri_canal_v2'
        """))
        existing = {row[0] for row in result.fetchall()}
        print(f'当前列: {sorted(existing)}')

        for old, new in RENAME_MAP:
            if old not in existing:
                print(f'  跳过 {old}（已不存在）')
                continue
            if new in existing:
                print(f'  跳过 {old} -> {new}（目标列已存在）')
                continue
            await session.execute(text(
                f'ALTER TABLE agri_canal_v2 RENAME COLUMN "{old}" TO "{new}"'
            ))
            print(f'  {old} -> {new}')
        await session.commit()

        # 复检
        result = await session.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'agri_canal_v2'
        ORDER BY ordinal_position
        """))
        cols = [row[0] for row in result.fetchall()]
        print(f'\n重命名后列: {cols}')

        # 抽样数据
        result = await session.execute(text("""
        SELECT canal_id, length, design_flow, slope, roughness, water_demand
        FROM agri_canal_v2
        WHERE canal_id IN ('1', '1-1', '1-1-1', '1-1-1-1')
        """))
        for row in result.fetchall():
            print(f'  {row[0]}: length={row[1]}, design_flow={row[2]}, slope={row[3]}, '
                  f'roughness={row[4]}, water_demand={row[5]}')


if __name__ == '__main__':
    asyncio.run(main())
