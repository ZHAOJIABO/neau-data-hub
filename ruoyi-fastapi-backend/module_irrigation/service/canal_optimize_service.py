"""
渠系优化配水服务：异步执行全渠系三级 NSGA-III 优化，返回结构化 JSON。

不写 ZIP、不落盘，所有结果由 `solve_full_optimization` 直接返回 dataclass，
controller 序列化为 JSON 响应。
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from exceptions.exception import ServiceException
from module_irrigation.model.canal_full_optimize import (
    FullCanalContext,
    FullResult,
    solve_full_optimization,
)
from module_irrigation.model.canals_data import (
    CanalRecord,
    CanalsData,
    build_children_index,
    build_parent_map,
    build_records_map,
)
from utils.log_util import logger


# 新版 canal_id 命名：
#   干渠 1
#   支渠 1-1 / 1-2 ...
#   斗渠 1-1-1 / 1-1-2 ...
#   农渠 1-1-1-1 / 1-1-1-2 ...
# 段数 == level；正则按段数（'-' 数）匹配。
_BRANCH_PATTERN = re.compile(r'^\d+(-\d+){1}$')   # 2 段
_LATERAL_PATTERN = re.compile(r'^\d+(-\d+){2}$')  # 3 段


class CanalOptimizeService:
    """渠系优化配水服务：参数校验 + 渠段映射 + 异步求解。"""

    # ------------------------------------------------------------------
    # 全渠系三级
    # ------------------------------------------------------------------
    @classmethod
    async def run_full(
        cls,
        main_canal_id: str = '1',
        t_max: float = 360.0,
        flow_ratio_min: float = 0.8,
        flow_ratio_max: float = 1.0,
        min_groups: int = 2,
        max_groups: int = 6,
        pop_size: int = 80,
        n_gen: int = 60,
        seed: int = 1,
        permeability_index: float = 0.4,
        permeability_coefficient: float = 1.9,
        pref_weight_time: float = 0.4,
        pref_weight_loss: float = 0.3,
        pref_weight_flow_var: float = 0.3,
        alpha: float = 0.5,
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            cls._run_full_sync,
            main_canal_id,
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
            canal_records,
            parent_ids,
        )

    @classmethod
    def _run_full_sync(
        cls,
        main_canal_id: str,
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
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        records_by_id, children_index = cls._resolve_dataset(canal_records, parent_ids)

        # 如果 main_canal_id 不在数据中，按 level=1 自动选第一条干渠
        if main_canal_id not in records_by_id:
            level1_candidates = [
                cid for cid, r in records_by_id.items()
                if str(r.level).strip() == '1'
            ]
            if not level1_candidates:
                raise ServiceException(
                    message=f'未知渠段编号: {main_canal_id}（数据中也没有 level=1 的干渠）'
                )
            main_canal_id = level1_candidates[0]
            logger.info(
                'main_canal_id not in dataset, fallback to first level=1 record: {}',
                main_canal_id
            )
        main = cls._get_record(main_canal_id, records_by_id)

        # 收集支渠
        branches = cls._collect_branches(main_canal_id, records_by_id, children_index)
        if len(branches) < 1:
            raise ServiceException(
                message=f'干渠 {main_canal_id} 下未找到任何支渠（命名形如 Z1, Z2）'
            )

        # 收集每个支渠下的斗渠；过滤掉没有任何斗渠的空支渠（前端数据不全时静默跳过）
        laterals_by_branch: dict[str, list[CanalRecord]] = {}
        empty_branches: list[str] = []
        for branch in branches:
            laterals = cls._collect_laterals(branch.canal_id, records_by_id, children_index)
            if laterals:
                laterals_by_branch[branch.canal_id] = laterals
            else:
                empty_branches.append(branch.canal_id)
        if empty_branches:
            logger.warning(
                '支渠 {} 下未找到任何斗渠，将跳过（仅参与干-支配水）',
                empty_branches,
            )
        if not laterals_by_branch:
            logger.warning('所有支渠下均无斗渠；NSGA-III 将仅优化干-支配水')

        pop_size = max(10, int(pop_size))
        n_gen = max(1, int(n_gen))
        min_groups = max(2, int(min_groups))
        max_groups = max(min_groups, int(max_groups))
        if flow_ratio_max < flow_ratio_min:
            raise ServiceException(message='flow_ratio_max 必须不小于 flow_ratio_min')

        ctx = FullCanalContext(
            main=main,
            branches=branches,
            laterals_by_branch=laterals_by_branch,
            t_max=float(t_max),
            flow_ratio_min=float(flow_ratio_min),
            flow_ratio_max=float(flow_ratio_max),
            min_groups=min_groups,
            max_groups=max_groups,
            pop_size=pop_size,
            n_gen=n_gen,
            seed=int(seed),
            permeability_index=float(permeability_index),
            permeability_coefficient=float(permeability_coefficient),
            pref_weight_time=float(pref_weight_time),
            pref_weight_loss=float(pref_weight_loss),
            pref_weight_flow_var=float(pref_weight_flow_var),
            alpha=float(alpha),
        )
        logger.info(
            'canal full optimize: main={}, n_branches={}, n_laterals_by_branch={}, '
            't_max={}, pop={}, gen={}, seed={}',
            main_canal_id,
            len(branches),
            {k: len(v) for k, v in laterals_by_branch.items()},
            t_max,
            pop_size,
            n_gen,
            seed,
        )
        try:
            result: FullResult = solve_full_optimization(ctx)
        except (KeyError, ValueError, RuntimeError) as exc:
            raise ServiceException(message=str(exc)) from exc
        return result.to_dict()

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_dataset(
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> tuple[dict[str, CanalRecord], dict[str, list[str]]]:
        # 空列表或 None 均从数据库加载
        if not canal_records:
            if not CanalsData.is_loaded():
                raise ServiceException(message='渠系数据未加载或格式错误')
            return CanalsData.all(), {
                cid: CanalsData.children_of(cid) for cid in CanalsData.all().keys()
            }
        try:
            records_by_id = build_records_map(canal_records)
            parent_map = build_parent_map(canal_records, parent_ids)
            children_index = build_children_index(records_by_id.keys(), parent_map)
        except (TypeError, ValueError) as exc:
            raise ServiceException(message=f'渠道输入数据格式错误: {exc}') from exc
        if not records_by_id:
            raise ServiceException(message='渠道输入数据不能为空')
        return records_by_id, children_index

    @staticmethod
    def _get_record(canal_id: str, records_by_id: dict[str, CanalRecord]) -> CanalRecord:
        if canal_id not in records_by_id:
            raise ServiceException(message=f'未知渠段编号: {canal_id}')
        return records_by_id[canal_id]

    @staticmethod
    def _collect_branches(
        main_canal_id: str,
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
    ) -> list[CanalRecord]:
        children_ids = list(dict.fromkeys(children_index.get(main_canal_id, [])))
        if not children_ids:
            # 兜底：按 level=2 识别支渠（前端数据可能没有正确传 parent_id）
            children_ids = [
                cid for cid, r in records_by_id.items()
                if str(r.level).strip() == '2'
            ]
        records = [records_by_id[cid] for cid in children_ids if cid in records_by_id]
        # 优先 level 数字: 2=支渠; 正则作为兜底
        filtered: list[CanalRecord] = []
        for r in records:
            lv = str(r.level).strip() if r.level is not None else ''
            if lv == '2':
                filtered.append(r)
            elif lv not in ('1', '2', '3', '4') and _BRANCH_PATTERN.match(r.canal_id):
                filtered.append(r)
        filtered.sort(key=lambda r: r.canal_id)
        return filtered

    @staticmethod
    def _collect_laterals(
        parent_canal_id: str,
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
    ) -> list[CanalRecord]:
        children_ids = list(dict.fromkeys(children_index.get(parent_canal_id, [])))
        if not children_ids:
            # 兜底：parent_canal_id 是某支渠 ID（例如 Z1），按命名规则（如 Z1-D1）找子斗渠
            children_ids = [
                cid for cid in records_by_id
                if cid.startswith(f'{parent_canal_id}-') or cid.startswith(f'{parent_canal_id}_')
            ]
            if not children_ids:
                # 再兜底：从 level=3 里找 canal_id 以 parent_canal_id 开头的
                children_ids = [
                    cid for cid, r in records_by_id.items()
                    if str(r.level).strip() == '3' and r.canal_id.startswith(parent_canal_id)
                ]
        records = [records_by_id[cid] for cid in children_ids if cid in records_by_id]
        filtered: list[CanalRecord] = []
        for r in records:
            lv = str(r.level).strip() if r.level is not None else ''
            if lv == '3':
                filtered.append(r)
            elif lv not in ('1', '2', '3', '4') and _LATERAL_PATTERN.match(r.canal_id):
                filtered.append(r)
        filtered.sort(key=lambda r: r.canal_id)
        return filtered
