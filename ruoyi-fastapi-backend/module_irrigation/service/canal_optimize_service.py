"""
渠系优化配水服务：按拓扑自动识别所有根渠段，串行求解后合并为单条 JSON 返回。

不写 ZIP、不落盘，所有结果由 `solve_full_optimization` 直接返回 dataclass，
controller 序列化为 JSON 响应。

层级选择：
  通过 `start_level` 控制参与优化的连续 3 级渠道区间：
  - start_level=1 → 干(1) - 支(2) - 斗(3) （默认，与历史行为一致）
  - start_level=2 → 支(2) - 斗(3) - 农(4)
  - start_level=3 → 斗(3) - 农(4) - 末级(5)

  不在 [start_level, start_level+2] 区间内的渠道在服务入口直接过滤。
  根渠段 = 上层（start_level）；中层 = start_level+1；下层 = start_level+2。
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
    parse_new_canal_id_level,
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

# 渠道级别可识别字符集：1=干 2=支 3=斗 4=农 ...
_KNOWN_LEVELS: frozenset[str] = frozenset({'1', '2', '3', '4', '5', '6', '7', '8', '9'})


def _pre_validate_structure(
    records_by_id: dict[str, CanalRecord],
    parent_map: dict[str, str | None],
    children_index: dict[str, list[str]],
    roots: list[CanalRecord],
    upper: int,
    middle: int,
    lower: int,
) -> None:
    """
    过滤后数据完整性预校验，提前发现结构性缺失并即时返回明确错误。

    校验项：
    1. 过滤后数据集为空
    2. 中层渠道（level=middle）全部缺失
    3. 所有根渠段下均无中层渠道
    4. 下层渠道（level=lower）全部缺失
    """
    if not records_by_id:
        raise ServiceException(message='过滤后渠道数据为空，请检查 start_level 是否与实际渠系层级匹配')

    # ── 检查中层渠道是否存在 ──
    middle_str = str(middle)
    middle_canals = [
        cid for cid, r in records_by_id.items()
        if str(r.level).strip() == middle_str
        or (r.level is None and _BRANCH_PATTERN.match(cid))
    ]

    if not middle_canals:
        raise ServiceException(
            message=(
                f'未找到任何 level={middle}（中层）渠道，当前 start_level={upper} 对应 '
                f'层级区间 [{upper}-{middle}-{lower}]，但数据中不存在 level={middle} 的渠道。'
                f'请确认 start_level 参数与实际渠系层级是否匹配。'
            )
        )

    # ── 检查每个根渠段是否有中层渠道 ──
    root_ids_missing_branch: list[str] = []
    for root in roots:
        branches = [
            cid for cid in children_index.get(root.canal_id, [])
            if cid in records_by_id
            and str(records_by_id[cid].level).strip() == middle_str
        ]
        if not branches:
            # 兜底：检查正则匹配
            if not _BRANCH_PATTERN.findall(root.canal_id):
                root_ids_missing_branch.append(root.canal_id)

    if root_ids_missing_branch:
        raise ServiceException(
            message=(
                f'以下根渠段下未找到任何中层渠道（level={middle}）：{root_ids_missing_branch}。'
                f'请确认 start_level={upper} 与渠系数据层级一致。'
            )
        )

    # ── 检查下层渠道是否存在 ──
    lower_str = str(lower)
    lower_canals = [
        cid for cid, r in records_by_id.items()
        if str(r.level).strip() == lower_str
        or (r.level is None and _LATERAL_PATTERN.match(cid))
    ]

    if not lower_canals:
        raise ServiceException(
            message=(
                f'未找到任何 level={lower}（下层）渠道，start_level={upper} 对应层级区间 '
                f'[{upper}-{middle}-{lower}]，但数据中不存在 level={lower} 的渠道。'
                f'请确认 start_level 参数与实际渠系层级是否匹配，或该渠系是否已达到末级。'
            )
        )

    # ── 检查每个中层渠道是否有下层渠道 ──
    middle_missing_lower: list[str] = []
    for mid_cid in middle_canals:
        children = [
            cid for cid in children_index.get(mid_cid, [])
            if cid in records_by_id
            and str(records_by_id[cid].level).strip() == lower_str
        ]
        if not children:
            # 兜底：检查前缀匹配
            if not any(
                cid.startswith(f'{mid_cid}-') or cid.startswith(f'{mid_cid}_')
                for cid in records_by_id
            ):
                middle_missing_lower.append(mid_cid)

    if middle_missing_lower:
        raise ServiceException(
            message=(
                f'以下中层渠道（level={middle}）下未找到任何下层渠道（level={lower}）：'
                f'{middle_missing_lower}。该渠系可能已达到末级，建议降低 start_level。'
            )
        )


def _resolve_level_window(start_level: int) -> tuple[int, int, int]:
    """将 start_level 拆为 (上层, 中层, 下层)，确保 1 ≤ upper < lower。"""
    if start_level < 1:
        raise ServiceException(message='start_level 必须 >= 1')
    upper = int(start_level)
    middle = upper + 1
    lower = upper + 2
    return upper, middle, lower


def _filter_records_by_level_window(
    records_by_id: dict[str, CanalRecord],
    upper: int,
    lower: int,
) -> tuple[dict[str, CanalRecord], int]:
    """保留 level ∈ [upper, lower] 的渠道；其它过滤掉。"""
    dropped = 0
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
        if lv_int is None or lv_int < upper or lv_int > lower:
            dropped += 1
            continue
        filtered[cid] = rec
    return filtered, dropped


class CanalOptimizeService:
    """渠系优化配水服务：参数校验 + 渠段映射 + 异步求解。"""

    @classmethod
    async def run_full(
        cls,
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
        start_level: int = 1,
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            cls._run_full_sync,
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
            start_level,
            canal_records,
            parent_ids,
        )

    @classmethod
    def _run_full_sync(
        cls,
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
        start_level: int,
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        upper, middle, lower = _resolve_level_window(int(start_level))
        records_by_id, children_index, parent_map = cls._resolve_dataset_full(
            canal_records, parent_ids,
        )
        records_by_id, dropped = _filter_records_by_level_window(records_by_id, upper, lower)
        if dropped:
            logger.info(
                'canal optimize: start_level={} (range {}-{}-{})，已过滤 {} 条不在 [{}-{}] 区间内的渠道',
                start_level, upper, middle, lower, dropped, upper, lower,
            )
        # 过滤后重新构建 children_index / parent_map
        children_index = build_children_index(records_by_id.keys(), parent_map)
        # parent_map 中指向被过滤渠道的项置 None
        parent_map = {cid: parent_map.get(cid) for cid in records_by_id}
        for cid, p in list(parent_map.items()):
            if p is not None and p not in records_by_id:
                parent_map[cid] = None

        roots = cls._detect_roots(records_by_id, parent_map, upper_level=upper)
        if not roots:
            raise ServiceException(
                message=f'未识别到任何 level={upper} 的根渠段（数据为空或该级别渠道全部缺失）'
            )

        # ── 数据完整性预校验：提前发现结构性缺失，避免逐一求解时才暴露 ──
        _pre_validate_structure(records_by_id, parent_map, children_index, roots, upper, middle, lower)

        return cls._solve_multi_roots(
            roots=roots,
            records_by_id=records_by_id,
            children_index=children_index,
            t_max=t_max,
            flow_ratio_min=flow_ratio_min,
            flow_ratio_max=flow_ratio_max,
            min_groups=min_groups,
            max_groups=max_groups,
            pop_size=pop_size,
            n_gen=n_gen,
            seed=seed,
            permeability_index=permeability_index,
            permeability_coefficient=permeability_coefficient,
            pref_weight_time=pref_weight_time,
            pref_weight_loss=pref_weight_loss,
            pref_weight_flow_var=pref_weight_flow_var,
            alpha=alpha,
            upper_level=upper,
            middle_level=middle,
            lower_level=lower,
        )

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_dataset_full(
        canal_records: list[dict[str, Any]] | None = None,
        parent_ids: dict[str, str | None] | None = None,
    ) -> tuple[dict[str, CanalRecord], dict[str, list[str]], dict[str, str | None]]:
        """同时返回 records_by_id / children_index / parent_map（多根识别需要 parent_map）。"""
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
    def _detect_roots(
        records_by_id: dict[str, CanalRecord],
        parent_map: dict[str, str | None],
        upper_level: int,
    ) -> list[CanalRecord]:
        """识别所有根渠段（无父级或父级不在数据集中）。

        优先级：parent_map 显式为 None → canal_id 中不含 '-' → 兜底为 level=upper_level。
        """
        upper_level_str = str(upper_level)
        roots: list[CanalRecord] = []
        for cid, rec in records_by_id.items():
            parent = parent_map.get(cid)
            if parent is None or parent not in records_by_id:
                roots.append(rec)
        if not roots:
            roots = [
                r for cid, r in records_by_id.items()
                if str(r.level).strip() == upper_level_str
            ]
        roots.sort(key=lambda r: r.canal_id)
        return roots

    @classmethod
    def _build_full_canal_context(
        cls,
        main: CanalRecord,
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
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
        middle_level: int,
        lower_level: int,
    ) -> FullCanalContext:
        """构造一个根渠段的 FullCanalContext。"""
        branches = cls._collect_branches(
            main.canal_id, records_by_id, children_index, middle_level,
        )
        laterals_by_branch: dict[str, list[CanalRecord]] = {}
        empty_branches: list[str] = []
        for branch in branches:
            laterals = cls._collect_laterals(
                branch.canal_id, records_by_id, children_index, lower_level,
            )
            if laterals:
                laterals_by_branch[branch.canal_id] = laterals
            else:
                empty_branches.append(branch.canal_id)
        if empty_branches:
            logger.warning(
                '根 {} 下中层渠道 {} 未找到下层渠道，将跳过（仅参与上层-中层级配水）',
                main.canal_id, empty_branches,
            )
        return FullCanalContext(
            main=main,
            branches=branches,
            laterals_by_branch=laterals_by_branch,
            t_max=float(t_max),
            flow_ratio_min=float(flow_ratio_min),
            flow_ratio_max=float(flow_ratio_max),
            min_groups=max(2, int(min_groups)),
            max_groups=max(int(min_groups), int(max_groups)),
            pop_size=max(10, int(pop_size)),
            n_gen=max(1, int(n_gen)),
            seed=int(seed),
            permeability_index=float(permeability_index),
            permeability_coefficient=float(permeability_coefficient),
            pref_weight_time=float(pref_weight_time),
            pref_weight_loss=float(pref_weight_loss),
            pref_weight_flow_var=float(pref_weight_flow_var),
            alpha=float(alpha),
            upper_level=int(middle_level) - 1,
            middle_level=middle_level,
            lower_level=lower_level,
        )

    @classmethod
    def _solve_one_root(
        cls,
        main: CanalRecord,
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
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
        middle_level: int,
        lower_level: int,
    ) -> dict[str, Any]:
        if flow_ratio_max < flow_ratio_min:
            raise ServiceException(message='flow_ratio_max 必须不小于 flow_ratio_min')
        ctx = cls._build_full_canal_context(
            main, records_by_id, children_index,
            t_max, flow_ratio_min, flow_ratio_max,
            min_groups, max_groups, pop_size, n_gen, seed,
            permeability_index, permeability_coefficient,
            pref_weight_time, pref_weight_loss, pref_weight_flow_var, alpha,
            middle_level, lower_level,
        )
        if not ctx.branches:
            raise ServiceException(
                message=(
                    f'根渠段 {main.canal_id} 下未找到任何中层渠道（level={middle_level}），'
                    f'请检查 start_level 与实际渠系层级的对应关系'
                )
            )
        if not ctx.laterals_by_branch:
            raise ServiceException(
                message=(
                    f'根渠段 {main.canal_id} 下所有中层渠道均无下层渠道（level={lower_level}），'
                    f'请检查 start_level 与实际渠系层级的对应关系'
                )
            )
        logger.info(
            'canal full optimize: main={}, n_branches={}, n_laterals_by_branch={}, '
            't_max={}, pop={}, gen={}, seed={}',
            main.canal_id, len(ctx.branches),
            {k: len(v) for k, v in ctx.laterals_by_branch.items()},
            t_max, ctx.pop_size, ctx.n_gen, ctx.seed,
        )
        try:
            result: FullResult = solve_full_optimization(ctx)
        except (KeyError, ValueError, RuntimeError) as exc:
            raise ServiceException(message=str(exc)) from exc
        return result.to_dict()

    @classmethod
    def _solve_multi_roots(
        cls,
        roots: list[CanalRecord],
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
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
        upper_level: int,
        middle_level: int,
        lower_level: int,
    ) -> dict[str, Any]:
        """对多条根渠段串行求解，合并结果为单条 JSON 返回。"""
        if flow_ratio_max < flow_ratio_min:
            raise ServiceException(message='flow_ratio_max 必须不小于 flow_ratio_min')

        logger.info(
            'canal full optimize multi-roots: n_roots={}, roots={}, t_max={}, pop={}, gen={}, seed={}, '
            'level_range={}-{}-{}',
            len(roots), [r.canal_id for r in roots], t_max, pop_size, n_gen, seed,
            upper_level, middle_level, lower_level,
        )

        per_root_results: list[tuple[CanalRecord, dict[str, Any] | None, str | None]] = []
        for root in roots:
            try:
                one = cls._solve_one_root(
                    main=root,
                    records_by_id=records_by_id,
                    children_index=children_index,
                    t_max=t_max,
                    flow_ratio_min=flow_ratio_min,
                    flow_ratio_max=flow_ratio_max,
                    min_groups=min_groups,
                    max_groups=max_groups,
                    pop_size=pop_size,
                    n_gen=n_gen,
                    seed=seed,
                    permeability_index=permeability_index,
                    permeability_coefficient=permeability_coefficient,
                    pref_weight_time=pref_weight_time,
                    pref_weight_loss=pref_weight_loss,
                    pref_weight_flow_var=pref_weight_flow_var,
                    alpha=alpha,
                    middle_level=middle_level,
                    lower_level=lower_level,
                )
                per_root_results.append((root, one, None))
            except (KeyError, ValueError, RuntimeError, ServiceException) as exc:
                logger.warning(
                    '根渠段 {} 求解失败：{}；将跳过该根',
                    root.canal_id, exc,
                )
                per_root_results.append((root, None, str(exc)))

        successful = [(r, d) for r, d, err in per_root_results if d is not None]
        if not successful:
            raise ServiceException(
                message='所有根渠段求解均失败：' + '; '.join(
                    err for _, _, err in per_root_results if err
                ),
            )

        return cls._merge_multi_root_results(
            per_root_results,
            upper_level=upper_level,
            middle_level=middle_level,
            lower_level=lower_level,
        )

    @staticmethod
    def _merge_multi_root_results(
        per_root_results: list[tuple[CanalRecord, dict[str, Any] | None, str | None]],
        upper_level: int,
        middle_level: int,
        lower_level: int,
    ) -> dict[str, Any]:
        """合并多根求解结果为单条 JSON（与单根 schema 兼容 + 额外 roots 字段）。"""
        successful = [(r, d) for r, d, err in per_root_results if d is not None]

        # 顶层聚合
        all_branches: list[dict] = []
        all_laterals: list[dict] = []
        all_groups: list[dict] = []
        all_pareto: list[dict] = []
        all_time_series: list[dict] = []
        root_summaries: list[dict] = []

        total_loss = 0.0
        total_main_loss = 0.0
        total_branch_loss = 0.0
        total_lateral_loss = 0.0
        max_time_h = 0.0
        weighted_F1 = 0.0
        weighted_F2 = 0.0
        weighted_F3 = 0.0
        total_weight = 0.0

        for root, data in successful:
            sum_root = data.get('summary', {})
            main_loss = float(sum_root.get('main_loss_m3') or 0.0)
            branch_loss = float(sum_root.get('branch_loss_m3') or 0.0)
            lateral_loss = float(sum_root.get('lateral_loss_m3') or 0.0)
            total_root_loss = float(sum_root.get('total_loss_m3') or 0.0)
            obj = sum_root.get('objective_values', {}) or {}
            n_br = sum_root.get('n_branches', 0) or 0
            n_lat = sum_root.get('n_laterals', 0) or 0
            time_h = float((data.get('topsis_summary') or {}).get('total_time_h') or 0.0)

            total_main_loss += main_loss
            total_branch_loss += branch_loss
            total_lateral_loss += lateral_loss
            total_loss += total_root_loss
            max_time_h = max(max_time_h, time_h)
            # 加权用 n_laterals 反映规模
            w = max(1, n_lat)
            weighted_F1 += float(obj.get('F1_total_time_h') or 0.0) * w
            weighted_F2 += float(obj.get('F2_total_loss_m3') or 0.0) * w
            weighted_F3 += float(obj.get('F3_flow_var') or 0.0) * w
            total_weight += w

            all_branches.extend(data.get('branches', []) or [])
            all_laterals.extend(data.get('laterals', []) or [])
            all_groups.extend(data.get('groups', []) or [])
            all_time_series.extend(data.get('time_series', []) or [])
            for p in data.get('pareto', []) or []:
                p_copy = dict(p)
                p_copy['root_id'] = root.canal_id
                all_pareto.append(p_copy)

            root_summaries.append({
                'root_id': root.canal_id,
                'n_branches': n_br,
                'n_laterals': n_lat,
                'main_canal_id': root.canal_id,
                'topsis_score': float(sum_root.get('topsis_score') or 0.0),
                'objective_values': obj,
                'main_loss_m3': round(main_loss, 2),
                'branch_loss_m3': round(branch_loss, 2),
                'lateral_loss_m3': round(lateral_loss, 2),
                'total_loss_m3': round(total_root_loss, 2),
                'total_time_h': round(time_h, 3),
                'q_max_m3s': float(sum_root.get('q_max_m3s') or 0.0),
                'ok': True,
            })

        # 失败的根也写入 roots 列表（方便前端展示）
        for root, _data, err in per_root_results:
            if _data is not None:
                continue
            root_summaries.append({
                'root_id': root.canal_id,
                'n_branches': 0,
                'n_laterals': 0,
                'ok': False,
                'error': err,
            })

        # 顶层 main_canal 用首根，main_canal 区块聚合
        first_root_id = successful[0][0].canal_id
        avg_F1 = weighted_F1 / total_weight if total_weight > 0 else 0.0
        avg_F2 = weighted_F2 / total_weight if total_weight > 0 else 0.0
        avg_F3 = weighted_F3 / total_weight if total_weight > 0 else 0.0

        summary = {
            'mode': 'full_multi_roots',
            'start_level': int(upper_level),
            'level_range': {
                'upper': int(upper_level),
                'middle': int(middle_level),
                'lower': int(lower_level),
            },
            'main_canal_id': first_root_id,
            'n_roots': len(successful),
            'n_branches': len(all_branches),
            'n_laterals': len(all_laterals),
            'branch_ids': [b.get('name') for b in all_branches],
            'q_max_m3s': max(
                (rs.get('q_max_m3s') or 0.0) for rs in root_summaries if rs.get('ok')
            ) if successful else 0.0,
            'topsis_score': float(
                sum(rs.get('topsis_score', 0.0) for rs in root_summaries if rs.get('ok'))
                / max(1, len(successful))
            ),
            'entropy_weights': successful[0][1].get('summary', {}).get('entropy_weights', {}),
            'objective_values': {
                'F1_total_time_h': round(avg_F1, 3),
                'F2_total_loss_m3': round(avg_F2, 2),
                'F3_flow_var': round(avg_F3, 6),
            },
            'main_loss_m3': round(total_main_loss, 2),
            'branch_loss_m3': round(total_branch_loss, 2),
            'lateral_loss_m3': round(total_lateral_loss, 2),
            'total_loss_m3': round(total_loss, 2),
            'roots': root_summaries,
        }

        main_canal = {
            'Q_total_m3s': round(
                sum(rs.get('q_max_m3s', 0.0) for rs in root_summaries if rs.get('ok')), 4,
            ),
            't_max_h': round(max_time_h, 3),
            'main_loss_m3': round(total_main_loss, 2),
            'branch_loss_m3': round(total_branch_loss, 2),
            'lateral_loss_m3': round(total_lateral_loss, 2),
            'total_loss_m3': round(total_loss, 2),
        }

        topsis_summary = {
            'total_time_h': round(max_time_h, 3),
            'total_loss_m3': round(total_loss, 2),
            'main_loss_m3': round(total_main_loss, 2),
            'branch_loss_m3': round(total_branch_loss, 2),
            'lateral_loss_m3': round(total_lateral_loss, 2),
            'flow_var': round(avg_F3, 6),
        }

        return {
            'summary': summary,
            'main_canal': main_canal,
            'branches': all_branches,
            'laterals': all_laterals,
            'groups': all_groups,
            'time_series': all_time_series,
            'pareto': all_pareto,
            'topsis_summary': topsis_summary,
            'roots': root_summaries,
        }

    @staticmethod
    def _collect_branches(
        main_canal_id: str,
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
        middle_level: int,
    ) -> list[CanalRecord]:
        """根据 `middle_level`（默认 2=支渠）从根渠段下识别中层渠道。"""
        middle_str = str(int(middle_level))
        children_ids = list(dict.fromkeys(children_index.get(main_canal_id, [])))
        if not children_ids:
            # 兜底：按 level=middle_level 识别中层渠道
            children_ids = [
                cid for cid, r in records_by_id.items()
                if str(r.level).strip() == middle_str
            ]
        records = [records_by_id[cid] for cid in children_ids if cid in records_by_id]
        # 优先 level 数字: middle_str; 正则作为兜底
        filtered: list[CanalRecord] = []
        for r in records:
            lv = str(r.level).strip() if r.level is not None else ''
            if lv == middle_str:
                filtered.append(r)
            elif lv not in _KNOWN_LEVELS and _BRANCH_PATTERN.match(r.canal_id):
                filtered.append(r)
        filtered.sort(key=lambda r: r.canal_id)
        return filtered

    @staticmethod
    def _collect_laterals(
        parent_canal_id: str,
        records_by_id: dict[str, CanalRecord],
        children_index: dict[str, list[str]],
        lower_level: int,
    ) -> list[CanalRecord]:
        """根据 `lower_level`（默认 3=斗渠）从中层渠道下识别下层渠道。"""
        lower_str = str(int(lower_level))
        children_ids = list(dict.fromkeys(children_index.get(parent_canal_id, [])))
        if not children_ids:
            # 兜底：按 canal_id 命名规则找直接子
            children_ids = [
                cid for cid in records_by_id
                if cid.startswith(f'{parent_canal_id}-') or cid.startswith(f'{parent_canal_id}_')
            ]
            if not children_ids:
                # 再兜底：从 level=lower_level 里找 canal_id 以 parent_canal_id 开头的
                children_ids = [
                    cid for cid, r in records_by_id.items()
                    if str(r.level).strip() == lower_str and r.canal_id.startswith(parent_canal_id)
                ]
        records = [records_by_id[cid] for cid in children_ids if cid in records_by_id]
        filtered: list[CanalRecord] = []
        for r in records:
            lv = str(r.level).strip() if r.level is not None else ''
            if lv == lower_str:
                filtered.append(r)
            elif lv not in _KNOWN_LEVELS and _LATERAL_PATTERN.match(r.canal_id):
                filtered.append(r)
        filtered.sort(key=lambda r: r.canal_id)
        return filtered
