<template>
  <div class="app-container agri-page canal-kinematic-page">
    <!-- ============ Hero ============ -->
    <section class="agri-page__hero canal-kinematic-hero">
      <div class="hero-decor" aria-hidden="true">
        <span class="hero-decor__wave hero-decor__wave--1" />
        <span class="hero-decor__wave hero-decor__wave--2" />
        <span class="hero-decor__wave hero-decor__wave--3" />
      </div>
      <div class="hero-content">
        <span class="agri-page__eyebrow canal-kinematic-eyebrow">KINEMATIC WAVE HYDRODYNAMICS</span>
        <h1 class="agri-page__title">渠系水动力学仿真</h1>
        <p class="agri-page__desc">
          基于 Kinematic Wave 隐式迎风有限差分法（Manning 摩阻 + Thomas 三对角追赶法），
          对渠段进行一维非恒定流仿真，返回时空水位/流量序列供 EChartsas 可视化展示。
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
        <span class="tag tag--cyan">Kinematic Wave</span>
        <span class="tag tag--teal">隐式迎风</span>
        <span class="tag tag--indigo">Thomas 追赶法</span>
        <span class="tag tag--violet">三角形分水</span>
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
                <div class="card-desc">选择渠段并配置分水口，上游边界自动按 Manning 均匀流初始化</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'" effect="dark" round>
                {{ resultError ? '仿真异常' : result ? '仿真完成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <div class="config-body">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="从渠系管理加载数据后选择渠段，配置分水口参数后提交仿真。"
              class="mb12"
            />

            <!-- 加载数据 -->
            <div class="db-row mb12">
              <el-button size="small" type="primary" plain @click="loadFromDb" :loading="loadingDb">
                加载渠系数据
              </el-button>
              <span class="muted-text">已加载 {{ dbCanals.length }} 条</span>
            </div>

            <!-- 渠段选择 -->
            <el-form-item label="选择渠段" class="mb12">
              <el-select
                v-model="form.canalId"
                placeholder="请先加载渠系数据，再选择渠段"
                filterable
                clearable
                style="width: 100%"
                :disabled="dbCanals.length === 0"
                @change="onCanalChange"
              >
                <el-option
                  v-for="c in dbCanals"
                  :key="c.canal_id"
                  :label="`${c.canal_id}${c.canal_name ? ' · ' + c.canal_name : ''} (Q=${c.design_flow} m³/s, L=${c.length}m)`"
                  :value="c.canal_id"
                />
              </el-select>
            </el-form-item>

            <!-- 渠段参数（自动填入） -->
            <template v-if="selectedCanal">
              <div class="param-grid mb12">
                <div class="param-item">
                  <span class="param-label">渠底宽 b (m)</span>
                  <el-input-number v-model="form.b" :min="0.1" :step="0.5" size="small" controls-position="right" />
                </div>
                <div class="param-item">
                  <span class="param-label">边坡 m</span>
                  <el-input-number v-model="form.m" :min="0" :step="0.1" size="small" controls-position="right" />
                </div>
                <div class="param-item">
                  <span class="param-label">糙率 n</span>
                  <el-input-number v-model="form.nManning" :min="0.001" :max="0.2" :step="0.001" :precision="3" size="small" controls-position="right" />
                </div>
                <div class="param-item">
                  <span class="param-label">坡降 S0</span>
                  <el-input-number v-model="form.S0" :min="0" :step="0.00001" :precision="6" size="small" controls-position="right" />
                </div>
                <div class="param-item">
                  <span class="param-label">上游流量 Q (m³/s)</span>
                  <el-input-number v-model="form.QUpstream" :min="0" :step="0.5" :precision="3" size="small" controls-position="right" />
                </div>
              </div>
            </template>

            <!-- Rating Curve Q-y 曲线（自动生成 + 可编辑） -->
            <div class="divider-soft" />
            <el-collapse v-model="ratingCurveOpen" class="rating-curve-collapse mb12">
              <el-collapse-item title="下游边界 · 流量-水位曲线（自动生成）" name="true">
                <template #title>
                  <div class="rating-curve-header">
                    <span class="rating-curve-title">下游边界 · 流量-水位曲线</span>
                    <el-tag size="small" type="success" effect="plain">自动生成</el-tag>
                  </div>
                </template>
                <div v-if="ratingCurvePoints.length > 0">
                  <div class="rating-curve-toolbar mb6">
                    <span style="font-size:11px;color:var(--text-secondary);">Manning 公式 · 共 {{ ratingCurvePoints.length }} 个点</span>
                    <el-button size="small" link type="primary" @click.stop="recomputeRatingCurve">
                      <el-icon><RefreshRight /></el-icon> 重新计算
                    </el-button>
                  </div>
                  <el-table :data="ratingCurvePoints" size="small" stripe max-height="220" style="font-size:12px;">
                    <el-table-column label="序号" type="index" width="50" align="center" />
                    <el-table-column label="y 水位 (m)" prop="y" align="right" min-width="120">
                      <template #default="{ row, $index }">
                        <el-input-number
                          v-model="ratingCurvePoints[$index].y"
                          :min="0.001" :step="0.05" :precision="4"
                          size="small" controls-position="right"
                          style="width: 110px;"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column label="Q 流量 (m³/s)" prop="Q" align="right" min-width="120">
                      <template #default="{ row, $index }">
                        <el-input-number
                          v-model="ratingCurvePoints[$index].Q"
                          :min="0" :step="0.5" :precision="4"
                          size="small" controls-position="right"
                          style="width: 110px;"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="60" align="center">
                      <template #default="{ $index }">
                        <el-button size="small" type="danger" link @click="ratingCurvePoints.splice($index, 1)">
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  <el-button size="small" plain class="mt6" @click="addRatingCurvePoint">
                    <el-icon><Plus /></el-icon> 添加点
                  </el-button>
                </div>
                <div v-else class="muted-text" style="font-size:12px;padding:8px 0;">
                  选择渠段后自动生成 Q-y 曲线
                </div>
              </el-collapse-item>
            </el-collapse>

            <div class="divider-soft" />

            <!-- 仿真时长 -->
            <div class="param-grid mb12">
              <div class="param-item">
                <span class="param-label">仿真时长 (min)</span>
                <el-input-number v-model="form.tfMin" :min="1" :max="14400" :step="10" size="small" controls-position="right" />
              </div>
              <div class="param-item">
                <span class="param-label">时间步长 dt (s)</span>
                <el-input-number v-model="form.dtSec" :min="0.1" :max="300" :step="1" :precision="1" size="small" controls-position="right" />
              </div>
              <div class="param-item">
                <span class="param-label">空间格点 nx</span>
                <el-input-number v-model="form.nx" :min="3" :max="500" :step="10" size="small" controls-position="right" />
              </div>
              <div class="param-item">
                <span class="param-label">输出间隔 (s)</span>
                <el-input-number v-model="form.outputIntervalSec" :min="1" :max="600" :step="5" size="small" controls-position="right" />
              </div>
            </div>

            <div class="divider-soft" />

            <!-- 上游流量模式 -->
            <el-form-item label="上游流量" class="mb12">
              <el-radio-group v-model="form.inflowMode" size="small">
                <el-radio-button value="steady">恒定</el-radio-button>
                <el-radio-button value="series">时序</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <template v-if="form.inflowMode === 'series'">
              <div class="mb8" style="font-size: 12px; color: var(--text-secondary);">流量时序（t_sec, Q_m3s），按 t_sec 升序</div>
              <div v-for="(pt, i) in form.inflowSeries" :key="i" class="inflow-row mb6">
                <el-input-number v-model="pt.tSec" :min="0" size="small" controls-position="right" placeholder="t (s)" style="width: 80px;" />
                <el-input-number v-model="pt.qM3s" :min="0" :step="0.1" :precision="3" size="small" controls-position="right" placeholder="Q (m³/s)" style="width: 100px;" />
                <el-button size="small" type="danger" link @click="removeInflowPoint(i)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <el-button size="small" plain @click="addInflowPoint" class="mb12">
                <el-icon><Plus /></el-icon> 添加时序点
              </el-button>
            </template>

            <div class="divider-soft" />

            <!-- 分水口配置 -->
            <div class="section-label mb8">
              分水口
              <el-button size="small" type="primary" link @click="addBranch">
                <el-icon><Plus /></el-icon> 添加
              </el-button>
            </div>

            <div v-if="form.branches.length === 0" class="muted-text mb12" style="font-size: 12px;">
              暂无分水口（可不填，渠段无分水时运行均匀流仿真）
            </div>

            <div v-for="(br, i) in form.branches" :key="i" class="branch-card mb8">
              <div class="branch-card__header">
                <span class="branch-card__title">分水口 #{{ i + 1 }}</span>
                <el-button size="small" type="danger" link @click="removeBranch(i)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <div class="branch-fields">
                <div class="branch-field">
                  <span class="field-label">位置 x (m)</span>
                  <el-input-number v-model="br.xPosition" :min="0" :step="100" :precision="1" size="small" controls-position="right" />
                </div>
                <div class="branch-field">
                  <span class="field-label">分水流量 Q (m³/s)</span>
                  <el-input-number v-model="br.QOfftake" :min="0" :step="0.1" :precision="3" size="small" controls-position="right" />
                </div>
                <div class="branch-field">
                  <span class="field-label">影响格点（半宽）</span>
                  <el-input-number v-model="br.spreadCells" :min="0" :max="20" :step="1" size="small" controls-position="right" />
                </div>
              </div>
            </div>

            <div class="divider-soft" />

            <!-- 操作按钮 -->
            <div class="action-row">
              <el-button
                type="primary"
                size="default"
                class="action-primary"
                :loading="submitting"
                :disabled="!form.canalId || submitting"
                @click="handleSubmit"
              >
                {{ submitting ? '仿真中...' : '提交仿真' }}
              </el-button>
              <el-button size="default" class="action-secondary" @click="handleReset" :disabled="submitting">
                重置
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- ============ 右侧：结果展示 ============ -->
      <el-col :xs="24" :lg="16" class="result-col">

        <!-- 未提交时的占位 -->
        <div v-if="!result && !resultError" class="placeholder glass-card result-card">
          <div class="placeholder-title">尚未提交仿真</div>
          <div class="placeholder-desc">
            选择渠段并配置参数后提交。后端返回时空水位/流量序列，
            将在右侧依次展示：KPI 概览、时空热力图、上下游时序曲线。
          </div>
        </div>

        <!-- 异常信息 -->
        <div v-else-if="resultError" class="placeholder glass-card result-card" style="border-color: rgba(245, 158, 11, 0.3); background: rgba(245, 158, 11, 0.05);">
          <div class="placeholder-title" style="color: #f59e0b;">仿真异常</div>
          <div class="placeholder-desc" style="color: #92400e;">{{ resultError }}</div>
          <el-button type="warning" size="small" class="mt16" @click="resultError = null">清除错误</el-button>
        </div>

        <!-- 仿真结果 -->
        <template v-else-if="result">
          <!-- KPI 概览 -->
          <div class="kpi-row">
            <div class="kpi-box kpi-box--0">
              <div class="kpi-label">上游流量</div>
              <div class="kpi-value">{{ fmtNumber(form.QUpstream, 3) }}<span class="kpi-unit">m³/s</span></div>
              <div class="kpi-foot">设计流量</div>
            </div>
            <div class="kpi-box kpi-box--1">
              <div class="kpi-label">下游流量</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.Q_downstream_final, 3) }}<span class="kpi-unit">m³/s</span></div>
              <div class="kpi-foot">末端出流</div>
            </div>
            <div class="kpi-box kpi-box--2">
              <div class="kpi-label">上游水深</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.y_upstream_final, 3) }}<span class="kpi-unit">m</span></div>
              <div class="kpi-foot">仿真末刻</div>
            </div>
            <div class="kpi-box kpi-box--3">
              <div class="kpi-label">下游水深</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.y_downstream_final, 3) }}<span class="kpi-unit">m</span></div>
              <div class="kpi-foot">仿真末刻</div>
            </div>
            <div class="kpi-box kpi-box--4">
              <div class="kpi-label">分水流总量</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.total_offtake_m3s, 3) }}<span class="kpi-unit">m³/s</span></div>
              <div class="kpi-foot">{{ result.branches?.length || 0 }} 个分水口</div>
            </div>
            <div class="kpi-box kpi-box--5">
              <div class="kpi-label">仿真规模</div>
              <div class="kpi-value">{{ result.channel?.nx }}<span class="kpi-unit">格点</span></div>
              <div class="kpi-foot">L={{ fmtNumber(result.channel?.L, 0) }}m · {{ fmtNumber(result.channel?.tf, 1) }}s</div>
            </div>
          </div>

          <!-- 时空热力图（水位） -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">时空水位分布</span>
                  <span class="chart-sub">x=空间格点 (m) · y=时间 (s) · 颜色=水深 (m)</span>
                </div>
                <div class="chart-tags">
                  <el-tag size="small" type="info">热力图</el-tag>
                </div>
              </div>
            </template>
            <div ref="waterLevelHeatmapRef" class="chart chart--heatmap" />
          </el-card>

          <!-- 流量时空3D曲面 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">流量时空3D曲面</span>
                  <span class="chart-sub">x=空间 (km) · t=时间 (h) · z=Q 流量 (m³/s)</span>
                </div>
                <div class="chart-tags">
                  <el-tag size="small" type="warning">3D 曲面</el-tag>
                </div>
              </div>
            </template>
            <div ref="flowSeriesRef" class="chart chart--surface" />
          </el-card>

          <!-- 水深时空3D曲面 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">水深时空3D曲面</span>
                  <span class="chart-sub">x=空间 (km) · t=时间 (h) · z=水深 y (m)</span>
                </div>
                <div class="chart-tags">
                  <el-tag size="small" type="primary">3D 曲面</el-tag>
                </div>
              </div>
            </template>
            <div ref="depthSeriesRef" class="chart chart--surface" />
          </el-card>

          <!-- 渠段剖面（最终状态） -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">渠段剖面（仿真末刻）</span>
                  <span class="chart-sub">沿程水位 / 流量分布</span>
                </div>
              </div>
            </template>
            <div ref="profileRef" class="chart" />
          </el-card>

          <!-- 分水口信息表 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16" v-if="result.branches?.length">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">分水口配置</span>
                  <span class="chart-sub">{{ result.branches.length }} 个分水口</span>
                </div>
              </div>
            </template>
            <el-table :data="result.branches" stripe size="small">
              <el-table-column label="#" type="index" width="50" align="center" />
              <el-table-column label="分水口ID" prop="id" min-width="120" />
              <el-table-column label="位置 x (m)" prop="x_position" min-width="100" align="right">
                <template #default="{ row }">{{ fmtNumber(row.x_position, 1) }}</template>
              </el-table-column>
              <el-table-column label="分水流量 Q (m³/s)" prop="Q_offtake" min-width="140" align="right">
                <template #default="{ row }">{{ fmtNumber(row.Q_offtake, 3) }}</template>
              </el-table-column>
              <el-table-column label="影响半宽 (格点)" prop="spread_cells" min-width="120" align="right" />
            </el-table>
          </el-card>
        </template>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Plus, Promotion, RefreshRight } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-gl'
