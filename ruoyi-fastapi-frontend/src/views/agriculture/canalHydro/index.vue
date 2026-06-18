<template>
  <div class="app-container agri-page canal-hydro-page">
    <!-- ============ Hero ============ -->
    <section class="agri-page__hero canal-hydro-hero">
      <div class="hero-decor" aria-hidden="true">
        <span class="hero-decor__wave hero-decor__wave--1" />
        <span class="hero-decor__wave hero-decor__wave--2" />
        <span class="hero-decor__wave hero-decor__wave--3" />
      </div>
      <div class="hero-content">
        <span class="agri-page__eyebrow canal-hydro-eyebrow">TWO-LEVEL SUBTREE HYDRODYNAMICS</span>
        <h1 class="agri-page__title">两级渠段水动力学仿真</h1>
<p class="agri-page__desc">
        前端选择某条父渠道，将该父渠道及其直接下级子渠道（两级）传入后端，
        后端基于 Preissmann 四点隐式 + 线性化双扫（追赶法）逐分钟仿真，返回 (t, x, Q, h, V) 时空序列供 ECharts 动态展示。
      </p>
        <div class="agri-page__siblings">
          <router-link to="/model/irrigation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>灌溉决策</span>
          </router-link>
          <router-link to="/model/canal/optimize" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系配水优化</span>
          </router-link>
          <router-link to="/model/canal" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系管理</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="tag tag--cyan">Preissmann 隐式</span>
        <span class="tag tag--teal">双扫 (Thomas)</span>
        <span class="tag tag--indigo">θ = 0.5</span>
        <span class="tag tag--violet">≤ 24 h</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <!-- ============ 左侧：参数配置 ============ -->
      <el-col :xs="24" :lg="8" class="config-col">
        <el-card shadow="hover" class="config-card glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">仿真参数</div>
                <div class="card-desc">父渠道 + 直接下级子渠道（两级）</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'" effect="dark" round>
                {{ resultError ? '接口异常' : result ? '仿真完成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <div class="config-body">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="从渠系管理加载数据后选择父渠道，后端自动仿真父 + 直接下级子渠道两级。"
              class="mb16"
            />

            <!-- 加载数据 -->
            <div class="db-row mb12">
              <el-button size="small" type="primary" plain @click="loadFromDb" :loading="loadingDb">
                加载渠系数据
              </el-button>
              <span class="muted-text">已加载 {{ dbCanals.length }} 条</span>
            </div>

            <!-- 父渠道选择 -->
            <el-form-item label="选择父渠道" class="mb12">
              <el-select
                v-model="form.parentCanalId"
                placeholder="请先加载渠系数据，再选择父渠道"
                filterable
                clearable
                style="width: 100%"
                :disabled="dbCanals.length === 0"
                @change="onParentChange"
              >
                <el-option
                  v-for="c in dbCanals"
                  :key="c.canal_id"
                  :label="`${c.canal_id}${c.canal_name ? ' · ' + c.canal_name : ''} (Q=${c.design_flow} m³/s)`"
                  :value="c.canal_id"
                />
              </el-select>
            </el-form-item>

            <!-- 自动显示子渠道预览 -->
            <div v-if="selectedChildren.length > 0" class="children-preview mb12">
              <div class="children-preview__label">将传入 {{ selectedChildren.length }} 条子渠道：</div>
              <el-tag
                v-for="c in selectedChildren"
                :key="c.canal_id"
                size="small"
                class="child-tag"
                type="info"
              >
                {{ c.canal_id }} ({{ c.level || '-' }})
              </el-tag>
            </div>

            <div v-if="!form.parentCanalId && dbCanals.length > 0" class="mb12">
              <el-alert type="warning" :closable="false" show-icon title="请在上方选择一条父渠道" />
            </div>

            <div class="divider-soft" />

            <!-- 仿真参数 -->
            <el-form label-position="top" size="small" class="hydro-form">
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="仿真时长 (h)">
                    <el-input-number
                      v-model="form.simDurationH"
                      :min="1"
                      :max="24"
                      :step="1"
                      style="width: 100%"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="时间步 dt (s)">
                    <el-select v-model="form.dtSec" style="width: 100%">
                      <el-option :value="30" label="30s" />
                      <el-option :value="60" label="60s" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="空间步长参考值 dx (m)">
                <el-input-number v-model="form.dxM" :min="10" :max="500" :step="10" style="width: 100%" />
              </el-form-item>
            </el-form>

            <el-button
              type="primary"
              :loading="running"
              :disabled="!canSubmit"
              class="run-btn"
              @click="onSubmit"
            >
              <el-icon v-if="!running"><VideoPlay /></el-icon>
              <span>{{ running ? '仿真进行中…' : '运行两级仿真' }}</span>
            </el-button>

            <el-alert
              v-if="resultError"
              type="error"
              :title="resultError"
              :closable="false"
              show-icon
              class="mt12"
            />
          </div>
        </el-card>
      </el-col>

      <!-- ============ 右侧：结果展示 ============ -->
      <el-col :xs="24" :lg="16" class="result-col">
        <!-- KPI 总览 -->
        <el-card v-if="result" shadow="hover" class="result-card glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">仿真总览</div>
                <div class="card-desc">
                  {{ result.summary.n_canals }} 条渠段 · {{ formatHours(result.summary.sim_duration_min) }} · dt {{ result.summary.dt_sec }}s
                </div>
              </div>
            </div>
          </template>
          <el-row :gutter="12">
            <el-col :xs="12" :sm="6" v-for="(kpi, idx) in kpiList" :key="kpi.label">
              <div class="kpi-box" :class="`kpi-box--${idx}`">
                <div class="kpi-label">{{ kpi.label }}</div>
                <div class="kpi-value">{{ kpi.value }}</div>
                <div class="kpi-hint">{{ kpi.hint }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>

        <!-- 渠系拓扑 -->
        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠系拓扑</div>
                <div class="card-desc">父子关系示意（线宽 ∝ 渠长）</div>
              </div>
              <div class="legend-pills">
                <span class="legend-pill"><i class="dot dot--cyan" />干</span>
                <span class="legend-pill"><i class="dot dot--teal" />支</span>
                <span class="legend-pill"><i class="dot dot--amber" />斗</span>
                <span class="legend-pill"><i class="dot dot--rose" />农</span>
              </div>
            </div>
          </template>
          <div ref="topologyChartEl" class="chart-large chart-glass" />
        </el-card>

        <!-- 热力图 -->
        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠段 × 时间 热力图</div>
                <div class="card-desc">每行 = 1 条渠段 · 每列 = 1 个时间点</div>
              </div>
              <el-radio-group v-model="heatMetric" size="small" class="metric-switch">
                <el-radio-button value="q_m3s">流量 Q</el-radio-button>
                <el-radio-button value="h_m">水深 h</el-radio-button>
                <el-radio-button value="v_mps">流速 v</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="heatChartEl" class="chart-large chart-glass" />
        </el-card>

        <!-- 代表断面时序 -->
        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">代表断面时序</div>
                <div class="card-desc">每条渠段取首 / 中 / 末三个断面</div>
              </div>
              <div v-if="result?.canals?.length" class="canal-picker canal-picker-list">
                <el-checkbox-group v-model="selectedCanals" size="small" class="canal-checkbox-group">
                  <el-checkbox
                    v-for="c in result.canals"
                    :key="c.canal_id"
                    :value="c.canal_id"
                    :label="c.canal_id"
                    border
                    size="small"
                  >
                    {{ c.canal_id }} ({{ c.level || '-' }})
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </template>
          <el-empty v-if="selectedCanals.length === 0" description="请从右上角选择要展示的渠段" />
          <el-row v-else :gutter="12">
            <el-col v-for="cid in selectedCanals" :key="cid" :xs="24" :md="12">
              <div :ref="(el) => setSeriesChartEl(el, cid)" class="chart-medium chart-glass" :data-cid="cid" />
            </el-col>
          </el-row>
        </el-card>

        <!-- 无结果提示 -->
        <el-empty v-if="!result && !resultError && !running" description="从左侧加载渠系数据后选择父渠道开始仿真">
          <template #image>
            <el-icon class="empty-icon"><Aim /></el-icon>
          </template>
        </el-empty>

        <div v-if="running" class="running-overlay glass-card">
          <div class="running-content">
            <div class="running-spinner" />
            <div class="running-title">两级水动力学仿真中</div>
            <div class="running-desc">Preissmann 隐式 · 双扫 (Thomas) · 父+子两级 · 请稍候</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { GraphChart, HeatmapChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import { Aim, Promotion, VideoPlay } from '@element-plus/icons-vue'
import { listCanal as fetchCanals, runSubtreeHydro } from '@/api/agriculture/canal'

echarts.use([
  GraphChart,
  HeatmapChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer
])

const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

function formatHours(totalMin) {
  const m = Number(totalMin) || 0
  const h = m / 60
  return Number.isInteger(h) ? `${h} h` : `${h.toFixed(2)} h`
}

const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  simDurationH: 24,
  dtSec: 30,
  dxM: 50,
  parentCanalId: ''
})

const dbCanals = ref([])
const loadingDb = ref(false)
const running = ref(false)
const result = ref(null)
const resultError = ref('')
const heatMetric = ref('q_m3s')
const selectedCanals = ref([])

// ---- 父子渠道派生 ----
const selectedChildren = computed(() => {
  if (!form.parentCanalId) return []
  return dbCanals.value.filter((c) => c.parent_id === form.parentCanalId)
})

function onParentChange() {
  // 父渠道切换时自动选中前 6 条子渠道
  const kids = selectedChildren.value
  selectedCanals.value = kids.slice(0, Math.min(kids.length, 6)).map((c) => c.canal_id)
}

const canSubmit = computed(() => {
  return form.parentCanalId && selectedChildren.value.length > 0
})

// ---- KPI ----
const kpiList = computed(() => {
  if (!result.value) return []
  const s = result.value.summary
  return [
    { label: '渠段数', value: s.n_canals, hint: '仿真节点' },
    { label: '仿真时长', value: formatHours(s.sim_duration_min), hint: `dt = ${s.dt_sec} s` },
    { label: '时间步数', value: s.n_steps ?? '-', hint: '步' },
    { label: '求解器', value: s.solver === 'preissmann_double_sweep' ? 'Preissmann 双扫' : (s.solver || '-'), hint: `θ = ${s.theta ?? '-'}` }
  ]
})

// ---- 加载数据 ----
async function loadFromDb() {
  loadingDb.value = true
  try {
    const res = await fetchCanals({ pageNum: 1, pageSize: 200 })
    const rows = res?.rows || res?.data?.rows || []
    dbCanals.value = rows.map((r) => ({
      canal_id: r.canal_id ?? r.canalId,
      canal_name: r.canal_name ?? r.canalName,
      parent_id: r.parent_id ?? r.parentId,
      level: r.level || null,
      length: Number(r.length || 0),
      design_flow: Number(r.design_flow ?? r.designFlow ?? 0),
      design_depth: Number(r.design_depth ?? r.designDepth ?? 0),
      top_width: Number(r.top_width ?? r.topWidth ?? 0),
      bottom_width: Number(r.bottom_width ?? r.bottomWidth ?? 0),
      slope: Number(r.slope || 0),
      side_slope: Number(r.side_slope ?? r.sideSlope ?? 1.5),
      roughness: Number(r.roughness || 0.015),
      water_demand: Number(r.water_demand ?? r.waterDemand ?? 0)
    }))
    form.parentCanalId = ''
    ElMessage.success(`已加载 ${dbCanals.value.length} 条渠段`)
  } catch (err) {
    ElMessage.error(`加载失败：${err?.message || err}`)
  } finally {
    loadingDb.value = false
  }
}

// ---- 构建 payload ----
function buildCanalsPayload() {
  const root = dbCanals.value.find((c) => c.canal_id === form.parentCanalId)
  if (!root) return []
  const children = selectedChildren.value
  const all = [root, ...children]
  return all.map((c) => ({
    canal_id: c.canal_id,
    canal_name: c.canal_name || null,
    parent_id: c.parent_id || null,
    level: c.level || null,
    length: c.length,
    design_flow: c.design_flow,
    design_depth: c.design_depth,
    top_width: c.top_width,
    bottom_width: c.bottom_width,
    slope: c.slope,
    side_slope: c.side_slope,
    roughness: c.roughness,
    water_demand: c.water_demand,
    // 只有根渠段带 inflow_series；子渠段不传，后端按 design_flow 恒定
    inflow_series: c.canal_id === form.parentCanalId
      ? [{ time_min: 0, q_m3s: c.design_flow }, { time_min: form.simDurationH * 60, q_m3s: c.design_flow }]
      : undefined
  }))
}

function clearCharts() {
  topologyChart && topologyChart.dispose()
  heatChart && heatChart.dispose()
  for (const ch of seriesCharts.values()) ch.dispose()
  seriesCharts.clear()
  topologyChart = null
  heatChart = null
}

// ---- 提交 ----
async function onSubmit() {
  if (!canSubmit.value) return
  running.value = true
  resultError.value = ''
  clearCharts()
  result.value = null
  selectedCanals.value = []
  try {
    const payload = {
      canals: buildCanalsPayload(),
      sim_duration_min: form.simDurationH * 60,
      dt_sec: form.dtSec,
      dx_m: form.dxM
    }
    const data = await runSubtreeHydro(payload, form.apiKey)
    result.value = data
    await nextTick()
    if (data?.canals?.length) {
      selectedCanals.value = data.canals.slice(0, Math.min(data.canals.length, 6)).map((c) => c.canal_id)
    }
    await nextTick()
    setTimeout(renderAllCharts, 0)
    ElMessage.success('仿真完成')
  } catch (err) {
    resultError.value = err?.response?.data?.msg || err?.message || String(err)
    result.value = null
    selectedCanals.value = []
  } finally {
    running.value = false
  }
}

// ---- 图表渲染 ----
function renderAllCharts() {
  if (!result.value) return
  setTimeout(renderTopology, 0)
  setTimeout(renderHeat, 0)
  setTimeout(renderSeries, 0)
}

watch(heatMetric, () => setTimeout(renderHeat, 0))
watch(selectedCanals, () => setTimeout(renderSeries, 0))

function levelColor(level) {
  const map = {
    '1': '#0EA5E9', main: '#0EA5E9',
    '2': '#14B8A6', branch: '#14B8A6',
    '3': '#F59E0B', lateral: '#F59E0B',
    '4': '#F43F5E', farm: '#F43F5E'
  }
  return map[level] || '#8B5CF6'
}

const topologyChartEl = ref(null)
const heatChartEl = ref(null)
let topologyChart = null
let heatChart = null
const seriesCharts = new Map()
const seriesElByCid = new Map()
const seriesElVersion = ref(0)
let seriesRenderRaf = 0

function setSeriesChartEl(el, cid) {
  if (el) {
    const isNew = !seriesElByCid.has(cid)
    seriesElByCid.set(cid, el)
    if (isNew) seriesElVersion.value++
  } else {
    seriesElByCid.delete(cid)
  }
}

function renderTopology() {
  if (!topologyChartEl.value) return
  if (!topologyChart) topologyChart = echarts.init(topologyChartEl.value)

  const { roots, nodes, edges } = result.value.topology
  const root = (roots && roots[0]) || form.parentCanalId

  const childrenOf = {}
  for (const e of edges) {
    if (!childrenOf[e.from]) childrenOf[e.from] = []
    childrenOf[e.from].push(e.to)
  }

  const rawX = {}
  const depthOf = {}

  function subtreeWidth(nodeId) {
    const children = childrenOf[nodeId] || []
    if (children.length === 0) return 1
    return children.reduce((sum, c) => sum + subtreeWidth(c), 0)
  }

  function walkX(nodeId, depth) {
    depthOf[nodeId] = depth
    const children = childrenOf[nodeId] || []
    if (children.length === 0) { rawX[nodeId] = 0; return }
    for (const child of children) walkX(child, depth + 1)
    rawX[nodeId] = (rawX[children[0]] + rawX[children[children.length - 1]]) / 2
  }
  walkX(root, 0)

  const SLOT = 2
  function spread(nodeId) {
    const children = childrenOf[nodeId] || []
    if (children.length < 2) { for (const c of children) spread(c); return }
    const widths = children.map(c => subtreeWidth(c))
    let left = rawX[children[0]]
    for (let i = 1; i < children.length; i++) {
      const right = rawX[children[i]]
      const needed = left + widths[i - 1] * SLOT + 1 - right
      if (needed > 0) shiftSubtree(children[i], needed)
      left = rawX[children[i]] + widths[i] * SLOT
    }
    for (const c of children) spread(c)
  }

  function shiftSubtree(nodeId, delta) {
    rawX[nodeId] += delta
    for (const c of childrenOf[nodeId] || []) shiftSubtree(c, delta)
  }
  spread(root)

  for (const n of nodes) {
    if (rawX[n.id] === undefined) rawX[n.id] = 0
    if (depthOf[n.id] === undefined) depthOf[n.id] = 0
  }

  const xVals = Object.values(rawX)
  const xMin = Math.min(...xVals)
  const xMax = Math.max(...xVals)
  const xRange = Math.max(xMax - xMin, 1)
  const dMax = Math.max(...Object.values(depthOf), 0)

  const PAD_X = 60, PAD_Y = 50, STEP_X = 90, STEP_Y = 70

  const nodeMap = {}
  for (const n of nodes) {
    const flow = n.design_flow || 1
    const d = depthOf[n.id] || 0
    nodeMap[n.id] = {
      id: n.id,
      name: n.id,
      x: PAD_X + (rawX[n.id] - xMin) / xRange * (xRange * STEP_X),
      y: PAD_Y + d * STEP_Y,
      symbolSize: Math.max(16, Math.min(50, flow * 2.5 + 12)),
      label: { show: true, fontSize: 10, color: '#0b3b66', fontWeight: 600 },
      itemStyle: { color: levelColor(n.level), borderColor: '#ffffff', borderWidth: 2, shadowBlur: 10, shadowColor: 'rgba(14, 165, 233, 0.28)' },
      value: n
    }
  }

  const echartsNodes = Object.values(nodeMap)
  const echartsEdges = edges.map((e) => ({
    source: e.from, target: e.to,
    lineStyle: { width: Math.max(0.6, Math.min(3.5, (e.length || 100) / 1500)), color: '#4ab8e8', curveness: 0, opacity: 0.65 }
  }))

  topologyChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (p) => {
        if (p.dataType === 'node') {
          return `<b>${p.data.id}</b><br/>L=${p.data.value.length} m<br/>Q=${p.data.value.design_flow} m³/s`
        }
        return `${p.data.source} → ${p.data.target}`
      }
    },
    series: [{
      type: 'graph', layout: 'none', roam: true, symbol: 'circle',
      edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 5,
      data: echartsNodes, links: echartsEdges,
      lineStyle: { opacity: 0.65 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } }
    }]
  })
}

