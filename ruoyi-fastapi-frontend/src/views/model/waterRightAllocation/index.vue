<template>
  <div class="app-container agri-page water-right-allocation-page">
    <section class="agri-page__hero water-right-allocation-hero">
      <div class="hero-content">
        <span class="agri-page__eyebrow">STACKELBERG GAME x LP MARKET CLEARING</span>
        <h1 class="agri-page__title">初始水权分配与水权交易</h1>
        <p class="agri-page__desc">
          灌区管理单位（领导者）下发保留价区间，14 个管理区（跟随者）通过线性规划全局最优地决定
          自用/购入/售出水量，实现社会福利、公平性与节水激励的多目标平衡。
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
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="resource-tag">14 管理区</span>
        <span class="resource-tag resource-tag--green">Stackelberg 主从博弈</span>
        <span class="resource-tag resource-tag--orange">LP 全局出清</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <el-col :xs="24" :lg="9">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">参数配置</div>
                <div class="card-desc">作物参数、需水量、市场机制与目标权重均可调整。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'">
                {{ resultError ? '接口异常' : result ? '方案已生成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <el-form :model="form" label-position="top" size="small" class="resource-form">
            <el-form-item label="接口 API Key" required>
              <el-input v-model="form.apiKey" type="password" show-password clearable placeholder="X-Irrigation-Api-Key" />
            </el-form-item>

            <el-divider content-position="left">作物参数</el-divider>
            <el-table :data="crops" border size="small" stripe max-height="240" class="crop-config-table">
              <el-table-column prop="crop_name" label="作物" width="80" fixed />
              <el-table-column label="产量<br>(kg/ha)" min-width="100" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.yield_kg_per_ha" :min="0" :step="100" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="单价<br>(元/kg)" min-width="95" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.price_yuan_per_kg" :min="0" :step="0.1" :precision="2" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="成本<br>(元/ha)" min-width="90" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.cost_yuan_per_ha" :min="0" :step="100" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="灌溉定额<br>(m³/ha)" min-width="100" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.water_quota_m3_per_ha" :min="1" :step="100" controls-position="right" size="small" />
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left">市场参数</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="全灌区可供水量 (m³)" required>
                  <el-input-number v-model="form.initialTotalWater" :min="1" :step="10000000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="交易费率 tx">
                  <el-input-number v-model="form.transactionCostRate" :min="0" :max="0.5" :step="0.01" :precision="3" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="价底 (元/m³)">
                  <el-input-number v-model="form.priceFloor" :min="0" :step="0.1" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="价顶 (元/m³)">
                  <el-input-number v-model="form.priceCeiling" :min="0.1" :step="0.1" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="初始保留价 τ (元/m³)">
                  <el-input-number v-model="form.reservePrice" :min="0" :step="0.1" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="公平性权重">
                  <el-input-number v-model="form.fairnessWeight" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="节水激励权重">
                  <el-input-number v-model="form.savingIncentiveWeight" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">14分区参数</el-divider>
            <el-table :data="zones" border size="small" stripe max-height="320" class="zone-config-table">
              <el-table-column prop="zone_name" label="分区" width="80" fixed />
              <el-table-column label="面积<br>(ha)" min-width="110" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.land_area" :min="1" :step="10" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="需水量 (m³)" min-width="160" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.water_demand_m3" :min="0" :step="100000" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="节水潜力 (m³)" min-width="160" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.water_saving_potential_m3" :min="0" :step="100000" controls-position="right" size="small" />
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left">作物结构 (默认按面积加权)</el-divider>
            <el-form-item label="是否使用推荐分区作物比例">
              <el-switch v-model="form.useDefaultCrops" />
            </el-form-item>
            <el-row v-if="!form.useDefaultCrops" :gutter="12">
              <el-col :span="12">
                <el-form-item label="水稻份额">
                  <el-input-number v-model="form.riceShare" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="玉米份额">
                  <el-input-number v-model="form.cornShare" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="大豆份额">
                  <el-input-number v-model="form.soybeanShare" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitSolve" class="action-primary">
                开始水权分配求解
              </el-button>
              <el-button :disabled="!result" @click="resetResult">清空结果</el-button>
            </div>
          </el-form>

          <el-divider content-position="left">接口说明</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="接口地址">/api/v1/irrigation/water-right-allocation/solve</el-descriptions-item>
            <el-descriptions-item label="请求方式">POST / application/json</el-descriptions-item>
            <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <div v-if="!result" class="placeholder">
          <div class="placeholder-title">尚未提交水权分配</div>
          <div class="placeholder-desc">
            提交后将展示市场出清价、社会福利、Stackelberg 上层迭代轨迹，以及分区买卖角色与交易对。
          </div>
        </div>

        <template v-else>
          <div class="kpi-row">
            <div class="kpi-box">
              <div class="kpi-label">市场出清价 p*</div>
              <div class="kpi-value">{{ fmtNumber(clearingPrice, 3) }}<span>元/m³</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">总交易量</div>
              <div class="kpi-value">{{ fmtNumber(totalTraded, 1) }}<span>万 m³</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">社会福利</div>
              <div class="kpi-value">{{ fmtNumber(socialWelfare, 1) }}<span>万元</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">公平性指数</div>
              <div class="kpi-value">{{ fmtNumber(fairness, 4) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">卖家 / 买家</div>
              <div class="kpi-value">
                {{ nSellers }}<span>/</span>{{ nBuyers }}
              </div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">交易成本</div>
              <div class="kpi-value">{{ fmtNumber(txCost, 1) }}<span>万元</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">上层迭代</div>
              <div class="kpi-value">{{ leaderIters }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">节水总量</div>
              <div class="kpi-value">{{ fmtNumber(waterSaved, 1) }}<span>万 m³</span></div>
            </div>
          </div>

          <el-row :gutter="20" class="chart-row">
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="result-card chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">分区角色构成</span>
                    <span class="chart-sub">seller / buyer / self</span>
                  </div>
                </template>
                <div ref="rolePieRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="result-card chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">分区自用 vs 初始水权</span>
                    <span class="chart-sub">万 m³</span>
                  </div>
                </template>
                <div ref="initialUsedRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="result-card chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">分区净收益</span>
                    <span class="chart-sub">万元</span>
                  </div>
                </template>
                <div ref="profitRef" class="chart" />
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="hover" class="result-card chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">上层 Stackelberg 迭代轨迹</span>
                  <span class="chart-sub">沿 τ 网格扫描出清价与社会福利</span>
                </div>
              </div>
            </template>
            <div ref="leaderRef" class="chart chart-tall" />
          </el-card>

          <el-card shadow="hover" class="result-card chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">贸易配对 (Top 10)</span>
                  <span class="chart-sub">卖家 → 买家 流量 (万 m³)</span>
                </div>
              </div>
            </template>
            <div ref="tradeFlowRef" class="chart chart-tall" />
          </el-card>

          <el-card shadow="hover" class="result-card mt16">
            <template #header><span class="chart-title">初始水权分配表</span></template>
            <el-table :data="result.initial_allocation || []" border size="small" stripe max-height="320">
              <el-table-column prop="zone_name" label="分区" min-width="100" fixed />
              <el-table-column label="面积" min-width="90" align="right">
                <template #default="{ row }">{{ fmtNumber(row.land_area_ha, 1) }} ha</template>
              </el-table-column>
              <el-table-column label="初始水权" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.initial_right_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="面积占比" min-width="100" align="right">
                <template #default="{ row }">{{ fmtNumber(Number(row.share_pct || 0) * 100, 2) }}%</template>
              </el-table-column>
              <el-table-column label="估计需水量" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.estimated_demand_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="边际产值 ρ" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.marginal_value_yuan_per_m3, 3) }} 元/m³</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="hover" class="result-card mt16">
            <template #header><span class="chart-title">分区水权交易结果</span></template>
            <el-table :data="result.zone_outcomes || []" border size="small" stripe max-height="320">
              <el-table-column prop="zone_id" label="分区" min-width="80" fixed />
              <el-table-column prop="zone_name" label="名称" min-width="100" />
              <el-table-column label="初始水权" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.initial_right_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="自用量" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.self_used_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="购入" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.purchased_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="售出" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.sold_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="角色" min-width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="净收益" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.net_profit_yuan, 0) }} 元</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card v-if="tradePairs.length" shadow="hover" class="result-card mt16">
            <template #header><span class="chart-title">贸易配对清单</span></template>
            <el-table :data="tradePairs" border size="small" stripe max-height="320">
              <el-table-column prop="seller_zone_id" label="卖方" min-width="80" />
              <el-table-column prop="seller_zone_name" label="卖方分区" min-width="120" />
              <el-table-column prop="buyer_zone_id" label="买方" min-width="80" />
              <el-table-column prop="buyer_zone_name" label="买方分区" min-width="120" />
              <el-table-column label="水量" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.amount_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="单价" min-width="100" align="right">
                <template #default="{ row }">{{ fmtNumber(row.price_yuan_per_m3, 3) }} 元/m³</template>
              </el-table-column>
              <el-table-column label="成交额" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.transaction_value_yuan, 0) }} 元</template>
              </el-table-column>
            </el-table>
          </el-card>
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
import { Promotion } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

