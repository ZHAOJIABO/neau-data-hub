"""
渠系优化配水服务：提供干支优化和支斗优化两个入口。

- run_trunk_branch：干渠 + 支渠子网（level-2 + level-3）
- run_branch_lateral：支渠 + 斗渠子网（level-3 + level-4）
"""

import asyncio
import logging
import os
import re
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import Any

from exceptions.exception import ServiceException
from module_model.model.branch_lateral_optimize import (
    BranchLateralContext,
    BranchLateralResult,
    solve_branch_lateral,
)
from module_model.model.canals_data import (
    CanalRecord,
    CanalsData,
    build_children_index,
    build_parent_map,
    build_records_map,
    parse_new_canal_id_level,
)
from module_model.model.trunk_branch_optimize import (
    TrunkBranchContext,
    TrunkBranchResult,
    solve_trunk_branch,
)
from utils.log_util import logger

_BRANCH_PATTERN = re.compile(r'^\d+(-\d+){1}$')
_LATERAL_PATTERN = re.compile(r'^\d+(-\d+){2}$')
_KNOWN_LEVELS: frozenset[str] = frozenset({'1', '2', '3', '4', '5', '6', '7', '8', '9'})

# ---------------------------------------------------------------------------
# 进程级 worker 函数（模块级函数可被 pickle，用于 ProcessPoolExecutor）
# 注意：不能在 worker 中捕获类实例方法中的局部变量上下文
# ---------------------------------------------------------------------------

def _trunk_branch_worker(
    trunk_canal_id: str,
    canal_records: list[dict[str, Any]] | None,
    topology: list[dict[str, str]] | None,
    t_max: float,
    flow_ratio_min: float,
    flow_ratio_max: float,
    pop_size: int,
    n_gen: int,
    seed: int,
    permeability_index: float,
    permeability_coefficient: float,
    pref_weight_time: float,
    pref_weight_loss: float,
    pref_weight_flow_var: float,
    alpha: float,
) -> dict[str, Any]:
    """进程级入口：在独立进程中执行 NSGA-II，避免 uvicorn 事件循环阻塞。"""
    records_by_id, children_index, parent_map = CanalOptimizeService._resolve_dataset_full(
        canal_records,
        ({item['canal_id']: item.get('parent_id') for item in topology} if topology else None),
    )

    # 过滤 level ∈ {2, 3}
    filtered: dict[str, CanalRecord] = {}
    for cid, rec in records_by_id.items():
        lv_raw = rec.level
        lv_int: int | None = None
        if lv_raw is None or str(lv_raw).strip() not in _KNOWN_LEVELS:
            inferred = parse_new_canal_id_level(cid)
            if inferred.isdigit():
                lv_int = int(inferred)
        else:
            try:
                lv_int = int(str(lv_raw).strip())
            except (TypeError, ValueError):
                lv_int = None
        if lv_int is not None and lv_int in (2, 3):
            filtered[cid] = rec

    if not filtered:
        raise ServiceException(message='过滤后 level=2/3 的渠道为空，请检查输入数据')

    # 重建拓扑
    children_index_f = build_children_index(filtered.keys(), parent_map)
    parent_map_f = {cid: parent_map.get(cid) for cid in filtered}
    for cid, p in list(parent_map_f.items()):
        if p is not None and p not in filtered:
            parent_map_f[cid] = None

    # 定位干渠
    trunk_rec: CanalRecord | None = None
    for cid, rec in filtered.items():
        if cid == trunk_canal_id:
            trunk_rec = rec
            break
    if trunk_rec is None:
        raise ServiceException(
            message=f'未找到 canal_id={trunk_canal_id} 的干渠（需 level=2），当前 level-2 渠道：'
            + str([cid for cid, r in filtered.items() if str(r.level).strip() == '2'])
        )

    # 收集 level-3 支渠
    branch_ids = children_index_f.get(trunk_canal_id, [])
    branches: list[CanalRecord] = []
    for cid in branch_ids:
        if cid not in filtered:
            continue
        rec = filtered[cid]
        if str(rec.level).strip() == '3' or (
            (rec.level is None or str(rec.level).strip() not in _KNOWN_LEVELS)
            and _BRANCH_PATTERN.match(cid)
        ):
            branches.append(rec)
    branches.sort(key=lambda r: r.canal_id)

    if not branches:
        raise ServiceException(
            message=f'干渠 {trunk_canal_id} 下未找到 level-3 支渠，请确认该干渠存在 level-3 子渠道'
        )

    logger.info(
        'trunk-branch optimize: trunk=%s, n_branches=%d, t_max=%.1f, pop=%d, gen=%d',
        trunk_canal_id, len(branches), t_max, pop_size, n_gen,
    )

    ctx = TrunkBranchContext(
        trunk=trunk_rec,
        branches=branches,
        t_max=float(t_max),
        flow_ratio_min=float(flow_ratio_min),
        flow_ratio_max=float(flow_ratio_max),
        permeability_index=float(permeability_index),
        permeability_coefficient=float(permeability_coefficient),
        pop_size=max(10, int(pop_size)),
        n_gen=max(1, int(n_gen)),
        seed=int(seed),
        pref_weight_time=float(pref_weight_time),
        pref_weight_loss=float(pref_weight_loss),
        pref_weight_flow_var=float(pref_weight_flow_var),
        alpha=float(alpha),
    )

    try:
        result: TrunkBranchResult = solve_trunk_branch(ctx)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise ServiceException(message=str(exc)) from exc

    return result.to_dict()