function renderHeat() {
  if (!heatChartEl.value) return
  if (!heatChart) heatChart = echarts.init(heatChartEl.value)

  const canals = result.value.canals.map((c) => c.canal_id)
  const times = [...new Set(result.value.timeseries.map((r) => r.t_min))].sort((a, b) => a - b)
  const metric = heatMetric.value
  const data = []
  let vmin = Infinity, vmax = -Infinity
  const canalIdx = new Map(canals.map((c, i) => [c, i]))
  const timeIdx = new Map(times.map((t, i) => [t, i]))

  for (const r of result.value.timeseries) {
    if (!timeIdx.has(r.t_min) || !canalIdx.has(r.canal_id)) continue
    const v = Number(r[metric] || 0)
    data.push([timeIdx.get(r.t_min), canalIdx.get(r.canal_id), v])
    if (v < vmin) vmin = v
    if (v > vmax) vmax = v
  }
  if (!isFinite(vmin)) vmin = 0
  if (!isFinite(vmax)) vmax = 1

  const palette = { q_m3s: ['#E0F2FE', '#0EA5E9', '#082F49'], h_m: ['#ECFEFF', '#14B8A6', '#0F766E'], v_mps: ['#FEF3C7', '#F59E0B', '#92400E'] }

  heatChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { position: 'top', formatter: (p) => `${canals[p.value[1]]} · t=${times[p.value[0]]} min<br/>${metric} = ${p.value[2]}` },
    grid: { top: 30, left: 90, right: 30, bottom: 60 },
    xAxis: { type: 'category', data: times, axisLabel: { color: '#5b738e' }, splitArea: { show: true } },
    yAxis: { type: 'category', data: canals, axisLabel: { color: '#5b738e' }, splitArea: { show: true } },
    visualMap: { min: vmin, max: vmax, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, textStyle: { color: '#5b738e' }, inRange: { color: palette[metric] || palette.q_m3s } },
    series: [{
      name: metric, type: 'heatmap', data,
      progressive: 1000,
      itemStyle: { borderRadius: 2, borderColor: 'rgba(255,255,255,0.5)', borderWidth: 1 },
      emphasis: { itemStyle: { borderColor: '#082F49', borderWidth: 1 } }
    }]
  })
}

