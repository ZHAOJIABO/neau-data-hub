<template>
  <div class="app-container agri-page canal-optimize-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">NSGA-II OPTIMIZATION</span>
        <h1 class="agri-page__title">渠系优化配水</h1>
        <p class="agri-page__desc">
          基于 NSGA-II 多目标进化算法的全渠系三级顺序配水优化：先进行干-支连续配水优化，
          再对每个支渠下的斗渠进行组间轮灌组内续灌优化。前端从渠系管理接口获取渠段数据后
          提交后端计算，结果以结构化 JSON 返回，ECharts 动态渲染所有图表。
        </p>
        <div class="agri-page__siblings">
          <router-link to="/model/irrigation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>灌溉决策</span>
          </router-link>
          <router-link to="/model/canal/hydro" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系水动力学</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span>NSGA-II</span>
        <span>全渠系三级</span>
        <span>ECharts 动态</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <!-- 左侧：参数配置 -->
      <el-col :xs="24" :lg="8" class="config-col">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠系优化配水（NSGA-II）</div>
                <div class="card-desc">配置超参与土壤参数，提交后查看 Pareto + 配水方案。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'">
                {{ resultError ? '接口异常' : result ? '方案已生成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <div class="config-body">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="算法超参默认（POP=80, GEN=60）保证秒级响应；如需更高精度可调大 pop/n_gen。"
            class="mb16"
          />

          <el-form ref="formRef" :model="form" label-position="top" size="small" class="opt-form">
            <el-form-item label="接口 API Key" required>
              <el-input
                v-model="form.apiKey"
                type="password"
                show-password
                clearable
                placeholder="X-Irrigation-Api-Key"
              />
            </el-form-item>

            <el-form-item label="干渠编号">
              <el-input v-model="form.mainCanalId" placeholder="默认 1" />
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="t_max (h)">
                  <el-input-number v-model="form.tMax" :min="1" :max="2000" :step="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最大组数">
                  <el-input-number v-model="form.maxGroups" :min="2" :max="6" :step="1" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="q/qd 下限">
                  <el-input-number v-model="form.flowRatioMin" :min="0.1" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="q/qd 上限">
                  <el-input-number v-model="form.flowRatioMax" :min="0.1" :max="1.5" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="最小组数">
              <el-input-number v-model="form.minGroups" :min="2" :max="6" :step="1" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">NSGA-II 超参</el-divider>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="种群 pop">
                  <el-input-number v-model="form.popSize" :min="10" :max="600" :step="10" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="迭代 n_gen">
                  <el-input-number v-model="form.nGen" :min="10" :max="2000" :step="50" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="随机种子">
              <el-input-number v-model="form.seed" :min="0" :max="999" :step="1" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">土壤参数</el-divider>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="渗透指数 m">
                  <el-input-number v-model="form.permeabilityIndexM" :min="0" :step="0.05" :precision="3" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="渗透系数 A">
                  <el-input-number v-model="form.permeabilityCoefficientA" :min="0" :step="0.1" :precision="3" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">目标权重</el-divider>

            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="w_时间">
                  <el-input-number v-model="form.prefWeightTime" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="w_损失">
                  <el-input-number v-model="form.prefWeightLoss" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="w_波动">
                  <el-input-number v-model="form.prefWeightFlowVar" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="混合系数 α">
              <el-input-number v-model="form.alpha" :min="0" :max="1" :step="0.05" :precision="2" style="width: 100%" />
            </el-form-item>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" @click="submitOptimize" class="action-primary">
                开始优化
              </el-button>
              <el-button :disabled="!result" @click="resetResult" class="action-secondary">
                清空结果
              </el-button>
            </div>
          </el-form>

          <el-divider content-position="left">接口说明</el-divider>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="优化接口">/api/v1/irrigation/canal/optimize/full</el-descriptions-item>
            <el-descriptions-item label="请求方式">POST / application/json</el-descriptions-item>
            <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
            <el-descriptions-item label="返回">结构化 JSON</el-descriptions-item>
          </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：所有图表独立展示 -->
      <el-col :xs="24" :lg="16" class="result-col">
        <!-- 未提交时的占位 -->
        <div v-if="!result" class="placeholder">
          <div class="placeholder-title">尚未提交优化</div>
          <div class="placeholder-desc">
            提交后将在右侧依次展示：KPI 概览卡、熵权 & 目标值、Pareto 3D 前沿、全渠系配水甘特图、干渠流量/水位时序、各支渠斗渠配水甘特图、分组轮灌甘特图、损失构成、Pareto 2D 投影、支渠流量对比。
          </div>
        </div>

        <template v-else>
          <!-- ============ 区块 1：KPI 概览卡 ============ -->
          <div class="kpi-row">
            <div class="kpi-card kpi-card--primary">
              <div class="kpi-label">F1 总输水时间</div>
              <div class="kpi-value">
                {{ fmtNumber(result.topsis_summary.total_time_h, 2) }}<span class="kpi-unit">h</span>
              </div>
              <div class="kpi-foot">TOPSIS 优选方案</div>
            </div>
            <div class="kpi-card kpi-card--danger">
              <div class="kpi-label">F2 全渠系渗漏损失</div>
              <div class="kpi-value">
                {{ fmtNumber(result.topsis_summary.total_loss_m3, 0) }}<span class="kpi-unit">m³</span>
              </div>
              <div class="kpi-foot">
                干 {{ fmtNumber(result.topsis_summary.main_loss_m3, 0) }} +
                支 {{ fmtNumber(result.topsis_summary.branch_loss_m3, 0) }} +
                斗 {{ fmtNumber(result.topsis_summary.lateral_loss_m3, 0) }}
              </div>
            </div>
            <div class="kpi-card kpi-card--warning">
              <div class="kpi-label">F3 干渠流量波动</div>
              <div class="kpi-value">
                {{ fmtNumber(result.topsis_summary.flow_var, 3) }}
              </div>
              <div class="kpi-foot">Var(Q) 越小越平稳</div>
            </div>
            <div class="kpi-card kpi-card--success">
              <div class="kpi-label">TOPSIS 评分</div>
              <div class="kpi-value">
                {{ fmtNumber(result.summary.topsis_score, 4) }}
              </div>
              <div class="kpi-foot">越接近 1 越优</div>
            </div>
            <div class="kpi-card kpi-card--info">
              <div class="kpi-label">干渠峰值流量 Q_max</div>
              <div class="kpi-value">
                {{ fmtNumber(result.summary.q_max_m3s, 3) }}<span class="kpi-unit">m³/s</span>
              </div>
              <div class="kpi-foot">
                实际 {{ fmtNumber(result.main_canal.Q_total_m3s, 3) }} m³/s
              </div>
            </div>
            <div class="kpi-card kpi-card--purple">
              <div class="kpi-label">渠系规模</div>
              <div class="kpi-value">
                {{ result.summary.n_branches }}<span class="kpi-unit">支</span>
                / {{ nLaterals }}<span class="kpi-unit">斗</span>
              </div>
              <div class="kpi-foot">
                干渠 {{ result.summary.main_canal_id }} · 模式 {{ result.summary.mode }}
              </div>
            </div>
          </div>

          <!-- ============ 区块 2：熵权 / 目标值 / 损失构成 / Pareto 2D ============ -->
          <el-row :gutter="20" class="chart-row">
            <el-col :xs="24" :sm="12" :lg="12" :xl="6">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">熵权分布</span>
                    <span class="chart-sub">三目标权重</span>
                  </div>
                </template>
                <div ref="entropyRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="12" :xl="6">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">目标值归一化</span>
                    <span class="chart-sub">F1/F2/F3 相对</span>
                  </div>
                </template>
                <div ref="objectiveRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="12" :xl="6">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">损失构成</span>
                    <span class="chart-sub">干 / 支 / 斗</span>
                  </div>
                </template>
                <div ref="lossPieRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="12" :xl="6">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">Pareto 2D 投影</span>
                    <span class="chart-sub">F1-F2 / F1-F3</span>
                  </div>
                </template>
                <div ref="pareto2dRef" class="chart" />
              </el-card>
            </el-col>
          </el-row>

          <!-- ============ 区块 3：Pareto 3D 前沿 ============ -->
          <el-card shadow="hover" class="chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">Pareto 前沿（3D 散点）</span>
                  <span class="chart-sub">F1 输水时间 / F2 渗漏损失 / F3 流量波动 · 颜色=TOPSIS 评分</span>
                </div>
                <el-tag size="small" type="success">
                  已选 {{ paretoSelectedCount }} / {{ result.pareto?.length || 0 }}
                </el-tag>
              </div>
            </template>
            <div ref="paretoRef" class="chart chart-tall" />
          </el-card>

          <!-- ============ 区块 4：全渠系配水甘特图 ============ -->
          <el-card shadow="hover" class="chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">全渠系配水甘特图</span>
                  <span class="chart-sub">干-支连续配水 + 支-斗轮灌（组间轮灌、组内续灌）</span>
                </div>
                <div class="chart-tags">
                  <el-tag size="small" type="primary">干渠 {{ fmtNumber(result.main_canal.duration_h || result.main_canal.t_max_h, 2) }} h</el-tag>
                  <el-tag size="small" type="warning">峰值 {{ fmtNumber(result.main_canal.Q_total_m3s, 3) }} m³/s</el-tag>
                </div>
              </div>
            </template>
            <div ref="fullGanttRef" class="chart chart-tall" />
          </el-card>

          <!-- ============ 区块 5：干渠流量/水位时序 ============ -->
          <el-card shadow="hover" class="chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">干渠流量 / 水位 时序</span>
                  <span class="chart-sub">主调度曲线 · 阶梯式连续配水</span>
                </div>
                <div class="chart-tags">
                  <el-tag size="small">点 {{ result.time_series?.length || 0 }}</el-tag>
                </div>
              </div>
            </template>
            <div ref="timeSeriesRef" class="chart chart-tall" />
          </el-card>

          <!-- ============ 区块 6：损失堆叠 + 支渠损失对比 ============ -->
          <el-row :gutter="20" class="chart-row mt16">
            <el-col :xs="24" :md="12">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="chart-header">
                    <div>
                      <span class="chart-title">各级损失堆叠</span>
                      <span class="chart-sub">干 / 支 / 斗 渗漏量分布</span>
                    </div>
                  </div>
                </template>
                <div ref="lossBarRef" class="chart chart-tall" />
              </el-card>
            </el-col>
            <el-col :xs="24" :md="12">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="chart-header">
                    <div>
                      <span class="chart-title">支渠流量 / 损失对比</span>
                      <span class="chart-sub">设计 qd vs 实际 q_actual</span>
                    </div>
                  </div>
                </template>
                <div ref="branchBarRef" class="chart chart-tall" />
              </el-card>
            </el-col>
          </el-row>

          <!-- ============ 区块 7：分组轮灌甘特图 ============ -->
          <el-card v-if="result.groups?.length" shadow="hover" class="chart-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">支渠分组轮灌甘特图</span>
                  <span class="chart-sub">同组内续灌、组与组间轮灌 · 按 parent 支渠分组</span>
                </div>
                <el-tag size="small" type="info">共 {{ result.groups.length }} 个组</el-tag>
              </div>
            </template>
            <div ref="groupGanttRef" class="chart chart-tall" />
          </el-card>

          <!-- ============ 区块 8：各支渠下的斗渠配水甘特图（每条支渠一张） ============ -->
          <div v-for="(b, idx) in result.branches" :key="b.name" class="mt16">
            <el-card shadow="hover" class="chart-card">
              <template #header>
                <div class="chart-header">
                  <div>
                    <span class="chart-title">
                      支渠 {{ b.name }} 斗渠配水甘特图
                    </span>
                    <span class="chart-sub">
                      设计 qd={{ fmtNumber(b.qd, 2) }} m³/s · 实际 q={{ fmtNumber(b.q_actual, 3) }} m³/s ·
                      占比 {{ fmtNumber(b.ratio, 4) }} · {{ b.n_laterals }} 斗
                    </span>
                  </div>
                  <div class="chart-tags">
                    <el-tag size="small" type="primary">
                      开始 {{ fmtNumber(b.t_start_h, 2) }}h
                    </el-tag>
                    <el-tag size="small" type="warning">
                      持续 {{ fmtNumber(b.duration_h, 2) }}h
                    </el-tag>
                    <el-tag size="small" type="danger">
                      损失 {{ fmtNumber(b.loss_m3, 0) }} m³
                    </el-tag>
                  </div>
                </div>
              </template>
              <div :ref="el => setBranchGanttRef(el, idx)" class="chart chart-tall" />
              <!-- 斗渠详细数据表 -->
              <el-table
                :data="getBranchLaterals(b.name)"
                size="small"
                stripe
                border
                class="mt12 lateral-table"
              >
                <el-table-column prop="name" label="斗渠" width="110" />
                <el-table-column label="所属组" width="80" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.group === 1 ? 'primary' : 'success'">G{{ row.group }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="设计流量" width="100" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.Q_design, 2) }} m³/s
                  </template>
                </el-table-column>
                <el-table-column label="实际流量" width="100" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.Q_actual, 3) }} m³/s
                  </template>
                </el-table-column>
                <el-table-column label="占比" width="80" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.ratio, 4) }}
                  </template>
                </el-table-column>
                <el-table-column label="开始" width="80" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.start_h, 2) }} h
                  </template>
                </el-table-column>
                <el-table-column label="持续" width="80" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.duration_h, 2) }} h
                  </template>
                </el-table-column>
                <el-table-column label="结束" width="80" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.end_h, 2) }} h
                  </template>
                </el-table-column>
                <el-table-column label="渗漏损失" width="100" align="right">
                  <template #default="{ row }">
                    {{ fmtNumber(row.loss_m3, 0) }} m³
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>
        </template>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { getCurrentInstance, reactive, ref, watch, nextTick, onUnmounted, computed } from 'vue'
