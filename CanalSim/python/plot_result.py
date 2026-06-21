"""
plot_result.py - 从 result.json 读取模拟结果并生成可视化图表

用法:
    python python/plot_result.py
        (默认读取 runs/demo/result.json, 输出到 runs/demo/)

    python python/plot_result.py runs/demo/result.json runs/demo/
        (指定输入文件和输出目录)

输出:
    - water_level_3d.png   水位时空3D曲面图
    - flow_rate_3d.png     流量时空3D曲面图
    - timeseries.png       上下游水位/流量时程曲线
    - profile_final.png    最终时刻水面线沿程剖面图
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Windows 上使用非交互后端避免 tkinter 弹窗
matplotlib.use("Agg")

# 中文字体
try:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "WenQuanYi Micro Hei", "DejaVu Sans"
    ]
except Exception:
    pass
plt.rcParams["axes.unicode_minus"] = False


def load_result(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"result.json not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def reshape_matrix(flat: list, nx: int, n_steps: int) -> np.ndarray:
    """将展平的 [n_steps * nx] 数组变回 [n_steps, nx] 矩阵"""
    return np.array(flat, dtype=float).reshape(n_steps, nx)


def x_grid(L: float, nx: int) -> np.ndarray:
    return np.linspace(0, L, nx)


def plot_water_level_3d(ax, result: dict):
    """3D 水位时空曲面图"""
    st = result["spacetime"]
    ch = result["channel"]
    L, nx = ch["L"], ch["nx"]
    n_steps = st["n_steps"]

    if n_steps < 2 or nx < 2:
        ax.text(0.5, 0.5, "No spacetime data", transform=ax.transAxes, ha="center")
        return

    wl = reshape_matrix(st["water_level_matrix"], nx, n_steps)
    X = x_grid(L, nx)
    T = np.array(st["times"])
    X2d, T2d = np.meshgrid(X, T)

    surf = ax.plot_surface(
        X2d / 1000, T2d / 3600, wl,
        cmap="Blues", alpha=0.85, linewidth=0, antialiased=True,
    )
    ax.set_xlabel("x (km)", fontsize=11)
    ax.set_ylabel("t (h)", fontsize=11)
    ax.set_zlabel("Water depth y (m)", fontsize=11)
    ax.set_title("Water Depth Spacetime Surface", fontsize=13, pad=12)
    ax.view_init(elev=25, azim=230)
    plt.colorbar(surf, ax=ax, shrink=0.5, label="y (m)")


def plot_flow_rate_3d(ax, result: dict):
    """3D 流量时空曲面图"""
    st = result["spacetime"]
    ch = result["channel"]
    L, nx = ch["L"], ch["nx"]
    n_steps = st["n_steps"]

    if n_steps < 2 or nx < 2:
        ax.text(0.5, 0.5, "No spacetime data", transform=ax.transAxes, ha="center")
        return

    Q = reshape_matrix(st["flow_rate_matrix"], nx, n_steps)
    X = x_grid(L, nx)
    T = np.array(st["times"])
    X2d, T2d = np.meshgrid(X, T)

    surf = ax.plot_surface(
        X2d / 1000, T2d / 3600, Q,
        cmap="YlOrRd", alpha=0.85, linewidth=0, antialiased=True,
    )
    ax.set_xlabel("x (km)", fontsize=11)
    ax.set_ylabel("t (h)", fontsize=11)
    ax.set_zlabel("Flow rate Q (m3/s)", fontsize=11)
    ax.set_title("Flow Rate Spacetime Surface", fontsize=13, pad=12)
    ax.view_init(elev=25, azim=230)
    plt.colorbar(surf, ax=ax, shrink=0.5, label="Q (m3/s)")


def plot_timeseries(ax1, ax2, result: dict):
    """上下游水位 / 流量时程曲线"""
    ts = result["timeseries"]
    t = np.array(ts["t"]) / 3600   # 转小时
    Q_up   = np.array(ts["Q_upstream"])
    Q_down = np.array(ts["Q_downstream"])
    y_up   = np.array(ts["y_upstream"])
    y_down = np.array(ts["y_downstream"])

    color_Q_up   = "#2196F3"
    color_Q_down = "#F44336"
    color_y_up   = "#4CAF50"
    color_y_down = "#FF9800"

    ax1.plot(t, Q_up,   color=color_Q_up,   lw=1.8, label="Q upstream")
    ax1.plot(t, Q_down, color=color_Q_down, lw=1.8, label="Q downstream")
    ax1.axhline(y=result["summary"]["total_offtake_m3s"],
                 color="gray", lw=1, ls="--", label=f"Total offtake ({result['summary']['total_offtake_m3s']} m3/s)")
    ax1.set_xlabel("t (h)", fontsize=11)
    ax1.set_ylabel("Q (m3/s)", fontsize=11)
    ax1.set_title("Flow Rate Time Series", fontsize=13)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, t[-1])

    ax2.plot(t, y_up,   color=color_y_up,   lw=1.8, label="y upstream")
    ax2.plot(t, y_down, color=color_y_down, lw=1.8, label="y downstream")
    ax2.set_xlabel("t (h)", fontsize=11)
    ax2.set_ylabel("Water depth y (m)", fontsize=11)
    ax2.set_title("Water Depth Time Series", fontsize=13)
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, t[-1])


def plot_profile_final(ax, result: dict):
    """最终时刻水面线沿程剖面图"""
    fs = result["final_state"]
    ch = result["channel"]
    branches = result.get("branches", [])

    x  = np.array(fs["x"])
    y  = np.array(fs["y"])
    Q  = np.array(fs["Q"])
    L  = ch["L"]

    # 渠道底板 = z(x)
    z = ch["S0"] * (L - x)

    ax.fill_between(x / 1000, z, y + z, color="#90CAF9", alpha=0.4, label="Water body")
    ax.plot(x / 1000, y + z, "b-", lw=2.0, label="Water surface")
    ax.plot(x / 1000, z,       "k-", lw=1.5, label="Channel bed")
    ax.fill_between(x / 1000, 0, z, color="#BCAAA4", alpha=0.4, label="Channel fill")

    # 支渠分水口
    for br in branches:
        xb = br["x_position"]
        yb = np.interp(xb, x, y)
        zb = ch["S0"] * (L - xb)
        ax.axvline(x=xb / 1000, color="red", lw=1, ls="--", alpha=0.7)
        ax.annotate(
            f'Offtake\nQ={br["Q_offtake"]}m3/s',
            xy=(xb / 1000, yb + zb),
            xytext=(xb / 1000 + 0.1, (yb + zb) * 1.1),
            fontsize=8, color="red",
            arrowprops=dict(arrowstyle="->", color="red", lw=0.8),
        )

    ax.set_xlabel("x (km)", fontsize=11)
    ax.set_ylabel("Elevation (m)", fontsize=11)
    ax.set_title("Final Water Surface Profile (t=tf)", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)


def plot_all(result: dict, out_dir: Path):
    """生成全部图表"""
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Generating water_level_3d.png ...")
    fig = plt.figure(figsize=(10, 7))
    plot_water_level_3d(fig.add_subplot(111, projection="3d"), result)
    fig.tight_layout()
    fig.savefig(out_dir / "water_level_3d.png", dpi=150)
    plt.close(fig)

    print(f"  Generating flow_rate_3d.png ...")
    fig = plt.figure(figsize=(10, 7))
    plot_flow_rate_3d(fig.add_subplot(111, projection="3d"), result)
    fig.tight_layout()
    fig.savefig(out_dir / "flow_rate_3d.png", dpi=150)
    plt.close(fig)

    print(f"  Generating timeseries.png ...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    plot_timeseries(ax1, ax2, result)
    fig.tight_layout()
    fig.savefig(out_dir / "timeseries.png", dpi=150)
    plt.close(fig)

    print(f"  Generating profile_final.png ...")
    fig, ax = plt.subplots(figsize=(12, 5))
    plot_profile_final(ax, result)
    fig.tight_layout()
    fig.savefig(out_dir / "profile_final.png", dpi=150)
    plt.close(fig)

    print(f"\n  All plots saved to {out_dir}")


def main() -> int:
    if len(sys.argv) >= 3:
        result_path = Path(sys.argv[1])
        out_dir     = Path(sys.argv[2])
    elif len(sys.argv) == 2:
        result_path = Path(sys.argv[1])
        out_dir     = result_path.parent
    else:
        result_path = Path(__file__).resolve().parent.parent / "runs" / "demo" / "result.json"
        out_dir     = result_path.parent

    print(f"Loading: {result_path}")
    result = load_result(result_path)

    summary = result.get("summary", {})
    print(f"  Channel: L={result['channel']['L']}m, nx={result['channel']['nx']}, tf={result['channel']['tf']/3600:.1f}h")
    print(f"  Q_up={summary.get('Q_upstream', '?')} m3/s,  Q_down_final={summary.get('Q_downstream_final', '?')} m3/s")
    print(f"  y_up_final={summary.get('y_upstream_final', '?'):.3f}m,  y_down_final={summary.get('y_downstream_final', '?'):.3f}m")
    st = result.get("spacetime", {})
    print(f"  Spacetime snapshots: {st.get('n_steps', 0)} steps x {st.get('nx', 0)} nodes")
    print(f"  Branches: {len(result.get('branches', []))}")
    print()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", matplotlib.MatplotlibDeprecationWarning)
        plot_all(result, out_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
