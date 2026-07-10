<template>
  <div class="app-container agri-page water-soil-resource-page">
    <section class="agri-page__hero water-soil-resource-hero">
      <div class="hero-content">
        <span class="agri-page__eyebrow">NSGA-II WATER-NITROGEN ALLOCATION</span>
        <h1 class="agri-page__title">灌区水土资源优化配置</h1>
        <p class="agri-page__desc">
          面向14个管理区，协同优化水稻、玉米、大豆的种植面积、地表水量、地下水量和施氮量，
          兼顾单方水效益、公平性、用水效率与氮肥利用效率。
        </p>
        <div class="agri-page__siblings">
          <router-link to="/model/irrigation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>灌溉决策</span>
          </router-link>
          <router-link to="/model/canal/optimize" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系优化配水</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="resource-tag">14 管理区</span>
        <span class="resource-tag resource-tag--green">水稻 / 玉米 / 大豆</span>
        <span class="resource-tag resource-tag--orange">水量 / 氮量</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <el-col :xs="24" :lg="9">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">参数配置</div>
                <div class="card-desc">分区、作物参数、水量约束均可自定义。</div>
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
            <el-table :data="crops" border size="small" stripe max-height="280" class="crop-config-table">
              <el-table-column prop="crop_name" label="作物" width="80" fixed />
              <el-table-column label="产量<br>(kg/ha)" min-width="90" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.yield_kg_per_ha" :min="0" :step="100" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="单价<br>(元/kg)" min-width="90" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.price_yuan_per_kg" :min="0" :step="0.1" :precision="2" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="成本<br>(元/ha)" min-width="90" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.cost_yuan_per_ha" :min="0" :step="100" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="灌溉定额<br>(m³/ha)" min-width="95" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.water_quota_m3_per_ha" :min="1" :step="100" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="施氮下限<br>(kg/ha)" min-width="95" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.nitrogen_min_kg_ha" :min="0" :step="5" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="施氮上限<br>(kg/ha)" min-width="95" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.nitrogen_max_kg_ha" :min="1" :step="5" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="氮效系数" min-width="80" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.nitrogen_productivity_coeff" :min="0.01" :step="0.05" :precision="2" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="水效系数" min-width="80" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.water_productivity_coeff" :min="0.01" :step="0.05" :precision="2" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="氮成本<br>(元/kg)" min-width="85" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.nitrogen_cost_yuan_per_kg" :min="0" :step="0.1" :precision="2" controls-position="right" size="small" />
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left">全局水量约束</el-divider>
            <el-form-item label="灌区总可供水量 (m³)" required>
              <el-input-number v-model="form.totalWaterAvailable" :min="1" :step="100000" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">14分区参数</el-divider>
            <el-table :data="zones" border size="small" stripe max-height="360" class="zone-config-table">
              <el-table-column prop="zone_name" label="分区" width="80" fixed />
              <el-table-column label="面积<br>(ha)" min-width="108" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.land_area" :min="1" :step="10" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="最小面积<br>(ha)" min-width="108" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.min_area" :min="0" :step="10" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="最大面积<br>(ha)" min-width="108" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.max_area" :min="0" :step="10" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="地表水<br>(m³)" min-width="120" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.surface_water_available" :min="0" :step="100000" controls-position="right" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="地下水<br>(m³)" min-width="120" align="right">
                <template #default="{ row }">
                  <el-input-number v-model="row.groundwater_available" :min="0" :step="10000" controls-position="right" size="small" />
                </template>
              </el-table-column>
            </el-table>

            <el-divider content-position="left">NSGA-II 超参</el-divider>
            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="种群 pop">
                  <el-input-number v-model="form.popSize" :min="10" :max="600" :step="10" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="迭代 n_gen">
                  <el-input-number v-model="form.nGen" :min="1" :max="2000" :step="10" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="随机种子">
                  <el-input-number v-model="form.seed" :min="0" :max="999" :step="1" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">目标权重</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="单方水效益">
                  <el-input-number v-model="form.prefBenefit" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="公平性">
                  <el-input-number v-model="form.prefFairness" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="用水效率">
                  <el-input-number v-model="form.prefEfficiency" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="氮肥利用效率">
                  <el-input-number v-model="form.prefNitrogen" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="混合系数 α">
              <el-input-number v-model="form.alpha" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
            </el-form-item>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitOptimize" class="action-primary">
                开始水氮资源配置优化
              </el-button>
              <el-button :disabled="!result" @click="resetResult">清空结果</el-button>
            </div>
          </el-form>

          <el-divider content-position="left">接口说明</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="接口地址">/api/v1/irrigation/water-soil-resource/optimize</el-descriptions-item>
            <el-descriptions-item label="请求方式">POST / application/json</el-descriptions-item>
            <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <div v-if="!result" class="placeholder">
          <div class="placeholder-title">尚未提交优化</div>
          <div class="placeholder-desc">提交后将展示四目标 KPI、分区水源供需、作物水氮汇总和分区-作物配置。</div>
        </div>

        <template v-else>
          <div class="kpi-row">
            <div class="kpi-box">
              <div class="kpi-label">单方水效益</div>
              <div class="kpi-value">{{ fmtNumber(objectives.unit_water_benefit_yuan_per_m3, 3) }}<span>元/m³</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">公平性</div>
              <div class="kpi-value">{{ fmtNumber(objectives.fairness, 4) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">用水效率</div>
              <div class="kpi-value">{{ fmtNumber(objectives.water_efficiency_kg_per_m3, 3) }}<span>kg/m³</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">氮肥利用效率</div>
              <div class="kpi-value">{{ fmtNumber(objectives.nitrogen_efficiency_kg_per_kg, 3) }}<span>kg/kg</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">总种植面积</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.total_area_ha, 1) }}<span>ha</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">总施氮量</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.total_nitrogen_kg, 0) }}<span>kg</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">总用水量</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.total_water_m3, 0) }}<span>m³</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">TOPSIS 评分</div>
              <div class="kpi-value">{{ fmtNumber(result.summary?.topsis_score, 4) }}</div>
            </div>
          </div>

          <el-row :gutter="20" class="chart-row">
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="result-card chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">四目标表现</span>
                    <span class="chart-sub">归一化雷达</span>
                  </div>
                </template>
                <div ref="objectiveRadarRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="result-card chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">TOPSIS 权重</span>
                    <span class="chart-sub">四目标融合</span>
                  </div>
                </template>
                <div ref="weightPieRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="result-card chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">作物配置</span>
                    <span class="chart-sub">面积 / 水 / 氮</span>
                  </div>
                </template>
                <div ref="cropSummaryRef" class="chart" />
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="hover" class="result-card chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">分区水源与施氮配置</span>
                  <span class="chart-sub">地表水、地下水与总施氮量对比</span>
                </div>
              </div>
            </template>
            <div ref="zoneWaterNitrogenRef" class="chart chart-tall" />
          </el-card>

          <el-card shadow="hover" class="result-card chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">Pareto 前沿（3D 散点）</span>
                  <span class="chart-sub">X=单方水效益，Y=公平性，Z=用水效率，颜色=氮肥利用效率</span>
                </div>
                <el-tag size="small" type="success">
                  已选 {{ paretoSelectedCount }} / {{ result.pareto?.length || 0 }}
                </el-tag>
              </div>
            </template>
            <div ref="pareto3dRef" class="chart chart-3d" />
          </el-card>

          <el-card shadow="hover" class="result-card mt16">
            <template #header><span class="chart-title">分区水源与氮肥汇总</span></template>
            <el-table :data="result.zone_summary || []" border size="small" stripe max-height="360">
              <el-table-column prop="zone_name" label="分区" min-width="90" fixed />
              <el-table-column label="面积" min-width="90" align="right">
                <template #default="{ row }">{{ fmtNumber(row.allocated_area_ha, 1) }} ha</template>
              </el-table-column>
              <el-table-column label="地表水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.surface_water_used_m3, 0) }}</template>
              </el-table-column>
              <el-table-column label="地下水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.groundwater_used_m3, 0) }}</template>
              </el-table-column>
              <el-table-column label="总用水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.water_used_m3, 0) }}</template>
              </el-table-column>
              <el-table-column label="施氮量" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.total_nitrogen_kg, 0) }}</template>
              </el-table-column>
              <el-table-column label="满足度" min-width="90" align="right">
                <template #default="{ row }">{{ fmtNumber(row.satisfaction, 3) }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="hover" class="result-card mt16">
            <template #header><span class="chart-title">作物水氮配置汇总</span></template>
            <el-table :data="result.crop_summary || []" border size="small" stripe>
              <el-table-column prop="crop_name" label="作物" min-width="90" />
              <el-table-column label="面积" min-width="90" align="right">
                <template #default="{ row }">{{ fmtNumber(row.area_ha, 1) }} ha</template>
              </el-table-column>
              <el-table-column label="产量" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.yield_kg, 0) }} kg</template>
              </el-table-column>
              <el-table-column label="总用水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.total_water_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="总施氮" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.total_nitrogen_kg, 0) }} kg</template>
              </el-table-column>
              <el-table-column label="净收益" min-width="120" align="right">
                <template #default="{ row }">{{ fmtNumber(row.net_benefit_yuan, 0) }} 元</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="hover" class="result-card mt16">
            <template #header><span class="chart-title">分区-作物种植面积、水量与施氮量</span></template>
            <el-table :data="result.allocation || []" border size="small" stripe max-height="460">
              <el-table-column prop="zone_name" label="分区" min-width="90" fixed />
              <el-table-column prop="crop_name" label="作物" min-width="80" fixed />
              <el-table-column label="种植面积" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.area_ha, 2) }} ha</template>
              </el-table-column>
              <el-table-column label="地表水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.surface_water_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="地下水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.groundwater_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="总用水" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.total_water_m3, 0) }} m³</template>
              </el-table-column>
              <el-table-column label="单位施氮" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.nitrogen_kg_ha, 1) }} kg/ha</template>
              </el-table-column>
              <el-table-column label="总施氮" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.total_nitrogen_kg, 0) }} kg</template>
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
import 'echarts-gl'