import { listCanal as fetchCanals, runKinematicSim } from '@/api/agriculture/canal'

const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

// ---------------------------------------------------------------------------
// 图表实例
// ---------------------------------------------------------------------------
let waterLevelHeatmapChart = null
let flowSeriesChart = null
let depthSeriesChart = null
let profileChart = null

const waterLevelHeatmapRef = ref(null)
const flowSeriesRef = ref(null)
const depthSeriesRef = ref(null)
const profileRef = ref(null)

// ---------------------------------------------------------------------------
// 数据状态
// ---------------------------------------------------------------------------
const dbCanals = ref([])
const loadingDb = ref(false)
const submitting = ref(false)
const result = ref(null)
const resultError = ref(null)

// ---------------------------------------------------------------------------
// Rating Curve（Q-y 曲线）计算
// ---------------------------------------------------------------------------
function areaTopwidth(y, b, m) {
  const A = (b + m * y) * y
  const T = b + 2 * m * y
  return { A, T }
}

function computeRatingCurve(b, m, n_Manning, S0) {
  if (!b || !n_Manning || !S0 || S0 <= 0 || n_Manning <= 0) return []
  const n = n_Manning
  const Sf = Math.sqrt(S0)

  function manningNormalDepth(Q, b, m, n, S0) {
    if (Q <= 0 || n <= 0 || S0 <= 0) return 0.1
    let lo = 0.001, hi = 50.0
    for (let iter = 0; iter < 80; iter++) {
      const mid = (lo + hi) / 2
      const { A } = areaTopwidth(mid, b, m)
      const P = b + 2 * mid * Math.sqrt(1 + m * m)
      const R = A / P
      const Qmid = A * Math.pow(R, 2 / 3) * Math.sqrt(S0) / n
      if (Qmid < Q) lo = mid
      else hi = mid
    }
    return (lo + hi) / 2
  }

  const y0 = manningNormalDepth(form.QUpstream || 10.0, b, m, n, S0)
  const yMax = Math.max(2.5 * y0, 0.5)

  const points = []
  const step = (yMax - 0.05) / 19
  for (let i = 0; i < 20; i++) {
    const y = parseFloat((0.05 + i * step).toFixed(4))
    const { A } = areaTopwidth(y, b, m)
    const P = b + 2 * y * Math.sqrt(1 + m * m)
    const R = A / P
    const Q = parseFloat((A * Math.pow(R, 2 / 3) * Sf / n).toFixed(4))
    points.push({ y, Q })
  }
  return points
}

