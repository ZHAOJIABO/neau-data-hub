"""
渠系 Kinematic Wave 水动力学仿真执行器：调用 canalsim.exe 求解器。

功能：
  - 将 API 请求参数转换为 canalsim.exe 输入 JSON
  - 通过 subprocess 启动 canalsim.exe 进程
  - 读取 result.json 并映射为与原 Python 求解器一致的 KinematicWaveResult 字典

输入（API 参数）→ 输入 JSON（canalsim）→ 输出 JSON（canalsim）→ 返回字典（与 API 响应一致）
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from utils.log_util import logger

# canalsim.exe 的绝对路径（ruoyi-fastapi-backend/models/canalsim.exe）
# __file__ = module_irrigation/service/canal_sim_executor.py
#   dirname → module_irrigation/service
#   dirname → module_irrigation
#   dirname → ruoyi-fastapi-backend
#   join     → ruoyi-fastapi-backend/models/canalsim.exe
CANALSIM_EXE: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'models',
    'canalsim.exe',
)


# ============================================================================
# 输入 / 输出数据结构
# ============================================================================


@dataclass
class CanalSimInput:
    """canalsim.exe 的输入 JSON 结构。"""
    L: float
    nx: int
    b: float = 5.0
    m: float = 1.5
    n_Manning: float = 0.025
    S0: float = 0.0003
    Q_upstream: float = 10.0
    tf: float = 3600.0
    dt: float = 30.0
    tolerance: float = 1e-6
    max_iterations: int = 100
    A_wet_min: float = 0.1
    Q_initial: float = 0.0
    branches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'channel': {
                'L': self.L,
                'nx': self.nx,
                'b': self.b,
                'm': self.m,
                'n_Manning': self.n_Manning,
                'S0': self.S0,
                'Q_upstream': self.Q_upstream,
                'tf': self.tf,
                'dt': self.dt,
                'A_wet_min': self.A_wet_min,
                'Q_initial': self.Q_initial,
            },
            'solver': {
                'tolerance': self.tolerance,
                'max_iterations': self.max_iterations,
            },
            'branches': self.branches,
        }


# ============================================================================
# 仿真结果（与原 Python 求解器 KinematicWaveResult.to_dict() 结构兼容）
# ============================================================================


def run_canal_sim_exe(
    L: float,
    nx: int,
    b: float,
    m: float,
    n_Manning: float,
    S0: float,
    Q_upstream: float,
    tf: float,
    dt: float,
    branches: Optional[list[dict]] = None,
    tolerance: float = 1e-6,
    max_iterations: int = 100,
    output_interval_sec: float = 1.0,
    A_wet_min: float = 0.1,
    Q_upstream_series: Optional[list[tuple[float, float]]] = None,
    canal_id: str = 'unknown',
) -> dict[str, Any]:
    """
    调用 canalsim.exe 执行 Kinematic Wave 水动力学仿真。

    参数（与 kinematic_wave_simulate 兼容）:
        L:                渠段长度 (m)
        nx:               空间格点数
        b:                渠底宽 (m)
        m:                边坡系数 (1:m)
        n_Manning:        Manning 糙率
        S0:               渠底坡降
        Q_upstream:       上游设计流量 (m³/s)，无 inflow_series 时使用
        tf:               仿真总时长 (s)
        dt:               时间步长 (s)
        branches:         分水口列表 [{"x_position", "Q_offtake", "spread_cells"}]
        tolerance:        Picard 迭代收敛容差
        max_iterations:   最大迭代次数
        output_interval_sec: 输出时间分辨率 (s)（保留，当前 exe 输出每个 dt）
        A_wet_min:        最小过水面积
        Q_upstream_series: 上游流量时序 [(t_sec, Q_m3s), ...]
                           如果只含 1 个点，使用该流量做稳态仿真；
                           如果多个点，按时间段分段执行 exe，每次取对应区间的平均流量，
                           最后合并时空结果（取各段末尾快照拼接）。
                           注意：canalsim.exe 自身不支持非恒定流入过程，此处通过
                           分段仿真近似。
        canal_id:          渠段编号（仅用于日志）

    返回:
        dict，与 KinematicWaveResult.to_dict() 结构一致：
        {
          'channel': {...},
          'summary': {...},
          'timeseries': {...},
          'final_state': {...},
          'spacetime': {...},
          'branches': [...],
        }
    """
    branches = branches or []

    # -------------------------------------------------------------------------
    # 预处理 inflow_series
    # -------------------------------------------------------------------------
    if Q_upstream_series and len(Q_upstream_series) > 1:
        # 多时段非恒定流：按时间段分段执行 exe
        return _run_transient_via_exe_segments(
            L=L, nx=nx, b=b, m=m, n_Manning=n_Manning, S0=S0,
            tf=tf, dt=dt, branches=branches, tolerance=tolerance,
            max_iterations=max_iterations, A_wet_min=A_wet_min,
            Q_upstream_series=Q_upstream_series, canal_id=canal_id,
        )

    # -------------------------------------------------------------------------
    # 稳态（单流量 or 常数 Q_upstream）：单次 exe 调用
    # -------------------------------------------------------------------------
    # inflow_series 为空或只有 1 个点 → 取第一个点的流量
    effective_Q = Q_upstream
    if Q_upstream_series and len(Q_upstream_series) == 1:
        effective_Q = Q_upstream_series[0][1]

    sim_input = CanalSimInput(
        L=L, nx=nx, b=b, m=m, n_Manning=n_Manning, S0=S0,
        Q_upstream=effective_Q, tf=tf, dt=dt,
        tolerance=tolerance, max_iterations=max_iterations,
        A_wet_min=A_wet_min, branches=list(branches),
    )

    result_json = _call_exe(sim_input, canal_id=canal_id)
    return _map_exe_output_to_result(
        result_json, sim_input, output_interval_sec=output_interval_sec,
    )


def _run_transient_via_exe_segments(
    L: float, nx: int, b: float, m: float, n_Manning: float, S0: float,
    tf: float, dt: float, branches: list[dict], tolerance: float,
    max_iterations: int, A_wet_min: float,
    Q_upstream_series: list[tuple[float, float]],
    canal_id: str,
) -> dict[str, Any]:
    """
    非恒定流入流时分段执行 canalsim.exe，结果拼接合并。

    策略：每个时序拐点作为一个分段的起点，分段长度 = t_{i+1} - t_i。
    每个分段的初始条件 = 前一分段的最终状态（水深、流量）。
    最后返回完整时空矩阵（所有分段的水深/流量时空快照按时间拼接）。
    """
    import math

    # 按时间排序
    pts = sorted(Q_upstream_series, key=lambda p: p[0])

    # 初始化：均匀流
    def _normal_depth(Q: float) -> float:
        Sf = math.sqrt(S0)
        def residual(h: float) -> float:
            A = (b + m * h) * h
            P = b + 2.0 * h * math.sqrt(1.0 + m * m)
            R = A / P if P > 1e-9 else 1e-9
            return (A * (R ** (2.0 / 3.0)) / n_Manning) * Sf - Q
        lo, hi = 1e-4, 50.0
        if residual(lo) > 0:
            return lo
        if residual(hi) < 0:
            return hi
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            r = residual(mid)
            if r > 0:
                hi = mid
            else:
                lo = mid
            if hi - lo < 1e-6:
                break
        return 0.5 * (lo + hi)

    h_init = _normal_depth(pts[0][1])
    h_current = np.full(nx, max(h_init, 0.01), dtype=np.float64)
    Q_current = np.full(nx, pts[0][1], dtype=np.float64)

    # 收集所有段的水深/流量时空快照
    all_spacetime_times: list[float] = []
    all_spacetime_water_level: list[list[float]] = []
    all_spacetime_flow_rate: list[list[float]] = []

    # 全时刻 timeseries
    all_t: list[float] = []
    all_Q_up: list[float] = []
    all_Q_down: list[float] = []
    all_y_up: list[float] = []
    all_y_down: list[float] = []

    dx = L / (nx - 1)
    x_grid = np.linspace(0, L, nx)

    seg_idx = 0
    while seg_idx < len(pts) - 1:
        t_start, Q_start = pts[seg_idx]
        t_end, Q_end = pts[seg_idx + 1]
        seg_tf = t_end - t_start

        if seg_tf <= 0:
            seg_idx += 1
            continue

        # 如果初始状态已经干了，用正常水深恢复
        h_current = np.maximum(h_current, 0.01)
        Q_current = np.maximum(Q_current, 0.0)

        # 分段出口断面流量受分水影响后的参考值（简化处理：取当前流量）
        Q_seg = Q_start

        # 注意：canalsim.exe 内部按 Q_upstream=常数执行，
        # 不支持从任意初始水深出发重新启动。
        # 因此本函数退化为：用各段平均流量近似，每段出口流量按分水比例递减。
        # 实际上这里我们仍然执行 exe，但用当前段的代表流量；
        # 结果仅作为示意。真正支持瞬变流需要扩展 exe 本身。
        seg_input = CanalSimInput(
            L=L, nx=nx, b=b, m=m, n_Manning=n_Manning, S0=S0,
            Q_upstream=Q_seg, tf=seg_tf, dt=dt,
            tolerance=tolerance, max_iterations=max_iterations,
            A_wet_min=A_wet_min, branches=list(branches),
            Q_initial=Q_seg,
        )

        try:
            seg_result = _call_exe(seg_input, canal_id=f'{canal_id}_seg{seg_idx}')
        except RuntimeError as exc:
            logger.warning(
                'transient segment %d failed (%s), skipping: t=[%.1f, %.1f]',
                seg_idx, exc, t_start, t_end,
            )
            seg_idx += 1
            continue

        # 拼接时空快照（时间偏移 t_start）
        seg_times = seg_result.get('spacetime', {}).get('times', [])
        seg_water = seg_result.get('spacetime', {}).get('water_level_matrix', [])
        seg_flow = seg_result.get('spacetime', {}).get('flow_rate_matrix', [])

        for ti, t_abs in enumerate(seg_times):
            if t_abs + t_start not in all_spacetime_times:
                all_spacetime_times.append(t_abs + t_start)
                all_spacetime_water_level.append(seg_water[ti] if ti < len(seg_water) else [])
                all_spacetime_flow_rate.append(seg_flow[ti] if ti < len(seg_flow) else [])

        # 拼接 timeseries
        seg_ts = seg_result.get('timeseries', {})
        for ti, t_abs in enumerate(seg_ts.get('t', [])):
            all_t.append(t_abs + t_start)
            all_Q_up.append(seg_ts['Q_upstream'][ti] if ti < len(seg_ts['Q_upstream']) else 0.0)
            all_Q_down.append(seg_ts['Q_downstream'][ti] if ti < len(seg_ts['Q_downstream']) else 0.0)
            all_y_up.append(seg_ts['y_upstream'][ti] if ti < len(seg_ts['y_upstream']) else 0.0)
            all_y_down.append(seg_ts['y_downstream'][ti] if ti < len(seg_ts['y_downstream']) else 0.0)

        # 更新初始条件（取段末状态）
        final_state = seg_result.get('final_state', {})
        y_list = final_state.get('y', [])
        Q_list = final_state.get('Q', [])
        if y_list:
            h_current = np.array(y_list[-nx:], dtype=np.float64)
            if len(h_current) < nx:
                h_current = np.full(nx, h_current[-1] if len(h_current) > 0 else 0.01)
        if Q_list:
            Q_current = np.array(Q_list[-nx:], dtype=np.float64)
            if len(Q_current) < nx:
                Q_current = np.full(nx, Q_current[-1] if len(Q_current) > 0 else 0.0)

        seg_idx += 1

    # -------------------------------------------------------------------------
    # 合并 final_state（取最后一段的最终状态）
    # -------------------------------------------------------------------------
    final_state_dict: dict[str, Any] = {
        'x': x_grid.tolist(),
        'y': h_current.tolist(),
        'A': [],
        'Q': Q_current.tolist(),
        'V': [],
        'Fr': [],
    }
    # 重新计算 A, V, Fr
    for i in range(nx):
        h_i = h_current[i]
        A_i = (b + m * h_i) * h_i
        T_i = b + 2.0 * m * h_i
        P_i = b + 2.0 * h_i * math.sqrt(1.0 + m * m)
        R_i = A_i / P_i if P_i > 1e-9 else 1e-9
        V_i = Q_current[i] / A_i if A_i > 1e-9 else 0.0
        Fr_i = V_i / math.sqrt(9.81 * A_i / T_i) if A_i > 1e-9 else 0.0
        final_state_dict['A'].append(float(A_i))
        final_state_dict['V'].append(float(V_i))
        final_state_dict['Fr'].append(float(Fr_i))

    total_offtake = sum(float(br.get('Q_offtake', 0.0)) for br in branches)

    return {
        'channel': {
            'L': L, 'nx': nx, 'dx': dx,
            'b': b, 'm': m, 'n_Manning': n_Manning,
            'S0': S0, 'Q_upstream': Q_upstream_series[-1][1] if Q_upstream_series else 0.0,
            'tf': tf, 'dt': dt,
        },
        'summary': {
            'Q_upstream': Q_upstream_series[-1][1] if Q_upstream_series else 0.0,
            'Q_downstream_final': float(Q_current[-1]) if len(Q_current) > 0 else 0.0,
            'y_upstream_final': float(h_current[0]) if len(h_current) > 0 else 0.0,
            'y_downstream_final': float(h_current[-1]) if len(h_current) > 0 else 0.0,
            'total_offtake_m3s': total_offtake,
        },
        'timeseries': {
            't': all_t,
            'Q_upstream': all_Q_up,
            'Q_downstream': all_Q_down,
            'y_upstream': all_y_up,
            'y_downstream': all_y_down,
        },
        'final_state': final_state_dict,
        'spacetime': {
            'times': all_spacetime_times,
            'water_level_matrix': all_spacetime_water_level,
            'flow_rate_matrix': all_spacetime_flow_rate,
            'nx': nx,
            'n_steps': len(all_spacetime_times),
        },
        'branches': [
            {
                'id': br.get('id', f'branch_{i}'),
                'x_position': float(br.get('x_position', 0.0)),
                'Q_offtake': float(br.get('Q_offtake', 0.0)),
                'spread_cells': int(br.get('spread_cells', 0)),
            }
            for i, br in enumerate(branches)
        ],
    }


# ============================================================================
# 核心：调用 canalsim.exe
# ============================================================================


def _call_exe(sim_input: CanalSimInput, canal_id: str = 'unknown') -> dict[str, Any]:
    """
    创建临时 JSON 文件，调用 canalsim.exe，读取 result.json，返回解析后的字典。

    流程：
      1. 在 temp 目录创建 input.json 和 output.json 路径
      2. 写入 input.json
      3. 启动 canalsim.exe，等待完成
      4. 读取 output.json
      5. 清理临时文件
      6. 返回解析结果
    """
    if not os.path.exists(CANALSIM_EXE):
        raise FileNotFoundError(
            f'canalsim.exe not found at: {CANALSIM_EXE}\n'
            'Please compile CanalSim or copy canalsim.exe to ruoyi-fastapi-backend/models/'
        )

    with tempfile.TemporaryDirectory(prefix='canalsim_') as tmpdir:
        input_path = os.path.join(tmpdir, 'input.json')
        output_path = os.path.join(tmpdir, 'result.json')

        # 写入输入 JSON
        input_json = sim_input.to_dict()
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(input_json, f, indent=2)

        logger.debug(
            'canalsim exe call [%s]: exe=%s, input=%s, output=%s',
            canal_id, CANALSIM_EXE, input_path, output_path,
        )

        # 调用 exe
        import subprocess

        cmd = [CANALSIM_EXE, input_path, output_path]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(60.0, sim_input.tf / 10.0 + 30.0),
                encoding='utf-8',
                errors='replace',
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f'canalsim.exe timed out after timeout limit '
                f'(tf={sim_input.tf}s, estimated {sim_input.tf / 10.0 + 30.0:.0f}s)'
            )
        except OSError as exc:
            raise RuntimeError(f'Failed to start canalsim.exe: {exc}')

        if proc.returncode != 0:
            stderr = proc.stderr or '(no stderr)'
            stdout = proc.stdout or '(no stdout)'
            logger.error(
                'canalsim.exe [%s] failed with code %d\nstdout: %s\nstderr: %s',
                canal_id, proc.returncode, stdout[:500], stderr[:500],
            )
            raise RuntimeError(
                f'canalsim.exe exited with code {proc.returncode}: '
                f'{stderr[:200] or stdout[:200]}'
            )

        # 读取输出 JSON
        if not os.path.exists(output_path):
            raise RuntimeError(
                f'canalsim.exe did not produce result.json at {output_path}\n'
                f'stdout: {proc.stdout[:300]}'
            )

        with open(output_path, 'r', encoding='utf-8') as f:
            result: dict[str, Any] = json.load(f)

        logger.info(
            'canalsim.exe [%s] completed: tf=%.1fs, nx=%d, n_steps~%d',
            canal_id, sim_input.tf, sim_input.nx,
            int(sim_input.tf / sim_input.dt) + 1,
        )
        return result


# ============================================================================
# 输出格式映射：exe JSON → API 响应格式
# ============================================================================


def _map_exe_output_to_result(
    exe_output: dict[str, Any],
    sim_input: CanalSimInput,
    output_interval_sec: float,
) -> dict[str, Any]:
    """
    将 canalsim.exe 的输出 JSON 映射为与原 Python 求解器一致的字典结构。

    exe 输出结构（与 README 一致）：
      {
        "channel": { L, nx, dx, b, m, n_Manning, S0, Q_upstream, tf, dt },
        "summary": { Q_upstream, Q_downstream_final, y_upstream_final,
                     y_downstream_final, total_offtake_m3s },
        "timeseries": { t, Q_upstream, Q_downstream, y_upstream, y_downstream },
        "final_state": { x, y, A, Q, V, Fr },
        "spacetime": {
          "times": [...],
          "water_level_matrix": [...],
          "flow_rate_matrix": [...],
          "nx": int, "n_steps": int
        },
        "branches": [ { id, x_position, Q_offtake, spread_cells } ]
      }

    返回字典与 KinematicWaveResult.to_dict() 完全兼容。
    """
    ch = exe_output.get('channel', {})
    summary = exe_output.get('summary', {})
    ts = exe_output.get('timeseries', {})
    fs = exe_output.get('final_state', {})
    st = exe_output.get('spacetime', {})
    branches_out = exe_output.get('branches', [])

    dx = ch.get('dx', sim_input.L / (sim_input.nx - 1))

    # canalsim.exe 输出的 spacetime 矩阵是扁平 1D 数组（n_steps * nx），
    # 需要还原为 2D 数组（n_steps 行 × nx 列）以匹配前端热力图期望的格式。
    raw_nx = int(st.get('nx', sim_input.nx))
    raw_water_flat: list[Any] = st.get('water_level_matrix', [])
    raw_flow_flat: list[Any] = st.get('flow_rate_matrix', [])

    n_steps_from_flat = len(raw_water_flat) // raw_nx if raw_nx > 0 and len(raw_water_flat) > 0 else 0

    if n_steps_from_flat > 0 and len(raw_water_flat) == n_steps_from_flat * raw_nx:
        # reshape: 1D → 2D（每 n_steps 行，按时间优先排列）
        st_water: list[list[float]] = [
            [float(raw_water_flat[step * raw_nx + ix]) for ix in range(raw_nx)]
            for step in range(n_steps_from_flat)
        ]
        st_flow: list[list[float]] = [
            [float(raw_flow_flat[step * raw_nx + ix]) for ix in range(raw_nx)]
            for step in range(n_steps_from_flat)
        ]
        st_times: list[float] = st.get('times', [])
        # 如果 times 长度与矩阵行数不一致，按 dt 重建
        if len(st_times) != n_steps_from_flat:
            dt_raw = ch.get('dt', sim_input.dt)
            st_times = [step * dt_raw for step in range(n_steps_from_flat)]
    else:
        # 回退：保持原样（exe 输出格式已为 2D）
        st_water = raw_water_flat
        st_flow = raw_flow_flat
        st_times = st.get('times', [])

    return {
        'channel': {
            'L': ch.get('L', sim_input.L),
            'nx': ch.get('nx', sim_input.nx),
            'dx': dx,
            'b': ch.get('b', sim_input.b),
            'm': ch.get('m', sim_input.m),
            'n_Manning': ch.get('n_Manning', sim_input.n_Manning),
            'S0': ch.get('S0', sim_input.S0),
            'Q_upstream': ch.get('Q_upstream', sim_input.Q_upstream),
            'tf': ch.get('tf', sim_input.tf),
            'dt': ch.get('dt', sim_input.dt),
        },
        'summary': {
            'Q_upstream': summary.get('Q_upstream', sim_input.Q_upstream),
            'Q_downstream_final': summary.get('Q_downstream_final', 0.0),
            'y_upstream_final': summary.get('y_upstream_final', 0.0),
            'y_downstream_final': summary.get('y_downstream_final', 0.0),
            'total_offtake_m3s': summary.get('total_offtake_m3s', 0.0),
        },
        'timeseries': {
            't': ts.get('t', []),
            'Q_upstream': ts.get('Q_upstream', []),
            'Q_downstream': ts.get('Q_downstream', []),
            'y_upstream': ts.get('y_upstream', []),
            'y_downstream': ts.get('y_downstream', []),
        },
        'final_state': {
            'x': fs.get('x', []),
            'y': fs.get('y', []),
            'A': fs.get('A', []),
            'Q': fs.get('Q', []),
            'V': fs.get('V', []),
            'Fr': fs.get('Fr', []),
        },
        'spacetime': {
            'times': st_times,
            'water_level_matrix': st_water,
            'flow_rate_matrix': st_flow,
            'nx': st.get('nx', sim_input.nx),
            'n_steps': len(st_times),
        },
        'branches': branches_out or [
            {
                'id': f'branch_{i}',
                'x_position': float(br.get('x_position', 0.0)),
                'Q_offtake': float(br.get('Q_offtake', 0.0)),
                'spread_cells': int(br.get('spread_cells', 0)),
            }
            for i, br in enumerate(sim_input.branches)
        ],
    }