import { runWaterSoilResourceOptimize } from '@/api/model/waterSoilResource'

defineOptions({ name: 'WaterSoilResource' })

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
    min_area_ratio: 0.0,
    max_area_ratio: 1.0,
    yield_kg_per_ha: 9255.56,
    price_yuan_per_kg: 3.16,
    cost_yuan_per_ha: 8400,
    water_quota_m3_per_ha: 8000,
    nitrogen_min_kg_ha: 80,
    nitrogen_max_kg_ha: 250,
    nitrogen_productivity_coeff: 1.0,
    water_productivity_coeff: 1.0,
    nitrogen_cost_yuan_per_kg: 1.0
  },
  {
    crop: 'corn',
    crop_name: '玉米',
    min_area_ratio: 0.0,
    max_area_ratio: 1.0,
    yield_kg_per_ha: 5269.44,
    price_yuan_per_kg: 2.25,
    cost_yuan_per_ha: 7200,
    water_quota_m3_per_ha: 1900,
    nitrogen_min_kg_ha: 70,
    nitrogen_max_kg_ha: 230,
    nitrogen_productivity_coeff: 1.05,
    water_productivity_coeff: 1.03,
    nitrogen_cost_yuan_per_kg: 1.0
  },
  {
    crop: 'soybean',
    crop_name: '大豆',
    min_area_ratio: 0.0,
    max_area_ratio: 1.0,
    yield_kg_per_ha: 5945.0,
    price_yuan_per_kg: 5.4,
    cost_yuan_per_ha: 3000,
    water_quota_m3_per_ha: 1700,
    nitrogen_min_kg_ha: 40,
    nitrogen_max_kg_ha: 180,
    nitrogen_productivity_coeff: 1.08,
    water_productivity_coeff: 1.05,
    nitrogen_cost_yuan_per_kg: 1.0
  }
]