// ---------------------------------------------------------------------------
// 表单
// ---------------------------------------------------------------------------
const form = reactive({
  canalId: '',
  b: 8.0,
  m: 1.5,
  nManning: 0.025,
  S0: 0.0003,
  QUpstream: 10.0,
  tfMin: 60,
  dtSec: 10,
  nx: 51,
  outputIntervalSec: 5,
  inflowMode: 'steady',
  inflowSeries: [],
  branches: [],
  apiKey: IRRIGATION_API_KEY,
})

const selectedCanal = ref(null)
const ratingCurvePoints = ref([])
const ratingCurveOpen = ref([])

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------
function fmtNumber(v, decimals = 3) {
  if (v === null || v === undefined) return '—'
  return Number(v).toFixed(decimals)
}

function destroyAllCharts() {
  waterLevelHeatmapChart?.dispose(); waterLevelHeatmapChart = null
  flowSeriesChart?.dispose(); flowSeriesChart = null
  depthSeriesChart?.dispose(); depthSeriesChart = null
  profileChart?.dispose(); profileChart = null
}

function initChart(container, instance) {
  if (!container) return null
  const chart = echarts.init(container)
  return chart
}

// ---------------------------------------------------------------------------
// 数据加载
// ---------------------------------------------------------------------------
async function loadFromDb() {
  loadingDb.value = true
  try {
    const res = await fetchCanals({ pageNum: 1, pageSize: 1000 })
    const rows = res?.rows || res?.data?.rows || []
    dbCanals.value = rows
      .map(r => ({
        canal_id: r.canal_id ?? r.canalId,
        canal_name: r.canal_name ?? r.canalName,
        parent_id: r.parent_id ?? r.parentId ?? null,
        level: r.level != null ? String(r.level) : null,
        length: parseFloat(r.length ?? r.length ?? 0),
        design_flow: parseFloat(r.design_flow ?? r.designFlow ?? 0),
        bottom_width: parseFloat(r.bottom_width ?? r.bottomWidth ?? 0),
        slope: parseFloat(r.slope ?? 0),
        side_slope: parseFloat(r.side_slope ?? 1.5),
        roughness: parseFloat(r.roughness ?? 0.015),
        water_demand: parseFloat(r.water_demand ?? r.waterDemand ?? 0),
      }))
      .filter(r => r.canal_id != null)
    if (dbCanals.value.length === 0) ElMessage.warning('未加载到渠系数据')
    else ElMessage.success(`已加载 ${dbCanals.value.length} 条渠段`)
  } catch (e) {
    ElMessage.error('加载渠系数据失败: ' + (e.message || String(e)))
  } finally {
    loadingDb.value = false
  }
}

