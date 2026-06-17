"""一次性脚本：把 agri_canal_base 渠段重命名/重拓扑，并切到 canal_id 作主键。

新设计：
- canal_id 形如 "1", "1-1", "1-2", "1-1-1", "1-1-1-1"（干-支-斗-农）
- level 字段值: '1' 干 / '2' 支 / '3' 斗 / '4' 农
- 去掉 BigInteger id 列；canal_id 直接做主键

迁移策略：
1. 创建新表 agri_canal_v2（含原全部字段，canal_id PRIMARY KEY，parent_id FK self）
2. 按规则重新生成 canal_id 和 parent_id，把原表数据搬过去
3. 用 UNION（视图）让 ORM 暂时看不到差异；上层验证通过后替换

回滚：drop agri_canal_v2 即可，业务仍走 agri_canal_base。
"""

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text
from config.database import AsyncSessionLocal
from module_irrigation.model.canals_data import build_topology


def _build_new_canal_id(
    old_id: str, level: str, branch_seq_map: dict, lateral_seq_map: dict, farmer_seq_map: dict
) -> str | None:
    """
    把旧 canal_id 转成新 canal_id。

    规则：
    - 干渠 G -> 1
    - 支渠 Z{n} -> 1-{branch_seq_map[Z{n}]}
    - 斗渠 {i}-D{n} -> 1-{branch_seq_for_i}-{n}（保持原 D 序号）
    - 农渠 {i}-{j}-N{n} -> 1-{branch_seq_for_i}-{j}-{n}（保持原 j/n 序号）
    """
    if old_id == 'G':
        return '1'
    if old_id.startswith('Z') and old_id[1:].isdigit():
        return f"1-{branch_seq_map[old_id]}"
    parts = old_id.split('-')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].startswith('D'):
        i_num = int(parts[0])
        d_num = int(parts[1][1:])
        z_id = f'Z{i_num}'
        if z_id in branch_seq_map:
            return f"1-{branch_seq_map[z_id]}-{d_num}"
    if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].startswith('N'):
        i_num = int(parts[0])
        j_num = int(parts[1])
        n_num = int(parts[2][1:])
        z_id = f'Z{i_num}'
        if z_id in branch_seq_map:
            return f"1-{branch_seq_map[z_id]}-{j_num}-{n_num}"
    return None


