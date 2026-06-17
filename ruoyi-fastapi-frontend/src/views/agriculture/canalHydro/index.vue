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
        <span class="agri-page__eyebrow canal-hydro-eyebrow">MINUTE-BY-MINUTE HYDRODYNAMICS</span>
        <h1 class="agri-page__title">全渠系逐分钟水动力学仿真</h1>
        <p class="agri-page__desc">
          前端传入完整渠系数据并显式给出每条渠段的上游入流时序，后端按渠系拓扑逐条做
          MacCormack 显式 1D 圣维南仿真，通过节点连续校验实现干-支-斗-农的逐分钟接力，
          最终返回全渠系 (t, x, Q, h, V) 的时空结果，ECharts 动态展示。
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
        <span class="tag tag--cyan">MacCormack</span>
        <span class="tag tag--teal">节点连续耦合</span>
        <span class="tag tag--indigo">dt 30s</span>
        <span class="tag tag--violet">≤ 12h</span>
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
                <div class="card-desc">节点连续耦合 · 逐分钟接力</div>
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
              title="每条渠段必须给入流时序 inflow_series，未给则按恒定设计流量入流。"
              class="mb16"
            />

            <el-form ref="formRef" :model="form" label-position="top" size="small" class="hydro-form">
              <el-form-item label="干渠编号">
                <el-input v-model="form.mainCanalId" placeholder="默认 1" clearable />
              </el-form-item>

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="仿真时长 (min)">
                    <el-input-number v-model="form.simDurationMin" :min="1" :max="720" :step="10" style="width: 100%" />
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

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="v_max (m/s)">
                    <el-input-number v-model="form.vMax" :min="0.5" :max="5" :step="0.1" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="v_min (m/s)">
                    <el-input-number v-model="form.vMin" :min="0.05" :max="2" :step="0.05" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="末级下游水位模式">
                <el-select v-model="form.downstreamHMode" style="width: 100%">
                  <el-option value="normal" label="正常水深 (Manning)" />
                  <el-option value="design" label="设计水深" />
                  <el-option value="fixed" label="固定下游水位" />
                </el-select>
              </el-form-item>

              <el-form-item v-if="form.downstreamHMode === 'fixed'" label="固定下游水位 (m)">
                <el-input-number v-model="form.fixedDownstreamH" :min="0" :max="10" :step="0.05" style="width: 100%" />
              </el-form-item>

              <div class="divider-soft" />

              <el-form-item label="渠段数据来源">
                <el-radio-group v-model="form.source" class="source-switch">
                  <el-radio-button value="db">数据库</el-radio-button>
                  <el-radio-button value="manual">本页编辑</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="form.source === 'db'" class="mb12 db-row">
                <el-button size="small" type="primary" plain @click="loadFromDb" :loading="loadingDb">
                  从渠系管理加载
                </el-button>
                <span class="muted-text">已加载 {{ dbCanals.length }} 条渠段</span>
              </div>

              <el-button
                type="primary"
                :loading="running"
                :disabled="!canSubmit"
                class="run-btn"
                @click="onSubmit"
              >
                <el-icon v-if="!running"><VideoPlay /></el-icon>
                <span>{{ running ? '仿真进行中…' : '运行全渠系仿真' }}</span>
              </el-button>

              <el-alert
                v-if="resultError"
                type="error"
                :title="resultError"
                :closable="false"
                show-icon
                class="mt12"
              />
            </el-form>
          </div>
        </el-card>

        <el-card v-if="form.source === 'manual'" shadow="hover" class="config-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠段编辑（手动模式）</div>
                <div class="card-desc">至少 1 干 + 1 支 + 1 斗，每条必填 inflow_series</div>
              </div>
              <el-button size="small" type="primary" plain @click="addCanalRow">新增渠段</el-button>
            </div>
          </template>
          <div class="canal-edit-list">
            <el-collapse v-model="openCids">
              <el-collapse-item
                v-for="row in form.canals"
                :key="row.canal_id"
                :name="row.canal_id"
                :title="`${row.canal_id} · L=${row.length}m · Q=${row.design_flow} m³/s`"
              >
                <el-row :gutter="10">
                  <el-col :span="12">
                    <el-form-item label="渠段编号" label-position="top">
                      <el-input v-model="row.canal_id" size="small" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="父渠段" label-position="top">
                      <el-input v-model="row.parent_id" size="small" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="长度 m" label-position="top">
                      <el-input-number v-model="row.length" :min="0" :step="100" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="设计 Q m³/s" label-position="top">
                      <el-input-number v-model="row.design_flow" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="设计水深 m" label-position="top">
                      <el-input-number v-model="row.design_depth" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="渠底宽 m" label-position="top">
                      <el-input-number v-model="row.bottom_width" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="边坡 m" label-position="top">
                      <el-input-number v-model="row.side_slope" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="糙率" label-position="top">
                      <el-input-number v-model="row.roughness" :min="0" :step="0.001" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="纵坡" label-position="top">
                      <el-input-number v-model="row.slope" :min="0" :step="0.0001" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="入流 Q (m³/s)" label-position="top">
                      <el-input-number v-model="row._q" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8" class="remove-cell">
                    <el-button type="danger" size="small" plain @click="removeCanalRow(row.canal_id)">删除</el-button>
                  </el-col>
                </el-row>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>

      <!-- ============ 右侧：结果展示 ============ -->
      <el-col :xs="24" :lg="16" class="result-col">
        <el-card v-if="result" shadow="hover" class="result-card glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">KPI · 仿真总览</div>
                <div class="card-desc">
                  {{ result.summary.n_canals }} 段渠系 · {{ result.summary.sim_duration_min }} 分钟 · dt {{ result.summary.dt_sec }}s · 模式 {{ result.summary.downstream_h_mode }}
                </div>
              </div>
              <div class="header-actions">
                <el-tag :type="kpiConvergedType" effect="dark" round>{{ kpiConvergedText }}</el-tag>
                <el-tag :type="kpiViolationsType" effect="dark" round>违例 {{ result.summary.total_violations }}</el-tag>
                <el-tag :type="kpiContinuityType" effect="dark" round>节点连续违例 {{ result.summary.node_continuity_violations }}</el-tag>
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

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠系拓扑（节点连续）</div>
                <div class="card-desc">悬停查看父 → 子边（线宽 ∝ 渠长）</div>
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

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠段 × 时间 热力图</div>
                <div class="card-desc">每行 = 1 条渠段 · 每列 = 1 个时间点 · 单元颜色 = 数值</div>
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

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">代表断面时序子图</div>
                <div class="card-desc">每条渠段取首 / 中 / 末三个断面；可勾选要查看的渠段</div>
              </div>
              <el-select
                v-model="selectedCanals"
                multiple
                collapse-tags
                collapse-tags-tooltip
                placeholder="选择渠段"
                size="small"
                class="canal-picker"
              >
                <el-option
                  v-for="c in result.canals"
                  :key="c.canal_id"
                  :value="c.canal_id"
                  :label="`${c.canal_id} (${c.level || '-'})`"
                />
              </el-select>
            </div>
          </template>
          <el-empty v-if="selectedCanals.length === 0" description="请从右上角选择要展示的渠段" />
          <el-row v-else :gutter="12">
            <el-col v-for="cid in selectedCanals" :key="cid" :xs="24" :md="12">
              <div ref="seriesChartEl" class="chart-medium chart-glass" :data-cid="cid" />
            </el-col>
          </el-row>
        </el-card>

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">违例明细</div>
                <div class="card-desc">h_over · v_scour · v_silt · solver_fail · node_continuity</div>
              </div>
              <el-select v-model="violationFilter" size="small" class="filter-select" placeholder="按类型筛选">
                <el-option value="" label="全部" />
                <el-option value="h_over" label="h_over" />
                <el-option value="v_scour" label="v_scour" />
                <el-option value="v_silt" label="v_silt" />
                <el-option value="solver_fail" label="solver_fail" />
                <el-option value="node_continuity" label="node_continuity" />
              </el-select>
            </div>
          </template>
          <el-table :data="filteredViolations" size="small" max-height="320" stripe class="violation-table">
            <el-table-column prop="time_min" label="时间 (min)" width="110" />
            <el-table-column prop="canal_id" label="渠段" width="120" />
            <el-table-column prop="x_m" label="x (m)" width="90" />
            <el-table-column label="类型" width="160">
              <template #default="{ row }">
                <el-tag :type="violationTagType(row.type)" effect="light" size="small" round>
                  {{ row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="detail" label="详情" />
          </el-table>
        </el-card>

        <el-empty v-if="!result && !resultError && !running" description="提交左侧表单后开始全渠系水动力学仿真">
          <template #image>
            <el-icon class="empty-icon"><Aim /></el-icon>
          </template>
        </el-empty>

        <div v-if="running" class="running-overlay glass-card">
          <div class="running-content">
            <div class="running-spinner" />
            <div class="running-title">全渠系水动力学仿真中</div>
            <div class="running-desc">MacCormack 显式 · 节点连续接力 · 请稍候</div>
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
import { listCanal as fetchCanals } from '@/api/agriculture/canal'
import { runFullHydro } from '@/api/agriculture/canal'

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

const DEFAULT_API_KEY = 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const DEFAULT_INFLOW = (q) => [{ time_min: 0, q_m3s: q }, { time_min: 720, q_m3s: q }]

function makeBlankCanal(cid, parentId, designFlow, length) {
  return {
    canal_id: cid,
    parent_id: parentId,
    level: '',
    length,
    design_flow: designFlow,
    design_depth: 0.0,
    top_width: 0.0,
    bottom_width: 0.0,
    slope: 0.0,
    side_slope: 1.5,
    roughness: 0.015,
    water_demand: 0.0,
    _q: designFlow,
    inflow_series: DEFAULT_INFLOW(designFlow)
  }
}

const formRef = ref(null)
const form = reactive({
  apiKey: DEFAULT_API_KEY,
  mainCanalId: '1',
  simDurationMin: 60,
  dtSec: 30,
  vMax: 1.5,
  vMin: 0.3,
  downstreamHMode: 'normal',
  fixedDownstreamH: 0.5,
  source: 'db',
  canals: [
    makeBlankCanal('1', null, 4.0, 1500),
    makeBlankCanal('1-1', '1', 2.0, 800),
    makeBlankCanal('1-1-1', '1-1', 1.0, 400)
  ]
})

const openCids = ref(['1', '1-1', '1-1-1'])
const dbCanals = ref([])
const loadingDb = ref(false)
const running = ref(false)
const result = ref(null)
const resultError = ref('')
const heatMetric = ref('q_m3s')
const violationFilter = ref('')
const selectedCanals = ref([])

const topologyChartEl = ref(null)
const heatChartEl = ref(null)
const seriesChartEl = ref([])
let topologyChart = null
let heatChart = null
const seriesCharts = new Map()

const canSubmit = computed(() => {
  if (form.source === 'db' && dbCanals.value.length === 0) return false
  if (form.source === 'manual' && form.canals.length === 0) return false
  return true
})

const kpiConvergedText = computed(() => {
  if (!result.value) return ''
  const s = result.value.summary
  return `${s.n_converged}/${s.n_canals} 收敛 (${(s.converged_ratio * 100).toFixed(0)}%)`
})
const kpiConvergedType = computed(() => {
  if (!result.value) return 'info'
  return result.value.summary.converged_ratio >= 0.95 ? 'success' : 'warning'
})
const kpiViolationsType = computed(() => {
  if (!result.value) return 'info'
  const v = result.value.summary.total_violations
  if (v === 0) return 'success'
  if (v < 50) return 'warning'
  return 'danger'
})
const kpiContinuityType = computed(() => {
  if (!result.value) return 'info'
  const v = result.value.summary.node_continuity_violations
  if (v === 0) return 'success'
  if (v < 30) return 'warning'
  return 'danger'
})

const kpiList = computed(() => {
  if (!result.value) return []
  const s = result.value.summary
  return [
    { label: '渠段数', value: s.n_canals, hint: 'BFS 仿真节点' },
    { label: '仿真时长', value: `${s.sim_duration_min} min`, hint: `dt = ${s.dt_sec} s` },
    { label: '下游模式', value: s.downstream_h_mode, hint: '末级渠段边界' },
    { label: '总违例', value: s.total_violations, hint: '水深 / 流速 / 节点连续' }
  ]
})

const filteredViolations = computed(() => {
  if (!result.value) return []
  if (!violationFilter.value) return result.value.violations.slice(0, 200)
  return result.value.violations.filter((v) => v.type === violationFilter.value).slice(0, 200)
})

function violationTagType(type) {
  const map = {
    h_over: 'danger',
    v_scour: 'warning',
    v_silt: 'warning',
    solver_fail: 'danger',
    node_continuity: 'info'
  }
  return map[type] || 'info'
}

function addCanalRow() {
  const id = `manual-${form.canals.length + 1}`
  form.canals.push(makeBlankCanal(id, null, 1.0, 500))
  openCids.value.push(id)
}

function removeCanalRow(cid) {
  form.canals = form.canals.filter((c) => c.canal_id !== cid)
}

async function loadFromDb() {
  loadingDb.value = true
  try {
    const res = await fetchCanals({ pageNum: 1, pageSize: 200 })
    const rows = res?.rows || res?.data?.rows || []
    dbCanals.value = rows.map((r) => ({
      ...r,
      _q: Number(r.design_flow || 0),
      inflow_series: DEFAULT_INFLOW(Number(r.design_flow || 0))
    }))
    ElMessage.success(`已加载 ${dbCanals.value.length} 条渠段`)
  } catch (err) {
    ElMessage.error(`加载渠系数据失败：${err?.message || err}`)
  } finally {
    loadingDb.value = false
  }
}

function buildCanalsPayload() {
  const src = form.source === 'db' ? dbCanals.value : form.canals
  return src.map((c) => ({
    canal_id: c.canal_id,
    canal_name: c.canal_name || null,
    parent_id: c.parent_id || null,
    level: c.level || null,
    length: Number(c.length || 0),
    design_flow: Number(c.design_flow || 0),
    design_depth: Number(c.design_depth || 0),
    top_width: Number(c.top_width || 0),
    bottom_width: Number(c.bottom_width || 0),
    slope: Number(c.slope || 0),
    side_slope: Number(c.side_slope || 1.5),
    roughness: Number(c.roughness || 0.015),
    inflow_series: c.inflow_series
  }))
}

async function onSubmit() {
  running.value = true
  resultError.value = ''
  try {
    const payload = {
      main_canal_id: form.mainCanalId || '1',
      canals: buildCanalsPayload(),
      sim_duration_min: form.simDurationMin,
      dt_sec: form.dtSec,
      v_max: form.vMax,
      v_min: form.vMin,
      downstream_h_mode: form.downstreamHMode,
      fixed_downstream_h: form.downstreamHMode === 'fixed' ? form.fixedDownstreamH : null
    }
    const data = await runFullHydro(payload, form.apiKey)
    result.value = data
    if (data?.canals?.length) {
      selectedCanals.value = data.canals.slice(0, Math.min(data.canals.length, 6)).map((c) => c.canal_id)
    }
    await nextTick()
    renderAllCharts()
    ElMessage.success('全渠系仿真完成')
  } catch (err) {
    resultError.value = err?.response?.data?.msg || err?.message || String(err)
  } finally {
    running.value = false
  }
}

function renderAllCharts() {
  if (!result.value) return
  renderTopology()
  renderHeat()
  renderSeries()
}

watch(heatMetric, () => renderHeat())
watch(
  () => selectedCanals.value.slice(),
  () => nextTick(() => renderSeries()),
  { deep: true }
)

function levelColor(level) {
  const map = {
    '1': '#0EA5E9',
    main: '#0EA5E9',
    '2': '#14B8A6',
    branch: '#14B8A6',
    '3': '#F59E0B',
    lateral: '#F59E0B',
    '4': '#F43F5E',
    farm: '#F43F5E'
  }
  return map[level] || '#8B5CF6'
}

function renderTopology() {
  if (!topologyChartEl.value) return
  if (!topologyChart) {
    topologyChart = echarts.init(topologyChartEl.value)
  }
  const nodes = result.value.topology.nodes.map((n) => ({
    id: n.id,
    name: n.id,
    symbolSize: Math.max(28, Math.min(72, (n.design_flow || 1) * 5 + 18)),
    label: { show: true, fontSize: 12, color: '#0b3b66', fontWeight: 600 },
    itemStyle: {
      color: levelColor(n.level),
      borderColor: '#ffffff',
      borderWidth: 2,
      shadowBlur: 14,
      shadowColor: 'rgba(14, 165, 233, 0.35)'
    },
    value: n
  }))
  const edges = result.value.topology.edges.map((e) => ({
    source: e.from,
    target: e.to,
    lineStyle: {
      width: Math.max(1.5, Math.min(8, (e.length || 100) / 500)),
      color: '#5cd2ff',
      curveness: 0.18,
      opacity: 0.85
    }
  }))
  topologyChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (p) => {
        if (p.dataType === 'node') {
          return `<b>${p.data.id}</b><br/>长度 L=${p.data.value.length} m<br/>设计 Q=${p.data.value.design_flow} m³/s<br/>设计水深=${p.data.value.design_depth} m`
        }
        return `${p.data.source} → ${p.data.target}<br/>L=${p.data.value?.length || '-'} m`
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'tree',
        roam: true,
        symbol: 'circle',
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 7,
        data: nodes,
        links: edges,
        lineStyle: { opacity: 0.85 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 4 } }
      }
    ]
  })
}