import { runFullOptimize } from '@/api/agriculture/canalOptimize'
import { listCanal } from '@/api/agriculture/canal'
import { Promotion } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

defineOptions({ name: 'CanalOptimize' })

const { proxy } = getCurrentInstance()
const DEFAULT_API_KEY = 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const submitting = ref(false)
const result = ref(null)
const resultError = ref('')

const entropyRef = ref(null)
const objectiveRef = ref(null)
const lossPieRef = ref(null)
const pareto2dRef = ref(null)
const paretoRef = ref(null)
const fullGanttRef = ref(null)
const timeSeriesRef = ref(null)
const lossBarRef = ref(null)
const branchBarRef = ref(null)
const groupGanttRef = ref(null)
const branchGanttRefs = []

let entropyChart = null
let objectiveChart = null
let lossPieChart = null
let pareto2dChart = null
let paretoChart = null
let fullGanttChart = null
let timeSeriesChart = null
let lossBarChart = null
let branchBarChart = null
let groupGanttChart = null
const branchGanttCharts = []
let renderToken = 0

const form = reactive({
  apiKey: DEFAULT_API_KEY,
  mainCanalId: '1',
  tMax: 360,
  flowRatioMin: 0.8,
  flowRatioMax: 1.0,
  minGroups: 2,
  maxGroups: 6,
  popSize: 80,
  nGen: 60,
  seed: 1,
  permeabilityIndexM: 0.4,
  permeabilityCoefficientA: 1.9,
  prefWeightTime: 0.4,
  prefWeightLoss: 0.3,
  prefWeightFlowVar: 0.3,
  alpha: 0.5
})