function onCanalChange(canalId) {
  if (!canalId) { selectedCanal.value = null; ratingCurvePoints.value = []; result.value = null; resultError.value = null; return }
  const canal = dbCanals.value.find(c => c.canal_id === canalId)
  if (!canal) return
  selectedCanal.value = canal
  form.b = Number(canal.bottom_width) || 8.0
  form.m = Number(canal.side_slope) || 1.5
  form.nManning = Number(canal.roughness) || 0.025
  form.S0 = Number(canal.slope) || 0.0003
  form.QUpstream = Number(canal.design_flow) || 10.0
  ratingCurvePoints.value = computeRatingCurve(form.b, form.m, form.nManning, form.S0)
  ratingCurveOpen.value = ['true']
  result.value = null
  resultError.value = null
  buildDefaultBranches(canal)
}

function buildDefaultBranches(canal) {
  form.branches = []
  // 从全量数据中找该渠段的子渠道作为默认分水口
  const children = dbCanals.value.filter(c => c.parent_id === canal.canal_id)
  children.forEach(child => {
    // x_position 估算：按子渠道在渠段中的比例位置
    // 实际需从 position 字段获取，此处用 index * 1/3 渠长做占位
    const L = Number(canal.length) || 10000
    const n = children.length
    const idx = children.indexOf(child)
    const xPos = L * (0.2 + 0.6 * idx / Math.max(n - 1, 1))
    form.branches.push({
      id: child.canal_id,
      xPosition: Math.round(xPos),
      QOfftake: Number(child.design_flow) || 1.0,
      spreadCells: 3,
    })
  })
}

function recomputeRatingCurve() {
  ratingCurvePoints.value = computeRatingCurve(form.b, form.m, form.nManning, form.S0)
}

function addRatingCurvePoint() {
  const last = ratingCurvePoints.value[ratingCurvePoints.value.length - 1]
  const y0 = last ? last.y * 1.2 : 0.5
  const { A } = areaTopwidth(y0, form.b, form.m)
  const P = form.b + 2 * y0 * Math.sqrt(1 + form.m * form.m)
  const R = A / P
  const Q = parseFloat((A * Math.pow(R, 2 / 3) * Math.sqrt(form.S0) / form.nManning).toFixed(4))
  ratingCurvePoints.value.push({ y: parseFloat(y0.toFixed(4)), Q })
  ratingCurvePoints.value.sort((a, b) => a.y - b.y)
}

