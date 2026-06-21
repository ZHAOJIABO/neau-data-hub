# CanalSim

一维灌区梯形渠道非恒定流水动力模拟器。

基于**运动波（Kinematic Wave）**物理模型，采用**隐式迎风有限差分**格式，通过 **Picard 迭代**线性化 Manning 摩阻项并用三对角矩阵追赶法（Thomas 算法）求解，支持旁侧支渠分水的时空分布模拟。

---

## 核心特性

- **数值方法**：隐式迎风格式 + Thomas 追赶法（无条件稳定）
- **物理模型**：Kinematic Wave（连续方程 + Manning 公式）
- **支渠取水**：三角形权重空间分布，支持任意多点分水
- **边界条件**：上游 Dirichlet 定流量，下游零流量出流
- **输出格式**：`result.json` 含时空快照矩阵、时程序列、沿程最终状态
- **可视化**：Python 脚本生成 3D 时空曲面 + 时程曲线 + 沿程剖面

---

## 项目结构

```
CanalSim/
├── README.md                    本文件
├── SPEC.md                      数学模型与数值格式详细说明
├── CMakeLists.txt               CMake 构建配置
├── Makefile                     快速构建（g++）
├── canalsim.exe                 Windows 可执行文件
│
├── src/
│   ├── main.cpp                主程序、时间循环、I/O、进度条
│   ├── Channel.cpp             渠道几何、Manning、水深反算、边界条件
│   ├── Solver.cpp              运动波求解器（迎风格式 + Picard + Thomas）
│   ├── ConfigIO.cpp            JSON 输入解析 / 结果序列化
│   └── Output.cpp              时空快照缓冲器
│
├── include/
│   ├── Channel.h               渠道配置、Cell 结构、几何函数
│   ├── Solver.h                求解器配置与接口
│   ├── ConfigIO.h              JSON 序列化接口
│   ├── Branch.h                支渠取水网络（三角形分布）
│   └── Output.h                输出缓冲器接口
│
├── configs/
│   └── example_input.json      示例配置（L=5000m，5处分水，Q=15m³/s）
│
├── runs/demo/                   运行示例
│   ├── input.json              示例输入
│   ├── result.json             模拟输出
│   ├── water_level_3d.png     水深时空 3D 曲面
│   ├── flow_rate_3d.png       流量时空 3D 曲面
│   ├── timeseries.png          上下游水位/流量时程曲线
│   └── profile_final.png       最终水面线沿程剖面
│
└── python/
    ├── canalsim_client.py       Python 封装（直接传入 dict 调用模拟）
    └── plot_result.py           可视化脚本（读取 result.json 生成图表）
```

---

## 编译

### 方式一：Make（推荐，Windows/macOS/Linux）

```bash
make
```

或指定编译器：

```bash
g++ -std=c++17 -Wall -O2 -I include src/main.cpp src/Channel.cpp src/Solver.cpp src/ConfigIO.cpp src/Output.cpp -o canalsim.exe
```

### 方式二：CMake

```bash
mkdir build && cd build
cmake ..
cmake --build .
```

输出文件 `canalsim.exe`（Windows）或 `canalsim`（Linux/macOS）位于项目根目录。

---

## 运行

### 直接运行（CLI）

```bash
./canalsim.exe configs/example_input.json runs/demo/result.json
```

### Python 调用

```python
from canalsim_client import run

cfg = {
    "channel": {
        "L": 5000, "nx": 51, "b": 5.0, "m": 1.5,
        "n_Manning": 0.025, "S0": 0.0003,
        "Q_upstream": 15.0, "tf": 3600.0, "dt": 30.0
    },
    "solver": {"tolerance": 1e-6, "max_iterations": 100},
    "branches": [
        {"x_position": 1000.0, "Q_offtake": 3.0, "spread_cells": 2},
        {"x_position": 2000.0, "Q_offtake": 3.0, "spread_cells": 2},
    ]
}

result = run(cfg, workdir="runs/demo")
print(result["summary"])
```

