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
import math
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional

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
    theta: float = 0.5
    branches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        ch: dict[str, Any] = {
            'L': self.L,
            'nx': self.nx,
            'b': self.b,
            'm': self.m,
            'n_Manning': self.n_Manning,
            'S0': self.S0,
            'tf': self.tf,
            'dt': self.dt,
            'A_wet_min': self.A_wet_min,
            'Q_initial': self.Q_initial,
            'g': 9.81,
        }
        # Rating curve downstream BC
        if getattr(self, 'use_rating_curve', False):
            ch['use_rating_curve'] = True
            ch['y_ds_curve'] = getattr(self, 'y_ds_curve', [])
            ch['Q_ds_curve'] = getattr(self, 'Q_ds_curve', [])
            ch['Q_upstream'] = self.Q_upstream
        elif getattr(self, 'Q_upstream_series', None):
            ch['Q_upstream_series'] = self.Q_upstream_series
            ch['t_series'] = getattr(self, 't_series', [])
            ch['Q_upstream'] = self.Q_upstream
        else:
            ch['Q_upstream'] = self.Q_upstream

        return {
            'channel': ch,
            'solver': {
                'theta': getattr(self, 'theta', 0.5),
                'tolerance': self.tolerance,
                'max_iterations': self.max_iterations,
            },
            'branches': self.branches,
        }


def _area_topwidth(y: float, b: float, m: float) -> tuple[float, float]:
    A = (b + m * y) * y
    P = b + 2 * y * math.sqrt(1 + m * m)
    return A, P


def _manning_normal_depth(Q: float, b: float, m: float, n: float, S0: float) -> float:
    if Q <= 0 or n <= 0 or S0 <= 0:
        return 0.1
    lo, hi = 0.001, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        A, _ = _area_topwidth(mid, b, m)
        P = b + 2 * mid * math.sqrt(1 + m * m)
        R = A / P
        Qmid = A * math.pow(R, 2 / 3) * math.sqrt(S0) / n
        (lo := mid) if Qmid < Q else (hi := mid)
    return (lo + hi) / 2