const crops = reactive(defaultCrops.map(item => ({ ...item })))

const zones = reactive(defaultZones.map(([zone_id, zone_name, land_area, surface_water_available, groundwater_available]) => ({
  zone_id,
  zone_name,
  land_area,
  min_area: Number((land_area * 0.75).toFixed(4)),
  max_area: land_area,
  surface_water_available,
  groundwater_available
})))

const submitting = ref(false)
const result = ref(null)
const resultError = ref('')
const objectiveRadarRef = ref(null)
const weightPieRef = ref(null)
const cropSummaryRef = ref(null)
const zoneWaterNitrogenRef = ref(null)
const pareto3dRef = ref(null)

let objectiveRadarChart = null
let weightPieChart = null
let cropSummaryChart = null
let zoneWaterNitrogenChart = null
let pareto3dChart = null

const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  totalWaterAvailable: 0,
  popSize: 80,
  nGen: 60,
  seed: 1,
  prefBenefit: 0.35,
  prefFairness: 0.25,
  prefEfficiency: 0.25,
  prefNitrogen: 0.15,
  alpha: 0.5
})

const canSubmit = computed(() => {
  if (!form.apiKey.trim()) return false
  if (form.totalWaterAvailable <= 0) return false
  if (!zones.every(item => item.land_area > 0 && (item.surface_water_available + item.groundwater_available) > 0)) return false
  if (!crops.every(item =>
    item.yield_kg_per_ha > 0 &&
    item.price_yuan_per_kg > 0 &&
    item.water_quota_m3_per_ha > 0 &&
    item.nitrogen_max_kg_ha > 0 &&
    item.nitrogen_min_kg_ha <= item.nitrogen_max_kg_ha
  )) return false
  return true
})