const COLOR_PALETTE = [
  '#5b8def', '#22c55e', '#f97316', '#a855f7', '#ec4899',
  '#14b8a6', '#facc15', '#06b6d4', '#84cc16', '#ef4444',
  '#6366f1', '#0ea5e9', '#f59e0b', '#10b981', '#8b5cf6'
]

const nLaterals = computed(() => (result.value?.laterals || []).length)
const paretoSelectedCount = computed(() => (result.value?.pareto || []).filter(p => p.selected).length)

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--'
  }
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '--'
  }
  return num.toFixed(digits)
}

function getColor(i) {
  return COLOR_PALETTE[i % COLOR_PALETTE.length]
}

function getBranchLaterals(branchName) {
  if (!result.value) return []
  return (result.value.laterals || [])
    .filter(l => l.parent === branchName || l.parent_id === branchName)
    .slice()
    .sort((a, b) => {
      if (a.group !== b.group) return a.group - b.group
      return a.name.localeCompare(b.name)
    })
}

function setBranchGanttRef(el, idx) {
  if (el) branchGanttRefs[idx] = el
}

function resetResult() {
  renderToken += 1
  result.value = null
  resultError.value = ''
  destroyCharts()
}

function destroyCharts() {
  ;[
    entropyChart, objectiveChart, lossPieChart, pareto2dChart,
    paretoChart, fullGanttChart, timeSeriesChart, lossBarChart,
    branchBarChart, groupGanttChart
  ].forEach(c => { if (c) c.dispose() })
  entropyChart = objectiveChart = lossPieChart = pareto2dChart = null
  paretoChart = fullGanttChart = timeSeriesChart = lossBarChart = null
  branchBarChart = groupGanttChart = null
  branchGanttCharts.forEach(c => { if (c) c.dispose() })
  branchGanttCharts.length = 0
  branchGanttRefs.length = 0
}