def _generate_manning_rating_curve(
    b: float, m: float, n_Manning: float, S0: float, n_points: int = 20
) -> tuple[list[float], list[float]]:
    """用 Manning 公式自动生成下游 Q-y 曲线。"""
    if S0 <= 0 or n_Manning <= 0 or b <= 0:
        return [], []

    # 以设计流量 Q=10 m³/s 估算正常水深作为参考
    y0 = _manning_normal_depth(Q_upstream, b, m, n_Manning, S0)
    y_max = max(2.5 * y0, 0.5)
    Sf = math.sqrt(S0)

    ys, qs = [], []
    step = (y_max - 0.05) / max(n_points - 1, 1)
    for i in range(n_points):
        y = round(0.05 + i * step, 4)
        A, _ = _area_topwidth(y, b, m)
        P = b + 2 * y * math.sqrt(1 + m * m)
        R = A / P
        Q = round(A * math.pow(R, 2 / 3) * Sf / n_Manning, 4)
        ys.append(y)
        qs.append(Q)

    return ys, qs


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
    theta: float = 0.5,
    Q_initial: Optional[float] = None,
    use_rating_curve: bool = False,
    y_ds_curve: Optional[list[float]] = None,
    Q_ds_curve: Optional[list[float]] = None,
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
        output_interval_sec: 输出时间分辨率 (s)
        A_wet_min:        最小过水面积
        Q_upstream_series: 上游流量时序 [(t_sec, Q_m3s), ...]；exe 自身支持
        canal_id:          渠段编号（仅用于日志）
        theta:             迎风因子，默认 0.5（直接传给 exe solver）
        Q_initial:         初始均匀流流量，默认 Q_upstream
        use_rating_curve:  启用下游水位-流量关系曲线
        y_ds_curve:        下游水位曲线（m）
        Q_ds_curve:        下游流量曲线（m³/s）

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
    y_ds_curve = y_ds_curve or []
    Q_ds_curve = Q_ds_curve or []
    effective_Q_initial = Q_initial if Q_initial is not None else Q_upstream

    # -------------------------------------------------------------------------
    # 构建 CanalSimInput：exe 支持 Q_upstream_series 和 rating_curve 原生
    # -------------------------------------------------------------------------
    sim_input = CanalSimInput(
        L=L, nx=nx, b=b, m=m, n_Manning=n_Manning, S0=S0,
        Q_upstream=Q_upstream, Q_initial=effective_Q_initial,
        tf=tf, dt=dt,
        tolerance=tolerance, max_iterations=max_iterations,
        A_wet_min=A_wet_min, branches=list(branches),
        theta=theta,
    )
    # 注入非恒定流入或 rating curve
    if Q_upstream_series:
        sim_input.Q_upstream_series = [q for _, q in Q_upstream_series]
        sim_input.t_series = [t for t, _ in Q_upstream_series]
    if use_rating_curve and y_ds_curve and Q_ds_curve:
        sim_input.use_rating_curve = True
        sim_input.y_ds_curve = y_ds_curve
        sim_input.Q_ds_curve = Q_ds_curve
    elif use_rating_curve and (not y_ds_curve or not Q_ds_curve):
        # 前端仅传了 flag 未传曲线，自动用 Manning 生成兜底
        auto_y, auto_Q = _generate_manning_rating_curve(b, m, n_Manning, S0)
        sim_input.use_rating_curve = True
        sim_input.y_ds_curve = auto_y
        sim_input.Q_ds_curve = auto_Q
        logger.info(
            'rating_curve auto-generated: %d points, y=[%.4f, %.4f], Q=[%.4f, %.4f]',
            len(auto_y), auto_y[0], auto_y[-1], auto_Q[0], auto_Q[-1],
        )

    result_json = _call_exe(sim_input, canal_id=canal_id)
    return _map_exe_output_to_result(
        result_json, sim_input, output_interval_sec=output_interval_sec,
    )


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
    raw_nx = int(st.get('nx', sim_input.nx))
    raw_n_steps = int(st.get('n_steps', 0))
    raw_water_flat: list[Any] = st.get('water_level_matrix', [])
    raw_flow_flat: list[Any] = st.get('flow_rate_matrix', [])

    # new exe outputs spacetime as flat 1D arrays (n_steps * nx), not 2D lists.
    # Detect by checking if first element is a float (flat) or list (2D legacy format).
    if raw_n_steps > 0 and raw_nx > 0 and len(raw_water_flat) == raw_n_steps * raw_nx:
        # Reshape flat 1D → 2D (n_steps rows × nx cols), row-major order
        st_water: list[list[float]] = [
            [float(raw_water_flat[step * raw_nx + ix]) for ix in range(raw_nx)]
            for step in range(raw_n_steps)
        ]
        st_flow: list[list[float]] = [
            [float(raw_flow_flat[step * raw_nx + ix]) for ix in range(raw_nx)]
            for step in range(raw_n_steps)
        ]
        st_times: list[float] = st.get('times', [])
        if len(st_times) != raw_n_steps:
            dt_raw = ch.get('dt', sim_input.dt)
            st_times = [step * dt_raw for step in range(raw_n_steps)]
    elif raw_n_steps > 0 and len(raw_water_flat) > 0 and isinstance(raw_water_flat[0], list):
        # Legacy 2D list format already
        st_water = [[float(v) for v in row] for row in raw_water_flat]
        st_flow = [[float(v) for v in row] for row in raw_flow_flat]
        st_times = st.get('times', [])
    else:
        # Fallback: keep as-is
        st_water = raw_water_flat
        st_flow = raw_flow_flat
        st_times = st.get('times', [])
        raw_n_steps = len(st_water) if st_water else 0

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
