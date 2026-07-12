<template>
  <div class="app-container agri-page water-efficiency-page">
    <section class="agri-page__hero water-efficiency-hero">
      <div class="hero-content">
        <span class="agri-page__eyebrow">ENTROPY-WEIGHTED TOPSIS EVALUATION</span>
        <h1 class="agri-page__title">灌区年度用水评价</h1>
        <p class="agri-page__desc">
          基于熵权-TOPSIS 法，对灌区 14 个分区的年度用水效率进行多指标综合评价，
          客观量化各分区用水效率水平与差距。所有指标由前端表格直接输入，后端不涉及派生计算。
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
          <router-link to="/model/water-right-allocation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>水权分配</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="resource-tag">熵权法</span>
        <span class="resource-tag resource-tag--green">TOPSIS</span>
        <span class="resource-tag resource-tag--orange">14 分区</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <!-- 左侧：配置面板 -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">年度用水评价</div>
                <div class="card-desc">填写各分区年度指标值后提交评价，初次加载已预置模拟数据。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'">
                {{ resultError ? '接口异常' : result ? '已评价' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <el-form :model="form" label-position="top" size="small" class="efficiency-form">
            <el-form-item label="接口 API Key" required>
              <el-input v-model="form.apiKey" type="password" show-password clearable placeholder="X-Irrigation-Api-Key" />
            </el-form-item>

            <el-form-item label="评价年份">
              <el-input-number v-model="form.year" :min="2000" :max="2099" :step="1" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">
              14 分区年度指标
              <el-button type="primary" size="small" plain style="margin-left: 12px" @click="resetToDefault">
                <el-icon><RefreshRight /></el-icon> 重置模拟数据
              </el-button>
            </el-divider>

            <div class="zone-table-wrapper">
              <el-table
                :data="form.zones"
                border
                size="small"
                stripe
                max-height="480"
                class="zone-indicator-table"
              >
                <el-table-column prop="zoneId" label="分区" width="80" fixed />
                <el-table-column label="名称" width="90" fixed>
                  <template #default="{ row }">
                    <span class="zone-name-cell">{{ row.zoneName }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="IWUE" min-width="85" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.iwue" :min="0" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="WUE kg/m³" min-width="95" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.waterProductivityKgM3" :min="0" :step="0.1" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="BEC 元/m³" min-width="95" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.benefitYuanPerM3" :min="0" :step="0.1" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="IRS" min-width="80" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.irrigationReliability" :min="0" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="FE" min-width="75" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.fieldEfficiency" :min="0" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="SUR" min-width="75" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.surfaceWaterUtilization" :min="0" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="GWR" min-width="75" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.groundwaterUtilization" :min="0" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="GWI" min-width="75" align="right">
                  <template #default="{ row }">
                    <el-input-number v-model="row.groundwaterDependency" :min="0" :max="1" :step="0.01" :precision="3" size="small" controls-position="right" />
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="indicator-legend">
              <span>IWUE 灌溉水利用系数</span>
              <span>WUE 水分生产率 (kg/m³)</span>
              <span>BEC 单方水净效益 (元/m³)</span>
              <span>IRS 灌溉保证率</span>
              <span>FE 田间水利用系数</span>
              <span>SUR 地表水利用率</span>
              <span>GWR 地下水利用率</span>
              <span>GWI 地下水依赖度 (越小越好)</span>
            </div>

            <el-divider content-position="left">评价参数</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="混合系数 α (0=纯熵权)">
                  <el-input-number v-model="form.alpha" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitEvaluate" class="action-primary">
                开始综合评价
              </el-button>
              <el-button :disabled="!result" @click="resetResult">清空结果</el-button>
            </div>
          </el-form>

          <el-divider content-position="left">接口说明</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="接口地址">/api/v1/irrigation/water-efficiency/evaluate</el-descriptions-item>
            <el-descriptions-item label="请求方式">POST / application/json</el-descriptions-item>
            <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 右侧：结果面板 -->
      <el-col :xs="24" :lg="14">
        <div v-if="!result" class="placeholder">
          <div class="placeholder-title">尚未提交评价</div>
          <div class="placeholder-desc">填写 14 分区年度指标后提交，获取各分区用水效率综合评分与等级排名。</div>
        </div>

        <template v-else>
          <!-- 总体统计 -->
          <div class="kpi-row">
            <div class="kpi-box">
              <div class="kpi-label">评价分区</div>
              <div class="kpi-value">{{ result.summary?.totalZones }}<span>个</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">平均得分</div>
              <div class="kpi-value">{{ fmtNumber(periodResult?.summary?.meanScore, 3) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">优秀分区</div>
              <div class="kpi-value kpi-green">{{ result.summary?.gradeDistribution?.excellent || 0 }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">良好分区</div>
              <div class="kpi-value kpi-blue">{{ result.summary?.gradeDistribution?.good || 0 }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">合格分区</div>
              <div class="kpi-value kpi-orange">{{ result.summary?.gradeDistribution?.qualified || 0 }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">不合格分区</div>
              <div class="kpi-value kpi-red">{{ result.summary?.gradeDistribution?.unqualified || 0 }}</div>
            </div>
          </div>

          <!-- 结果卡片 -->
          <div class="period-result">
            <el-card shadow="hover" class="result-card">
              <template #header>
                <div class="card-header">
                  <div>
                    <span class="period-title">{{ form.year }} 年度用水效率评价</span>
                    <span class="period-desc">共 {{ periodResult?.nZones }} 个分区</span>
                  </div>
                  <el-tag size="small" type="info">
                    平均分 {{ fmtNumber(periodResult?.summary?.meanScore, 3) }}
                  </el-tag>
                </div>
              </template>

              <!-- 图表 -->
              <el-row :gutter="16" class="chart-row">
                <el-col :xs="24" :sm="12">
                  <div ref="gradeChartRef" class="chart" />
                </el-col>
                <el-col :xs="24" :sm="12">
                  <div ref="scoreChartRef" class="chart" />
                </el-col>
              </el-row>

              <!-- 分区评价结果表 -->
              <el-table :data="periodResult?.zoneResults" border size="small" stripe max-height="380" class="result-table mt12">
                <el-table-column prop="rank" label="排名" width="60" fixed>
                  <template #default="{ row }">
                    <el-tag
                      v-if="row.rank === 1"
                      type="warning" effect="dark"
                      style="font-weight: 700"
                    >{{ row.rank }}</el-tag>
                    <el-tag v-else type="info">{{ row.rank }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="zoneId" label="分区" width="80" />
                <el-table-column prop="zoneName" label="名称" width="90" />
                <el-table-column label="综合得分" width="100" align="right">
                  <template #default="{ row }">
                    <span class="score-value">{{ fmtNumber(row.score, 4) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="等级" width="80">
                  <template #default="{ row }">
                    <el-tag :type="gradeTagType(row.grade)">{{ row.grade }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="IWUE" width="80" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.iwue, 3) }}</template>
                </el-table-column>
                <el-table-column label="WUE" width="85" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.waterProductivityKgM3, 3) }}</template>
                </el-table-column>
                <el-table-column label="BEC" width="85" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.benefitYuanPerM3, 3) }}</template>
                </el-table-column>
                <el-table-column label="IRS" width="75" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.irrigationReliability, 3) }}</template>
                </el-table-column>
                <el-table-column label="FE" width="70" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.fieldEfficiency, 3) }}</template>
                </el-table-column>
                <el-table-column label="SUR" width="70" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.surfaceWaterUtilization, 3) }}</template>
                </el-table-column>
                <el-table-column label="GWR" width="70" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.groundwaterUtilization, 3) }}</template>
                </el-table-column>
                <el-table-column label="GWI" width="70" align="right">
                  <template #default="{ row }">{{ fmtNumber(row.original?.groundwaterDependency, 3) }}</template>
                </el-table-column>
                <el-table-column type="expand" label="详情" width="55">
                  <template #default="{ row }">
                    <div class="detail-expand">
                      <div class="detail-section">
                        <div class="detail-title">各指标标准化值（统一越大越好）</div>
                        <div class="detail-grid">
                          <div v-for="(v, k) in row.normalized" :key="k" class="detail-item">
                            <span class="detail-key">{{ INDICATOR_NAMES[k] || k }}</span>
                            <span class="detail-val">{{ fmtNumber(v, 4) }}</span>
                          </div>
                        </div>
                      </div>
                      <div class="detail-section">
                        <div class="detail-title">各指标加权值</div>
                        <div class="detail-grid">
                          <div v-for="(v, k) in row.weighted" :key="k" class="detail-item">
                            <span class="detail-key">{{ INDICATOR_NAMES[k] || k }}</span>
                            <span class="detail-val">{{ fmtNumber(v, 4) }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
                </el-table-column>
              </el-table>

              <!-- 权重信息 -->
              <div class="weight-info mt12">
                <div class="weight-title">最终指标权重（混合赋权，α={{ result.summary?.alpha }}）</div>
                <div class="weight-grid">
                  <div v-for="(v, k) in periodResult?.indicatorWeights" :key="k" class="weight-item">
                    <span>{{ INDICATOR_NAMES[k] || k }}</span>
                    <el-progress :percentage="Number((v * 100).toFixed(1))" :stroke-width="8" :show-text="true" />
                  </div>
                </div>
              </div>
            </el-card>
          </div>
        </template>

        <div v-if="resultError" class="error-box mt16">
          <el-alert type="danger" :title="resultError" show-icon :closable="true" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, getCurrentInstance, nextTick, onUnmounted, reactive, ref, watch } from 'vue'
