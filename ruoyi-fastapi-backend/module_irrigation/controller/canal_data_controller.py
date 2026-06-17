"""
渠系拓扑接口：GET /api/v1/irrigation/canal/topology
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from exceptions.exception import ServiceException
from module_irrigation.model.canals_data import CanalsData
from utils.response_util import ResponseUtil

canal_data_controller = APIRouterPro(
    prefix='/api/v1/irrigation/canal',
    order_num=23,
    tags=['渠系数据'],
    dependencies=[irrigation_api_key_dependency()],
)


@canal_data_controller.get(
    '/topology',
    summary='渠系拓扑（节点 / 边 / 根）',
)
async def canal_topology() -> JSONResponse:
    if not CanalsData.is_loaded():
        raise ServiceException(message='渠系数据未加载或格式错误')
    nodes: list[dict] = []
    edges: list[dict] = []
    for cid, rec in CanalsData.all().items():
        nodes.append({
            'id': cid,
            'name': rec.canal_name,
            'level': rec.level,
            'length': rec.length,
            'design_flow': rec.design_flow,
            'design_depth': rec.design_depth,
            'water_demand': rec.water_demand,
            'has_gate': rec.has_gate,
        })
        parent = CanalsData.parent_of(cid)
        if parent is not None:
            edges.append({
                'from': parent,
                'to': cid,
                'length': rec.length,
                'Q_design': rec.design_flow,
            })
    data = {
        'roots': [CanalsData.root_id()],
        'nodes': nodes,
        'edges': edges,
    }
    return ResponseUtil.success(data=data)