def _branch_lateral_worker(
    branch_canal_id: str,
    canal_records: list[dict[str, Any]] | None,
    topology: list[dict[str, str]] | None,
    t_max: float,
    flow_ratio_min: float,
    flow_ratio_max: float,
    min_groups: int,
    max_groups: int,
    pop_size: int,
    n_gen: int,
    seed: int,
    permeability_index: float,
    permeability_coefficient: float,
    pref_weight_time: float,
    pref_weight_loss: float,
    pref_weight_flow_var: float,
    alpha: float,
) -> dict[str, Any]:
    """进程级入口：在独立进程中执行 NSGA-II。"""
    records_by_id, children_index, parent_map = CanalOptimizeService._resolve_dataset_full(
        canal_records,
        ({item['canal_id']: item.get('parent_id') for item in topology} if topology else None),
    )

    # 过滤 level ∈ {3, 4}
    filtered: dict[str, CanalRecord] = {}
    for cid, rec in records_by_id.items():
        lv_raw = rec.level
        lv_int: int | None = None
        if lv_raw is None or str(lv_raw).strip() not in _KNOWN_LEVELS:
            inferred = parse_new_canal_id_level(cid)
            if inferred.isdigit():
                lv_int = int(inferred)
        else:
            try:
                lv_int = int(str(lv_raw).strip())
            except (TypeError, ValueError):
                lv_int = None
        if lv_int is not None and lv_int in (3, 4):
            filtered[cid] = rec

    if not filtered:
        raise ServiceException(message='过滤后 level=3/4 的渠道为空，请检查输入数据')

    children_index_f = build_children_index(filtered.keys(), parent_map)
    parent_map_f = {cid: parent_map.get(cid) for cid in filtered}
    for cid, p in list(parent_map_f.items()):
        if p is not None and p not in filtered:
            parent_map_f[cid] = None

    # 定位支渠
    branch_rec: CanalRecord | None = None
    for cid, rec in filtered.items():
        if cid == branch_canal_id:
            branch_rec = rec
            break
    if branch_rec is None:
        raise ServiceException(
            message=f'未找到 canal_id={branch_canal_id} 的支渠（需 level=3），当前 level-3 渠道：'
            + str([cid for cid, r in filtered.items() if str(r.level).strip() == '3'])
        )

    # 收集 level-4 斗渠
    lateral_ids = children_index_f.get(branch_canal_id, [])
    laterals: list[CanalRecord] = []
    for cid in lateral_ids:
        if cid not in filtered:
            continue
        rec = filtered[cid]
        if str(rec.level).strip() == '4' or (
            (rec.level is None or str(rec.level).strip() not in _KNOWN_LEVELS)
            and _LATERAL_PATTERN.match(cid)
        ):
            laterals.append(rec)
    laterals.sort(key=lambda r: r.canal_id)

    if not laterals:
        raise ServiceException(
            message=f'支渠 {branch_canal_id} 下未找到 level-4 斗渠，请确认该支渠存在 level-4 子渠道'
        )

    if flow_ratio_max < flow_ratio_min:
        raise ServiceException(message='flow_ratio_max 必须不小于 flow_ratio_min')

    logger.info(
        'branch-lateral optimize: branch=%s, n_laterals=%d, groups=[%d,%d], t_max=%.1f, pop=%d, gen=%d',
        branch_canal_id, len(laterals), min_groups, max_groups, t_max, pop_size, n_gen,
    )

    ctx = BranchLateralContext(
        branch=branch_rec,
        laterals=laterals,
        t_max=float(t_max),
        flow_ratio_min=float(flow_ratio_min),
        flow_ratio_max=float(flow_ratio_max),
        min_groups=max(2, int(min_groups)),
        max_groups=max(int(min_groups), int(max_groups)),
        permeability_index=float(permeability_index),
        permeability_coefficient=float(permeability_coefficient),
        pop_size=max(10, int(pop_size)),
        n_gen=max(1, int(n_gen)),
        seed=int(seed),
        pref_weight_time=float(pref_weight_time),
        pref_weight_loss=float(pref_weight_loss),
        pref_weight_flow_var=float(pref_weight_flow_var),
        alpha=float(alpha),
    )

    try:
        result: BranchLateralResult = solve_branch_lateral(ctx)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise ServiceException(message=str(exc)) from exc

    return result.to_dict()