import { runWaterRightAllocation } from '@/api/model/waterRightAllocation'

defineOptions({ name: 'WaterRightAllocation' })

const { proxy } = getCurrentInstance()
const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const defaultZones = [
  ['Z01', '红河', 2865.02, 36259380, 4696734],
  ['Z02', '万发', 3135.47, 39296070, 4873331],
  ['Z03', '金光', 3398.08, 41055570, 5091537],
  ['Z04', '稻花香', 3550.21, 30910780, 3833423],
  ['Z05', '发展', 2672.96, 44974950, 5877602],
  ['Z06', '金星', 3212.89, 39945480, 5253868],
  ['Z07', '太平湖', 1761.67, 43645990, 5412790],
  ['Z08', '海洋', 3889.15, 64301350, 8974380],
  ['Z09', '新立', 3454.23, 19992150, 2979341],
  ['Z10', '丰收', 3774.23, 37951930, 4006637],
  ['Z11', '二十八方', 5560.37, 26396760, 3273614],
  ['Z12', '联合', 1795.09, 42364060, 1153810],
  ['Z13', '金边', 2139.52, 7026099, 871347],
  ['Z14', '长吉岗', 5459.97, 33879440, 6701584]
]

const defaultCrops = [
  {
    crop: 'rice',
    crop_name: '水稻',
    yield_kg_per_ha: 9255.56,
    price_yuan_per_kg: 3.16,
    cost_yuan_per_ha: 8400,
    water_quota_m3_per_ha: 8000
  },
  {
    crop: 'corn',
    crop_name: '玉米',
    yield_kg_per_ha: 5269.44,
    price_yuan_per_kg: 2.25,
    cost_yuan_per_ha: 7200,
    water_quota_m3_per_ha: 1900
  },
  {
    crop: 'soybean',
    crop_name: '大豆',
    yield_kg_per_ha: 5945.0,
    price_yuan_per_kg: 5.4,
    cost_yuan_per_ha: 3000,
    water_quota_m3_per_ha: 1700
  }
]

