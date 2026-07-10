"""
渠系数据加载与单例管理。

数据来源：PostgreSQL 表 `agri_canal`（见 `module_agriculture.entity.do.canal_do.CanalBase`）。
`CanalsData` 保留为内存单例，给 `module_model.model.canal_models` 中的求解函数做只读快照。

CSV 格式（canal.csv）：
  canal_id, canal_name, parent_id, level, length, design_flow,
  bottom_width, slope, side_slope, roughness, water_demand,
  position, latitude, longitude

`CanalRecord` 保留 design_depth / gate_* 等字段，由调用方根据需要补充或设为默认值 0.0。
"""

from __future__ import annotations

import re
from typing import Any, ClassVar, Iterable


def parse_canal_value(value: Any, default: float = 0.0) -> float:
    """
    解析 CSV / DB 中的字符串数字，支持 "1/5000" 形式的坡降。
    """
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    if '/' in s and re.match(r'^\d+/\d+$', s):
        num, den = s.split('/', 1)
        return float(num) / float(den)
    try:
        return float(s)
    except ValueError:
        return default


def parse_canal_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """
    解析 canal.csv 字典行，返回渠段字段字典。

    返回字典字段与 agri_canal 表对齐。
    """
    canal_id = (row.get('canal_id') or '').strip()
    if not canal_id:
        return None
    return {
        'canal_id': canal_id,
        'canal_name': (row.get('canal_name') or '').strip() or None,
        'parent_id': (row.get('parent_id') or '').strip() or None,
        'level': (row.get('level') or '').strip() or None,
        'length': parse_canal_value(row.get('length')),
        'design_flow': parse_canal_value(row.get('design_flow')),
        'bottom_width': parse_canal_value(row.get('bottom_width')),
        'slope': parse_canal_value(row.get('slope')),
        'side_slope': parse_canal_value(row.get('side_slope')),
        'roughness': parse_canal_value(row.get('roughness')),
        'water_demand': parse_canal_value(row.get('water_demand')),
        'position': parse_canal_value(row.get('position')),
    }


def infer_canal_parent(canal_id: str, all_ids: set[str]) -> str | None:
    """
    根据新版 canal_id 命名规则推断父渠段。

    命名规则：
    - 干渠：'1'
    - 支渠：'1-1', '1-2' …
    - 斗渠：'1-1-1', '1-1-2' …
    - 农渠：'1-1-1-1', '1-1-1-2' …

    父渠段 = 切掉最后一段（'1-1-2' → '1-1'）。
    """
    if '-' not in canal_id:
        return None
    parent = '-'.join(canal_id.split('-')[:-1])
    return parent if parent in all_ids else None


def parse_new_canal_id_level(canal_id: str) -> str:
    """
    从 canal_id 推断 level：段数 = 级别
    1 段 → 1 干；2 段 → 2 支；3 段 → 3 斗；4 段 → 4 农
    """
    return str(canal_id.count('-') + 1)


def build_topology(
    canal_ids: Iterable[str],
) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    """
    根据 canal_id 集合推断父子关系。

    :return: (parent_map, children_index)
    """
    ids = set(canal_ids)
    parent_map: dict[str, str | None] = {cid: None for cid in ids}
    children_index: dict[str, list[str]] = {cid: [] for cid in ids}
    for cid in ids:
        parent = infer_canal_parent(cid, ids)
        parent_map[cid] = parent
        if parent is not None:
            children_index[parent].append(cid)
    return parent_map, children_index