function renderHeat() {
  if (!heatChartEl.value) return
  if (!heatChart) {
    heatChart = echarts.init(heatChartEl.value)
  }
  const canals = result.value.canals.map((c) => c.canal_id)
  const times = [...new Set(result.value.timeseries.map((r) => r.t_min))].sort((a, b) => a - b)
  const metric = heatMetric.value
  const data = []
  let vmin = Infinity
  let vmax = -Infinity
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
  const palette = {
    q_m3s: ['#E0F2FE', '#0EA5E9', '#082F49'],
    h_m: ['#ECFEFF', '#14B8A6', '#0F766E'],
    v_mps: ['#FEF3C7', '#F59E0B', '#92400E']
  }
  heatChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      formatter: (p) => `${canals[p.value[1]]} · t=${times[p.value[0]]} min<br/>${metric} = ${p.value[2]}`
    },
    grid: { top: 30, left: 90, right: 30, bottom: 60 },
    xAxis: { type: 'category', data: times, axisLabel: { color: '#5b738e' }, splitArea: { show: true } },
    yAxis: { type: 'category', data: canals, axisLabel: { color: '#5b738e' }, splitArea: { show: true } },
    visualMap: {
      min: vmin,
      max: vmax,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#5b738e' },
      inRange: { color: palette[metric] || palette.q_m3s }
    },
    series: [
      {
        name: metric,
        type: 'heatmap',
        data,
        progressive: 1000,
        itemStyle: { borderRadius: 2, borderColor: 'rgba(255,255,255,0.5)', borderWidth: 1 },
        emphasis: { itemStyle: { borderColor: '#082F49', borderWidth: 1 } }
      }
    ]
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
        name: `x = ${x} m`,
        type: 'line',
        smooth: true,
        showSymbol: false,
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
    const el = seriesChartEl.value.find((node) => node && node.dataset.cid === cid)
    if (!el) continue
    let ch = seriesCharts.get(cid)
    if (!ch) {
      ch = echarts.init(el)
      seriesCharts.set(cid, ch)
    }
    ch.setOption({
      backgroundColor: 'transparent',
      title: {
        text: `${cid} · h(t)`,
        left: 'center',
        textStyle: { color: '#1e3a8a', fontSize: 13, fontWeight: 600 }
      },
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#5b738e' }, top: 22, type: 'scroll', icon: 'roundRect' },
      grid: { top: 56, left: 50, right: 18, bottom: 30 },
      xAxis: {
        type: 'category',
        name: 't (min)',
        data: tSet,
        axisLabel: { color: '#5b738e' },
        nameTextStyle: { color: '#5b738e' }
      },
      yAxis: {
        type: 'value',
        name: 'h (m)',
        axisLabel: { color: '#5b738e' },
        nameTextStyle: { color: '#5b738e' },
        splitLine: { lineStyle: { color: 'rgba(91, 115, 142, 0.18)' } }
      },
      series
    })
  }
}