import { Promotion, RefreshRight } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

import { runWaterEfficiencyEvaluate } from '@/api/model/waterEfficiency'

defineOptions({ name: 'WaterEfficiency' })

const { proxy } = getCurrentInstance()
const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const INDICATOR_NAMES = {
  iwue: 'IWUE',
  waterProductivityKgM3: 'WUE',
  benefitYuanPerM3: 'BEC',
  irrigationReliability: 'IRS',
  fieldEfficiency: 'FE',
  surfaceWaterUtilization: 'SUR',
  groundwaterUtilization: 'GWR',
  groundwaterDependency: 'GWI'
}

const GRADE_COLORS = {
  '优秀': '#22c55e',
  '良好': '#3b82f6',
  '合格': '#f97316',
  '不合格': '#ef4444'
}

// 14 分区名称（与水土资源、水权分配模型保持一致）
const ZONE_NAMES = [
  '红河', '万发', '金光', '稻花香', '发展',
  '金星', '太平湖', '海洋', '新立', '丰收',
  '二十八方', '联合', '金边', '长吉岗'
]

// 各分区模拟指标数据（IWUE, WUE, BEC, IRS, FE, SUR, GWR, GWI）
// 设计差异化：Z01 红河 / Z08 海洋 — 综合优秀；Z02-Z05 良好；Z06-Z10 合格；Z11-Z14 不合格
const DEFAULT_ZONE_DATA = [
  // Z01 红河 — 地表水丰沛、综合表现优秀（贴近阈值 0.70）
  { iwue: 0.74, waterProductivityKgM3: 3.45, benefitYuanPerM3: 15.5, irrigationReliability: 0.98, fieldEfficiency: 0.97, surfaceWaterUtilization: 0.90, groundwaterUtilization: 0.14, groundwaterDependency: 0.08 },
  // Z02 万发 — 水源条件好，灌溉保证率高（良好）
  { iwue: 0.60, waterProductivityKgM3: 2.70, benefitYuanPerM3: 11.5, irrigationReliability: 0.90, fieldEfficiency: 0.90, surfaceWaterUtilization: 0.72, groundwaterUtilization: 0.28, groundwaterDependency: 0.22 },
  // Z03 金光 — 田间设施完善，WUE 较高（良好）
  { iwue: 0.58, waterProductivityKgM3: 2.65, benefitYuanPerM3: 10.9, irrigationReliability: 0.87, fieldEfficiency: 0.89, surfaceWaterUtilization: 0.70, groundwaterUtilization: 0.30, groundwaterDependency: 0.25 },
  // Z04 稻花香 — 水稻主产区，灌溉面积大，保证率高（良好）
  { iwue: 0.56, waterProductivityKgM3: 2.45, benefitYuanPerM3: 10.2, irrigationReliability: 0.85, fieldEfficiency: 0.87, surfaceWaterUtilization: 0.68, groundwaterUtilization: 0.32, groundwaterDependency: 0.28 },
  // Z05 发展 — 综合良好（良好边界）
  { iwue: 0.54, waterProductivityKgM3: 2.30, benefitYuanPerM3: 9.6, irrigationReliability: 0.82, fieldEfficiency: 0.85, surfaceWaterUtilization: 0.65, groundwaterUtilization: 0.35, groundwaterDependency: 0.30 },
  // Z06 金星 — 中等水平，设施有待改善（合格）
  { iwue: 0.52, waterProductivityKgM3: 2.15, benefitYuanPerM3: 8.8, irrigationReliability: 0.78, fieldEfficiency: 0.83, surfaceWaterUtilization: 0.60, groundwaterUtilization: 0.40, groundwaterDependency: 0.35 },
  // Z07 太平湖 — 局部供水不足（合格）
  { iwue: 0.50, waterProductivityKgM3: 2.05, benefitYuanPerM3: 8.2, irrigationReliability: 0.73, fieldEfficiency: 0.80, surfaceWaterUtilization: 0.55, groundwaterUtilization: 0.45, groundwaterDependency: 0.40 },
  // Z08 海洋 — 地表水丰富、设施先进、综合表现优秀
  { iwue: 0.74, waterProductivityKgM3: 3.42, benefitYuanPerM3: 15.1, irrigationReliability: 0.97, fieldEfficiency: 0.96, surfaceWaterUtilization: 0.92, groundwaterUtilization: 0.12, groundwaterDependency: 0.06 },
  // Z09 新立 — 设施条件中等，水源相对紧张（合格）
  { iwue: 0.55, waterProductivityKgM3: 2.38, benefitYuanPerM3: 9.9, irrigationReliability: 0.80, fieldEfficiency: 0.86, surfaceWaterUtilization: 0.62, groundwaterUtilization: 0.38, groundwaterDependency: 0.33 },
  // Z10 丰收 — 农艺管理水平良好（合格边界）
  { iwue: 0.58, waterProductivityKgM3: 2.55, benefitYuanPerM3: 10.6, irrigationReliability: 0.86, fieldEfficiency: 0.88, surfaceWaterUtilization: 0.68, groundwaterUtilization: 0.32, groundwaterDependency: 0.27 },
  // Z11 二十八方 — 面积最大，水源分布不均（不合格）
  { iwue: 0.42, waterProductivityKgM3: 1.55, benefitYuanPerM3: 5.0, irrigationReliability: 0.50, fieldEfficiency: 0.68, surfaceWaterUtilization: 0.32, groundwaterUtilization: 0.68, groundwaterDependency: 0.65 },
  // Z12 联合 — 地下水利用率偏高，保证率偏低（不合格）
  { iwue: 0.40, waterProductivityKgM3: 1.45, benefitYuanPerM3: 4.5, irrigationReliability: 0.45, fieldEfficiency: 0.65, surfaceWaterUtilization: 0.28, groundwaterUtilization: 0.72, groundwaterDependency: 0.70 },
  // Z13 金边 — 综合水平较差，需要重点改进（不合格）
  { iwue: 0.38, waterProductivityKgM3: 1.30, benefitYuanPerM3: 3.8, irrigationReliability: 0.40, fieldEfficiency: 0.62, surfaceWaterUtilization: 0.22, groundwaterUtilization: 0.78, groundwaterDependency: 0.76 },
  // Z14 长吉岗 — 面积大、水源条件复杂，综合效率最低（不合格）
  { iwue: 0.35, waterProductivityKgM3: 1.20, benefitYuanPerM3: 3.2, irrigationReliability: 0.35, fieldEfficiency: 0.58, surfaceWaterUtilization: 0.18, groundwaterUtilization: 0.82, groundwaterDependency: 0.82 }
]