const objectives = computed(() => result.value?.summary?.objective_values || {})
const paretoSelectedCount = computed(() => (result.value?.pareto || []).filter(item => item.selected).length)

const OBJECTIVE_LABELS = [
  ['unit_water_benefit_yuan_per_m3', '单方水效益'],
  ['fairness', '公平性'],
  ['water_efficiency_kg_per_m3', '用水效率'],
  ['nitrogen_efficiency_kg_per_kg', '氮肥利用效率']
]

const CHART_COLORS = ['#5b8def', '#22c55e', '#f97316', '#14b8a6', '#a855f7']

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return num.toFixed(digits)
}

function initChart(el, chartRef) {
  if (!el || !el.isConnected) return null
  if (chartRef) chartRef.dispose()
  return echarts.init(el)
}

function destroyCharts() {
  ;[objectiveRadarChart, weightPieChart, cropSummaryChart, zoneWaterNitrogenChart, pareto3dChart].forEach(chart => {
    if (chart) chart.dispose()
  })
  objectiveRadarChart = null
  weightPieChart = null
  cropSummaryChart = null
  zoneWaterNitrogenChart = null
  pareto3dChart = null
}

function resizeCharts() {
  ;[objectiveRadarChart, weightPieChart, cropSummaryChart, zoneWaterNitrogenChart, pareto3dChart].forEach(chart => {
    if (chart) chart.resize()
  })
}

function normalizeObjectiveValues() {
  const vals = OBJECTIVE_LABELS.map(([key]) => Number(objectives.value[key] || 0))
  const max = Math.max(...vals.map(v => Math.abs(v)), 1e-6)
  return vals.map(v => Number((v / max).toFixed(6)))
}

function renderObjectiveRadar() {
  objectiveRadarChart = initChart(objectiveRadarRef.value, objectiveRadarChart)
  if (!objectiveRadarChart) return
  objectiveRadarChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      radius: '62%',
      indicator: OBJECTIVE_LABELS.map(([, name]) => ({ name, max: 1 })),
      splitNumber: 4,
      axisName: { color: '#475569', fontSize: 12 }
    },
    series: [{
      type: 'radar',
      areaStyle: { color: 'rgba(91, 141, 239, 0.18)' },
      lineStyle: { color: CHART_COLORS[0], width: 2 },
      itemStyle: { color: CHART_COLORS[0] },
      data: [{ name: 'TOPSIS优选方案', value: normalizeObjectiveValues() }]
    }]
  })
}