async def main():
    async with AsyncSessionLocal() as session:
        # 1) 读出全部老数据（立即把字段全拷贝出来，避免 session expire 后 lazy load）
        result = await session.execute(
            text("SELECT canal_id, canal_name, parent_id, level, length_m, design_q_m3s, "
                 "design_depth_m, design_top_width_m, design_bottom_width_m, design_slope, "
                 "side_slope_m, manning_n, gate_height_m, gate_width_m, min_gate_opening_m, "
                 "max_gate_opening_m, water_demand_m3, created_at, updated_at "
                 "FROM agri_canal_base ORDER BY canal_id")
        )
        col_names = [
            'canal_id', 'canal_name', 'parent_id', 'level', 'length_m', 'design_q_m3s',
            'design_depth_m', 'design_top_width_m', 'design_bottom_width_m', 'design_slope',
            'side_slope_m', 'manning_n', 'gate_height_m', 'gate_width_m', 'min_gate_opening_m',
            'max_gate_opening_m', 'water_demand_m3', 'created_at', 'updated_at',
        ]
        rows = [dict(zip(col_names, r)) for r in result.fetchall()]
        print(f'老表记录数: {len(rows)}')

        # 2) 给支渠分配 1/2 序号
        branch_records = [r for r in rows if (r['canal_id'] or '').startswith('Z') and (r['canal_id'] or '')[1:].isdigit()]
        branch_records.sort(key=lambda r: r['canal_id'])
        branch_seq_map = {r['canal_id']: idx + 1 for idx, r in enumerate(branch_records)}
        print(f'支渠映射: {branch_seq_map}')

        # 3) 斗渠的"原 i" -> 父支渠
        lateral_seq_map: dict[str, int] = {}
        farmer_seq_map: dict[str, int] = {}

        # 4) 创建 v2 表
        await session.execute(text("""
        CREATE TABLE IF NOT EXISTS agri_canal_v2 (
            canal_id            VARCHAR(64) PRIMARY KEY,
            canal_name          VARCHAR(100),
            parent_id           VARCHAR(64) REFERENCES agri_canal_v2(canal_id),
            level               VARCHAR(8),
            length_m            NUMERIC(12,3),
            design_q_m3s        NUMERIC(12,4),
            design_depth_m      NUMERIC(8,4),
            design_top_width_m  NUMERIC(10,4),
            design_bottom_width_m NUMERIC(10,4),
            design_slope        NUMERIC(14,10),
            side_slope_m        NUMERIC(8,4),
            manning_n           NUMERIC(8,5),
            gate_height_m       NUMERIC(8,4),
            gate_width_m        NUMERIC(8,4),
            min_gate_opening_m  NUMERIC(8,4),
            max_gate_opening_m  NUMERIC(8,4),
            water_demand_m3     NUMERIC(18,4),
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """))
        await session.commit()
        print('agri_canal_v2 表已创建')

        # 5) 清空 v2（重跑幂等）
        await session.execute(text("DELETE FROM agri_canal_v2"))
        await session.commit()

        # 6) 数据转换
        new_records: list[dict] = []
        skipped: list[str] = []
        for r in rows:
            new_id = _build_new_canal_id(
                r['canal_id'], r['level'], branch_seq_map, lateral_seq_map, farmer_seq_map
            )
            if new_id is None:
                skipped.append(r['canal_id'])
                continue
            new_level = str(r['level'] or '').strip()
            if new_level not in ('1', '2', '3', '4'):
                new_level = new_level  # 保留原值
            new_records.append({
                'canal_id': new_id,
                'canal_name': r['canal_name'],
                'level': new_level,
                '_old_id': r['canal_id'],
            })

        # 用 build_topology 给每条找父（适配新编号 1-1-1-1：父 = 切掉最后一段）
        for r in new_records:
            parts = r['canal_id'].split('-')
            if len(parts) == 1:
                r['parent_id'] = None
            else:
                r['parent_id'] = '-'.join(parts[:-1])

        # 7) 按 canal_id 字符序写入（确保父在子之前；新命名规则下字典序正确）
        new_records.sort(key=lambda r: r['canal_id'])
        for r in new_records:
            old = next(o for o in rows if o['canal_id'] == r['_old_id'])
            await session.execute(
                text("""
                INSERT INTO agri_canal_v2
                (canal_id, canal_name, parent_id, level,
                 length_m, design_q_m3s, design_depth_m, design_top_width_m, design_bottom_width_m,
                 design_slope, side_slope_m, manning_n,
                 gate_height_m, gate_width_m, min_gate_opening_m, max_gate_opening_m,
                 water_demand_m3, created_at, updated_at)
                VALUES (:canal_id, :canal_name, :parent_id, :level,
                        :length_m, :design_q_m3s, :design_depth_m, :design_top_width_m, :design_bottom_width_m,
                        :design_slope, :side_slope_m, :manning_n,
                        :gate_height_m, :gate_width_m, :min_gate_opening_m, :max_gate_opening_m,
                        :water_demand_m3, :created_at, :updated_at)
                """),
                {
                    'canal_id': r['canal_id'],
                    'canal_name': old['canal_name'],
                    'parent_id': r['parent_id'],
                    'level': r['level'],
                    'length_m': old['length_m'],
                    'design_q_m3s': old['design_q_m3s'],
                    'design_depth_m': old['design_depth_m'],
                    'design_top_width_m': old['design_top_width_m'],
                    'design_bottom_width_m': old['design_bottom_width_m'],
                    'design_slope': old['design_slope'],
                    'side_slope_m': old['side_slope_m'],
                    'manning_n': old['manning_n'],
                    'gate_height_m': old['gate_height_m'],
                    'gate_width_m': old['gate_width_m'],
                    'min_gate_opening_m': old['min_gate_opening_m'],
                    'max_gate_opening_m': old['max_gate_opening_m'],
                    'water_demand_m3': old['water_demand_m3'],
                    'created_at': old['created_at'],
                    'updated_at': old['updated_at'],
                },
            )
        await session.commit()
        print(f'\n写入 v2: {len(new_records)} 条，跳过: {len(skipped)}')
        if skipped:
            print(f'  跳过列表: {skipped}')

        # 8) 复检 v2
        v2_rows = (await session.execute(
            text("SELECT canal_id, canal_name, parent_id, level FROM agri_canal_v2 ORDER BY canal_id")
        )).fetchall()
        print(f'\nv2 实际行数: {len(v2_rows)}')
        # 干渠 + 各支渠子数
        level_count: dict[str, int] = {}
        for row in v2_rows:
            level_count[row[3]] = level_count.get(row[3], 0) + 1
        print(f'  level 分布: {level_count}')

        # 9) 显示关键路径
        ids_in_v2 = {row[0] for row in v2_rows}
        bad = [row[0] for row in v2_rows if row[2] and row[2] not in ids_in_v2]
        print(f'  孤儿渠段: {len(bad)}')

        # 10) 抽样显示：1, 1-1, 1-1-1, 1-1-1-1
        for cid in ('1', '1-1', '1-2', '1-1-1', '1-1-11', '1-2-1', '1-2-7', '1-1-1-1'):
            row = next((r for r in v2_rows if r[0] == cid), None)
            if row:
                children = [r[0] for r in v2_rows if r[2] == cid]
                print(f'  {cid}: level={row[3]}, parent_id={row[2]!r}, 子数={len(children)}')


if __name__ == '__main__':
    asyncio.run(main())