const crops = reactive(defaultCrops.map(item => ({ ...item })))

const zones = reactive(defaultZones.map(([zone_id, zone_name, land_area, surface_water_available, groundwater_available]) => ({
  zone_id,
  zone_name,
  land_area,
  surface_water_available,
  groundwater_available,
  water_demand_m3: Number((land_area * 8000).toFixed(0)),
  water_saving_potential_m3: 0
})))

const submitting = ref(false)
const result = ref(null)
const resultError = ref('')
const rolePieRef = ref(null)
const initialUsedRef = ref(null)
const profitRef = ref(null)
const leaderRef = ref(null)
const tradeFlowRef = ref(null)

let rolePieChart = null
let initialUsedChart = null
let profitChart = null
let leaderChart = null
let tradeFlowChart = null

const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  initialTotalWater: 300000000,
  transactionCostRate: 0.02,
  priceFloor: 0.5,
  priceCeiling: 8.0,
  reservePrice: 1.5,
  fairnessWeight: 0.3,
  savingIncentiveWeight: 0.2,
  useDefaultCrops: true,
  riceShare: 0.5,
  cornShare: 0.3,
  soybeanShare: 0.2
})

const canSubmit = computed(() => {
  if (!form.apiKey.trim()) return false
  if (form.initialTotalWater <= 0) return false
  if (form.priceFloor >= form.priceCeiling) return false
  if (form.reservePrice < form.priceFloor || form.reservePrice > form.priceCeiling) return false
  if (!zones.every(item => item.land_area > 0 && item.water_demand_m3 >= 0)) return false
  if (!crops.every(item => item.yield_kg_per_ha > 0 && item.price_yuan_per_kg > 0 && item.water_quota_m3_per_ha > 0)) return false
  return true
})