function removeRatingCurvePoint(index) {
  ratingCurvePoints.value.splice(index, 1)
}

// ---------------------------------------------------------------------------
// 分水口操作
// ---------------------------------------------------------------------------
function addBranch() {
  const L = Number(selectedCanal.value?.length) || 10000
  form.branches.push({
    id: `B${form.branches.length + 1}`,
    xPosition: Math.round(L * 0.5),
    QOfftake: 1.0,
    spreadCells: 3,
  })
}

function removeBranch(index) {
  form.branches.splice(index, 1)
}

// ---------------------------------------------------------------------------
// 入流时序操作
// ---------------------------------------------------------------------------
function addInflowPoint() {
  const last = form.inflowSeries[form.inflowSeries.length - 1]
  const t0 = last ? Number(last.tSec) : 0
  const q0 = last ? Number(last.qM3s) : form.QUpstream
  form.inflowSeries.push({ tSec: t0 + 600, qM3s: q0 })
}

function removeInflowPoint(index) {
  form.inflowSeries.splice(index, 1)
}

// ---------------------------------------------------------------------------
// 提交仿真
// ---------------------------------------------------------------------------
async function handleSubmit() {
  if (!form.canalId) { ElMessage.warning('请选择渠段'); return }
  const canal = selectedCanal.value
  if (!canal) return

  submitting.value = true
  resultError.value = null
  result.value = null

  const branches = form.branches.map(br => ({
    id: br.id,
    x_position: Number(br.xPosition),
    Q_offtake: Number(br.QOfftake),
    spread_cells: Number(br.spreadCells),
  }))

  const inflowSeries = form.inflowMode === 'series' && form.inflowSeries.length >= 2
    ? form.inflowSeries.map(pt => ({ t_sec: Number(pt.tSec), q_m3s: Number(pt.qM3s) }))
    : null

  const payload = {
    canal_id: form.canalId,
    L: Number(canal.length) || 10000,
    nx: Number(form.nx),
    b: Number(form.b),
    m: Number(form.m),
    n_Manning: Number(form.nManning),
    S0: Number(form.S0),
    Q_upstream: Number(form.QUpstream),
    tf: Number(form.tfMin) * 60,
    dt: Number(form.dtSec),
    output_interval_sec: Number(form.outputIntervalSec),
    branches,
    inflow_series: inflowSeries,
    use_rating_curve: ratingCurvePoints.value.length >= 2,
    y_ds_curve: ratingCurvePoints.value.map(p => Number(p.y)),
    Q_ds_curve: ratingCurvePoints.value.map(p => Number(p.Q)),
  }

  try {
    const data = await runKinematicSim(payload, form.apiKey)
    result.value = data
    ElMessage.success('仿真完成')
  } catch (e) {
    resultError.value = e.message || String(e)
    ElMessage.error('仿真失败: ' + resultError.value)
  } finally {
    submitting.value = false
  }
}

function handleReset() {
  form.canalId = ''
  form.inflowMode = 'steady'
  form.inflowSeries = []
  form.branches = []
  form.tfMin = 60
  form.dtSec = 10
  form.nx = 51
  form.outputIntervalSec = 5
  selectedCanal.value = null
  ratingCurvePoints.value = []
  ratingCurveOpen.value = []
  result.value = null
  resultError.value = null
}

// ---------------------------------------------------------------------------
// 图表渲染
// ---------------------------------------------------------------------------
const COLOR_PALETTE = [
  '#5b8def', '#22c55e', '#f97316', '#ef4444', '#a855f7',
  '#14b8a6', '#eab308', '#06b6d4', '#ec4899', '#84cc16',
]

function renderAllCharts() {
  if (!result.value) return
  ;[waterLevelHeatmapChart, flowSeriesChart, depthSeriesChart, profileChart].forEach(c => {
    if (c) { c.dispose(); c = null }
  })
  renderWaterLevelHeatmap()
  renderFlowSeries()
  renderDepthSeries()
  renderProfile()
}

function renderWaterLevelHeatmap() {
  waterLevelHeatmapChart = initChart(waterLevelHeatmapRef.value, waterLevelHeatmapChart)
  if (!waterLevelHeatmapChart) return

  const spacetime = result.value?.spacetime
  const channel = result.value?.channel
  if (!spacetime || !channel) return

  const nx = Number(channel.nx) || 51
  const L = Number(channel.L) || 10000
  const times = spacetime.times || []
  const wlm = spacetime.water_level_matrix || []

  if (times.length === 0 || wlm.length === 0) {
    waterLevelHeatmapChart.setOption({ title: { text: '无时空数据', left: 'center' } })
    return
  }

  const xData = Array.from({ length: nx }, (_, i) => parseFloat((i * L / (nx - 1)).toFixed(1)))
  const data = []
  for (let tIdx = 0; tIdx < times.length; tIdx++) {
    const row = wlm[tIdx]
    if (!row) continue
    for (let xIdx = 0; xIdx < Math.min(row.length, nx); xIdx++) {
      data.push([xIdx, tIdx, parseFloat(Number(row[xIdx]).toFixed(4))])
    }
  }

  const allVals = data.map(d => d[2])
  const minV = Math.min(...allVals)
  const maxV = Math.max(...allVals, 1)

  waterLevelHeatmapChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p) => `x=${xData[p.data[0]]}m<br/>t=${times[p.data[1]]}s<br/>h=${p.data[2].toFixed(4)}m`
    },
    grid: { top: 30, left: 60, right: 60, bottom: 50 },
    xAxis: { type: 'category', name: 'x (m)', nameLocation: 'middle', nameGap: 30, data: xData, axisLabel: { fontSize: 10, interval: Math.floor(nx / 8) } },
    yAxis: { type: 'category', name: 't (s)', nameLocation: 'middle', nameGap: 40, data: times, axisLabel: { fontSize: 10 } },
    visualMap: {
      show: true, calculable: true,
      min: minV, max: maxV,
      orient: 'vertical', right: 10, top: 'center',
      text: [maxV.toFixed(2), minV.toFixed(2)],
      inRange: { color: ['#eff6ff', '#3b82f6', '#1d4ed8'] }
    },
    series: [{
      type: 'heatmap',
      data,
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.3)' } }
    }]
  })
}