function renderWeightPie() {
  weightPieChart = initChart(weightPieRef.value, weightPieChart)
  if (!weightPieChart) return
  const weights = result.value?.summary?.entropy_weights || {}
  const data = OBJECTIVE_LABELS.map(([key, name]) => ({
    name,
    value: Number(weights[key.replace('_yuan_per_m3', '').replace('_kg_per_m3', '').replace('_kg_per_kg', '')] ?? weights[key] ?? 0)
  }))
  weightPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} ({d}%)' },
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10 },
    color: CHART_COLORS,
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '43%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data
    }]
  })
}

function renderCropSummary() {
  cropSummaryChart = initChart(cropSummaryRef.value, cropSummaryChart)
  if (!cropSummaryChart) return
  const rows = result.value?.crop_summary || []
  cropSummaryChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0 },
    grid: { left: 50, right: 44, top: 28, bottom: 48 },
    xAxis: { type: 'category', data: rows.map(item => item.crop_name) },
    yAxis: [
      { type: 'value', name: '面积(ha)', axisLabel: { fontSize: 11 } },
      { type: 'value', name: '水/氮', axisLabel: { fontSize: 11 } }
    ],
    color: CHART_COLORS,
    series: [
      { name: '面积(ha)', type: 'bar', data: rows.map(item => Number(item.area_ha || 0)), yAxisIndex: 0 },
      { name: '总用水(万m³)', type: 'bar', data: rows.map(item => Number(item.total_water_m3 || 0) / 10000), yAxisIndex: 1 },
      { name: '总施氮(t)', type: 'line', smooth: true, data: rows.map(item => Number(item.total_nitrogen_kg || 0) / 1000), yAxisIndex: 1 }
    ]
  })
}

function renderZoneWaterNitrogen() {
  zoneWaterNitrogenChart = initChart(zoneWaterNitrogenRef.value, zoneWaterNitrogenChart)
  if (!zoneWaterNitrogenChart) return
  const rows = result.value?.zone_summary || []
  zoneWaterNitrogenChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0 },
    grid: { left: 58, right: 64, top: 44, bottom: 76 },
    dataZoom: [{ type: 'slider', bottom: 28, height: 18 }, { type: 'inside' }],
    xAxis: { type: 'category', data: rows.map(item => item.zone_name), axisLabel: { interval: 0, rotate: 35 } },
    yAxis: [
      { type: 'value', name: '水量(万m³)' },
      { type: 'value', name: '施氮(t)' }
    ],
    color: CHART_COLORS,
    series: [
      { name: '地表水', type: 'bar', stack: 'water', data: rows.map(item => Number(item.surface_water_used_m3 || 0) / 10000), yAxisIndex: 0 },
      { name: '地下水', type: 'bar', stack: 'water', data: rows.map(item => Number(item.groundwater_used_m3 || 0) / 10000), yAxisIndex: 0 },
      { name: '总施氮', type: 'line', smooth: true, data: rows.map(item => Number(item.total_nitrogen_kg || 0) / 1000), yAxisIndex: 1 }
    ]
  })
}