const clearingPrice = computed(() => Number(result.value?.equilibrium?.clearing_price_yuan_per_m3 || 0))
const totalTraded = computed(() => Number(result.value?.summary?.total_traded_m3 || 0) / 1e4)
const socialWelfare = computed(() => Number(result.value?.summary?.total_social_welfare_yuan || 0) / 1e4)
const fairness = computed(() => Number(result.value?.summary?.fairness_index || 0))
const nSellers = computed(() => Number(result.value?.equilibrium?.n_sellers || 0))
const nBuyers = computed(() => Number(result.value?.equilibrium?.n_buyers || 0))
const txCost = computed(() => Number(result.value?.summary?.total_transaction_cost_yuan || 0) / 1e4)
const leaderIters = computed(() => (result.value?.leader_history || []).length)
const waterSaved = computed(() => Number(result.value?.summary?.total_water_saved_m3 || 0) / 1e4)
const tradePairs = computed(() => result.value?.trade_flows || [])

const CHART_COLORS = ['#5b8def', '#22c55e', '#f97316', '#14b8a6', '#a855f7']

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return num.toFixed(digits)
}

function roleLabel(role) {
  return role === 'seller' ? '卖家' : role === 'buyer' ? '买家' : '自给'
}

function roleTagType(role) {
  return role === 'seller' ? 'success' : role === 'buyer' ? 'warning' : 'info'
}

function initChart(el, chartRef) {
  if (!el || !el.isConnected) return null
  if (chartRef) chartRef.dispose()
  return echarts.init(el)
}

function destroyCharts() {
  ;[rolePieChart, initialUsedChart, profitChart, leaderChart, tradeFlowChart].forEach(chart => {
    if (chart) chart.dispose()
  })
  rolePieChart = null
  initialUsedChart = null
  profitChart = null
  leaderChart = null
  tradeFlowChart = null
}

function resizeCharts() {
  ;[rolePieChart, initialUsedChart, profitChart, leaderChart, tradeFlowChart].forEach(chart => {
    if (chart) chart.resize()
  })
}

function renderRolePie() {
  rolePieChart = initChart(rolePieRef.value, rolePieChart)
  if (!rolePieChart) return
  const rows = result.value?.zone_outcomes || []
  const counts = { seller: 0, buyer: 0, self: 0 }
  rows.forEach(r => {
    const role = r.role || 'self'
    counts[role] = (counts[role] || 0) + 1
  })
  rolePieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    color: ['#22c55e', '#f97316', '#94a3b8'],
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '43%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{c}区', fontSize: 11 },
      data: [
        { name: '卖家', value: counts.seller || 0 },
        { name: '买家', value: counts.buyer || 0 },
        { name: '自给', value: counts.self || 0 }
      ]
    }]
  })
}

function renderInitialUsed() {
  initialUsedChart = initChart(initialUsedRef.value, initialUsedChart)
  if (!initialUsedChart) return
  const rows = result.value?.zone_outcomes || []
  initialUsedChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 56, right: 36, top: 30, bottom: 56 },
    xAxis: { type: 'category', data: rows.map(item => item.zone_name), axisLabel: { interval: 0, rotate: 35 } },
    yAxis: { type: 'value', name: '水量(万m³)' },
    color: CHART_COLORS,
    series: [
      { name: '初始水权', type: 'bar', data: rows.map(item => Number(item.initial_right_m3 || 0) / 1e4) },
      { name: '自用量', type: 'bar', data: rows.map(item => Number(item.self_used_m3 || 0) / 1e4) }
    ]
  })
}