function renderFlowSeries() {
  flowSeriesChart = initChart(flowSeriesRef.value, flowSeriesChart)
  if (!flowSeriesChart) return

  const spacetime = result.value?.spacetime
  const channel = result.value?.channel
  if (!spacetime || !channel) {
    const ts = result.value?.timeseries
    if (!ts) return
    const t = ts.t || []
    const qUp = ts.Q_upstream || []
    const qDown = ts.Q_downstream || []
    flowSeriesChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: ['上游流量', '下游流量'], top: 0, textStyle: { fontSize: 12 } },
      grid: { top: 40, left: 55, right: 20, bottom: 40 },
      xAxis: { type: 'category', data: t, name: 't (s)', nameLocation: 'middle', nameGap: 30, axisLabel: { fontSize: 11, interval: Math.max(0, Math.floor(t.length / 6) - 1) } },
      yAxis: { type: 'value', name: 'Q (m³/s)', axisLabel: { fontSize: 11 } },
      series: [
        { name: '上游流量', type: 'line', data: qUp, smooth: true, itemStyle: { color: '#3b82f6' }, lineStyle: { width: 2 }, showSymbol: false },
        { name: '下游流量', type: 'line', data: qDown, smooth: true, itemStyle: { color: '#22c55e' }, lineStyle: { width: 2 }, showSymbol: false },
      ]
    })
    return
  }

  const nx = Number(channel.nx) || 51
  const L = Number(channel.L) || 10000
  const times = spacetime.times || []
  const qm = spacetime.flow_rate_matrix || []

  if (times.length < 2 || qm.length < 2 || nx < 2) {
    flowSeriesChart.setOption({ title: { text: '无流量时空数据', left: 'center' } })
    return
  }

  const xData = Array.from({ length: nx }, (_, i) => parseFloat((i * L / (nx - 1) / 1000).toFixed(4)))
  const tHours = times.map(s => parseFloat((s / 3600).toFixed(4)))
  const xMax = xData[xData.length - 1]
  const tMax = tHours[tHours.length - 1]

  const data = []
  for (let tIdx = 0; tIdx < times.length; tIdx++) {
    const row = qm[tIdx]
    if (!row) continue
    for (let xIdx = 0; xIdx < Math.min(row.length, nx); xIdx++) {
      data.push([xData[xIdx], tHours[tIdx], parseFloat(Number(row[xIdx]).toFixed(4))])
    }
  }

  const allVals = data.map(d => d[2])
  const minV = Math.min(...allVals)
  const maxV = Math.max(...allVals, minV + 0.01)

  flowSeriesChart.setOption({
    notMerge: true,
    tooltip: {
      trigger: 'item',
      formatter: (p) => `x=${p.data[0].toFixed(1)} km<br/>t=${p.data[1].toFixed(3)} h<br/>Q=${p.data[2].toFixed(4)} m³/s`
    },
    visualMap: {
      show: true, calculable: true,
      min: minV, max: maxV,
      orient: 'vertical', right: 10, top: 'center',
      text: [maxV.toFixed(2), minV.toFixed(2)],
      inRange: { color: ['#fef3c7', '#fbbf24', '#f97316', '#dc2626'] }
    },
    xAxis3D: { type: 'value', name: 'x (km)', nameLocation: 'middle', nameGap: 35, min: 0, max: xMax, axisLabel: { fontSize: 9 } },
    yAxis3D: { type: 'value', name: 't (h)', nameLocation: 'middle', nameGap: 35, min: 0, max: tMax, axisLabel: { fontSize: 9 } },
    zAxis3D: { type: 'value', name: 'Q (m³/s)', nameLocation: 'middle', nameGap: 55, axisLabel: { fontSize: 9 } },
    grid3D: {
      top: 20, left: 15, right: 60, bottom: 15,
      viewControl: { alpha: 40, beta: 215, distance: 240, minDistance: 60, maxDistance: 600, rotateSensitivity: 1, zoomSensitivity: 1 },
    },
    series: [{
      type: 'surface',
      data,
      shading: 'color',
      silent: true,
      dataShape: [times.length, nx],
      wireframe: { show: true, lineStyle: { color: 'rgba(0,0,0,0.08)', width: 1 } },
      itemStyle: { borderWidth: 0 },
      emphasis: { disabled: true },
    }]
  })
}

