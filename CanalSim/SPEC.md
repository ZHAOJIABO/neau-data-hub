# CanalSim - 灌区梯形渠道水动力模拟

## 1. Project Overview

**项目名称**: CanalSim
**类型**: 水力学数值模拟 / 科学计算
**核心功能**: 使用**运动波近似（Kinematic Wave Approximation）**对梯形渠道进行一维非恒定流水动力模拟。采用隐式线性化有限差分格式，配合三对角矩阵追赶法求解，产生完整的时空分布结果并通过 Python 脚本渲染三维可视化图表。
**目标用户**: 水利工程研究人员、灌区管理人员

> **注意**：当前实现的是 Kinematic Wave 模型，仅包含连续方程（质量守恒）和 Manning 阻力公式。与完整 Saint-Venant 方程的区别在于忽略动量方程中的惯性项 $gA\\partial Z/\\partial x$ 和对流项，**不能**模拟回水曲线向上游传播、闸门快速启闭的水面波动、或缓流/急流过渡现象。如需上述能力，需升级为完整 Preissmann 求解器。

---

## 2. Physical & Mathematical Model

### 2.1 Kinematic Wave 方程组

**连续方程（质量守恒）**:
$$\frac{\partial A}{\partial t} + \frac{\partial Q}{\partial x} = -q_L(x)$$

其中 $q_L(x)$ 为单位长度旁侧取水流量（m³/s/m），来自支渠分水口。

**Manning 状态方程**:
$$Q = \frac{1}{n} A R^{2/3} \sqrt{S_0}$$

其中 $S_0$ 为底坡（Kinematic Wave 中 $S_f \\approx S_0$，即假设阻力坡降与底坡近似相等）。

与完整 Saint-Venant 相比，Kinematic Wave 省略了：

- 动量方程中的惯性项 $\\frac{\partial Q}{\partial t}$
- 对流项 $\\frac{\partial}{\partial x}(\\beta Q^2/A)$
- 压力项 $gA\\frac{\partial Z}{\partial x}$
- 变摩擦项 $gA(S_f - S_0)$ 中 $S_f \\neq S_0$ 的部分

### 2.2 梯形断面几何

```
         B_full
|<------------->|
  \            /
   \          /
    \        /
     \      /
      \    /
       \  /
        \/
       b_bottom

- 底宽: b
- 边坡系数: m (水平:垂直)
- 水深: y
- 过水面积: A = (b + my)y
- 水面宽: B = b + 2my
- 湿周: P = b + 2y√(1+m²)
```

### 2.3 Manning 阻力公式

$$Q = \frac{1}{n} A R^{2/3} \sqrt{S_0}, \quad R = \frac{A}{P}$$

---

## 3. Numerical Scheme

### 3.1 隐式线性化有限差分

对连续方程进行迎风差分离散（第 i 个内格点）:

$$\frac{A_i^{n+1} - A_i^n}{\Delta t} + \frac{Q_i^{n+1} - Q_{i-1}^{n+1}}{\Delta x} = -q_{L,i}$$

将 $Q_i^{n+1}$ 用 Manning 公式线性化（Picard 迭代）：

$$Q(A) \approx Q(A^*) + \frac{dQ}{dA}\Big|_{A^*} \cdot (A - A^*)$$

得到三对角方程组：

$$a_i \\delta A_{i-1}^{n+1} + b_i \\delta A_i^{n+1} + c_i \\delta A_{i+1}^{n+1} = d_i$$

其中 Jacobian 系数：

$$a_i = -\\frac{1}{2\\Delta x}\\frac{dQ}{dA}\Big|_{i-1}, \quad c_i = +\\frac{1}{2\\Delta x}\\frac{dQ}{dA}\Big|_{i+1}, \quad b_i = \\frac{1}{\\Delta t}$$

$dQ/dA$ 通过数值微分计算。

### 3.2 旁侧取水的三角形分布

每条支渠分水口的取水量 $Q_{offtake}$ 在其中心格点 $\\pm s$ 范围内按三角形分布：

$$\\text{权重}_j = (s+1) - |j - c|, \quad q_{L,j} = \\frac{\\text{权重}_j}{(s+1)^2 \\Delta x} Q_{offtake}$$

其中 $s = \\max(1, \\text{spread\\_cells})$，默认 $s=2$。该分布保证 $\\sum_j q_{L,j} \\Delta x = Q_{offtake}$。

### 3.3 三对角矩阵求解（Thomas 算法）

追赶法分为两步：
1. **消元步**：从上游到下游，依次消去下标较小的未知量
2. **回代步**：从下游到上游，依次求得所有格点的面积增量 $\\delta A$