class CanalOptimizeService:
    """渠系优化配水服务：干支优化 + 支斗优化。"""

    @staticmethod
    def _resolve_dataset_full(
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> tuple[dict[str, CanalRecord], dict[str, list[str]], dict[str, str | None]]:
        if not canal_records:
            if not CanalsData.is_loaded():
                raise ServiceException(message='渠系数据未加载或格式错误')
            records_by_id = CanalsData.all()
            parent_map: dict[str, str | None] = {}
            for cid, rec in records_by_id.items():
                pid = CanalsData.parent_of(cid)
                parent_map[cid] = pid
            children_index = {
                cid: CanalsData.children_of(cid) for cid in records_by_id.keys()
            }
            return records_by_id, children_index, parent_map
        try:
            records_by_id = build_records_map(canal_records)
            parent_map = build_parent_map(canal_records, parent_ids)
            children_index = build_children_index(records_by_id.keys(), parent_map)
        except (TypeError, ValueError) as exc:
            raise ServiceException(message=f'渠道输入数据格式错误: {exc}') from exc
        if not records_by_id:
            raise ServiceException(message='渠道输入数据不能为空')
        return records_by_id, children_index, parent_map

    @staticmethod
    def _topology_to_parent_ids(
        topology: list[dict[str, str]] | None,
    ) -> dict[str, str | None] | None:
        if not topology:
            return None
        return {item['canal_id']: item.get('parent_id') for item in topology}

    # =============================================================================
    # 干支优化（level-2 干渠 + level-3 支渠）
    # =============================================================================

    @classmethod
    async def run_trunk_branch(
        cls,
        trunk_canal_id: str,
        canal_records: list[dict[str, Any]] | None = None,
        topology: list[dict[str, str]] | None = None,
        t_max: float = 360.0,
        flow_ratio_min: float = 0.8,
        flow_ratio_max: float = 1.0,
        pop_size: int = 80,
        n_gen: int = 60,
        seed: int = 1,
        permeability_index: float = 0.4,
        permeability_coefficient: float = 1.9,
        pref_weight_time: float = 0.7,
        pref_weight_loss: float = 0.1,
        pref_weight_flow_var: float = 0.2,
        alpha: float = 0.5,
    ) -> dict[str, Any]:
        """干支优化：level-2 干渠 + level-3 支渠子网，NSGA-II 三目标优化。"""
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(
                pool,
                partial(
                    _trunk_branch_worker,
                    trunk_canal_id,
                    canal_records,
                    topology,
                    t_max,
                    flow_ratio_min,
                    flow_ratio_max,
                    pop_size,
                    n_gen,
                    seed,
                    permeability_index,
                    permeability_coefficient,
                    pref_weight_time,
                    pref_weight_loss,
                    pref_weight_flow_var,
                    alpha,
                ),
            )
        return result


    # =============================================================================
    # 支斗轮续灌优化（level-3 支渠 + level-4 斗渠）
    # =============================================================================

    @classmethod
    async def run_branch_lateral(
        cls,
        branch_canal_id: str,
        canal_records: list[dict[str, Any]] | None = None,
        topology: list[dict[str, str]] | None = None,
        t_max: float = 360.0,
        flow_ratio_min: float = 0.6,
        flow_ratio_max: float = 1.0,
        min_groups: int = 2,
        max_groups: int = 6,
        pop_size: int = 150,
        n_gen: int = 100,
        seed: int = 1,
        permeability_index: float = 0.4,
        permeability_coefficient: float = 1.9,
        pref_weight_time: float = 0.4,
        pref_weight_loss: float = 0.3,
        pref_weight_flow_var: float = 0.3,
        alpha: float = 0.5,
    ) -> dict[str, Any]:
        """支斗轮续灌优化：level-3 支渠 + level-4 斗渠子网，NSGA-II 组间轮灌组内续灌。"""
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(
                pool,
                partial(
                    _branch_lateral_worker,
                    branch_canal_id,
                    canal_records,
                    topology,
                    t_max,
                    flow_ratio_min,
                    flow_ratio_max,
                    min_groups,
                    max_groups,
                    pop_size,
                    n_gen,
                    seed,
                    permeability_index,
                    permeability_coefficient,
                    pref_weight_time,
                    pref_weight_loss,
                    pref_weight_flow_var,
                    alpha,
                ),
            )
        return result