function renderDepthSeries() {
  depthSeriesChart = initChart(depthSeriesRef.value, depthSeriesChart)
  if (!depthSeriesChart) return

  const spacetime = result.value?.spacetime
  const channel = result.value?.channel
  if (!spacetime || !channel) {
    const ts = result.value?.timeseries
    if (!ts) return
    const t = ts.t || []
    const yUp = ts.y_upstream || []
    const yDown = ts.y_downstream || []
    depthSeriesChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: ['上游水深', '下游水深'], top: 0, textStyle: { fontSize: 12 } },
      grid: { top: 40, left: 55, right: 20, bottom: 40 },
      xAxis: { type: 'category', data: t, name: 't (s)', nameLocation: 'middle', nameGap: 30, axisLabel: { fontSize: 11, interval: Math.max(0, Math.floor(t.length / 6) - 1) } },
      yAxis: { type: 'value', name: 'h (m)', axisLabel: { fontSize: 11 } },
      series: [
        { name: '上游水深', type: 'line', data: yUp, smooth: true, itemStyle: { color: '#f97316' }, lineStyle: { width: 2 }, showSymbol: false },
        { name: '下游水深', type: 'line', data: yDown, smooth: true, itemStyle: { color: '#a855f7' }, lineStyle: { width: 2 }, showSymbol: false },
      ]
    })
    return
  }

  const nx = Number(channel.nx) || 51
  const L = Number(channel.L) || 10000
  const times = spacetime.times || []
  const wlm = spacetime.water_level_matrix || []

  if (times.length < 2 || wlm.length < 2 || nx < 2) {
    depthSeriesChart.setOption({ title: { text: '无水位时空数据', left: 'center' } })
    return
  }

  const xData = Array.from({ length: nx }, (_, i) => parseFloat((i * L / (nx - 1) / 1000).toFixed(4)))
  const tHours = times.map(s => parseFloat((s / 3600).toFixed(4)))
  const xMax = xData[xData.length - 1]
  const tMax = tHours[tHours.length - 1]

  const data = []
  for (let tIdx = 0; tIdx < times.length; tIdx++) {
    const row = wlm[tIdx]
    if (!row) continue
    for (let xIdx = 0; xIdx < Math.min(row.length, nx); xIdx++) {
      data.push([xData[xIdx], tHours[tIdx], parseFloat(Number(row[xIdx]).toFixed(4))])
    }
  }

  const allVals = data.map(d => d[2])
  const minV = Math.min(...allVals)
  const maxV = Math.max(...allVals, minV + 0.01)

  depthSeriesChart.setOption({
    notMerge: true,
    tooltip: {
      trigger: 'item',
      formatter: (p) => `x=${p.data[0].toFixed(1)} km<br/>t=${p.data[1].toFixed(3)} h<br/>y=${p.data[2].toFixed(4)} m`
    },
    visualMap: {
      show: true, calculable: true,
      min: minV, max: maxV,
      orient: 'vertical', right: 10, top: 'center',
      text: [maxV.toFixed(2), minV.toFixed(2)],
      inRange: { color: ['#eff6ff', '#3b82f6', '#1d4ed8'] }
    },
    xAxis3D: { type: 'value', name: 'x (km)', nameLocation: 'middle', nameGap: 35, min: 0, max: xMax, axisLabel: { fontSize: 9 } },
    yAxis3D: { type: 'value', name: 't (h)', nameLocation: 'middle', nameGap: 35, min: 0, max: tMax, axisLabel: { fontSize: 9 } },
    zAxis3D: { type: 'value', name: 'Water depth y (m)', nameLocation: 'middle', nameGap: 65, axisLabel: { fontSize: 9 } },
    grid3D: {
      top: 20, left: 15, right: 60, bottom: 15,
      viewControl: { alpha: 40, beta: 215, distance: 240, minDistance: 60, maxDistance: 600, rotateSensitivity: 1, zoomSensitivity: 1 },
    },
    series: [{
      type: 'surface',
      data,
      shading: 'color',
      silent: true,
      dataShape: [times.length, nx],
      wireframe: { show: true, lineStyle: { color: 'rgba(0,0,0,0.08)', width: 1 } },
      itemStyle: { borderWidth: 0 },
      emphasis: { disabled: true },
    }]
  })
}

function renderProfile() {
  profileChart = initChart(profileRef.value, profileChart)
  if (!profileChart) return

  const fs = result.value?.final_state
  if (!fs) return

  const x = fs.x || []
  const y = fs.y || []
  const Q = fs.Q || []
  const n = x.length

  profileChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['水位 h (m)', '流量 Q (m³/s)'], top: 0, textStyle: { fontSize: 12 } },
    grid: { top: 40, left: 55, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: x, name: 'x (m)', nameLocation: 'middle', nameGap: 30, axisLabel: { fontSize: 11, interval: Math.max(0, Math.floor(n / 6) - 1) } },
    yAxis: [
      { type: 'value', name: 'h (m)', nameTextStyle: { fontSize: 11 }, axisLabel: { fontSize: 11 } },
      { type: 'value', name: 'Q (m³/s)', nameTextStyle: { fontSize: 11 }, axisLabel: { fontSize: 11 } },
    ],
    series: [
      { name: '水位 h (m)', type: 'line', yAxisIndex: 0, data: y, smooth: true, itemStyle: { color: '#3b82f6' }, lineStyle: { width: 2 }, showSymbol: false },
      { name: '流量 Q (m³/s)', type: 'line', yAxisIndex: 1, data: Q, smooth: true, itemStyle: { color: '#22c55e' }, lineStyle: { width: 2, type: 'dashed' }, showSymbol: false },
    ]
  })
}

// ---------------------------------------------------------------------------
// 监听结果变化，重绘图表
// ---------------------------------------------------------------------------
watch(result, async (val) => {
  if (!val) return
  await nextTick()
  requestAnimationFrame(() => {
    renderAllCharts()
  })
})

// ---------------------------------------------------------------------------
// 响应式
// ---------------------------------------------------------------------------
window.addEventListener('resize', () => {
  ;[waterLevelHeatmapChart, flowSeriesChart, depthSeriesChart, profileChart].forEach(c => { if (c) c.resize() })
})

onUnmounted(() => {
  destroyAllCharts()
})
</script>

<style scoped>
.canal-kinematic-page { padding-bottom: 28px; }

.agri-page__siblings { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.sibling-link { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: var(--surface-soft-bg); border: 1px solid var(--hairline-color); color: var(--text-primary); font-size: 0.867em; text-decoration: none; transition: all 0.2s ease; }
.sibling-link:hover { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary-light-5); color: var(--el-color-primary); }