function renderProfit() {
  profitChart = initChart(profitRef.value, profitChart)
  if (!profitChart) return
  const rows = result.value?.zone_outcomes || []
  const data = rows.map(item => Number(item.net_profit_yuan || 0) / 1e4)
  const isAllZero = data.every(v => Math.abs(v) < 1e-6)
  profitChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 56, right: 36, top: 28, bottom: 56 },
    xAxis: { type: 'category', data: rows.map(item => item.zone_name), axisLabel: { interval: 0, rotate: 35 } },
    yAxis: { type: 'value', name: '净收益(万元)' },
    series: [{
      name: '净收益',
      type: 'bar',
      data: data.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? '#22c55e' : '#f97316' }
      }))
    }]
  })
  if (isAllZero) {
    profitChart.setOption({
      title: { text: '净收益接近 0', left: 'center', top: 'middle', textStyle: { color: '#94a3b8', fontSize: 12 } }
    })
  }
}

function renderLeader() {
  leaderChart = initChart(leaderRef.value, leaderChart)
  if (!leaderChart) return
  const history = result.value?.leader_history || []
  if (!history.length) {
    leaderChart.setOption({ title: { text: '暂无上层迭代数据', left: 'center', top: 'middle' } })
    return
  }
  leaderChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 60, right: 60, top: 36, bottom: 56 },
    xAxis: {
      type: 'category',
      name: '保留价 τ',
      data: history.map(item => Number(item.reserve_price || 0).toFixed(2))
    },
    yAxis: [
      { type: 'value', name: '社会福利', position: 'left', axisLabel: { fontSize: 11 } },
      { type: 'value', name: '总交易量(万m³)', position: 'right', axisLabel: { fontSize: 11 } }
    ],
    color: [CHART_COLORS[0], CHART_COLORS[2]],
    series: [
      { name: '社会福利', type: 'line', smooth: true, yAxisIndex: 0, data: history.map(item => Number(item.social_welfare || 0) / 1e4) },
      { name: '总交易量', type: 'bar', yAxisIndex: 1, data: history.map(item => Number(item.total_buy_m3 || 0) / 1e4) }
    ]
  })
}

function renderTradeFlow() {
  tradeFlowChart = initChart(tradeFlowRef.value, tradeFlowChart)
  if (!tradeFlowChart) return
  const pairs = (result.value?.trade_flows || []).slice(0, 10)
  const labels = pairs.map(item => `${item.seller_zone_name} → ${item.buyer_zone_name}`)
  const amounts = pairs.map(item => Number(item.amount_m3 || 0) / 1e4)
  tradeFlowChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 60, right: 28, top: 28, bottom: 96 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30, interval: 0, fontSize: 10 } },
    yAxis: { type: 'value', name: '水量(万m³)' },
    color: CHART_COLORS,
    series: [{ name: '水量', type: 'bar', data: amounts, itemStyle: { color: CHART_COLORS[2] } }]
  })
}

function renderCharts() {
  renderRolePie()
  renderInitialUsed()
  renderProfit()
  renderLeader()
  renderTradeFlow()
  setTimeout(resizeCharts, 50)
}

