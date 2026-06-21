"""
渠系 Kinematic Wave 水动力学仿真接口：

- POST /api/v1/irrigation/canal/hydro/kinematic  Kinematic Wave 仿真

调用 canalsim.exe（编译后的 C++ 求解器），通过 subprocess 执行。
支持三角形权重分水，返回时空快照矩阵、时程序列、沿程最终状态。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Body
from fastapi.responses import JSONResponse

from common.aspect.irrigation_auth import irrigation_api_key_dependency
from common.router import APIRouterPro
from module_irrigation.service.canal_sim_executor import run_canal_sim_exe
from utils.log_util import logger
from utils.response_util import ResponseUtil

canal_kinematic_controller = APIRouterPro(
    prefix='/api/v1/irrigation/canal/hydro',
    order_num=23,
    tags=['渠系水动力学'],
    dependencies=[irrigation_api_key_dependency()],
)


@canal_kinematic_controller.post(
    '/kinematic',
    summary='Kinematic Wave 水动力学仿真',
    response_model=None,
)
async def run_kinematic_sim(
    payload: Annotated[
        dict[str, Any],
        Body(description='Kinematic Wave 仿真 JSON 请求体'),
    ],
) -> JSONResponse:
    """Kinematic Wave 隐式迎风仿真：连续方程 + Manning 摩阻，Thomas 追赶法求解。

    请求体字段：
        canal_id:       渠段编号
        L:              渠段长度 (m)
        nx:             空间格点数
        b:              渠底宽 (m)
        m:              边坡系数 (1:m)
        n_Manning:      Manning 糙率
        S0:             渠底坡降
        Q_upstream:     上游流量 (m³/s)
        tf:             仿真总时长 (s)
        dt:             时间步长 (s)
        tolerance:      Picard 收敛容差（默认 1e-6）
        max_iterations: Picard 最大迭代次数（默认 100）
        output_interval_sec: 输出时间分辨率 (s)（默认 1.0）
        A_wet_min:     最小过水面积（默认 0.1）
        branches:       分水口列表 [{"x_position": float, "Q_offtake": float, "spread_cells": int}]
        inflow_series:  上游流量时序 [{"t_sec": float, "q_m3s": float}]（可选）
    """
    canal_id = str(payload.get('canal_id', 'unknown'))
    L = float(payload.get('L', 1000.0))
    nx = int(payload.get('nx', 51))
    b = float(payload.get('b', 8.0))
    m = float(payload.get('m', 1.5))
    n_Manning = float(payload.get('n_Manning', 0.025))
    S0 = float(payload.get('S0', 1 / 3000.0))
    Q_upstream = float(payload.get('Q_upstream', 10.0))
    tf = float(payload.get('tf', 3600.0))
    dt = float(payload.get('dt', 10.0))
    tolerance = float(payload.get('tolerance', 1e-6))
    max_iterations = int(payload.get('max_iterations', 100))
    output_interval_sec = float(payload.get('output_interval_sec', 1.0))
    A_wet_min = float(payload.get('A_wet_min', 0.1))

    branches = payload.get('branches', [])
    inflow_series_raw = payload.get('inflow_series', None)
    Q_upstream_series = None
    if inflow_series_raw:
        Q_upstream_series = [(float(p['t_sec']), float(p['q_m3s'])) for p in inflow_series_raw]

    logger.info(
        'kinematic wave request: canal_id=%s, L=%.1f, nx=%d, Q=%.3f, tf=%.1f, dt=%.1f, n_branches=%d',
        canal_id, L, nx, Q_upstream, tf, dt, len(branches),
    )

    try:
        result = run_canal_sim_exe(
            L=L,
            nx=nx,
            b=b,
            m=m,
            n_Manning=n_Manning,
            S0=S0,
            Q_upstream=Q_upstream,
            tf=tf,
            dt=dt,
            branches=branches,
            tolerance=tolerance,
            max_iterations=max_iterations,
            output_interval_sec=output_interval_sec,
            A_wet_min=A_wet_min,
            Q_upstream_series=Q_upstream_series,
            canal_id=canal_id,
        )
    except FileNotFoundError as exc:
        logger.error('canalsim.exe not found: %s', exc)
        return ResponseUtil.error(msg='仿真求解器未找到，请确认 canalsim.exe 已部署')
    except (ValueError, RuntimeError) as exc:
        logger.error('canal sim exe failed: %s', exc)
        return ResponseUtil.error(msg=f'仿真执行失败: {exc}')
    except Exception as exc:
        logger.error('canal sim unexpected error: %s', exc)
        return ResponseUtil.error(msg=f'仿真异常: {exc}')

    return ResponseUtil.success(data=result)
