# 渠系优化配水与渠道水动力学模型接口文档

本文档面向外部系统调用。两个模型均提供标准 JSON 接口，调用方应在请求体中传入本次计算所需的渠道数据和模型参数；服务端数据库中的渠道数据仅作为平台内部页面和兼容接口的数据源。

## 通用约定

- Base URL: `http://<host>:<port>`
- 鉴权请求头: `X-Irrigation-Api-Key: irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY`
- 请求头: `Content-Type: application/json`
- 响应格式:

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": {}
}
```

## 渠道数据对象

标准接口中的 `canals` 或 `canal` 使用以下字段。字段名为 snake_case。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `canal_id` | string | 是 | 渠段编号（业务主键），命名规则：干渠 `1`、支渠 `1-1`、斗渠 `1-1-1`、农渠 `1-1-1-1`；`-` 分隔的段数等于 `level` |
| `canal_name` | string | 否 | 渠段名称 |
| `parent_id` | string/null | 否 | 父渠段编号；未传时按命名规则推断（去掉最后一段） |
| `level` | string | 否 | 渠段级别：`1` 干 / `2` 支 / `3` 斗 / `4` 农，或 `main` / `branch` / `lateral` / `farm` |
| `length` | number | 是 | 渠段长度，单位 m |
| `design_flow` | number | 是 | 设计流量，单位 m3/s |
| `design_depth` | number | 是 | 设计水深，单位 m |
| `top_width` | number | 否 | 设计渠顶宽，单位 m |
| `bottom_width` | number | 是 | 设计渠底宽，单位 m |
| `slope` | number | 是 | 设计纵坡，如 `0.0002` |
| `side_slope` | number | 是 | 边坡系数 `1:m` 中的 m |
| `roughness` | number | 是 | Manning 糙率 |
| `gate_height` | number | 否 | 闸门高度，单位 m |
| `gate_width` | number | 否 | 闸门宽度，单位 m |
| `min_gate_opening` | number | 否 | 闸门最小开度，单位 m |
| `max_gate_opening` | number | 否 | 闸门最大开度，单位 m |
| `water_demand` | number | 优化必填 | 单次配水需水量，单位 m3 |
| `inflow_series` | array/null | 水动力学必填 | 该渠段上游入流时序 `[{time_min, q_m3s}]`；未传时按恒定设计流量入流 |

可选 `topology` 用于显式指定父子关系：

```json
[
  { "canal_id": "1", "parent_id": null },
  { "canal_id": "1-1", "parent_id": "1" },
  { "canal_id": "1-1-1", "parent_id": "1-1" },
  { "canal_id": "1-1-1-1", "parent_id": "1-1-1" }
]
```

如果同时传 `parent_id` 和 `topology`，`topology` 中的关系优先。

## 0. 渠系拓扑查询

### 0.1 获取当前数据库渠系拓扑

`GET /api/v1/irrigation/canal/topology`

读取服务端加载的渠系数据，返回 `roots` / `nodes` / `edges`，供前端画树状拓扑。该接口使用服务端数据库中的渠道数据，不接受请求体。

响应 `data` 字段：

| 字段 | 说明 |
| --- | --- |
| `roots` | 根渠段 id 列表（数组长度为 1） |
| `nodes` | 节点数组：`id` / `name` / `level` / `length` / `design_flow` / `design_depth` / `water_demand` / `has_gate` |
| `edges` | 边数组：`from`（父） / `to`（子） / `length` / `Q_design` |

## 1. 渠系优化配水模型

### 1.1 全渠系三级优化

`POST /api/v1/irrigation/canal/optimize/full`

适用于干渠-支渠-斗渠三级顺序配水优化：先进行干-支连续配水优化，再对每个支渠下的斗渠进行轮灌分组优化。

请求体字段：

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `main_canal_id` | string | `1` | 干渠编号 |
| `canals` | array | 无 | 本次计算使用的完整渠道数据（干渠+支渠+斗渠） |
| `topology` | array/null | null | 可选显式拓扑 |
| `t_max` | number | `360.0` | 总输水时间上限，单位 h |
| `flow_ratio_min` | number | `0.8` | 斗渠配水流量/设计流量下限 |
| `flow_ratio_max` | number | `1.0` | 斗渠配水流量/设计流量上限 |
| `min_groups` | integer | `2` | 每个支渠下斗渠的候选最小分组数 |
| `max_groups` | integer | `6` | 每个支渠下斗渠的候选最大分组数 |
| `pop_size` | integer | `80` | NSGA-III 种群规模 |
| `n_gen` | integer | `60` | NSGA-III 迭代代数 |
| `seed` | integer | `1` | 随机种子 |
| `permeability_index` | number | `0.4` | 渠床土壤透水指数 |
| `permeability_coefficient` | number | `1.9` | 渠床土壤透水系数 |
| `pref_weight_time` | number | `0.4` | 总输水时间先验权重 |
| `pref_weight_loss` | number | `0.3` | 全渠系渗漏损失先验权重 |
| `pref_weight_flow_var` | number | `0.3` | 干渠流量波动先验权重 |
| `alpha` | number | `0.5` | 先验权重与熵权混合系数 |

请求示例：

```json
{
  "main_canal_id": "1",
  "canals": [
    {
      "canal_id": "1",
      "level": "1",
      "length": 3000,
      "design_flow": 8.0,
      "design_depth": 1.8,
      "bottom_width": 2.5,
      "slope": 0.0002,
      "side_slope": 1.5,
      "roughness": 0.015,
      "water_demand": 0
    },
    {
      "canal_id": "1-1",
      "parent_id": "1",
      "level": "2",
      "length": 1200,
      "design_flow": 2.4,
      "design_depth": 1.2,
      "bottom_width": 1.4,
      "slope": 0.0002,
      "side_slope": 1.5,
      "roughness": 0.015,
      "gate_height": 0.8,
      "gate_width": 1.2,
      "water_demand": 0
    },
    {
      "canal_id": "1-1-1",
      "parent_id": "1-1",
      "level": "3",
      "length": 600,
      "design_flow": 0.18,
      "design_depth": 0.5,
      "bottom_width": 0.5,
      "slope": 0.0003,
      "side_slope": 1.5,
      "roughness": 0.017,
      "water_demand": 4200
    },
    {
      "canal_id": "1-1-2",
      "parent_id": "1-1",
      "level": "3",
      "length": 720,
      "design_flow": 0.2,
      "design_depth": 0.55,
      "bottom_width": 0.55,
      "slope": 0.0003,
      "side_slope": 1.5,
      "roughness": 0.017,
      "water_demand": 5100
    }
  ],
  "t_max": 360,
  "flow_ratio_min": 0.8,
  "flow_ratio_max": 1.0,
  "pop_size": 150,
  "n_gen": 200,
  "min_groups": 2,
  "max_groups": 4
}
```

调用示例：

```bash
curl -X POST "http://8.146.227.98/api/v1/irrigation/canal/optimize/full" \
  -H "X-Irrigation-Api-Key: irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY" \
  -H "Content-Type: application/json" \
  -d @request.json