def build_parent_map(
    records: list[dict[str, Any]],
    parent_ids: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """
    构建父渠段映射。优先级：
    1. 显式传入的 parent_ids（非空时覆盖一切）；
    2. 父渠段在数据集中存在时，使用 records 里的 parent_id；
    3. 否则按 canal_id 命名规则推断。

    records.parent_id 指向数据集中真实存在的渠段时才算可信。
    数据库里如果 parent_id 是错值（如 '1'、'4'），会自动落到推断分支。
    """
    ids = {str(r.get('canal_id', '')).strip() for r in records if r.get('canal_id')}
    explicit: dict[str, str | None] = {}
    for r in records:
        cid = r.get('canal_id')
        pid = r.get('parent_id')
        if not cid or not pid:
            continue
        cid = str(cid).strip()
        pid = str(pid).strip()
        # 仅当 parent 真实存在时才算可信
        if pid in ids:
            explicit[cid] = pid
    inferred, _ = build_topology(ids)
    for cid, parent in explicit.items():
        inferred[cid] = parent
    if parent_ids is not None:
        for cid, parent in parent_ids.items():
            if cid in inferred:
                inferred[cid] = parent
    return inferred


def build_children_index(
    canal_ids: Iterable[str],
    parent_ids: dict[str, str | None],
) -> dict[str, list[str]]:
    """根据父渠段映射构建 children 索引。"""
    ids = set(canal_ids)
    children_index: dict[str, list[str]] = {cid: [] for cid in ids}
    for cid, parent in parent_ids.items():
        if cid in ids and parent is not None and parent in children_index:
            children_index[parent].append(cid)
    for children in children_index.values():
        children.sort()
    return children_index


def build_canal_record(fields: dict[str, Any]) -> 'CanalRecord':
    """把外部输入 / DB 字段字典转换为内部 CanalRecord。"""
    canal_id = str(fields.get('canal_id') or '').strip()
    if not canal_id:
        raise ValueError('canal_id 不能为空')
    return CanalRecord(
        canal_id=canal_id,
        canal_name=str(fields.get('canal_name') or ''),
        level=str(fields.get('level') or ''),
        length=float(fields.get('length') or 0.0),
        design_flow=float(fields.get('design_flow') or 0.0),
        design_depth=float(fields.get('design_depth') or 0.0),
        top_width=float(fields.get('top_width') or 0.0),
        bottom_width=float(fields.get('bottom_width') or 0.0),
        slope=float(fields.get('slope') or 0.0),
        side_slope=float(fields.get('side_slope') or 0.0),
        roughness=float(fields.get('roughness') or 0.0),
        gate_height=float(fields.get('gate_height') or 0.0),
        gate_width=float(fields.get('gate_width') or 0.0),
        min_gate_opening=float(fields.get('min_gate_opening') or 0.0),
        max_gate_opening=float(fields.get('max_gate_opening') or 0.0),
        water_demand=float(fields.get('water_demand') or 0.0),
    )


def build_records_map(records: list[dict[str, Any]]) -> dict[str, 'CanalRecord']:
    """把渠道字段列表转换为 canal_id -> CanalRecord。"""
    result: dict[str, CanalRecord] = {}
    for fields in records:
        record = build_canal_record(fields)
        result[record.canal_id] = record
    return result


# ---------------------------------------------------------------------------
# 内存单例（保持旧 API 不变，给渠系模型做只读快照）
# ---------------------------------------------------------------------------


class CanalRecord:
    """
    单条渠段参数（不可变 dataclass 风格）。

    全灌区共享的常量（透水指数/系数、μ/σs/ε）不在此处，模型求解时由调用方传入；重力 g 为常量。
    """

    __slots__ = (
        'canal_id',
        'canal_name',
        'level',
        'length',
        'design_flow',
        'design_depth',
        'top_width',
        'bottom_width',
        'slope',
        'side_slope',
        'roughness',
        'gate_height',
        'gate_width',
        'min_gate_opening',
        'max_gate_opening',
        'water_demand',
    )

    def __init__(
        self,
        canal_id: str,
        canal_name: str,
        level: str,
        length: float,
        design_flow: float,
        design_depth: float,
        top_width: float,
        bottom_width: float,
        slope: float,
        side_slope: float,
        roughness: float,
        gate_height: float,
        gate_width: float,
        min_gate_opening: float,
        max_gate_opening: float,
        water_demand: float,
    ) -> None:
        self.canal_id = canal_id
        self.canal_name = canal_name
        self.level = level
        self.length = length
        self.design_flow = design_flow
        self.design_depth = design_depth
        self.top_width = top_width
        self.bottom_width = bottom_width
        self.slope = slope
        self.side_slope = side_slope
        self.roughness = roughness
        self.gate_height = gate_height
        self.gate_width = gate_width
        self.min_gate_opening = min_gate_opening
        self.max_gate_opening = max_gate_opening
        self.water_demand = water_demand

    @property
    def has_gate(self) -> bool:
        return self.gate_height > 0 and self.gate_width > 0


class CanalsData:
    """
    渠系数据单例：保存所有渠段记录 + 父子拓扑。

    使用方式：
        from module_model.model.canals_data import CanalsData
        CanalsData.load_from_records(records)   # records from DB
        CanalsData.canal('1')
        CanalsData.children_of('1-1')
    """

    _records: ClassVar[dict[str, CanalRecord]] = {}
    _topology: ClassVar[dict[str, str | None]] = {}
    _children_index: ClassVar[dict[str, list[str]]] = {}
    _root_id: ClassVar[str] = '1'
    _loaded: ClassVar[bool] = False

    @classmethod
    def load_from_records(
        cls, records: list[dict[str, Any]], parent_ids: dict[str, str | None] | None = None
    ) -> None:
        """
        用已含字段的字典列表初始化单例。`parent_ids` 可选；缺省时用 `infer_canal_parent` 推断。
        """
        canal_records: dict[str, CanalRecord] = {}
        for fields in records:
            canal_id = fields['canal_id']
            canal_records[canal_id] = build_canal_record(fields)

        ids = set(canal_records.keys())
        parent_ids = build_parent_map(records, parent_ids)
        children_index = build_children_index(ids, parent_ids)

        cls._records = canal_records
        cls._topology = parent_ids
        cls._children_index = children_index
        cls._root_id = '1' if '1' in ids else (next(iter(ids)) if ids else '1')
        cls._loaded = bool(canal_records)

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded

    @classmethod
    def all(cls) -> dict[str, CanalRecord]:
        return cls._records

    @classmethod
    def canal(cls, canal_id: str) -> CanalRecord:
        if not cls._loaded:
            raise RuntimeError('CanalsData 尚未加载，请先调用 CanalsData.load_from_records()')
        rec = cls._records.get(canal_id)
        if rec is None:
            raise KeyError(f'未知渠段编号: {canal_id}')
        return rec

    @classmethod
    def parent_of(cls, canal_id: str) -> str | None:
        return cls._topology.get(canal_id)

    @classmethod
    def children_of(cls, canal_id: str) -> list[str]:
        return list(cls._children_index.get(canal_id, []))

    @classmethod
    def root_id(cls) -> str:
        return cls._root_id

    @classmethod
    def reset(cls) -> None:
        """仅测试使用：清空单例。"""
        cls._records = {}
        cls._topology = {}
        cls._children_index = {}
        cls._root_id = '1'
        cls._loaded = False