function handleResize() {
  topologyChart && topologyChart.resize()
  heatChart && heatChart.resize()
  for (const ch of seriesCharts.values()) ch.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  topologyChart && topologyChart.dispose()
  heatChart && heatChart.dispose()
  for (const ch of seriesCharts.values()) ch.dispose()
  seriesCharts.clear()
})

watch(seriesChartEl, async () => {
  await nextTick()
  if (result.value) renderSeries()
})
</script>

<style scoped>
/* ============ Hero 装饰 ============ */
.canal-hydro-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(at 18% 18%, rgba(20, 184, 166, 0.22) 0%, transparent 55%),
    radial-gradient(at 82% 12%, rgba(14, 165, 233, 0.28) 0%, transparent 55%),
    radial-gradient(at 65% 90%, rgba(139, 92, 246, 0.18) 0%, transparent 55%),
    linear-gradient(135deg, #ecfeff 0%, #f0f9ff 60%, #f5f3ff 100%);
  color: #0b3b66;
  border: 1px solid rgba(14, 165, 233, 0.18);
}
.canal-hydro-hero .hero-content {
  position: relative;
  z-index: 2;
}
.canal-hydro-eyebrow {
  background: linear-gradient(120deg, rgba(14, 165, 233, 0.18), rgba(20, 184, 166, 0.18));
  color: #0e7490;
  border: 1px solid rgba(14, 165, 233, 0.3);
}
.canal-hydro-hero .agri-page__title {
  background: linear-gradient(120deg, #0c4a6e 0%, #0e7490 50%, #6d28d9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.canal-hydro-hero .agri-page__desc {
  color: #1e5577;
}
.hero-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}
.hero-decor__wave {
  position: absolute;
  height: 2px;
  width: 240%;
  left: -70%;
  background: linear-gradient(90deg, transparent 0%, rgba(14, 165, 233, 0.35) 50%, transparent 100%);
  filter: blur(0.5px);
  border-radius: 9999px;
  animation: hero-wave-move 12s linear infinite;
}
.hero-decor__wave--1 { top: 28%; }
.hero-decor__wave--2 { top: 56%; animation-duration: 16s; opacity: 0.65; }
.hero-decor__wave--3 { top: 80%; animation-duration: 20s; opacity: 0.45; }
@keyframes hero-wave-move {
  0%   { transform: translateX(-30%) rotate(-2deg); }
  50%  { transform: translateX(0%)   rotate(2deg); }
  100% { transform: translateX(30%)  rotate(-2deg); }
}