async function submitOptimize() {
  if (!form.apiKey.trim()) {
    proxy.$modal.msgError('请输入接口 API Key')
    return
  }
  if (!form.mainCanalId.trim()) {
    proxy.$modal.msgError('请输入干渠编号')
    return
  }
  const requestToken = ++renderToken
  result.value = null
  resultError.value = ''
  destroyCharts()
  submitting.value = true

  let canals = []
  try {
    const canalRes = await listCanal({ canalName: '', pageNum: 1, pageSize: 1000 })
    canals = canalRes?.rows || canalRes || []
    if (!canals.length) {
      canals = canalRes?.data?.rows || []
    }
  } catch (e) {
    if (requestToken !== renderToken) return
    proxy.$modal.msgError('获取渠系数据失败：' + (e?.message || e))
    submitting.value = false
    return
  }

  const payload = {
    main_canal_id: form.mainCanalId.trim(),
    canals: canals.map(c => ({
      canal_id: c.canalId || c.canal_id,
      canal_name: c.canalName || c.canal_name,
      level: c.level,
      length: parseFloat(c.lengthM ?? c.length ?? 0),
      design_flow: parseFloat(c.designQM3s ?? c.designQ3s ?? c.designFlow ?? c.design_flow ?? 0),
      design_depth: parseFloat(c.designDepthM ?? c.designDepth ?? c.design_depth ?? 0),
      top_width: parseFloat(c.designTopWidthM ?? c.topWidth ?? c.top_width ?? 0),
      bottom_width: parseFloat(c.designBottomWidthM ?? c.bottomWidth ?? c.bottom_width ?? 0),
      slope: parseFloat(c.designSlope ?? c.slope ?? 0),
      side_slope: parseFloat(c.sideSlopeM ?? c.sideSlope ?? c.side_slope ?? 0),
      roughness: parseFloat(c.manningN ?? c.roughness ?? c.roughness_n ?? 0),
      gate_height: parseFloat(c.gateHeightM ?? c.gateHeight ?? c.gate_height ?? 0),
      gate_width: parseFloat(c.gateWidthM ?? c.gateWidth ?? c.gate_width ?? 0),
      min_gate_opening: parseFloat(c.minGateOpeningM ?? c.minGateOpening ?? c.min_gate_opening ?? 0),
      max_gate_opening: parseFloat(c.maxGateOpeningM ?? c.maxGateOpening ?? c.max_gate_opening ?? 0),
      water_demand: parseFloat(c.waterDemandM3 ?? c.waterDemand ?? c.water_demand ?? 0),
      parent_id: c.parentId || c.parent_id
    })),
    t_max: form.tMax,
    flow_ratio_min: form.flowRatioMin,
    flow_ratio_max: form.flowRatioMax,
    min_groups: form.minGroups,
    max_groups: form.maxGroups,
    pop_size: form.popSize,
    n_gen: form.nGen,
    seed: form.seed,
    permeability_index_m: form.permeabilityIndexM,
    permeability_coefficient_a: form.permeabilityCoefficientA,
    pref_weight_time: form.prefWeightTime,
    pref_weight_loss: form.prefWeightLoss,
    pref_weight_flow_var: form.prefWeightFlowVar,
    alpha: form.alpha
  }

  try {
    const data = await runFullOptimize(payload, form.apiKey.trim())
    if (requestToken !== renderToken) return
    result.value = data
    proxy.$modal.msgSuccess('优化完成')
    await nextTick()
    renderAllCharts()
  } catch (err) {
    if (requestToken !== renderToken) return
    resultError.value = err?.message || '优化失败'
    proxy.$modal?.msgError?.(resultError.value)
  } finally {
    submitting.value = false
  }
}

function initChart(el, currentChart) {
  if (!el || !el.isConnected) return null
  if (currentChart) currentChart.dispose()
  return echarts.init(el)
}

function renderAllCharts() {
  if (!result.value) return
  renderEntropy()
  renderObjective()
  renderLossPie()
  renderPareto2D()
  renderPareto()
  renderFullGantt()
  renderTimeSeries()
  renderLossBar()
  renderBranchBar()
  if (result.value.groups?.length) renderGroupGantt()
  renderBranchGantts()
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'))
  }, 50)
}

function renderEntropy() {
  entropyChart = initChart(entropyRef.value, entropyChart)
  if (!entropyChart) return
  const w = result.value.summary.entropy_weights || {}
  const data = [
    { name: 'F1 输水时间', value: Number(w.F1_time || 0) },
    { name: 'F2 渗漏损失', value: Number(w.F2_loss || 0) },
    { name: 'F3 流量波动', value: Number(w.F3_flow_var || 0) }
  ]
  entropyChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>权重 {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data,
      color: ['#5b8def', '#ef4444', '#f59e0b']
    }]
  })
}

