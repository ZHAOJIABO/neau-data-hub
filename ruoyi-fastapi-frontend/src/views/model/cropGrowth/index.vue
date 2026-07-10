<template>
  <div class="app-container agri-page crop-growth-page">
    <section class="agri-page__hero crop-growth-hero">
      <div class="hero-content">
        <span class="agri-page__eyebrow">PCSE / WOFOST RICE MODEL</span>
        <h1 class="agri-page__title">水稻作物生长模拟</h1>
        <p class="agri-page__desc">
          基于 PCSE WOFOST72 水分限制模型，按经纬度调用 NASA POWER 气象数据，输出水稻全生育期逐日生长指标。
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
        <span>WOFOST72</span>
        <span>NASA POWER</span>
        <span>逐日指标</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">模拟参数</div>
                <div class="card-desc">填写地块位置、生育期和灌溉阈值后提交模型计算。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'">
                {{ resultError ? '接口异常' : result ? '结果已生成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="small">
            <el-divider content-position="left">地块位置</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="经度" prop="longitude">
                  <el-input-number v-model="form.longitude" :min="-180" :max="180" :step="0.01" :precision="4" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="纬度" prop="latitude">
                  <el-input-number v-model="form.latitude" :min="-90" :max="90" :step="0.01" :precision="4" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">生育期</el-divider>
            <el-form-item label="模拟开始日期" prop="simulationStartDate">
              <el-date-picker v-model="form.simulationStartDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
            <el-form-item label="作物开始日期" prop="plantStartDate">
              <el-date-picker v-model="form.plantStartDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
            <el-form-item label="灌溉结束日期" prop="irrigationEndDate">
              <el-date-picker v-model="form.irrigationEndDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
            <el-form-item label="作物结束日期" prop="plantEndDate">
              <el-date-picker v-model="form.plantEndDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">灌溉参数</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="土壤水分阈值" prop="soilMoistureThreshold">
                  <el-input-number v-model="form.soilMoistureThreshold" :min="0.01" :max="0.99" :step="0.01" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="灌溉效率" prop="irrigationEfficiency">
                  <el-input-number v-model="form.irrigationEfficiency" :min="0.01" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="单次灌溉水层(cm)" prop="singleIrrigationAmount">
                  <el-input-number v-model="form.singleIrrigationAmount" :min="0" :max="20" :step="0.5" :precision="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="水稻品种">
                  <el-input v-model="form.varietyName" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">站点水文参数</el-divider>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="IFUNRN">
                  <el-input-number v-model="form.site.ifunrn" :min="0" :max="1" :step="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="NOTINF">
                  <el-input-number v-model="form.site.notinf" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="SSI(cm)">
                  <el-input-number v-model="form.site.ssi" :min="0" :step="0.5" :precision="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="SSMAX(cm)">
                  <el-input-number v-model="form.site.ssmax" :min="0" :step="0.5" :precision="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="WAV(cm)">
                  <el-input-number v-model="form.site.wav" :min="0" :step="1" :precision="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="SMLIM">
                  <el-input-number v-model="form.site.smlim" :min="0.01" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" @click="submitSimulation">
                <el-icon><TrendCharts /></el-icon>
                开始模拟
              </el-button>
              <el-button @click="resetForm">
                <el-icon><Refresh /></el-icon>
                重置
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="16">
        <div v-if="!result" class="placeholder">
          <div class="placeholder-title">尚未提交模拟</div>
          <div class="placeholder-desc">提交后将展示水稻 LAI、干物质、土壤含水量和灌溉量逐日变化。</div>
        </div>

        <template v-else>
          <div class="kpi-row">
            <div class="kpi-box">
              <div class="kpi-label">模拟天数</div>
              <div class="kpi-value">{{ summary.simulationDays }}<span>天</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">最终产量指标</div>
              <div class="kpi-value">{{ fmtNumber(summary.finalYield, 1) }}<span>kg/ha</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">最大 LAI</div>
              <div class="kpi-value">{{ fmtNumber(summary.maxLai, 2) }}</div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">累计灌溉</div>
              <div class="kpi-value">{{ fmtNumber(summary.totalIrrigation, 2) }}<span>cm</span></div>
            </div>
            <div class="kpi-box">
              <div class="kpi-label">灌溉次数</div>
              <div class="kpi-value">{{ summary.irrigationCount }}<span>次</span></div>
            </div>
          </div>

          <section class="metric-section">
            <div class="metric-section__header">
              <div>
                <h2>逐日生长曲线</h2>
                <p>全生育期指标独立视图</p>
              </div>
              <el-tag size="small" type="success">{{ summary.weatherSource }}</el-tag>
            </div>
            <div class="metric-grid">
              <MetricChart
                v-for="metric in chartMetrics"
                :key="metric.key"
                :metric="metric"
                :rows="dailyResults"
              />
            </div>
          </section>

          <el-card shadow="hover" class="result-card mt16">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">逐日指标表</span>
                <el-tag size="small" type="info">{{ dailyResults.length }} 条</el-tag>
              </div>
            </template>
            <el-table :data="dailyResults" border stripe size="small" max-height="520">
              <el-table-column prop="day" label="日期" width="112" fixed />
              <el-table-column prop="dvs" label="DVS" width="86" align="right" :formatter="tableNumber" />
              <el-table-column prop="lai" label="LAI" width="86" align="right" :formatter="tableNumber" />
              <el-table-column prop="tagp" label="TAGP" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="twso" label="TWSO" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="twlv" label="TWLV" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="twst" label="TWST" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="twrt" label="TWRT" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="tra" label="TRA" width="96" align="right" :formatter="tableNumber" />
              <el-table-column prop="rd" label="RD" width="96" align="right" :formatter="tableNumber" />
              <el-table-column prop="sm" label="SM" width="96" align="right" :formatter="tableNumber" />
              <el-table-column prop="wwlow" label="WWLOW" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="rftra" label="RFTRA" width="108" align="right" :formatter="tableNumber" />
              <el-table-column prop="rirr" label="RIRR" width="96" align="right" :formatter="tableNumber" />
              <el-table-column prop="totirr" label="TOTIRR" width="108" align="right" :formatter="tableNumber" />
            </el-table>
          </el-card>
        </template>

        <el-alert v-if="resultError" class="mt16" type="danger" :title="resultError" show-icon />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion, Refresh, TrendCharts } from '@element-plus/icons-vue'

import { simulateRiceGrowth } from '@/api/model/cropGrowth'
import MetricChart from './MetricChart.vue'

defineOptions({ name: 'CropGrowth' })

const defaultForm = () => ({
  longitude: 126.63,
  latitude: 45.75,
  simulationStartDate: '2025-05-15',
  plantStartDate: '2025-05-20',
  irrigationEndDate: '2025-08-20',
  plantEndDate: '2025-09-10',
  soilMoistureThreshold: 0.32,
  irrigationEfficiency: 0.75,
  singleIrrigationAmount: 3.0,
  varietyName: 'Rice_IR72_WS',
  site: {
    ifunrn: 0,
    notinf: 0,
    ssi: 0,
    ssmax: 0,
    wav: 20,
    smlim: 0.4
  }
})

const formRef = ref(null)
const form = reactive(defaultForm())
const submitting = ref(false)
const result = ref(null)
const resultError = ref('')

const chartMetrics = [
  { key: 'dvs', name: 'DVS', label: '发育阶段', unit: '指数', color: '#2563eb', area: true },
  { key: 'lai', name: 'LAI', label: '叶面积指数', unit: 'm²/m²', color: '#16a34a', area: true },
  { key: 'tagp', name: 'TAGP', label: '地上部总干物质', unit: 'kg/ha', color: '#d97706', area: true, scale: false },
  { key: 'twso', name: 'TWSO', label: '贮藏器官干物质', unit: 'kg/ha', color: '#dc2626', area: true, scale: false },
  { key: 'twlv', name: 'TWLV', label: '叶干物质', unit: 'kg/ha', color: '#059669', area: true, scale: false },
  { key: 'twst', name: 'TWST', label: '茎干物质', unit: 'kg/ha', color: '#7c3aed', area: true, scale: false },
  { key: 'twrt', name: 'TWRT', label: '根干物质', unit: 'kg/ha', color: '#92400e', area: true, scale: false },
  { key: 'tra', name: 'TRA', label: '实际蒸腾', unit: 'cm/day', color: '#0891b2', area: true },
  { key: 'rd', name: 'RD', label: '根系深度', unit: 'cm', color: '#4f46e5', area: true, scale: false },
  { key: 'sm', name: 'SM', label: '土壤含水量', unit: 'cm³/cm³', color: '#0f766e', area: true },
  { key: 'wwlow', name: 'WWLOW', label: '根区及下层水量', unit: 'cm', color: '#0284c7', area: true },
  { key: 'rftra', name: 'RFTRA', label: '蒸腾胁迫因子', unit: '系数', color: '#be123c', area: true },
  { key: 'rirr', name: 'RIRR', label: '当日实际灌溉量', unit: 'cm', color: '#ea580c', type: 'bar', scale: false },
  { key: 'totirr', name: 'TOTIRR', label: '累计实际灌溉量', unit: 'cm', color: '#9333ea', area: true, scale: false }
]

const rules = {
  longitude: [{ required: true, message: '请输入经度', trigger: 'blur' }],
  latitude: [{ required: true, message: '请输入纬度', trigger: 'blur' }],
  simulationStartDate: [{ required: true, message: '请选择模拟开始日期', trigger: 'change' }],
  plantStartDate: [{ required: true, message: '请选择作物开始日期', trigger: 'change' }],
  irrigationEndDate: [{ required: true, message: '请选择灌溉结束日期', trigger: 'change' }],
  plantEndDate: [{ required: true, message: '请选择作物结束日期', trigger: 'change' }],
  soilMoistureThreshold: [{ required: true, message: '请输入土壤水分阈值', trigger: 'blur' }],
  irrigationEfficiency: [{ required: true, message: '请输入灌溉效率', trigger: 'blur' }],
  singleIrrigationAmount: [{ required: true, message: '请输入单次灌溉水层', trigger: 'blur' }]
}

const summary = computed(() => result.value?.summary || {})
const dailyResults = computed(() => result.value?.dailyResults || [])

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return Number(value).toFixed(digits)
}