/* ============ Hero 标签 ============ */
.tag {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.7);
  color: #0b3b66;
}
.tag--cyan   { background: rgba(14, 165, 233, 0.12); border-color: rgba(14, 165, 233, 0.3); color: #0369a1; }
.tag--teal   { background: rgba(20, 184, 166, 0.12); border-color: rgba(20, 184, 166, 0.3); color: #0f766e; }
.tag--indigo { background: rgba(99, 102, 241, 0.12); border-color: rgba(99, 102, 241, 0.3); color: #4338ca; }
.tag--violet { background: rgba(139, 92, 246, 0.12); border-color: rgba(139, 92, 246, 0.3); color: #6d28d9; }

.sibling-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(14, 165, 233, 0.2);
  color: #0c4a6e;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: all 200ms ease;
  backdrop-filter: blur(6px);
}
.sibling-link:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(14, 165, 233, 0.15);
}

/* ============ 卡片 / 玻璃感 ============ */
.glass-card {
  border: 1px solid rgba(14, 165, 233, 0.18);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-radius: 24px;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 8px 28px rgba(15, 42, 92, 0.08);
}
.glass-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(14, 165, 233, 0.12);
  padding: 18px 22px;
}
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.card-title { font-size: 16px; font-weight: 700; color: #0c2c4d; }
.card-desc  { font-size: 12px; color: #5b738e; margin-top: 2px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.mb12 { margin-bottom: 12px; }
.mt12 { margin-top: 12px; }
.mt16 { margin-top: 16px; }
.mb16 { margin-bottom: 16px; }
.muted-text { color: #5b738e; font-size: 12px; margin-left: 8px; }
.db-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }

.divider-soft {
  height: 1px;
  margin: 6px 0 14px;
  background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.25), transparent);
}

.source-switch { display: inline-flex; }
.metric-switch { display: inline-flex; }

/* ============ 运行按钮 ============ */
.run-btn {
  width: 100%;
  height: 44px;
  border: 0;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #ffffff;
  background: linear-gradient(120deg, #0EA5E9 0%, #14B8A6 60%, #6366F1 100%);
  box-shadow:
    0 8px 24px rgba(14, 165, 233, 0.35),
    0 2px 6px rgba(20, 184, 166, 0.2);
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.run-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
  box-shadow:
    0 14px 32px rgba(14, 165, 233, 0.45),
    0 4px 10px rgba(20, 184, 166, 0.28);
}
.run-btn:active { transform: translateY(0); filter: brightness(0.98); }
.run-btn.is-disabled,
.run-btn:disabled {
  background: linear-gradient(120deg, #cbd5e1, #94a3b8);
  box-shadow: none;
  color: #f8fafc;
  cursor: not-allowed;
}

/* ============ KPI 卡 ============ */
.kpi-box {
  position: relative;
  border-radius: 18px;
  padding: 18px 18px 16px;
  color: #0b3b66;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.6));
  border: 1px solid rgba(14, 165, 233, 0.18);
  box-shadow: 0 6px 18px rgba(15, 42, 92, 0.05);
  overflow: hidden;
  transition: transform 180ms ease, box-shadow 180ms ease;
}
.kpi-box:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(15, 42, 92, 0.1); }
.kpi-box::after {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, #0EA5E9, #14B8A6, #6366F1);
}
.kpi-box--0::after { background: linear-gradient(90deg, #0EA5E9, #38BDF8); }
.kpi-box--1::after { background: linear-gradient(90deg, #14B8A6, #2DD4BF); }
.kpi-box--2::after { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.kpi-box--3::after { background: linear-gradient(90deg, #F43F5E, #FB7185); }
.kpi-label { font-size: 12px; color: #5b738e; font-weight: 600; }
.kpi-value {
  font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace;
  font-size: 26px;
  font-weight: 700;
  color: #0c2c4d;
  margin-top: 6px;
  letter-spacing: 0.02em;
}
.kpi-hint { font-size: 11px; color: #8298b8; margin-top: 2px; }

/* ============ Legend pills ============ */
.legend-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.legend-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 12px;
  color: #5b738e;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(91, 115, 142, 0.2);
}
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot--cyan  { background: #0EA5E9; box-shadow: 0 0 8px #0EA5E9; }
.dot--teal  { background: #14B8A6; box-shadow: 0 0 8px #14B8A6; }
.dot--amber { background: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
.dot--rose  { background: #F43F5E; box-shadow: 0 0 8px #F43F5E; }

/* ============ 图表容器 ============ */
.chart-large { width: 100%; height: 380px; border-radius: 16px; }
.chart-medium { width: 100%; height: 240px; border-radius: 16px; }
.chart-glass {
  background: linear-gradient(180deg, rgba(240, 249, 255, 0.5), rgba(236, 254, 255, 0.2));
  border: 1px solid rgba(14, 165, 233, 0.12);
  box-shadow: 0 4px 12px rgba(15, 42, 92, 0.05);
  padding: 6px;
}

.canal-picker { min-width: 220px; }
.filter-select { min-width: 160px; }

.canal-edit-list { max-height: 360px; overflow-y: auto; }
.remove-cell { display: flex; align-items: center; padding-top: 18px; }

.config-body { max-height: calc(100vh - 340px); overflow-y: auto; padding-right: 6px; }
.config-body::-webkit-scrollbar,
.canal-edit-list::-webkit-scrollbar { width: 6px; }
.config-body::-webkit-scrollbar-thumb,
.canal-edit-list::-webkit-scrollbar-thumb { background: rgba(14, 165, 233, 0.25); border-radius: 3px; }

/* ============ Empty state ============ */
.empty-icon { font-size: 56px; color: #93c5fd; }

/* ============ 运行遮罩 ============ */
.running-overlay {
  margin-top: 16px;
  padding: 40px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(240, 249, 255, 0.7));
  border: 1px solid rgba(14, 165, 233, 0.2);
}
.running-content { text-align: center; }
.running-spinner {
  width: 48px; height: 48px;
  margin: 0 auto 12px;
  border-radius: 50%;
  border: 3px solid rgba(14, 165, 233, 0.2);
  border-top-color: #0EA5E9;
  animation: spin 0.9s linear infinite;
}
.running-title { font-size: 16px; font-weight: 700; color: #0c2c4d; }
.running-desc  { font-size: 12px; color: #5b738e; margin-top: 4px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ============ 违例表 ============ */
.violation-table :deep(th.el-table__cell) {
  background: rgba(240, 249, 255, 0.8) !important;
  color: #0c2c4d;
}

/* ============ 响应式 ============ */
@media (max-width: 1100px) {
  .chart-large { height: 320px; }
}
@media (max-width: 768px) {
  .chart-large { height: 280px; }
  .chart-medium { height: 220px; }
}
</style>