function buildDefaultZones() {
  return ZONE_NAMES.map((name, i) => ({
    zoneId: `Z${String(i + 1).padStart(2, '0')}`,
    zoneName: name,
    ...DEFAULT_ZONE_DATA[i]
  }))
}

const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  year: new Date().getFullYear(),
  zones: buildDefaultZones(),
  alpha: 0.5
})

const submitting = ref(false)
const result = ref(null)
const resultError = ref('')
const gradeChartRef = ref(null)
const scoreChartRef = ref(null)

let gradeChart = null
let scoreChart = null

const periodResult = computed(() => {
  return result.value?.periodResults?.[0] || null
})

const canSubmit = computed(() => {
  if (!form.apiKey.trim()) return false
  if (!form.zones.length) return false
  return form.zones.every(z => z.zoneId.trim())
})

function resetToDefault() {
  form.zones.splice(0, form.zones.length, ...buildDefaultZones())
}

function buildPayload() {
  return {
    periods: [{
      periodId: String(form.year),
      periodLabel: `${form.year} 年`,
      zones: form.zones.map(z => ({
        zoneId: z.zoneId,
        zoneName: z.zoneName,
        iwue: Number(z.iwue) || 0,
        waterProductivityKgM3: Number(z.waterProductivityKgM3) || 0,
        benefitYuanPerM3: Number(z.benefitYuanPerM3) || 0,
        irrigationReliability: Number(z.irrigationReliability) || 0,
        fieldEfficiency: Number(z.fieldEfficiency) || 0,
        surfaceWaterUtilization: Number(z.surfaceWaterUtilization) || 0,
        groundwaterUtilization: Number(z.groundwaterUtilization) || 0,
        groundwaterDependency: Number(z.groundwaterDependency) || 0
      }))
    }],
    alpha: Number(form.alpha) || 0.5
  }
}

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return Number(value).toFixed(digits)
}