function renderSeries() {
  for (const [cid, ch] of seriesCharts.entries()) {
    if (!selectedCanals.value.includes(cid)) {
      ch.dispose()
      seriesCharts.delete(cid)
    }
  }
  for (const cid of selectedCanals.value) {
    const rows = result.value.timeseries.filter((r) => r.canal_id === cid)
    if (!rows.length) continue
    const xSet = [...new Set(rows.map((r) => r.x_m))].sort((a, b) => a - b)
    const tSet = [...new Set(rows.map((r) => r.t_min))].sort((a, b) => a - b)
    const palette = ['#0EA5E9', '#14B8A6', '#8B5CF6']

    const series = xSet.map((x, i) => {
      const points = rows.filter((r) => r.x_m === x).sort((a, b) => a.t_min - b.t_min)
      return {
        name: `x=${x}m`,
        type: 'line', smooth: true, showSymbol: false,
        lineStyle: { width: 2, color: palette[i % palette.length] },
        itemStyle: { color: palette[i % palette.length] },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: palette[i % palette.length] + '55' },
            { offset: 1, color: palette[i % palette.length] + '00' }
          ])
        },
        data: points.map((p) => [p.t_min, p.h_m])
      }
    })

    const el = seriesElByCid.get(cid)
    if (!el) continue
    let ch = seriesCharts.get(cid)
    if (!ch) { ch = echarts.init(el); seriesCharts.set(cid, ch) }
    ch.setOption({
      backgroundColor: 'transparent',
      title: { text: `${cid} · h(t)`, left: 'center', textStyle: { color: '#1e3a8a', fontSize: 13, fontWeight: 600 } },
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#5b738e' }, top: 22, type: 'scroll', icon: 'roundRect' },
      grid: { top: 56, left: 50, right: 18, bottom: 30 },
      xAxis: { type: 'category', name: 't (min)', data: tSet, axisLabel: { color: '#5b738e' }, nameTextStyle: { color: '#5b738e' } },
      yAxis: { type: 'value', name: 'h (m)', axisLabel: { color: '#5b738e' }, nameTextStyle: { color: '#5b738e' }, splitLine: { lineStyle: { color: 'rgba(91, 115, 142, 0.18)' } } },
      series
    })
  }
}