function tableNumber(_row, _column, value) {
  return fmtNumber(value, 3)
}

function validateDateOrder() {
  const sim = new Date(form.simulationStartDate)
  const plant = new Date(form.plantStartDate)
  const irrigationEnd = new Date(form.irrigationEndDate)
  const plantEnd = new Date(form.plantEndDate)
  if (sim > plant) return '模拟开始日期不能晚于作物开始日期'
  if (plant >= plantEnd) return '作物开始日期必须早于作物结束日期'
  if (irrigationEnd < plant || irrigationEnd > plantEnd) return '灌溉结束日期必须位于作物生育期内'
  return ''
}

async function submitSimulation() {
  await formRef.value?.validate()
  const dateError = validateDateOrder()
  if (dateError) {
    ElMessage.warning(dateError)
    return
  }

  submitting.value = true
  resultError.value = ''
  try {
    result.value = await simulateRiceGrowth({ ...form, site: { ...form.site } })
    await nextTick()
    ElMessage.success('水稻作物生长模拟完成')
  } catch (error) {
    resultError.value = error?.message || '水稻作物生长模拟失败'
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, defaultForm())
  result.value = null
  resultError.value = ''
  formRef.value?.clearValidate()
}
</script>

<style scoped lang="scss">
.crop-growth-page {
  .crop-growth-hero {
    background:
      linear-gradient(120deg, rgba(37, 99, 235, 0.92), rgba(15, 118, 110, 0.86)),
      url('https://images.unsplash.com/photo-1536304993881-ff6e9eefa2a6?auto=format&fit=crop&w=1600&q=80') center/cover;
  }
}

.page-layout {
  margin-top: 18px;
}

.config-card,
.result-card {
  border-radius: 8px;
}

.card-header,
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title,
.chart-title {
  font-weight: 700;
  color: #172033;
}

.card-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.action-row {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.placeholder {
  min-height: 360px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #64748b;
}

.placeholder-title {
  font-size: 20px;
  font-weight: 700;
  color: #334155;
}

.placeholder-desc {
  margin-top: 8px;
  max-width: 520px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-box {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
  padding: 14px 16px;
}

.kpi-label {
  color: #64748b;
  font-size: 12px;
}

.kpi-value {
  margin-top: 8px;
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
  color: #0f172a;

  span {
    margin-left: 4px;
    font-size: 12px;
    font-weight: 500;
    color: #64748b;
  }
}

.metric-section {
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f6f8fb;
}

.metric-section__header {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    color: #172033;
    font-size: 18px;
  }

  p {
    margin: 5px 0 0;
    color: #64748b;
    font-size: 12px;
  }
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.mt16 {
  margin-top: 16px;
}

@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(130px, 1fr));
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }

  .action-row {
    flex-direction: column;
  }
}
</style>