function gradeTagType(grade) {
  const map = { '优秀': 'success', '良好': '', '合格': 'warning', '不合格': 'danger' }
  return map[grade] || 'info'
}

function initChart(el, chartRef) {
  if (!el || !el.isConnected) return null
  if (chartRef) chartRef.dispose()
  return echarts.init(el)
}

function renderGradePie() {
  if (!gradeChartRef.value) return
  const pr = periodResult.value
  if (!pr) return
  const dist = pr.summary?.gradeDistribution || {}
  const data = [
    { name: '优秀', value: dist.excellent || 0, itemStyle: { color: '#22c55e' } },
    { name: '良好', value: dist.good || 0, itemStyle: { color: '#3b82f6' } },
    { name: '合格', value: dist.qualified || 0, itemStyle: { color: '#f97316' } },
    { name: '不合格', value: dist.unqualified || 0, itemStyle: { color: '#ef4444' } }
  ].filter(d => d.value > 0)

  gradeChart = initChart(gradeChartRef.value, gradeChart)
  gradeChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    title: { text: '等级分布', left: 'center', top: 8, textStyle: { fontSize: 13, fontWeight: 600 } },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data
    }]
  })
}

function renderScoreBar() {
  if (!scoreChartRef.value) return
  const pr = periodResult.value
  if (!pr) return
  const zones = pr.zoneResults || []
  const labels = zones.map(z => z.zoneName || z.zoneId)
  const scores = zones.map(z => Number(z.score || 0))
  const colors = zones.map(z => GRADE_COLORS[z.grade] || '#94a3b8')

  scoreChart = initChart(scoreChartRef.value, scoreChart)
  scoreChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    title: { text: '各分区综合得分', left: 'center', top: 8, textStyle: { fontSize: 13, fontWeight: 600 } },
    grid: { left: 80, right: 20, top: 38, bottom: 40 },
    xAxis: { type: 'value', max: 1, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: scores.map((s, i) => ({ value: s, itemStyle: { color: colors[i] } })),
      label: { show: true, position: 'right', formatter: '{c}', fontSize: 10 }
    }]
  })
}

