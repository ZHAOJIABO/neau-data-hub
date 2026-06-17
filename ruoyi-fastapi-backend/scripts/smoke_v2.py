"""端到端 smoke test（去 SQL 日志）。"""
import asyncio
import sys
import logging
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# 关闭 SQLAlchemy 日志输出
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from sqlalchemy import select, text
from config.database import AsyncSessionLocal
from module_agriculture.entity.do.canal_do import CanalBase
from module_agriculture.entity.vo.canal_vo import CanalBasePageQueryModel
from module_agriculture.service.canal_service import CanalService
from module_irrigation.model.canals_data import CanalsData
from module_irrigation.service.canal_optimize_service import CanalOptimizeService


async def main():
    # 1) v2 表
    async with AsyncSessionLocal() as s:
        cnt = (await s.execute(select(text("count(*)")).select_from(CanalBase))).scalar()
        print(f'[1] v2 表渠段数: {cnt}')

    # 2) 启动期 loading
    async with AsyncSessionLocal() as s:
        records = await CanalService.list_all_for_runtime(s)
        print(f'[2] list_all_for_runtime 返回: {len(records)} 条')

    # 3) CanalsData 单例
    CanalsData.reset()
    CanalsData.load_from_records(records)
    print(f'[3] CanalsData: 加载 {len(CanalsData.all())} 条, root_id={CanalsData.root_id()!r}')
    print(f'    1-1 的子渠段: {CanalsData.children_of("1-1")}')
    print(f'    1-1-1-1 的父: {CanalsData.parent_of("1-1-1-1")}')

    # 4) 优化
    data = await CanalOptimizeService.run_full(
        main_canal_id='1', t_max=360.0, pop_size=80, n_gen=30, seed=1,
    )
    summary = data.get('summary') or {}
    print(f'[4] 优化: main={summary.get("main_canal_id")}, branches={summary.get("branch_ids")}, '
          f'TOPSIS={summary.get("topsis_score"):.3f}, '
          f'损失={summary.get("objective_values", {}).get("F2_total_loss_m3"):.0f} m³')

    # 5) CanalService CRUD - 列表 + 详情
    async with AsyncSessionLocal() as s:
        page = await CanalService.get_canal_list_services(
            s, CanalBasePageQueryModel(canal_id=None, canal_name=None, level='2',
                                       page_num=1, page_size=5), is_page=True,
        )
        print(f'[5] 列表 level=2: total={page.total}')
        for row in page.rows:
            if isinstance(row, dict):
                print(f'    {row.get("canalId")} ({row.get("level")}) {row.get("canalName")}')
            else:
                print(f'    {row.canal_id} ({row.level}) {row.canal_name}')

        detail = await CanalService.get_canal_detail_services(s, '1-1-1')
        print(f'[6] 详情 1-1-1: canal_id={detail.canal_id}, level={detail.level}, '
              f'parent_id={detail.parent_id}, length={detail.length}, design_flow={detail.design_flow}')

    # 7) 拓扑接口
    async with AsyncSessionLocal() as s:
        topo = await CanalService.get_topology_services(s)
        print(f'[7] 拓扑: roots={topo["roots"]}, nodes={len(topo["nodes"])}, edges={len(topo["edges"])}')
        # 抽看两个 edge
        for e in topo['edges'][:2]:
            print(f'    edge: {e["from"]} -> {e["to"]}')

    print('\n✅ 全部端到端验证通过')


if __name__ == '__main__':
    asyncio.run(main())