```

`data` 响应字段：

| 字段 | 说明 |
| --- | --- |
| `summary` | 模式、干渠编号、支渠数、斗渠总数、TOPSIS 评分、熵权、各级渗漏损失 |
| `main_schedule` | 干渠运行信息：开始时间、持续时间 |
| `branches` | 每条支渠的配水信息：设计流量、实际流量、起止时间、持续时间、损失 |
| `laterals` | 所有斗渠的轮灌配水信息：分组、实际流量、配水时长、起止时间、损失 |
| `pareto` | Pareto 解集，含 F1(时间)/F2(损失)/F3(流量波动)/score/selected |
| `topsis_summary` | 最优方案核心指标：总时间、总损失、干渠/支渠/斗渠损失、流量波动方差 |

## 2. 渠道水动力学模型

### 2.1 全渠系逐分钟水动力学仿真

`POST /api/v1/irrigation/canal/hydro/full/standard`

全渠系逐分钟水动力学仿真（节点连续耦合）。前端传入完整渠系数据 + 每条渠段的上游入流时序，后端按拓扑逐条做 MacCormack 显式 1D 圣维南方程仿真，并对每个父→子节点做流量连续性校验，最终返回每条渠段 (t, x, Q, h, V) 的展平时空序列，供前端动态展示。

请求体字段：

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `main_canal_id` | string | `1` | 干渠编号 |
| `canals` | array | 无 | 完整渠系数据（干+支+斗+农），每条 `inflow_series` 必填 |
| `topology` | array/null | null | 可选显式父子拓扑；不传则按 `canal_id` 命名规则推断 |
| `sim_duration_min` | integer | `60` | 仿真时长，单位 min，范围 `[1, 1440]`（最大 24 小时） |
| `dt_sec` | integer | `30` | 时间步长，单位 s，范围 `[30, 60]` |
| `dx_m` | number | `200.0` | 空间步长参考值，单位 m |
| `design_flow_ratio_min` | number | `0.6` | 流量下限比（相对设计流量 Q_design）：`0<Q<ratio*Q_design` 视为 `v_silt`；`Q>Q_design` 视为 `v_scour` |
| `h_safety_margin_m` | number | `0.3` | 水深安全余量 (m)：`h_max = design_depth + h_safety_margin`，`h > h_max` 视为 `h_over` |
| `downstream_h_mode` | string | `normal` | 末级渠段下游水位模式：`normal`=正常水深 / `design`=设计水深 / `fixed`=由 `fixed_downstream_h` 决定 |
| `fixed_downstream_h` | number/null | null | 下游固定水位（m），仅 `downstream_h_mode=fixed` 时生效 |

请求示例（1 干 + 2 支 + 4 斗，6 段）：

```json
{
  "main_canal_id": "1",
  "canals": [
    {
      "canal_id": "1",
      "level": "1",
      "length": 3000,
      "design_flow": 6.0,
      "design_depth": 1.8,
      "bottom_width": 2.5,
      "slope": 0.0002,
      "side_slope": 1.5,
      "roughness": 0.015,
      "inflow_series": [
        { "time_min": 0, "q_m3s": 6.0 },
        { "time_min": 60, "q_m3s": 0.0 }
      ]
    },
    {
      "canal_id": "1-1",
      "parent_id": "1",
      "level": "2",
      "length": 1200,
      "design_flow": 2.0,
      "design_depth": 1.2,
      "bottom_width": 1.4,
      "slope": 0.0002,
      "side_slope": 1.5,
      "roughness": 0.015,
      "inflow_series": [{ "time_min": 0, "q_m3s": 2.0 }]
    },
    {
      "canal_id": "1-1-1",
      "parent_id": "1-1",
      "level": "3",
      "length": 600,
      "design_flow": 0.5,
      "design_depth": 0.5,
      "bottom_width": 0.5,
      "slope": 0.0003,
      "side_slope": 1.5,
      "roughness": 0.017,
      "inflow_series": [{ "time_min": 0, "q_m3s": 0.5 }]
    },
    {
      "canal_id": "1-1-2",
      "parent_id": "1-1",
      "level": "3",
      "length": 720,
      "design_flow": 0.6,
      "design_depth": 0.55,
      "bottom_width": 0.55,
      "slope": 0.0003,
      "side_slope": 1.5,
      "roughness": 0.017,
      "inflow_series": [{ "time_min": 0, "q_m3s": 0.6 }]
    }
  ],
  "sim_duration_min": 60,
  "dt_sec": 30,
  "downstream_h_mode": "normal"
}
```

调用示例：

```bash
curl -X POST "http://8.146.227.98/api/v1/irrigation/canal/hydro/full/standard" \
  -H "X-Irrigation-Api-Key: irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY" \
  -H "Content-Type: application/json" \
  -d @request.json