function renderAllCharts() {
  renderGradePie()
  renderScoreBar()
}

function destroyCharts() {
  if (gradeChart) { gradeChart.dispose(); gradeChart = null }
  if (scoreChart) { scoreChart.dispose(); scoreChart = null }
}

function resizeCharts() {
  gradeChart?.resize()
  scoreChart?.resize()
}

async function submitEvaluate() {
  if (!canSubmit.value) return
  resultError.value = ''
  destroyCharts()
  submitting.value = true
  try {
    result.value = await runWaterEfficiencyEvaluate(buildPayload(), form.apiKey.trim())
    await nextTick()
    renderAllCharts()
    proxy.$modal.msgSuccess('评价完成')
  } catch (err) {
    resultError.value = err?.message || '评价失败'
    proxy.$modal?.msgError?.(resultError.value)
  } finally {
    submitting.value = false
  }
}

function resetResult() {
  result.value = null
  resultError.value = ''
  destroyCharts()
}

watch(result, async () => {
  if (!result.value) return
  await nextTick()
  renderAllCharts()
})

window.addEventListener('resize', resizeCharts)
onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  destroyCharts()
})
</script>

<style scoped>
.water-efficiency-page { padding-bottom: 28px; }
.water-efficiency-hero { margin-bottom: 20px; }
.agri-page__siblings { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.sibling-link { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: var(--surface-soft-bg); border: 1px solid var(--hairline-color); color: var(--text-primary); font-size: 0.867em; text-decoration: none; transition: all 0.2s ease; }
.sibling-link:hover { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary-light-5); color: var(--el-color-primary); }
.resource-tag { display: inline-flex; align-items: center; padding: 6px 12px; border-radius: 999px; background: rgba(91, 141, 239, 0.12); color: #315db8; font-size: 12px; font-weight: 600; }
.resource-tag--green { background: rgba(34, 197, 94, 0.14); color: #15803d; }
.resource-tag--orange { background: rgba(249, 115, 22, 0.14); color: #c2410c; }
.page-layout { align-items: flex-start; }
.config-card, .result-card { border-radius: 18px; border: 1px solid var(--hairline-color); box-shadow: var(--content-shadow-soft); overflow: hidden; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.card-title { font-size: 18px; font-weight: 650; color: var(--text-primary); }
.card-desc { margin-top: 6px; color: var(--text-secondary); line-height: 1.6; }
.efficiency-form :deep(.el-form-item) { margin-bottom: 12px; }
.efficiency-form :deep(.el-form-item__label) { font-size: 0.8em; color: var(--text-regular); padding: 0 0 4px; line-height: 1.3; font-weight: 500; }
.zone-table-wrapper { overflow-x: auto; }
.zone-indicator-table :deep(.el-input-number) { width: 100%; min-width: 65px; }
.zone-indicator-table :deep(.el-input-number__decrease),
.zone-indicator-table :deep(.el-input-number__increase) { display: none; }
.zone-indicator-table :deep(.el-input__wrapper) { padding-left: 4px; padding-right: 4px; }
.zone-name-cell { font-size: 0.85em; color: var(--text-secondary); }
.indicator-legend { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.indicator-legend span { font-size: 11px; color: var(--text-secondary); background: var(--surface-soft-bg); padding: 2px 6px; border-radius: 4px; }
.action-row { display: flex; gap: 10px; margin-top: 12px; }
.action-primary { flex: 1; }
.placeholder { padding: 56px 20px; text-align: center; background: var(--surface-soft-bg); border-radius: 18px; border: 1px dashed var(--hairline-color); }
.placeholder-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.placeholder-desc { margin-top: 10px; font-size: 0.867em; line-height: 1.7; color: var(--text-secondary); }
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }
.kpi-box { padding: 18px 20px; border-radius: 18px; background: var(--surface-bg); border: 1px solid var(--hairline-color); box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05); }
.kpi-label { font-size: 0.867em; color: var(--text-secondary); font-weight: 500; }
.kpi-value { margin-top: 8px; font-size: 25px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.kpi-value span { margin-left: 4px; font-size: 0.58em; font-weight: 500; color: var(--text-secondary); }
.kpi-green { color: #22c55e; }
.kpi-blue { color: #3b82f6; }
.kpi-orange { color: #f97316; }
.kpi-red { color: #ef4444; }
.period-result { margin-top: 16px; }
.period-title { font-size: 16px; font-weight: 650; color: var(--text-primary); }
.period-desc { margin-left: 10px; font-size: 12px; color: var(--text-secondary); }
.chart-row { margin-top: 10px; }
.chart { width: 100%; height: 260px; min-width: 0; }
.result-table :deep(.el-table__expand-icon) { font-size: 14px; }
.score-value { font-weight: 700; color: var(--el-color-primary); }
.mt12 { margin-top: 12px; }
.mt16 { margin-top: 16px; }
.detail-expand { padding: 12px 16px; background: var(--surface-soft-bg); }
.detail-section { margin-bottom: 12px; }
.detail-section:last-child { margin-bottom: 0; }
.detail-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 6px; }
.detail-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: var(--surface-bg); border-radius: 6px; }
.detail-key { font-size: 12px; color: var(--text-secondary); }
.detail-val { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.weight-info { margin-top: 12px; padding: 12px; background: var(--surface-soft-bg); border-radius: 10px; }
.weight-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.weight-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
.weight-item { display: flex; align-items: center; gap: 8px; }
.weight-item span { font-size: 12px; color: var(--text-secondary); white-space: nowrap; min-width: 80px; }
.weight-item :deep(.el-progress) { flex: 1; }
.weight-item :deep(.el-progress__text) { font-size: 11px; }
.error-box { padding: 16px; border-radius: 18px; background: var(--surface-bg); border: 1px solid var(--hairline-color); }
@media (max-width: 768px) {
  .kpi-value { font-size: 22px; }
  .chart { height: 240px; }
}
</style>