function renderObjective() {
  objectiveChart = initChart(objectiveRef.value, objectiveChart)
  if (!objectiveChart) return
  const o = result.value.summary.objective_values || {}
  const f1 = Number(o.F1_total_time_h || 0)
  const f2 = Number(o.F2_total_loss_m3 || 0)
  const f3 = Number(o.F3_flow_var || 0)
  // 归一化：每个值除以三个值中的最大值，便于同图比较
  const f1n = f1 / Math.max(f1, 1)
  const f2n = f2 / Math.max(f2, 1)
  const f3n = f3 / Math.max(f3, 1)
  objectiveChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = params[0]
        return `<b>${p.name}</b><br/>相对值 ${p.value.toFixed(4)}<br/>原始 ${[f1, f2, f3][p.dataIndex].toFixed(2)}`
      }
    },
    grid: { top: 30, left: 50, right: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ['F1 时间', 'F2 损失', 'F3 波动'],
      axisLabel: { fontSize: 12 }
    },
    yAxis: { type: 'value', name: '相对值', axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: [
        { value: f1n, itemStyle: { color: '#5b8def' } },
        { value: f2n, itemStyle: { color: '#ef4444' } },
        { value: f3n, itemStyle: { color: '#f59e0b' } }
      ],
      barWidth: '50%',
      label: { show: true, position: 'top', formatter: ({ value }) => value.toFixed(2) }
    }]
  })
}

function renderLossPie() {
  lossPieChart = initChart(lossPieRef.value, lossPieChart)
  if (!lossPieChart) return
  const s = result.value.topsis_summary
  const data = [
    { name: '干渠损失', value: Number(s.main_loss_m3 || 0) },
    { name: '支渠损失', value: Number(s.branch_loss_m3 || 0) },
    { name: '斗渠损失', value: Number(s.lateral_loss_m3 || 0) }
  ]
  lossPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} m³ ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie',
      roseType: 'radius',
      radius: ['25%', '70%'],
      center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data,
      color: ['#5b8def', '#22c55e', '#f97316']
    }]
  })
}