function buildPayload() {
  const totalLandArea = zones.reduce((s, z) => s + Number(z.land_area || 0), 0) || 1
  let cropMix = null
  if (!form.useDefaultCrops) {
    const sum = form.riceShare + form.cornShare + form.soybeanShare || 1
    cropMix = {
      rice: form.riceShare / sum,
      corn: form.cornShare / sum,
      soybean: form.soybeanShare / sum
    }
  }
  return {
    crops: crops.map(item => ({ ...item })),
    zones: zones.map(item => {
      const ratio = Number(item.land_area || 0) / totalLandArea
      const mixed = cropMix || {
        rice: 0.45,
        corn: 0.25,
        soybean: 0.30
      }
      const payload = {
        zone_id: item.zone_id,
        zone_name: item.zone_name,
        land_area: item.land_area,
        surface_water_available: item.surface_water_available,
        groundwater_available: item.groundwater_available,
        water_demand_m3: item.water_demand_m3,
        crop_mix: mixed,
        water_saving_potential_m3: item.water_saving_potential_m3 || 0,
        marginal_value: 0
      }
      void ratio
      return payload
    }),
    market: {
      initial_total_water_m3: form.initialTotalWater,
      reserve_price_yuan_per_m3: form.reservePrice,
      price_floor: form.priceFloor,
      price_ceiling: form.priceCeiling,
      transaction_cost_rate: form.transactionCostRate,
      fairness_weight: form.fairnessWeight,
      saving_incentive_weight: form.savingIncentiveWeight,
      min_self_use_ratio: 0.0
    }
  }
}

async function submitSolve() {
  if (!canSubmit.value) return
  resultError.value = ''
  destroyCharts()
  submitting.value = true
  try {
    result.value = await runWaterRightAllocation(buildPayload(), form.apiKey.trim())
    await nextTick()
    renderCharts()
    proxy.$modal.msgSuccess('水权分配完成')
  } catch (err) {
    resultError.value = err?.message || '水权分配失败'
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

watch(result, async (val) => {
  if (!val) return
  await nextTick()
  renderCharts()
})

window.addEventListener('resize', resizeCharts)
onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  destroyCharts()
})
</script>

<style scoped>
.water-right-allocation-page { padding-bottom: 28px; }
.water-right-allocation-hero { margin-bottom: 20px; }
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
.resource-form :deep(.el-form-item) { margin-bottom: 14px; }
.resource-form :deep(.el-form-item__label) { font-size: 0.8em; color: var(--text-regular); padding: 0 0 4px; line-height: 1.3; font-weight: 500; }
.zone-config-table :deep(.el-input-number),
.crop-config-table :deep(.el-input-number) { width: 100%; min-width: 80px; }
.zone-config-table :deep(.el-input-number__decrease),
.zone-config-table :deep(.el-input-number__increase),
.crop-config-table :deep(.el-input-number__decrease),
.crop-config-table :deep(.el-input-number__increase) { display: none; }
.zone-config-table :deep(.el-input__wrapper),
.crop-config-table :deep(.el-input__wrapper) { padding-left: 4px; padding-right: 4px; }
.action-row { display: flex; gap: 10px; margin-top: 12px; }
.action-primary { flex: 1; }
.placeholder { padding: 56px 20px; text-align: center; background: var(--surface-soft-bg); border-radius: 18px; border: 1px dashed var(--hairline-color); }
.placeholder-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.placeholder-desc { margin-top: 10px; font-size: 0.867em; line-height: 1.7; color: var(--text-secondary); }
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 14px; }
.kpi-box { padding: 18px 20px; border-radius: 18px; background: var(--surface-bg); border: 1px solid var(--hairline-color); box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05); }
.kpi-label { font-size: 0.867em; color: var(--text-secondary); font-weight: 500; }
.kpi-value { margin-top: 8px; font-size: 25px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.kpi-value span { margin-left: 4px; font-size: 0.58em; font-weight: 500; color: var(--text-secondary); }
.chart-row { margin-top: 16px; }
.chart-card :deep(.el-card__body) { padding: 14px; }
.chart-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.chart-title { font-size: 1em; font-weight: 650; color: var(--text-primary); }
.chart-sub { margin-left: 8px; font-size: 12px; color: var(--text-secondary); font-weight: 400; }
.chart { width: 100%; height: 280px; min-width: 0; }
.chart-tall { height: 340px; }
.mt16 { margin-top: 16px; }
.error-box { padding: 16px; border-radius: 18px; background: var(--surface-bg); border: 1px solid var(--hairline-color); }
@media (max-width: 768px) {
  .kpi-value { font-size: 22px; }
  .chart { height: 260px; }
  .chart-tall { height: 320px; }
}
</style>