function renderPareto3d() {
  pareto3dChart = initChart(pareto3dRef.value, pareto3dChart)
  if (!pareto3dChart) return
  const data = result.value?.pareto || []
  if (!data.length) {
    pareto3dChart.setOption({ title: { text: '暂无 Pareto 数据', left: 'center', top: 'middle' } })
    return
  }
  const nitrogenVals = data.map(item => Number(item.nitrogen_efficiency_kg_per_kg || 0))
  const minNitrogen = Math.min(...nitrogenVals)
  const maxNitrogen = Math.max(...nitrogenVals)
  const makeValue = item => [
    Number(item.unit_water_benefit_yuan_per_m3 || 0),
    Number(item.fairness || 0),
    Number(item.water_efficiency_kg_per_m3 || 0),
    Number(item.nitrogen_efficiency_kg_per_kg || 0),
    Number(item.score || 0),
    item.selected ? 1 : 0
  ]
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const d = p.data.value
        return [
          `单方水效益: ${fmtNumber(d[0], 4)} 元/m³`,
          `公平性: ${fmtNumber(d[1], 4)}`,
          `用水效率: ${fmtNumber(d[2], 4)} kg/m³`,
          `氮肥利用效率: ${fmtNumber(d[3], 4)} kg/kg`,
          `TOPSIS: ${fmtNumber(d[4], 4)}`,
          d[5] ? 'TOPSIS 优选' : ''
        ].filter(Boolean).join('<br/>')
      }
    },
    visualMap: {
      show: true,
      dimension: 3,
      min: minNitrogen,
      max: maxNitrogen,
      calculable: true,
      right: 12,
      top: 'center',
      text: ['氮效', ''],
      inRange: { color: ['#bfdbfe', '#22c55e', '#f97316'] }
    },
    xAxis3D: { name: '单方水效益', type: 'value' },
    yAxis3D: { name: '公平性', type: 'value' },
    zAxis3D: { name: '用水效率', type: 'value' },
    grid3D: {
      boxWidth: 120,
      boxDepth: 110,
      viewControl: { projection: 'perspective', alpha: 22, beta: 34 },
      light: { main: { intensity: 1.2 }, ambient: { intensity: 0.35 } }
    },
    series: [{
      type: 'scatter3D',
      symbolSize: 11,
      data: data.map(item => ({
        value: makeValue(item),
        itemStyle: item.selected ? { borderColor: '#fff', borderWidth: 2 } : undefined
      }))
    }]
  }
  const selected = data.filter(item => item.selected)
  if (selected.length) {
    option.series.push({
      type: 'scatter3D',
      symbol: 'star',
      symbolSize: 26,
      data: selected.map(item => ({ value: makeValue(item) })),
      itemStyle: { color: '#f97316' }
    })
  }
  pareto3dChart.setOption(option)
}

function renderCharts() {
  renderObjectiveRadar()
  renderWeightPie()
  renderCropSummary()
  renderZoneWaterNitrogen()
  renderPareto3d()
  setTimeout(resizeCharts, 50)
}

function buildPayload() {
  return {
    mode: 'water-soil-resource',
    crops: crops.map(item => ({ ...item })),
    zones: zones.map(item => ({
      zone_id: item.zone_id,
      zone_name: item.zone_name,
      land_area: item.land_area,
      min_area: item.min_area,
      max_area: item.max_area || item.land_area,
      surface_water_available: item.surface_water_available,
      groundwater_available: item.groundwater_available
    })),
    stages: [],
    total_water_available: form.totalWaterAvailable,
    pop_size: form.popSize,
    n_gen: form.nGen,
    seed: form.seed,
    pref_weight_benefit: form.prefBenefit,
    pref_weight_fairness: form.prefFairness,
    pref_weight_efficiency: form.prefEfficiency,
    pref_weight_nitrogen_efficiency: form.prefNitrogen,
    alpha: form.alpha
  }
}

async function submitOptimize() {
  if (!canSubmit.value) return
  resultError.value = ''
  destroyCharts()
  submitting.value = true
  try {
    result.value = await runWaterSoilResourceOptimize(buildPayload(), form.apiKey.trim())
    await nextTick()
    renderCharts()
    proxy.$modal.msgSuccess('优化完成')
  } catch (err) {
    resultError.value = err?.message || '优化失败'
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
.water-soil-resource-page { padding-bottom: 28px; }
.water-soil-resource-hero { margin-bottom: 20px; }
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
.crop-config-table :deep(.el-input-number) { width: 100%; min-width: 70px; }
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
.chart-tall { height: 360px; }
.chart-3d { height: 440px; }
.mt16 { margin-top: 16px; }
.error-box { padding: 16px; border-radius: 18px; background: var(--surface-bg); border: 1px solid var(--hairline-color); }
@media (max-width: 768px) {
  .kpi-value { font-size: 22px; }
  .chart { height: 260px; }
  .chart-3d { height: 360px; }
}
</style>
