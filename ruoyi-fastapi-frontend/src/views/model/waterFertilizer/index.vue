<template>
  <div class="app-container agri-page water-fertilizer-page">
    <section class="agri-page__hero water-fertilizer-hero">
      <div class="hero-content">
        <span class="agri-page__eyebrow">NSGA-III WATER-FERTILIZER REGULATION</span>
        <h1 class="agri-page__title">水肥调控模型</h1>
        <p class="agri-page__desc">
          基于已入库的逐日降雨、蒸散发和水层阈值数据，协同优化水稻灌溉过程与施氮量，
          输出推荐解、帕累托解集和逐日水层变化。
        </p>
        <div class="agri-page__siblings">
          <router-link to="/model/irrigation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>灌溉决策</span>
          </router-link>
          <router-link to="/model/water-soil-resource" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>水土资源配置</span>
          </router-link>
          <router-link to="/model/crop-growth" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>作物生长模拟</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="resource-tag">NSGA-III</span>
        <span class="resource-tag resource-tag--green">TOPSIS 推荐解</span>
        <span class="resource-tag resource-tag--orange">水肥一体</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <el-col :xs="24" :lg="9">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">模型参数</div>
                <div class="card-desc">先查询入库时序数据，再运行多目标优化。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'">
                {{ resultError ? '接口异常' : result ? '方案已生成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <el-form :model="form" label-position="top" size="small" class="fertilizer-form">
            <el-form-item label="接口 API Key" required>
              <el-input v-model="form.apiKey" type="password" show-password clearable placeholder="X-Irrigation-Api-Key" />
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="开始日期" required>
                  <el-date-picker v-model="form.startDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="结束日期" required>
                  <el-date-picker v-model="form.endDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="action-row compact">
              <el-button :loading="loadingData" @click="loadPreview">
                <el-icon><Search /></el-icon>
                查询时序数据
              </el-button>
              <el-button :loading="loadingSummary" plain @click="loadAvailableRange">
                使用库内日期
              </el-button>
              <el-tag v-if="previewTotal" type="success">共 {{ previewTotal }} 条</el-tag>
            </div>
            <div v-if="availableRange.total" class="range-hint">
              库内日期范围：{{ availableRange.startDate }} 至 {{ availableRange.endDate }}，共 {{ availableRange.total }} 条。
            </div>

            <el-divider content-position="left">产量响应与水量参数</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="最大产量 kg/hm²">
                  <el-input-number v-model="form.yieldMax" :min="1" :step="100" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="每日最大灌溉 mm">
                  <el-input-number v-model="form.maxIrrigation" :min="0.1" :step="1" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="水分利用效率">
                  <el-input-number v-model="form.waterEfficiency" :min="0.01" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="泡田期净灌溉 mm">
                  <el-input-number v-model="form.paddyWater" :min="0" :step="5" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="深层渗漏 mm">
                  <el-input-number v-model="form.leakage" :min="0" :step="0.1" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">氮肥与函数系数</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="b0">
                  <el-input-number v-model="form.b0" :step="0.05" :precision="4" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="b1">
                  <el-input-number v-model="form.b1" :step="0.05" :precision="4" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="b2">
                  <el-input-number v-model="form.b2" :step="0.05" :precision="4" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="c">
                  <el-input-number v-model="form.c" :step="0.05" :precision="4" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="播前含氮 kg/hm²">
                  <el-input-number v-model="form.nitrogenBase" :min="0" :step="5" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最优施氮 kg/hm²">
                  <el-input-number v-model="form.nitrogenOptimal" :min="0.1" :step="5" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="施氮下限 kg/hm²">
                  <el-input-number v-model="form.nitrogenMin" :min="0" :step="5" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="施氮上限 kg/hm²">
                  <el-input-number v-model="form.nitrogenMax" :min="1" :step="5" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">NSGA-III 超参</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="种群大小">
                  <el-input-number v-model="form.populationSize" :min="20" :max="600" :step="10" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="进化代数">
                  <el-input-number v-model="form.generations" :min="1" :max="2000" :step="10" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitOptimize" class="action-primary">
                运行水肥调控优化
              </el-button>
              <el-button :disabled="!result" @click="resetResult">清空结果</el-button>
            </div>
          </el-form>

          <el-divider content-position="left">接口说明</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="查询接口">/api/v1/irrigation/water-fertilizer/regulation/list</el-descriptions-item>
            <el-descriptions-item label="优化接口">/api/v1/irrigation/water-fertilizer/optimize</el-descriptions-item>
            <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <el-card shadow="hover" class="preview-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">入库数据预览</div>
                <div class="card-desc">按记录日期升序展示当前查询范围内的前 10 条。</div>
              </div>
              <el-tag type="info">{{ previewTotal }} 条</el-tag>
            </div>
          </template>
          <el-table :data="previewRows" border stripe size="small" max-height="240">
            <el-table-column prop="recordTime" label="日期" width="110" fixed />
            <el-table-column label="有效降雨" align="right" min-width="90">
              <template #default="{ row }">{{ fmtNumber(row.dailyEffectiveRainfall, 2) }}</template>
            </el-table-column>
            <el-table-column label="最大蒸散发" align="right" min-width="100">
              <template #default="{ row }">{{ fmtNumber(row.dailyMaxCropEvapotranspiration, 2) }}</template>
            </el-table-column>
            <el-table-column label="最小蒸散发" align="right" min-width="100">
              <template #default="{ row }">{{ fmtNumber(row.dailyMinCropEvapotranspiration, 2) }}</template>
            </el-table-column>
            <el-table-column label="最大蓄水深度" align="right" min-width="110">
              <template #default="{ row }">{{ fmtNumber(row.maxWaterStorageDepth, 2) }}</template>
            </el-table-column>
            <el-table-column label="适宜水深范围" align="right" min-width="130">
              <template #default="{ row }">
                {{ fmtNumber(row.minSuitableWaterDepth, 2) }} - {{ fmtNumber(row.maxSuitableWaterDepth, 2) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <div v-if="!result" class="placeholder">
          <div class="placeholder-title">尚未生成调控方案</div>
          <div class="placeholder-desc">提交优化后将展示推荐解、帕累托解集和逐日水层过程。</div>
        </div>

        <template v-else>
          <div class="kpi-row">
            <div class="kpi-box">
              <div class="kpi-label">产量</div>
              <div class="kpi-value">{{ fmtNumber(bestSolution?.yield, 1) }}<span>kg/hm²</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">灌溉水利用效率</div>
              <div class="kpi-value">{{ fmtNumber(bestSolution?.giwp, 3) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">氮肥偏生产力</div>
              <div class="kpi-value">{{ fmtNumber(bestSolution?.cex, 3) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">碳排放指标</div>
              <div class="kpi-value">{{ fmtNumber(bestSolution?.gwp, 1) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">推荐施氮</div>
              <div class="kpi-value kpi-green">{{ fmtNumber(bestSolution?.nitrogen, 1) }}<span>kg/hm²</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">总灌溉量</div>
              <div class="kpi-value kpi-blue">{{ fmtNumber(bestSolution?.totalIrrigation, 1) }}<span>mm</span></div>
            </div>
          </div>

          <el-card shadow="hover" class="result-card">
            <template #header>
              <div class="card-header">
                <div>
                  <div class="card-title">逐日调控过程</div>
                  <div class="card-desc">
                    {{ dataSummary?.startDate }} 至 {{ dataSummary?.endDate }}，共 {{ dataSummary?.days }} 天。
                  </div>
                </div>
                <el-tag type="success">TOPSIS {{ fmtNumber(bestSolution?.topsisScore, 3) }}</el-tag>
              </div>
            </template>
            <div ref="processChartRef" class="chart chart-large" />
          </el-card>

          <el-row :gutter="16" class="result-grid">
            <el-col :xs="24" :lg="12">
              <el-card shadow="hover" class="result-card">
                <template #header>
                  <div class="card-header">
                    <div>
                      <div class="card-title">帕累托解集</div>
                      <div class="card-desc">X=产量，Y=GIWP，Z=CEX，颜色表示 GWP；星形点为 TOPSIS 推荐解。</div>
                    </div>
                    <el-tag type="info">{{ paretoSolutions.length }} 个解</el-tag>
                  </div>
                </template>
                <div ref="paretoChartRef" class="chart chart-3d" />
              </el-card>
            </el-col>
            <el-col :xs="24" :lg="12">
              <el-card shadow="hover" class="result-card">
                <template #header>
                  <div class="card-title">优化统计</div>
                </template>
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="算法">{{ optimizationInfo?.algorithm }}</el-descriptions-item>
                  <el-descriptions-item label="总解数">{{ optimizationInfo?.totalSolutions }}</el-descriptions-item>
                  <el-descriptions-item label="可行解">{{ optimizationInfo?.feasibleSolutions }}</el-descriptions-item>
                  <el-descriptions-item label="种群 / 代数">{{ optimizationInfo?.populationSize }} / {{ optimizationInfo?.generations }}</el-descriptions-item>
                  <el-descriptions-item label="优化时间">{{ optimizationInfo?.optimizationTime }}</el-descriptions-item>
                  <el-descriptions-item label="累计降雨">{{ fmtNumber(dataSummary?.totalRainfall, 2) }} mm</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
          </el-row>
        </template>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Search } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-gl'
import {
  getWaterFertilizerRegulationSummary,
  listWaterFertilizerRegulation,
  runWaterFertilizerOptimize
} from '@/api/model/waterFertilizer'

const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  startDate: '2024-05-15',
  endDate: '2024-09-25',
  yieldMax: 9000,
  maxIrrigation: 40,
  waterEfficiency: 0.75,
  paddyWater: 80,
  leakage: 2.5,
  b0: 0.62,
  b1: 0.55,
  b2: -0.17,
  c: 0.35,
  nitrogenBase: 45,
  nitrogenOptimal: 180,
  nitrogenMax: 260,
  nitrogenMin: 60,
  populationSize: 80,
  generations: 60
})

const loadingData = ref(false)
const loadingSummary = ref(false)
const submitting = ref(false)
const resultError = ref('')
const result = ref(null)
const previewRows = ref([])
const previewTotal = ref(0)
const availableRange = reactive({
  total: 0,
  startDate: '',
  endDate: ''
})
const processChartRef = ref(null)
const paretoChartRef = ref(null)
let processChart = null
let paretoChart = null

const bestSolution = computed(() => result.value?.bestSolution || null)
const paretoSolutions = computed(() => result.value?.paretoSolutions || [])
const detailedData = computed(() => result.value?.detailedData || [])
const optimizationInfo = computed(() => result.value?.optimizationInfo || {})
const dataSummary = computed(() => result.value?.dataSummary || {})
const canSubmit = computed(() => Boolean(form.apiKey && form.startDate && form.endDate && !submitting.value))

function buildPayload() {
  return {
    yieldMax: form.yieldMax,
    maxIrrigation: form.maxIrrigation,
    waterEfficiency: form.waterEfficiency,
    paddyWater: form.paddyWater,
    leakage: form.leakage,
    b0: form.b0,
    b1: form.b1,
    b2: form.b2,
    c: form.c,
    nitrogenBase: form.nitrogenBase,
    nitrogenOptimal: form.nitrogenOptimal,
    nitrogenMax: form.nitrogenMax,
    nitrogenMin: form.nitrogenMin,
    populationSize: form.populationSize,
    generations: form.generations,
    startDate: form.startDate,
    endDate: form.endDate
  }
}

async function loadPreview() {
  if (!form.startDate || !form.endDate) {
    ElMessage.warning('请选择查询日期范围')
    return
  }
  loadingData.value = true
  resultError.value = ''
  try {
    const response = await listWaterFertilizerRegulation({
      startDate: form.startDate,
      endDate: form.endDate,
      pageNum: 1,
      pageSize: 10
    }, form.apiKey)
    previewRows.value = response.rows || []
    previewTotal.value = response.total || previewRows.value.length
    if (!previewRows.value.length) {
      ElMessage.warning('当前日期范围内没有水肥调控数据')
    }
  } catch (error) {
    resultError.value = error?.message || '查询失败'
    ElMessage.error(resultError.value)
  } finally {
    loadingData.value = false
  }
}

async function loadAvailableRange() {
  loadingSummary.value = true
  resultError.value = ''
  try {
    const summary = await getWaterFertilizerRegulationSummary(form.apiKey)
    availableRange.total = summary.total || 0
    availableRange.startDate = summary.startDate || ''
    availableRange.endDate = summary.endDate || ''
    if (availableRange.startDate && availableRange.endDate) {
      form.startDate = availableRange.startDate
      form.endDate = availableRange.endDate
      await loadPreview()
    } else {
      ElMessage.warning('水肥调控数据表暂无记录')
    }
  } catch (error) {
    resultError.value = error?.message || '获取库内日期范围失败'
    ElMessage.error(resultError.value)
  } finally {
    loadingSummary.value = false
  }
}

async function submitOptimize() {
  if (!canSubmit.value) return
  submitting.value = true
  resultError.value = ''
  try {
    const response = await runWaterFertilizerOptimize(buildPayload(), form.apiKey)
    result.value = response
    ElMessage.success('水肥调控优化完成')
    await nextTick()
    renderProcessChart()
    renderParetoChart()
  } catch (error) {
    resultError.value = error?.message || '优化失败'
    ElMessage.error(resultError.value)
  } finally {
    submitting.value = false
  }
}

function renderParetoChart() {
  if (!paretoChartRef.value || !paretoSolutions.value.length) return
  if (!paretoChart) paretoChart = echarts.init(paretoChartRef.value)
  const points = paretoSolutions.value.map((item, index) => [
    Number(item.yield || 0),
    Number(item.giwp || 0),
    Number(item.cex || 0),
    Number(item.gwp || 0),
    Number(item.nitrogen || 0),
    Number(item.totalIrrigation || 0),
    index + 1
  ])
  const gwpValues = points.map(item => item[3])
  const best = bestSolution.value
    ? [[
        Number(bestSolution.value.yield || 0),
        Number(bestSolution.value.giwp || 0),
        Number(bestSolution.value.cex || 0),
        Number(bestSolution.value.gwp || 0),
        Number(bestSolution.value.nitrogen || 0),
        Number(bestSolution.value.totalIrrigation || 0),
        'TOPSIS'
      ]]
    : []
  const allPoints = best.length ? points.concat(best) : points
  const xRange = buildAxisRange(allPoints.map(item => item[0]))
  const yRange = buildAxisRange(allPoints.map(item => item[1]))
  const zRange = buildAxisRange(allPoints.map(item => item[2]))

  paretoChart.setOption({
    tooltip: {
      formatter(params) {
        const value = params.value || []
        return [
          params.seriesName,
          `产量：${fmtNumber(value[0], 1)} kg/hm²`,
          `GIWP：${fmtNumber(value[1], 3)}`,
          `CEX：${fmtNumber(value[2], 3)}`,
          `GWP：${fmtNumber(value[3], 1)}`,
          `施氮：${fmtNumber(value[4], 1)} kg/hm²`,
          `总灌溉：${fmtNumber(value[5], 1)} mm`
        ].join('<br/>')
      }
    },
    visualMap: {
      min: Math.min(...gwpValues),
      max: Math.max(...gwpValues),
      dimension: 3,
      text: ['GWP 高', 'GWP 低'],
      calculable: true,
      left: 8,
      bottom: 8,
      inRange: { color: ['#16a34a', '#f59e0b', '#ef4444'] }
    },
    grid3D: {
      left: 0,
      right: 0,
      top: -12,
      bottom: 0,
      boxWidth: 120,
      boxDepth: 92,
      viewControl: {
        projection: 'perspective',
        autoRotate: false,
        distance: 180,
        alpha: 24,
        beta: 38
      },
      axisLine: { lineStyle: { color: '#94a3b8' } },
      axisPointer: { lineStyle: { color: '#0ea5e9' } },
      splitLine: { lineStyle: { color: '#e2e8f0' } }
    },
    xAxis3D: { type: 'value', name: '产量', nameGap: 22, min: xRange.min, max: xRange.max },
    yAxis3D: { type: 'value', name: 'GIWP', nameGap: 22, min: yRange.min, max: yRange.max },
    zAxis3D: { type: 'value', name: 'CEX', nameGap: 22, min: zRange.min, max: zRange.max },
    series: [
      {
        name: '帕累托解',
        type: 'scatter3D',
        data: points,
        symbolSize: 9,
        emphasis: { itemStyle: { borderWidth: 2, borderColor: '#111827' } }
      },
      {
        name: 'TOPSIS 推荐解',
        type: 'scatter3D',
        data: best,
        symbol: 'diamond',
        symbolSize: 22,
        itemStyle: { color: '#2563eb', borderColor: '#ffffff', borderWidth: 2 }
      }
    ]
  })
}

function buildAxisRange(values) {
  const valid = values.map(Number).filter(Number.isFinite)
  if (!valid.length) return { min: 0, max: 1 }
  const min = Math.min(...valid)
  const max = Math.max(...valid)
  if (min === max) {
    const pad = Math.max(Math.abs(min) * 0.08, 1)
    return { min: min - pad, max: max + pad }
  }
  const pad = (max - min) * 0.08
  return { min: min - pad, max: max + pad }
}

function renderProcessChart() {
  if (!processChartRef.value || !detailedData.value.length) return
  if (!processChart) processChart = echarts.init(processChartRef.value)
  const rows = detailedData.value
  processChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['灌溉量', '有效降雨', '实际蒸散发', '水层深度', '水深下限', '水深上限'] },
    grid: { left: 48, right: 24, top: 52, bottom: 42 },
    xAxis: { type: 'category', data: rows.map(item => item.recordTime || item.period), axisLabel: { interval: 'auto' } },
    yAxis: [{ type: 'value', name: 'mm' }],
    series: [
      { name: '灌溉量', type: 'bar', data: rows.map(item => item.irrigation), itemStyle: { color: '#0ea5e9' } },
      { name: '有效降雨', type: 'bar', data: rows.map(item => item.rainfall), itemStyle: { color: '#22c55e' } },
      { name: '实际蒸散发', type: 'line', smooth: true, data: rows.map(item => item.evapotranspiration), itemStyle: { color: '#f59e0b' } },
      { name: '水层深度', type: 'line', smooth: true, data: rows.map(item => item.waterDepth), itemStyle: { color: '#6366f1' } },
      { name: '水深下限', type: 'line', symbol: 'none', data: rows.map(item => item.waterDepthMin), lineStyle: { type: 'dashed', color: '#ef4444' } },
      { name: '水深上限', type: 'line', symbol: 'none', data: rows.map(item => item.waterDepthMax), lineStyle: { type: 'dashed', color: '#64748b' } }
    ]
  })
}

function resetResult() {
  result.value = null
  resultError.value = ''
  if (processChart) processChart.clear()
  if (paretoChart) paretoChart.clear()
}

function fmtNumber(value, digits = 2) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

function handleResize() {
  processChart?.resize()
  paretoChart?.resize()
}

window.addEventListener('resize', handleResize)
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  processChart?.dispose()
  paretoChart?.dispose()
})

loadAvailableRange()
</script>

<style scoped lang="scss">
.water-fertilizer-page {
  background: #f5f7fb;
}

.water-fertilizer-hero {
  background:
    linear-gradient(135deg, rgba(14, 165, 233, 0.9), rgba(34, 197, 94, 0.78)),
    url('@/assets/images/profile.jpg') center/cover;
}

.page-layout {
  margin-top: 20px;
}

.config-card,
.preview-card,
.result-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
}

.card-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.action-row.compact {
  margin-bottom: 6px;
}

.range-hint {
  margin: 4px 0 10px;
  font-size: 12px;
  color: #64748b;
}

.action-primary {
  flex: 1;
}

.preview-card {
  margin-bottom: 16px;
}

.placeholder {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  background: #ffffff;
}

.placeholder-title {
  font-size: 18px;
  font-weight: 700;
  color: #334155;
}

.placeholder-desc {
  margin-top: 8px;
  font-size: 13px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-box {
  min-height: 92px;
  padding: 16px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.kpi-label {
  font-size: 12px;
  color: #64748b;
}

.kpi-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
}

.kpi-value span {
  margin-left: 4px;
  font-size: 12px;
  color: #64748b;
}

.kpi-green {
  color: #16a34a;
}

.kpi-blue {
  color: #0284c7;
}

.chart {
  width: 100%;
  height: 320px;
}

.chart-large {
  height: 420px;
}

.chart-3d {
  height: 380px;
}

.result-grid {
  margin-top: 16px;
}

@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }

  .action-row {
    align-items: stretch;
    flex-direction: column;
  }

  .action-primary {
    width: 100%;
  }
}
</style>