---

## 4. Boundary Conditions

### 4.1 上游边界（Dirichlet，恒定入流）

$$Q(0,t) = Q_{in} = \\text{const}$$
$$A_0^{n+1} = A(y_{normal}(Q_{in}))$$

第一格点的面积增量固定为 $\\delta A_0 = 0$（由三对角系统嵌入），面积值由 Manning 反算保持与给定 $Q_{in}$ 的一致。

### 4.2 下游边界（零流量出流）

$$Q(L,t) = 0$$

即 $\\frac{\\partial Q}{\\partial x} = 0$。在离散方程中体现为：

$$\\frac{A_{N-1}^{n+1} - A_{N-1}^n}{\\Delta t} + q_{L,N-1} = 0$$

> 当 $\\sum Q_{offtake} = Q_{in}$ 时（总取水量等于上游来量），下游自然无出流，该边界条件物理闭合。

---

## 5. Simulation Parameters

| 参数 | 符号 | 典型值 | 单位 |
|------|------|--------|------|
| 渠道长度 | L | 5000 | m |
| 底宽 | b | 5 | m |
| 边坡系数 | m | 1.5 | - |
| Manning 粗糙系数 | n | 0.025 | s/m^(1/3) |
| 底坡 | S₀ | 0.0003 | - |
| 空间步长 | Δx | 100 | m |
| 时间步长 | Δt | 30 | s |
| 迭代收敛容差 | tol | 1e-6 | m² |
| 最大迭代次数 | max_iter | 100 | - |
| 模拟时长 | tf | 3600 | s |
| 上游来流量 | Q_in | 15 | m³/s |
| 初始流量 | Q₀ | 10 | m³/s |

---

## 6. Output Files

| 文件 | 内容 |
|------|------|
| `result.json` | 完整结果：时空快照矩阵（water_level_matrix, flow_rate_matrix）、时程序列（timeseries）、最终断面状态（final_state）、摘要统计（summary）、支渠配置（branches） |

---

## 7. Visualization (Python 3D Plots)

运行 `python python/plot_result.py [result.json] [output_dir]` 生成以下图表：

### 7.1 水位时空 3D 曲面图 (water_level_3d.png)
- X 轴：距离 (km)
- Y 轴：时间 (h)
- Z 轴：水深 y (m)
- 颜色：水深热力图

### 7.2 流量时空 3D 曲面图 (flow_rate_3d.png)
- X 轴：距离 (km)
- Y 轴：时间 (h)
- Z 轴：流量 Q (m³/s)
- 颜色：流量热力图

### 7.3 时程曲线图 (timeseries.png)
- 上图：上下游流量随时间变化
- 下图：上下游水深随时间变化

### 7.4 最终水面线剖面图 (profile_final.png)
- 沿程水面线与渠底剖面
- 标注支渠分水口位置

---

## 8. Build System

- **C++ 编译器**: g++ (MinGW) with C++17
- **构建工具**: CMake + Make
- **依赖**: 仅标准库 + nlohmann/json (header-only)
- **Python**: matplotlib, numpy (for visualization)

---

## 9. Project Structure

```
CanalSim/
├── SPEC.md
├── CMakeLists.txt / Makefile
├── canalsim.exe
├── src/
│   ├── main.cpp           # 主程序、I/O、时间循环
│   ├── Channel.cpp        # 渠道几何、断面计算、Manning 公式
│   ├── Solver.cpp         # Kinematic Wave 隐式求解器（三对角）
│   ├── ConfigIO.cpp       # JSON 输入输出
│   └── Output.cpp         # 时空快照缓冲器
├── include/
│   ├── Channel.h
│   ├── Solver.h
│   ├── ConfigIO.h
│   ├── Branch.h           # 支渠取水网络
│   └── Output.h
├── configs/
│   └── example_input.json
├── runs/
│   └── demo/
│       ├── input.json
│       └── result.json    # 模拟输出
└── python/
    ├── canalsim_client.py  # Python 调用封装
    └── plot_result.py     # 可视化脚本
```

---

## 10. Acceptance Criteria

1. C++ 代码编译无错误（允许未使用参数警告）
2. 模拟程序运行完成，输出 `result.json`
3. `result.json` 包含 `spacetime` 字段（含时空快照矩阵）
4. 上游流量恒定为 $Q_{in}$，下游流量 $\\to 0$（当 $\\sum Q_{offtake} = Q_{in}$）
5. 水深时程曲线平滑连续，无锯齿震荡
6. `python python/plot_result.py` 成功生成全部 4 张可视化图
7. 水面线沿程单调递减（缓流），无物理不合理振荡