function renderPareto2D() {
  pareto2dChart = initChart(pareto2dRef.value, pareto2dChart)
  if (!pareto2dChart) return
  const data = result.value.pareto || []
  pareto2dChart.setOption({
    tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}<br/>F1=${p.value[0].toFixed(2)}<br/>F2=${p.value[1].toFixed(2)}<br/>score=${p.value[2].toFixed(4)}${p.value[3] ? '<br/>★ 已选' : ''}` },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    grid: { top: 20, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'value', name: 'F1 时间 (h)', nameLocation: 'middle', nameGap: 25, nameTextStyle: { fontSize: 11 } },
    yAxis: { type: 'value', name: 'F2 损失 (m³)', nameTextStyle: { fontSize: 11 } },
    series: [
      {
        name: 'F1-F2',
        type: 'scatter',
        symbolSize: 9,
        data: data.map(d => ({
          value: [d.F1, d.F2, d.score, d.selected],
          itemStyle: d.selected
            ? { color: '#ec8e5a', borderColor: '#fff', borderWidth: 2 }
            : { color: '#5b8def', opacity: 0.7 }
        }))
      }
    ]
  })
}

function renderPareto() {
  paretoChart = initChart(paretoRef.value, paretoChart)
  if (!paretoChart) return
  const data = result.value.pareto
  const option = {
    title: { text: 'Pareto 前沿（3D 散点）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const d = p.data
        return `F1=${d.value[0].toFixed(2)} h<br/>F2=${d.value[1].toFixed(2)} m³<br/>F3=${d.value[2].toFixed(3)}<br/>score=${d.value[3].toFixed(4)}${d.value[4] ? '<br/>★ TOPSIS 优选' : ''}`
      }
    },
    visualMap: {
      show: true,
      dimension: 3,
      min: Math.min(...data.map(d => d.score)),
      max: Math.max(...data.map(d => d.score)),
      orient: 'vertical',
      right: 10,
      top: 'center',
      calculable: true,
      text: ['score', ''],
      inRange: { color: ['#bfdfd2', '#53999d', '#ecb66b', '#ec8e5a'] }
    },
    xAxis3D: { name: 'F1: 输水时间 (h)', type: 'value' },
    yAxis3D: { name: 'F2: 渗漏损失 (m³)', type: 'value' },
    zAxis3D: { name: 'F3: 流量波动', type: 'value' },
    grid3D: {
      boxWidth: 110,
      boxDepth: 110,
      viewControl: { projection: 'perspective', alpha: 20, beta: 30 },
      light: { main: { intensity: 1.2 }, ambient: { intensity: 0.3 } }
    },
    series: [{
      type: 'scatter3D',
      symbolSize: 12,
      data: data.map(d => ({
        value: [d.F1, d.F2, d.F3, d.score, d.selected],
        itemStyle: d.selected
          ? { color: '#ec8e5a', borderColor: '#fff', borderWidth: 2 }
          : undefined
      }))
    }]
  }
  if (data.some(d => d.selected)) {
    option.series.push({
      type: 'scatter3D',
      symbolSize: 26,
      symbol: 'star',
      data: data.filter(d => d.selected).map(d => ({ value: [d.F1, d.F2, d.F3, d.score, true] })),
      itemStyle: { color: '#ec8e5a' }
    })
  }
  paretoChart.setOption(option)
}

function buildGanttSeries(rows, getStart, getDuration, getColorIdx) {
  return rows.map((r, i) => ({
    name: r.name || r.label,
    type: 'custom',
    renderItem: (params, api) => {
      const categoryIndex = api.value(0)
      const duration = api.value(1)
      const start = api.value(2)
      const end = start + duration
      const y = api.coord([0, categoryIndex])
      const x0 = api.coord([start, categoryIndex])
      const x1 = api.coord([end, categoryIndex])
      const height = api.size([0, 1])[1] * 0.6
      return {
        type: 'rect',
        shape: {
          x: x0[0],
          y: y[1] - height / 2,
          width: Math.max(x1[0] - x0[0], 1),
          height
        },
        style: api.style({
          fill: getColor(getColorIdx ? getColorIdx(r, i) : i),
          stroke: '#fff',
          lineWidth: 1
        })
      }
    },
    encode: { x: [1, 2], y: 0 },
    data: [[i, getDuration(r), getStart(r)]]
  }))
}

function renderFullGantt() {
  fullGanttChart = initChart(fullGanttRef.value, fullGanttChart)
  if (!fullGanttChart) return
  const branches = result.value.branches || []
  const laterals = result.value.laterals || []
  const mainData = result.value.main_canal || {}

  const rows = []
  // 干渠
  rows.push({ name: '干渠 G' + (result.value.summary.main_canal_id || ''), isMain: true,
    t_start: 0, duration: mainData.t_max_h || mainData.duration_h || 0 })
  // 支渠
  branches.forEach(b => {
    rows.push({
      name: `支渠 ${b.name}`,
      t_start: Number(b.t_start_h || 0),
      duration: Number(b.duration_h || 0),
      branch: b
    })
  })
  // 斗渠
  branches.forEach(b => {
    const bLaterals = laterals
      .filter(l => (l.parent === b.name || l.parent_id === b.name))
      .sort((a, c) => {
        if (a.group !== c.group) return a.group - c.group
        return a.name.localeCompare(c.name)
      })
    bLaterals.forEach(l => {
      rows.push({
        name: `  · ${l.name} (G${l.group})`,
        t_start: Number(l.start_h || l.t_start_h || 0),
        duration: Number(l.duration_h || 0),
        group: l.group,
        lateral: l
      })
    })
  })

  const yCategories = rows.map(r => r.name)
  const series = rows.map((r, i) => ({
    name: r.name,
    type: 'custom',
    renderItem: (params, api) => {
      const ci = api.value(0)
      const duration = api.value(1)
      const start = api.value(2)
      const end = start + duration
      const y = api.coord([0, ci])
      const x0 = api.coord([start, ci])
      const x1 = api.coord([end, ci])
      const height = api.size([0, 1])[1] * 0.55
      let color = getColor(ci)
      if (r.isMain) color = '#0f172a'
      else if (r.branch) color = '#5b8def'
      else if (r.group === 1) color = '#22c55e'
      else if (r.group === 2) color = '#f59e0b'
      return {
        type: 'rect',
        shape: {
          x: x0[0],
          y: y[1] - height / 2,
          width: Math.max(x1[0] - x0[0], 1),
          height
        },
        style: { fill: color, stroke: '#fff', lineWidth: 1 }
      }
    },
    encode: { x: [1, 2], y: 0 },
    data: [[i, r.duration, r.t_start]]
  }))

  fullGanttChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const r = rows[p.dataIndex]
        const start = fmtNumber(r.t_start, 2)
        const dur = fmtNumber(r.duration, 2)
        const end = fmtNumber(r.t_start + r.duration, 2)
        if (r.isMain) return `<b>${r.name}</b><br/>开始 ${start} h · 持续 ${dur} h · 结束 ${end} h`
        if (r.branch) return `<b>${r.name}</b><br/>设计 qd=${fmtNumber(r.branch.qd, 2)} m³/s<br/>实际 q=${fmtNumber(r.branch.q_actual, 3)} m³/s<br/>占比 ${fmtNumber(r.branch.ratio, 4)}<br/>开始 ${start} h · 持续 ${dur} h`
        if (r.lateral) return `<b>${r.lateral.name} (G${r.lateral.group})</b><br/>设计 ${fmtNumber(r.lateral.Q_design, 2)} · 实际 ${fmtNumber(r.lateral.Q_actual, 3)} m³/s<br/>开始 ${start} h · 持续 ${dur} h · 损失 ${fmtNumber(r.lateral.loss_m3, 0)} m³`
        return ''
      }
    },
    grid: { top: 30, left: 140, right: 30, bottom: 40 },
    xAxis: { type: 'value', name: '时间 (h)', nameLocation: 'middle', nameGap: 25 },
    yAxis: { type: 'category', data: yCategories, name: '渠段', axisLabel: { fontSize: 11 } },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, height: 18, bottom: 5 }
    ],
    series
  })
}

function renderTimeSeries() {
  timeSeriesChart = initChart(timeSeriesRef.value, timeSeriesChart)
  if (!timeSeriesChart) return
  const ts = result.value.time_series || []
  timeSeriesChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['Q (m³/s)', 'H (m)'], textStyle: { fontSize: 12 } },
    grid: { top: 36, left: 60, right: 60, bottom: 50 },
    xAxis: {
      type: 'category',
      data: ts.map(p => p.t_h),
      name: '时间 (h)',
      nameLocation: 'middle',
      nameGap: 25,
      axisLabel: { interval: Math.max(0, Math.floor(ts.length / 12) - 1) }
    },
    yAxis: [
      { type: 'value', name: 'Q (m³/s)', position: 'left', nameTextStyle: { fontSize: 11 } },
      { type: 'value', name: 'H (m)', position: 'right', nameTextStyle: { fontSize: 11 } }
    ],
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 18, bottom: 5 }
    ],
    series: [
      {
        name: 'Q (m³/s)',
        type: 'line',
        smooth: false,
        symbol: 'none',
        step: 'end',
        lineStyle: { width: 2, color: '#5b8def' },
        areaStyle: { color: 'rgba(91,141,239,0.18)' },
        data: ts.map(p => p.Q_m3s)
      },
      {
        name: 'H (m)',
        type: 'line',
        smooth: false,
        symbol: 'none',
        yAxisIndex: 1,
        lineStyle: { width: 2, color: '#22c55e' },
        data: ts.map(p => p.H_m)
      }
    ]
  })
}

function renderLossBar() {
  lossBarChart = initChart(lossBarRef.value, lossBarChart)
  if (!lossBarChart) return
  const s = result.value.topsis_summary
  lossBarChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 12 } },
    grid: { top: 36, left: 50, right: 30, bottom: 30 },
    xAxis: { type: 'category', data: ['渗漏损失构成'] },
    yAxis: { type: 'value', name: 'm³', nameTextStyle: { fontSize: 11 } },
    series: [
      {
        name: '干渠',
        type: 'bar',
        stack: 'loss',
        itemStyle: { color: '#5b8def' },
        data: [Number(s.main_loss_m3 || 0)],
        label: { show: true, position: 'inside', formatter: ({ value }) => fmtNumber(value, 0) }
      },
      {
        name: '支渠',
        type: 'bar',
        stack: 'loss',
        itemStyle: { color: '#22c55e' },
        data: [Number(s.branch_loss_m3 || 0)],
        label: { show: true, position: 'inside', formatter: ({ value }) => fmtNumber(value, 0) }
      },
      {
        name: '斗渠',
        type: 'bar',
        stack: 'loss',
        itemStyle: { color: '#f97316' },
        data: [Number(s.lateral_loss_m3 || 0)],
        label: { show: true, position: 'inside', formatter: ({ value }) => fmtNumber(value, 0) }
      }
    ]
  })
}

function renderBranchBar() {
  branchBarChart = initChart(branchBarRef.value, branchBarChart)
  if (!branchBarChart) return
  const branches = result.value.branches || []
  const series = []
  if (branches.length) {
    series.push({
      name: '设计流量 qd',
      type: 'bar',
      itemStyle: { color: '#94a3b8' },
      data: branches.map(b => Number(b.qd || 0))
    })
    series.push({
      name: '实际流量 q',
      type: 'bar',
      itemStyle: { color: '#5b8def' },
      data: branches.map(b => Number(b.q_actual || 0))
    })
    series.push({
      name: '损失 m³',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { width: 2, color: '#ef4444' },
      itemStyle: { color: '#ef4444' },
      data: branches.map(b => Number(b.loss_m3 || 0))
    })
  }
  branchBarChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 0, textStyle: { fontSize: 12 } },
    grid: { top: 36, left: 60, right: 60, bottom: 30 },
    xAxis: {
      type: 'category',
      data: branches.map(b => `支渠 ${b.name}`),
      axisLabel: { fontSize: 11 }
    },
    yAxis: [
      { type: 'value', name: 'm³/s', nameTextStyle: { fontSize: 11 } },
      { type: 'value', name: '损失 m³', position: 'right', nameTextStyle: { fontSize: 11 } }
    ],
    series
  })
}

function renderGroupGantt() {
  groupGanttChart = initChart(groupGanttRef.value, groupGanttChart)
  if (!groupGanttChart) return
  const groups = (result.value.groups || []).slice().sort((a, b) => {
    if (a.parent !== b.parent) return String(a.parent).localeCompare(String(b.parent))
    return a.group - b.group
  })
  const rows = groups.map(g => ({
    name: `${g.parent} · G${g.group}`,
    t_start: Number(g.start_h || 0),
    duration: Number(g.duration_h || 0),
    group: g
  }))
  const yCategories = rows.map(r => r.name)
  const series = rows.map((r, i) => ({
    name: r.name,
    type: 'custom',
    renderItem: (params, api) => {
      const ci = api.value(0)
      const dur = api.value(1)
      const start = api.value(2)
      const end = start + dur
      const y = api.coord([0, ci])
      const x0 = api.coord([start, ci])
      const x1 = api.coord([end, ci])
      const height = api.size([0, 1])[1] * 0.55
      return {
        type: 'rect',
        shape: { x: x0[0], y: y[1] - height / 2, width: Math.max(x1[0] - x0[0], 1), height },
        style: { fill: r.group.group === 1 ? '#22c55e' : '#f59e0b', stroke: '#fff', lineWidth: 1 }
      }
    },
    encode: { x: [1, 2], y: 0 },
    data: [[i, r.duration, r.t_start]]
  }))
  groupGanttChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const g = rows[p.dataIndex].group
        return `<b>${g.parent} · G${g.group}</b><br/>总流量 ${fmtNumber(g.total_flow, 2)} m³/s · 占比 ${fmtNumber(g.flow_ratio, 4)}<br/>开始 ${fmtNumber(g.start_h, 2)} h · 持续 ${fmtNumber(g.duration_h, 2)} h<br/>损失 ${fmtNumber(g.loss_m3, 0)} m³`
      }
    },
    grid: { top: 30, left: 130, right: 30, bottom: 40 },
    xAxis: { type: 'value', name: '时间 (h)', nameLocation: 'middle', nameGap: 25 },
    yAxis: { type: 'category', data: yCategories, axisLabel: { fontSize: 11 } },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, height: 18, bottom: 5 }
    ],
    series
  })
}

function renderBranchGantts() {
  const branches = result.value.branches || []
  branches.forEach((b, idx) => {
    const el = branchGanttRefs[idx]
    if (!el) return
    if (branchGanttCharts[idx]) branchGanttCharts[idx].dispose()
    const chart = echarts.init(el)
    branchGanttCharts[idx] = chart
    const rows = getBranchLaterals(b.name)
    if (!rows.length) {
      chart.setOption({
        title: { text: '无斗渠数据', left: 'center', top: 'middle' }
      })
      return
    }
    const yCategories = rows.map(r => r.name)
    const series = rows.map((r, i) => ({
      name: r.name,
      type: 'custom',
      renderItem: (params, api) => {
        const ci = api.value(0)
        const dur = api.value(1)
        const start = api.value(2)
        const end = start + dur
        const y = api.coord([0, ci])
        const x0 = api.coord([start, ci])
        const x1 = api.coord([end, ci])
        const height = api.size([0, 1])[1] * 0.55
        return {
          type: 'rect',
          shape: { x: x0[0], y: y[1] - height / 2, width: Math.max(x1[0] - x0[0], 1), height },
          style: {
            fill: r.group === 1 ? '#22c55e' : '#f59e0b',
            stroke: '#fff',
            lineWidth: 1
          }
        }
      },
      encode: { x: [1, 2], y: 0 },
      data: [[i, Number(r.duration_h || 0), Number(r.start_h || r.t_start_h || 0)]]
    }))
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (p) => {
          const r = rows[p.dataIndex]
          return `<b>${r.name} (G${r.group})</b><br/>设计 ${fmtNumber(r.Q_design, 2)} m³/s · 实际 ${fmtNumber(r.Q_actual, 3)} m³/s<br/>占比 ${fmtNumber(r.ratio, 4)}<br/>开始 ${fmtNumber(r.start_h, 2)} h · 持续 ${fmtNumber(r.duration_h, 2)} h<br/>损失 ${fmtNumber(r.loss_m3, 0)} m³`
        }
      },
      grid: { top: 30, left: 100, right: 30, bottom: 40 },
      xAxis: { type: 'value', name: '时间 (h)', nameLocation: 'middle', nameGap: 25 },
      yAxis: { type: 'category', data: yCategories, axisLabel: { fontSize: 11 } },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0 },
        { type: 'slider', xAxisIndex: 0, height: 18, bottom: 5 }
      ],
      series
    })
  })
}

watch(result, async (val) => {
  if (!val) return
  await nextTick()
  renderAllCharts()
})

window.addEventListener('resize', () => {
  ;[
    entropyChart, objectiveChart, lossPieChart, pareto2dChart,
    paretoChart, fullGanttChart, timeSeriesChart, lossBarChart,
    branchBarChart, groupGanttChart
  ].forEach(c => { if (c) c.resize() })
  branchGanttCharts.forEach(c => { if (c) c.resize() })
})

onUnmounted(() => {
  destroyCharts()
})
</script>

<style scoped>
.canal-optimize-page {
  padding-bottom: 28px;
}

.agri-page__siblings {
  display: flex;
  gap: 12px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.sibling-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--surface-soft-bg);
  border: 1px solid var(--hairline-color);
  color: var(--text-primary);
  font-size: 0.867em;
  text-decoration: none;
  transition: all 0.2s ease;
}

.sibling-link:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary);
}

.page-layout {
  align-items: stretch;
}

.config-col {
  display: flex;
  min-width: 0;
}

.config-col .config-card {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  width: 100%;
}

.config-col .config-card :deep(.el-card__body) {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.config-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.result-col {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.config-card,
.chart-card {
  border-radius: 20px;
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow-soft);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 650;
  color: var(--text-primary);
}

.card-desc {
  margin-top: 6px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.chart-title {
  font-size: 1em;
  font-weight: 650;
  color: var(--text-primary);
}

.chart-sub {
  display: block;
  margin-top: 4px;
  font-size: 0.8em;
  color: var(--text-secondary);
}

.chart-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.mb16 {
  margin-bottom: 16px;
}

.mt12 {
  margin-top: 12px;
}

.mt16 {
  margin-top: 16px;
}

.opt-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.opt-form :deep(.el-form-item__label) {
  font-size: 0.8em;
  color: var(--text-regular);
  padding: 0 0 4px;
  line-height: 1.3;
  font-weight: 500;
}

.action-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.action-primary {
  flex: 1;
}

.action-secondary {
  flex: 0 0 auto;
}

.placeholder {
  padding: 56px 20px;
  text-align: center;
  background: var(--surface-soft-bg);
  border-radius: 20px;
  border: 1px dashed var(--hairline-color);
}

.placeholder-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.placeholder-desc {
  margin-top: 10px;
  font-size: 0.867em;
  line-height: 1.7;
  color: var(--text-secondary);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.chart {
  width: 100%;
  height: 320px;
}

.chart-tall {
  height: 420px;
}

.chart-row {
  margin-top: 16px;
}

.chart-row + .chart-row {
  margin-top: 16px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.kpi-card {
  position: relative;
  padding: 18px 20px;
  border-radius: 18px;
  background: var(--surface-bg);
  border: 1px solid var(--hairline-color);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.kpi-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: var(--el-color-primary);
  opacity: 0.9;
}

.kpi-card--primary::before { background: linear-gradient(90deg, #5b8def, #6366f1); }
.kpi-card--danger::before { background: linear-gradient(90deg, #ef4444, #f97316); }
.kpi-card--warning::before { background: linear-gradient(90deg, #f59e0b, #facc15); }
.kpi-card--success::before { background: linear-gradient(90deg, #22c55e, #14b8a6); }
.kpi-card--info::before { background: linear-gradient(90deg, #06b6d4, #0ea5e9); }
.kpi-card--purple::before { background: linear-gradient(90deg, #a855f7, #ec4899); }

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.kpi-label {
  font-size: 0.867em;
  color: var(--text-secondary);
  font-weight: 500;
}

.kpi-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}

.kpi-unit {
  margin-left: 4px;
  font-size: 0.933em;
  font-weight: 500;
  color: var(--text-secondary);
}

.kpi-foot {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.lateral-table {
  border-radius: 12px;
  overflow: hidden;
}

@media (max-width: 1200px) {
  .chart {
    height: 300px;
  }
  .chart-tall {
    height: 380px;
  }
}

@media (max-width: 992px) {
  .config-col {
    display: block;
  }
  .config-body {
    max-height: none;
    overflow: visible;
  }
}

@media (max-width: 768px) {
  .kpi-value {
    font-size: 22px;
  }
  .chart {
    height: 280px;
  }
  .chart-tall {
    height: 340px;
  }
}
</style>