```

`data` 响应字段：

| 字段 | 说明 |
| --- | --- |
| `summary` | 模式、干渠编号、仿真时长、dt、渠段数、收敛渠段数与收敛率、违例总数、节点连续违例数、下游水位模式 |
| `canals` | 每条渠段 summary：`canal_id` / `level` / `length_m` / `design_flow` / `design_depth` / `n_t` / `n_x` / `converged` / `last_residual` / `violation_count` / `q_max` / `h_max` / `sample_indices` |
| `timeseries` | 展平后的时空结果行，字段为 `t_min` / `canal_id` / `x_m` / `q_m3s` / `h_m` / `v_mps`；每条渠段只取 (0, n_x//2, n_x-1) 三个代表断面 |
| `topology` | `roots` / `nodes` / `edges`，供前端画树状拓扑 |
| `violations` | 合并后的违例列表：`h_over`（水深超限）/ `v_scour`（冲刷）/ `v_silt`（不淤）/ `solver_fail`（求解失败）/ `node_continuity`（节点流量连续违例） |

节点连续校验：对每个父→子节点，校验父渠段末端 Q 是否 ≈ 各子渠段上游入流之和，相对误差 > 5% 时记一条 `node_continuity` 违例。

## 3. 通用错误响应

所有灌溉相关接口的错误响应格式统一为：

```json
{
  "code": 401,
  "msg": "操作失败"
}
```

常见错误码：

| `code` | 触发条件 |
| --- | --- |
| `401` | 缺少 `X-Irrigation-Api-Key` 请求头 |
| `401` | API Key 与 `irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY` 不匹配 |
| `500` | 请求体字段缺失或类型不合法（如缺 `inflow_series`） |
| `500` | 服务端计算异常（求解失败、渠系数据未加载等） |