function handleResize() {
  topologyChart && topologyChart.resize()
  heatChart && heatChart.resize()
  for (const ch of seriesCharts.values()) ch.resize()
}

onMounted(() => { window.addEventListener('resize', handleResize) })

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (seriesRenderRaf) cancelAnimationFrame(seriesRenderRaf)
  topologyChart && topologyChart.dispose()
  heatChart && heatChart.dispose()
  for (const ch of seriesCharts.values()) ch.dispose()
  seriesCharts.clear()
})

watch(seriesElVersion, () => {
  if (seriesRenderRaf) cancelAnimationFrame(seriesRenderRaf)
  seriesRenderRaf = requestAnimationFrame(() => {
    seriesRenderRaf = 0
    if (result.value) renderSeries()
  })
})
</script>

<style scoped>
/* ============ Hero ============ */
.canal-hydro-hero {
  position: relative; overflow: hidden; isolation: isolate;
  background:
    radial-gradient(at 18% 18%, rgba(20, 184, 166, 0.22) 0%, transparent 55%),
    radial-gradient(at 82% 12%, rgba(14, 165, 233, 0.28) 0%, transparent 55%),
    radial-gradient(at 65% 90%, rgba(139, 92, 246, 0.18) 0%, transparent 55%),
    linear-gradient(135deg, #ecfeff 0%, #f0f9ff 60%, #f5f3ff 100%);
  color: #0b3b66;
  border: 1px solid rgba(14, 165, 233, 0.18);
}
.canal-hydro-hero .hero-content { position: relative; z-index: 2; }
.canal-hydro-eyebrow { background: linear-gradient(120deg, rgba(14, 165, 233, 0.18), rgba(20, 184, 166, 0.18)); color: #0e7490; border: 1px solid rgba(14, 165, 233, 0.3); }
.canal-hydro-hero .agri-page__title { background: linear-gradient(120deg, #0c4a6e 0%, #0e7490 50%, #6d28d9 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.canal-hydro-hero .agri-page__desc { color: #1e5577; }

/* ============ Tags ============ */
.tag { display: inline-flex; align-items: center; min-height: 30px; padding: 0 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; border: 1px solid transparent; background: rgba(255, 255, 255, 0.7); color: #0b3b66; }
.tag--cyan   { background: rgba(14, 165, 233, 0.12); border-color: rgba(14, 165, 233, 0.3); color: #0369a1; }
.tag--teal   { background: rgba(20, 184, 166, 0.12); border-color: rgba(20, 184, 166, 0.3); color: #0f766e; }
.tag--indigo { background: rgba(99, 102, 241, 0.12); border-color: rgba(99, 102, 241, 0.3); color: #4338ca; }
.tag--violet { background: rgba(139, 92, 246, 0.12); border-color: rgba(139, 92, 246, 0.3); color: #6d28d9; }

.sibling-link { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 9999px; background: rgba(255, 255, 255, 0.65); border: 1px solid rgba(14, 165, 233, 0.2); color: #0c4a6e; font-size: 12px; font-weight: 600; text-decoration: none; transition: all 200ms ease; backdrop-filter: blur(6px); }
.sibling-link:hover { background: rgba(255, 255, 255, 0.95); transform: translateY(-1px); box-shadow: 0 6px 18px rgba(14, 165, 233, 0.15); }

/* ============ Card ============ */
.mb12 { margin-bottom: 12px; }
.mt12 { margin-top: 12px; }
.mt16 { margin-top: 16px; }
.mb16 { margin-bottom: 16px; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.card-title { font-size: 16px; font-weight: 700; color: #0c2c4d; }
.card-desc  { font-size: 12px; color: #5b738e; margin-top: 2px; }
.muted-text { color: #5b738e; font-size: 12px; margin-left: 8px; }
.db-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.divider-soft { height: 1px; margin: 6px 0 14px; background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.25), transparent); }

/* ============ Children preview ============ */
.children-preview { padding: 8px 12px; border-radius: 8px; background: rgba(14, 165, 233, 0.06); border: 1px solid rgba(14, 165, 233, 0.15); }
.children-preview__label { font-size: 12px; color: #5b738e; margin-bottom: 6px; }
.child-tag { margin: 2px 4px 2px 0; }

/* ============ Run button ============ */
.run-btn { width: 100%; height: 44px; border: 0; border-radius: 14px; font-size: 14px; font-weight: 700; letter-spacing: 0.04em; color: #ffffff; background: linear-gradient(120deg, #0EA5E9 0%, #14B8A6 60%, #6366F1 100%); box-shadow: 0 8px 24px rgba(14, 165, 233, 0.35), 0 2px 6px rgba(20, 184, 166, 0.2); transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease; display: inline-flex; align-items: center; justify-content: center; gap: 8px; }
.run-btn:hover { transform: translateY(-1px); filter: brightness(1.05); box-shadow: 0 14px 32px rgba(14, 165, 233, 0.45), 0 4px 10px rgba(20, 184, 166, 0.28); }
.run-btn:active { transform: translateY(0); filter: brightness(0.98); }
.run-btn.is-disabled, .run-btn:disabled { background: linear-gradient(120deg, #cbd5e1, #94a3b8); box-shadow: none; color: #f8fafc; cursor: not-allowed; }

/* ============ Legend ============ */
.legend-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.legend-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 9999px; font-size: 12px; color: #5b738e; background: rgba(255, 255, 255, 0.7); border: 1px solid rgba(91, 115, 142, 0.2); }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot--cyan  { background: #0EA5E9; box-shadow: 0 0 8px #0EA5E9; }
.dot--teal  { background: #14B8A6; box-shadow: 0 0 8px #14B8A6; }
.dot--amber { background: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
.dot--rose  { background: #F43F5E; box-shadow: 0 0 8px #F43F5E; }

/* ============ Charts ============ */
.chart-large { width: 100%; height: 380px; border-radius: 16px; }
.chart-medium { width: 100%; height: 240px; border-radius: 16px; }
.metric-switch { display: inline-flex; }
.canal-picker { min-width: 220px; }
.canal-picker-list { max-width: 720px; max-height: 120px; overflow-y: auto; padding: 4px; }
.canal-checkbox-group { display: flex; flex-wrap: wrap; gap: 6px; }
.canal-checkbox-group :deep(.el-checkbox) { margin-right: 0; }
.canal-checkbox-group :deep(.el-checkbox__label) { font-size: 12px; }
.config-body { max-height: calc(100vh - 340px); overflow-y: auto; padding-right: 6px; }
.config-body::-webkit-scrollbar { width: 6px; }
.config-body::-webkit-scrollbar-thumb { background: rgba(14, 165, 233, 0.25); border-radius: 3px; }

/* ============ Empty / Running ============ */
.empty-icon { font-size: 56px; color: #93c5fd; }
.running-overlay { margin-top: 16px; padding: 40px 24px; display: flex; align-items: center; justify-content: center; border-radius: 24px; background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(240, 249, 255, 0.7)); border: 1px solid rgba(14, 165, 233, 0.2); }
.running-content { text-align: center; }
.running-spinner { width: 48px; height: 48px; margin: 0 auto 12px; border-radius: 50%; border: 3px solid rgba(14, 165, 233, 0.2); border-top-color: #0EA5E9; animation: spin 0.9s linear infinite; }
.running-title { font-size: 16px; font-weight: 700; color: #0c2c4d; }
.running-desc  { font-size: 12px; color: #5b738e; margin-top: 4px; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