.page-layout { align-items: stretch; }
.db-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.muted-text { color: var(--text-secondary); font-size: 12px; margin-left: 8px; }
.divider-soft { height: 1px; margin: 8px 0 12px; background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.25), transparent); }
.section-label { font-size: 13px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; justify-content: space-between; }
.mb6 { margin-bottom: 6px; }
.mb8 { margin-bottom: 8px; }
.mb12 { margin-bottom: 12px; }
.mt16 { margin-top: 16px; }
.mr6 { margin-right: 6px; }

.param-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.param-item { display: flex; flex-direction: column; gap: 4px; }
.param-label { font-size: 11px; color: var(--text-secondary); }

.config-col { display: flex; min-width: 0; }
.config-col .config-card { display: flex; flex-direction: column; flex: 1 1 auto; width: 100%; }
.config-col .config-card :deep(.el-card__body) { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
.config-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding-right: 4px; }

.branch-card { border: 1px solid rgba(14, 165, 233, 0.2); border-radius: 10px; padding: 8px 10px; background: rgba(14, 165, 233, 0.03); }
.branch-card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.branch-card__title { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.branch-fields { display: flex; flex-direction: column; gap: 4px; }
.branch-field { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.field-label { font-size: 11px; color: var(--text-secondary); white-space: nowrap; }

.inflow-row { display: flex; align-items: center; gap: 4px; }

.action-row { display: flex; gap: 10px; margin-top: 12px; }
.action-primary { flex: 1; }
.action-secondary { flex: 0 0 auto; }

.config-card, .chart-card { border-radius: 20px; border: 1px solid var(--hairline-color); box-shadow: var(--content-shadow-soft); overflow: hidden; }
.result-card { border-radius: 20px; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.card-title { font-size: 18px; font-weight: 650; }
.card-desc { margin-top: 6px; color: var(--text-secondary); line-height: 1.6; }
.chart-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.chart-title { font-size: 1em; font-weight: 650; }
.chart-sub { display: block; margin-top: 4px; font-size: 0.8em; color: var(--text-secondary); }
.chart-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.chart { width: 100%; height: 280px; }
.chart--heatmap { height: 320px; }
.chart--surface { height: 360px; }

.placeholder { padding: 56px 20px; text-align: center; background: var(--surface-soft-bg); border-radius: 20px; border: 1px dashed var(--hairline-color); }
.placeholder-title { font-size: 1.1em; font-weight: 650; color: var(--text-primary); margin-bottom: 10px; }
.placeholder-desc { font-size: 0.875em; color: var(--text-secondary); line-height: 1.7; }

.kpi-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.kpi-box { padding: 14px 16px; border-radius: 16px; border: 1px solid var(--hairline-color); background: var(--surface-soft-bg); }
.kpi-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.kpi-value { font-size: 1.5em; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.kpi-unit { font-size: 0.55em; font-weight: 400; color: var(--text-secondary); margin-left: 3px; }
.kpi-foot { margin-top: 4px; font-size: 11px; color: var(--text-secondary); }

/* Hero 样式 */
.canal-kinematic-hero { position: relative; overflow: hidden; border-radius: 20px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0abfc14 100%); border: 1px solid rgba(14, 165, 233, 0.15); padding: 28px 32px; margin-bottom: 20px; }
.canal-kinematic-eyebrow { background: linear-gradient(120deg, rgba(14, 165, 233, 0.18), rgba(20, 184, 166, 0.18)); color: #0e7490; border: 1px solid rgba(14, 165, 233, 0.3); border-radius: 999px; padding: 4px 12px; font-size: 0.75em; font-weight: 700; letter-spacing: 0.08em; }
.canal-kinematic-hero .agri-page__title { background: linear-gradient(120deg, #0c4a6e 0%, #0e7490 50%, #6d28d9 100%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.canal-kinematic-hero .agri-page__desc { color: #1e5577; font-size: 0.95em; line-height: 1.7; margin-top: 8px; }
.canal-kinematic-hero .hero-decor { position: absolute; inset: 0; pointer-events: none; z-index: 0; }
.canal-kinematic-hero .hero-content { position: relative; z-index: 2; }
.canal-kinematic-hero .agri-page__tags { position: absolute; top: 20px; right: 24px; display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
.canal-kinematic-hero .tag { padding: 3px 10px; border-radius: 999px; font-size: 0.75em; font-weight: 600; border: 1px solid; }
.tag--cyan { background: rgba(14, 165, 233, 0.1); color: #0369a1; border-color: rgba(14, 165, 233, 0.3); }
.tag--teal { background: rgba(20, 184, 166, 0.1); color: #0f766e; border-color: rgba(20, 184, 166, 0.3); }
.tag--indigo { background: rgba(99, 102, 241, 0.1); color: #4338ca; border-color: rgba(99, 102, 241, 0.3); }
.tag--violet { background: rgba(139, 92, 246, 0.1); color: #6d28d9; border-color: rgba(139, 92, 246, 0.3); }

.rating-curve-collapse { border-radius: 10px; overflow: hidden; }
.rating-curve-collapse :deep(.el-collapse-item__header) { padding: 0 12px; font-size: 13px; font-weight: 600; background: rgba(34, 197, 94, 0.05); border-color: rgba(34, 197, 94, 0.15); border-radius: 10px; }
.rating-curve-collapse :deep(.el-collapse-item__wrap) { border-color: rgba(34, 197, 94, 0.15); }
.rating-curve-collapse :deep(.el-collapse-item__content) { padding: 10px 8px 8px; }
.rating-curve-header { display: flex; align-items: center; gap: 8px; }
.rating-curve-title { font-size: 13px; font-weight: 600; }
.rating-curve-toolbar { display: flex; align-items: center; justify-content: space-between; }
.mt6 { margin-top: 6px; }
</style>