### 生成可视化图表

```bash
python python/plot_result.py runs/demo/result.json runs/demo
```

输出 4 张图：`water_level_3d.png`、`flow_rate_3d.png`、`timeseries.png`、`profile_final.png`。

---

## 配置文件说明

`configs/example_input.json` 字段：

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `channel.L` | float | 渠道长度 (m) | **必填** |
| `channel.nx` | int | 空间格点数 | **必填** |
| `channel.tf` | float | 模拟总时长 (s) | **必填** |
| `channel.dt` | float | 时间步长 (s) | **必填** |
| `channel.b` | float | 底宽 (m) | 10.0 |
| `channel.m` | float | 边坡系数 (水平:垂直) | 1.5 |
| `channel.n_Manning` | float | Manning 粗糙系数 | 0.013 |
| `channel.S0` | float | 底坡 | 0.0001 |
| `channel.Q_upstream` | float | 上游恒定来流量 (m³/s) | 50.0 |
| `channel.Q_initial` | float | 初始均匀流流量；0 = 用 Q_upstream | 0.0 |
| `channel.A_wet_min` | float | 下游湿地面积下限 (m²)，防数值下溢 | 0.1 |
| `solver.tolerance` | float | Picard 迭代收敛容差（面积增量最大值） | 1e-6 |
| `solver.max_iterations` | int | 最大 Picard 迭代次数 | 100 |
| `branches[].x_position` | float | 分水口里程 (m) | **必填** |
| `branches[].Q_offtake` | float | 分水流量 (m³/s) | **必填** |
| `branches[].spread_cells` | int | 分水影响半径（±格点数） | 2 |

> `solver.theta` 字段保留但不使用（Kinematic Wave 为纯隐式迎风格式，无 Preissmann 权重参数）。

---

## result.json 输出结构

```json
{
  "channel":  { "L", "nx", "dx", "b", "m", "n_Manning", "S0", "Q_upstream", "tf", "dt" },
  "summary":  { "Q_upstream", "Q_downstream_final", "y_upstream_final", "y_downstream_final", "total_offtake_m3s" },
  "timeseries":  { "t", "Q_upstream", "Q_downstream", "y_upstream", "y_downstream" },
  "final_state":  { "x", "y", "A", "Q", "V", "Fr" },
  "spacetime":  {
    "times": [...],
    "water_level_matrix": [...],   // [nSteps × nx] 展平数组
    "flow_rate_matrix":   [...],   // [nSteps × nx] 展平数组
    "nx": 51, "n_steps": 61
  },
  "branches": [ { "id", "x_position", "Q_offtake", "spread_cells" } ]
}
```

---

## 物理模型说明

本求解器使用 **Kinematic Wave（运动波）** 近似：

$$\frac{\partial A}{\partial t} + \frac{\partial Q}{\partial x} = -q_L(x), \qquad Q = \frac{1}{n} A R^{2/3} \sqrt{S_0}$$

与完整 Saint-Venant 方程组的区别：忽略了动量方程中的惯性项 \(gA\partial Z/\partial x\) 和对流项 \(\partial(\beta Q^2/A)/\partial x\)。因此：

- **适用**：坡度平缓、变化缓慢的渠道明渠流（如灌区干渠、支渠）
- **不适用**：有回水影响、快速水力过渡（水闸快速启闭）、缓流/急流过渡的模拟

如需上述能力，需升级为完整 Preissmann 隐式格式求解器（Kinematic Wave → Diffusion Wave → Dynamic Wave 进阶路线）。

---

## 依赖

**C++ 端**
- C++17 编译器（g++ / clang++ / MSVC）
- [nlohmann/json](https://github.com/nlohmann/json)（header-only，已包含在 `include/`）

**Python 端**（可选，用于可视化）
- Python 3.8+
- `matplotlib`, `numpy`
