<template>
  <div class="dashboard-container">

    <!-- ======= Animated Hero Section ======= -->
    <section class="hero-card">
      <!-- Background 3D layers -->
      <div class="hero-bg-layer">
        <div class="hero-orb hero-orb--1"></div>
        <div class="hero-orb hero-orb--2"></div>
        <div class="hero-orb hero-orb--3"></div>
        <div class="hero-grid"></div>
      </div>

      <div class="hero-left">
        <div class="hero-badge">
          <span class="badge-dot"></span>
          <span>灌区水土资源数据与模型中台</span>
        </div>
        <h1 class="hero-title">
          灌区水土资源<br>
          智能决策平台
        </h1>
        <p class="hero-subtitle">
          专业水土资源优化模型驱动 · 多源异构数据融合中枢<br>
          精准灌溉 · 科学配水 · 智能调度
        </p>
        <p class="hero-desc">
          整合气象、水文、土壤、作物、渠系等全维数据资源，搭载灌区水土资源优化配置、
          渠系优化配水、灌溉决策预报、水氮耦合调控等八大专业模型，为灌区精准管理提供
          强大的数据底座与模型支撑能力。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="scrollToModels">进入平台</el-button>
          <el-button size="large" @click="scrollToModels">了解更多</el-button>
        </div>
      </div>

      <div class="hero-right">
        <div class="hero-3d-container">
          <!-- 3D rotating data visualization -->
          <div class="data-globe">
            <div class="globe-ring globe-ring--1"></div>
            <div class="globe-ring globe-ring--2"></div>
            <div class="globe-ring globe-ring--3"></div>
            <div class="globe-core">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
            </div>
            <!-- Orbiting data nodes -->
            <div class="orbit-node node-1">
              <span>气象</span>
            </div>
            <div class="orbit-node node-2">
              <span>水文</span>
            </div>
            <div class="orbit-node node-3">
              <span>土壤</span>
            </div>
            <div class="orbit-node node-4">
              <span>作物</span>
            </div>
            <div class="orbit-node node-5">
              <span>渠系</span>
            </div>
            <div class="orbit-node node-6">
              <span>水权</span>
            </div>
          </div>
          <!-- Floating stat cards -->
          <div class="stat-card stat-card--tl">
            <div class="stat-val">8+</div>
            <div class="stat-label">专业模型</div>
          </div>
          <div class="stat-card stat-card--tr">
            <div class="stat-val">7×24</div>
            <div class="stat-label">实时数据</div>
          </div>
          <div class="stat-card stat-card--bl">
            <div class="stat-val">100%</div>
            <div class="stat-label">API 驱动</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ======= Data Platform Stats ======= -->
    <section class="stats-section">
      <div class="stats-grid">
        <div class="stats-item" v-for="(stat, idx) in platformStats" :key="idx">
          <div class="stats-icon">
            <svg v-if="stat.icon === 'database'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
            <svg v-else-if="stat.icon === 'cpu'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>
              <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>
            </svg>
            <svg v-else-if="stat.icon === 'chart'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M18 20V10M12 20V4M6 20v-6"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
            </svg>
          </div>
          <div class="stats-text">
            <div class="stats-value">{{ stat.value }}</div>
            <div class="stats-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ======= Core Value Props ======= -->
    <section class="value-section">
      <div class="section-header">
        <h2 class="section-title">平台核心能力</h2>
        <p class="section-desc">数据中台 + 专业模型 = 智能决策底座</p>
      </div>
      <div class="value-grid">
        <div class="value-card" v-for="(card, idx) in valueCards" :key="idx">
          <div class="value-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path v-if="idx === 0" d="M4 7h16M4 12h16M4 17h10"/>
              <path v-else-if="idx === 1" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
              <path v-else-if="idx === 2" d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <path v-else d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <h3>{{ card.title }}</h3>
          <p>{{ card.desc }}</p>
          <div class="value-tags">
            <span v-for="tag in card.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ======= Data Flow Visualization ======= -->
    <section class="dataflow-section">
      <div class="section-header">
        <h2 class="section-title">全链路数据与模型服务</h2>
        <p class="section-desc">从多源数据融合到专业模型计算，全流程自动化闭环</p>
      </div>
      <div class="dataflow-canvas">
        <!-- Animated flowing connections -->
        <div class="flow-line flow-line--1"></div>
        <div class="flow-line flow-line--2"></div>
        <div class="flow-line flow-line--3"></div>

        <!-- Data source nodes -->
        <div class="flow-stage stage--sources">
          <div class="stage-label">数据源层</div>
          <div class="source-grid">
            <div class="source-node" v-for="src in dataSources" :key="src.name">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <ellipse cx="12" cy="5" rx="9" ry="3"/>
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
              </svg>
              <span>{{ src.name }}</span>
            </div>
          </div>
        </div>

        <!-- Processing node -->
        <div class="flow-stage stage--process">
          <div class="stage-label">数据中台</div>
          <div class="process-box">
            <div class="process-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/>
              </svg>
            </div>
            <div class="process-text">清洗 · 标准化 · 时空匹配 · API 服务</div>
          </div>
        </div>

        <!-- Model layer -->
        <div class="flow-stage stage--models">
          <div class="stage-label">专业模型层</div>
          <div class="model-pills">
            <span v-for="m in modelPills" :key="m" class="model-pill">{{ m }}</span>
          </div>
        </div>

        <!-- Output -->
        <div class="flow-stage stage--output">
          <div class="stage-label">决策输出</div>
          <div class="output-grid">
            <div class="output-node" v-for="out in outputs" :key="out">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9 11l3 3L22 4"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
              </svg>
              {{ out }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ======= Professional Model Cards ======= -->
    <section id="models-section" class="models-section">
      <div class="section-header">
        <h2 class="section-title">八大专业模型服务</h2>
        <p class="section-desc">专注灌区细分领域高精度计算，为智能调控提供专业模型支撑</p>
      </div>
      <div class="models-grid">
        <router-link to="/model/irrigation" class="model-card">
          <div class="model-card-icon water-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
            </svg>
          </div>
          <h3>灌溉决策动态预报</h3>
          <p>基于 Penman-Monteith 公式精准估算作物需水量，实现灌溉需水滚动预报与缺墒预警</p>
          <div class="model-tags">
            <span>Penman-Monteith</span>
            <span>滚动预报</span>
            <span>缺墒预警</span>
          </div>
        </router-link>

        <router-link to="/model/canal/optimize" class="model-card">
          <div class="model-card-icon canal-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
          </div>
          <h3>渠系优化配水</h3>
          <p>多级渠系协同配水优化、水力滞后自适应调度、闸门调控指令直接输出</p>
          <div class="model-tags">
            <span>NSGA-II</span>
            <span>MPC</span>
            <span>OID</span>
          </div>
        </router-link>

        <router-link to="/model/canal/kinematic" class="model-card">
          <div class="model-card-icon hydro-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <h3>渠系水动力学模拟</h3>
          <p>基于 Kinematic Wave 隐式迎风有限差分法，Manning 摩阻 + Thomas 追赶法，返回时空水位流量序列</p>
          <div class="model-tags">
            <span>Kinematic Wave</span>
            <span>Thomas 追赶法</span>
            <span>非恒定流</span>
          </div>
        </router-link>

        <router-link to="/model/water-soil-resource" class="model-card">
          <div class="model-card-icon resource-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>
            </svg>
          </div>
          <h3>水土资源优化配置</h3>
          <p>多水源联合优化配置、多目标协同求解、种植结构与灌溉制度协同优化</p>
          <div class="model-tags">
            <span>NSGA-II</span>
            <span>多目标优化</span>
            <span>时空匹配</span>
          </div>
        </router-link>

        <router-link to="#" class="model-card">
          <div class="model-card-icon waterright-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
            </svg>
          </div>
          <h3>初始水权分配</h3>
          <p>刚性与弹性水权分级分配、多准则均衡智能分配、水权交易情景模拟分析</p>
          <div class="model-tags">
            <span>博弈论</span>
            <span>基尼系数</span>
            <span>水权确权</span>
          </div>
        </router-link>

        <router-link to="/model/crop-growth" class="model-card">
          <div class="model-card-icon crop-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 22V8M5 12H2a10 10 0 0 0 20 0h-3"/>
              <circle cx="12" cy="5" r="3"/>
            </svg>
          </div>
          <h3>作物生长模拟</h3>
          <p>全生育期生长动态仿真、品种参数本地化率定、产量预测与灾害损失评估</p>
          <div class="model-tags">
            <span>WOFOST</span>
            <span>PCSE</span>
            <span>SCE-UA</span>
          </div>
        </router-link>

        <router-link to="#" class="model-card">
          <div class="model-card-icon fert-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M7 21h10M12 21V11M5 7l7-5 7 5M5 7h14v10H5z"/>
            </svg>
          </div>
          <h3>农田水氮耦合优化</h3>
          <p>农田水氮运移全过程模拟、产量效率环保多目标协同优化、精细化水肥指令输出</p>
          <div class="model-tags">
            <span>深度强化学习</span>
            <span>面源污染</span>
            <span>水肥一体</span>
          </div>
        </router-link>

        <router-link to="#" class="model-card">
          <div class="model-card-icon eval-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 11l3 3L22 4"/>
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
            </svg>
          </div>
          <h3>灌区用水综合评价</h3>
          <p>多维度全域综合评价、多周期动态趋势分析、短板问题精准诊断、评价报告自动生成</p>
          <div class="model-tags">
            <span>FAHP</span>
            <span>熵权法</span>
            <span>综合评价</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- ======= Architecture Section ======= -->
    <section class="arch-section">
      <div class="section-header">
        <h2 class="section-title">平台技术架构</h2>
        <p class="section-desc">三层解耦式分层架构，数据互通、任务协同、能力互补</p>
      </div>
      <div class="arch-diagram">
        <div class="arch-layer arch-layer--top">
          <div class="arch-layer-label">应用交互层</div>
          <div class="arch-apps-grid">
            <div class="arch-app-node">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <path d="M8 21h8M12 17v4"/>
              </svg>
              <span>Web 管理端</span>
            </div>
            <div class="arch-app-node">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="5" y="2" width="14" height="20" rx="2"/>
                <path d="M12 18h.01"/>
              </svg>
              <span>移动端</span>
            </div>
            <div class="arch-app-node">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <path d="M7.5 4.21l4.5 2.6 4.5-2.6M7.5 19.79V14.6L3 12M21 12l-4.5 2.6v5.19M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/>
              </svg>
              <span>API 服务</span>
            </div>
            <div class="arch-app-node">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2a4 4 0 0 1 4 4v1h1a2 2 0 0 1 2 2v1a6 6 0 0 1-6 6H7a6 6 0 0 1-6-6V9a2 2 0 0 1 2-2h1V6a4 4 0 0 1 4-4z"/>
              </svg>
              <span>智能体调用</span>
            </div>
          </div>
        </div>

        <div class="arch-connector-v">
          <div class="connector-dot"></div>
        </div>

        <div class="arch-layer arch-layer--mid">
          <div class="arch-layer-label">专业模型层</div>
          <div class="arch-agents-grid">
            <div class="arch-node" v-for="agent in archAgents" :key="agent">{{ agent }}</div>
          </div>
        </div>

        <div class="arch-connector-v">
          <div class="connector-dot"></div>
        </div>

        <div class="arch-layer arch-layer--bot">
          <div class="arch-layer-label">数据支撑层</div>
          <div class="arch-data-grid">
            <div class="arch-node arch-node--data" v-for="data in archData" :key="data">{{ data }}</div>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref } from 'vue'

defineOptions({
  name: 'DashBoard'
})

const platformStats = ref([
  { icon: 'database', value: '8+', label: '多源数据接入' },
  { icon: 'cpu', value: '8+', label: '专业模型服务' },
  { icon: 'chart', value: '7×24', label: '实时数据处理' },
  { icon: 'cloud', value: '100%', label: 'API 驱动' },
])

const valueCards = ref([
  {
    title: '多源异构数据融合',
    desc: '统一整合气象、水文、土壤、作物、渠系等灌区全维数据资源，通过数据清洗、标准化处理、时空匹配，为所有模型提供统一规范的数据支撑',
    tags: ['实时接入', '标准格式', '时空匹配']
  },
  {
    title: '专业模型高精度计算',
    desc: '八大垂直领域专业模型依托成熟行业机理模型构建，专注细分领域高精度计算与专业决策输出，保障计算结果符合自然规律与行业规范',
    tags: ['机理保真', '高精度', '可验证']
  },
  {
    title: '全流程 API 服务化',
    desc: '所有数据接口与模型服务均通过标准化 RESTful API 暴露，支持结构化数值、空间栅格、时序过程等多类型数据的无缝传输与调用',
    tags: ['RESTful API', '标准化接口', '灵活调用']
  },
  {
    title: '数据安全与合规保障',
    desc: '内置用水总量红线、地下水超采管控、生态基流保障等刚性约束校验，确保所有模型输出完全贴合国家及地方水资源管控政策',
    tags: ['约束校验', '合规审核', '安全可控']
  },
])

const dataSources = ref([
  { name: '气象监测' },
  { name: '水文水资源' },
  { name: '土壤理化' },
  { name: '作物种植' },
  { name: '渠系工程' },
  { name: '用水计量' },
  { name: '水肥管控' },
  { name: '生态环境' },
])

const modelPills = ref([
  '水土资源配置', '初始水权分配', '渠系优化配水',
  '水动力学模拟', '灌溉决策预报', '水氮耦合优化',
  '作物生长模拟', '用水综合评价'
])

const outputs = ref([
  '配水方案', '水权报表', '灌溉定额',
  '产量预测', '评价报告', '安全预警'
])

const archAgents = ref([
  '水土资源配置', '初始水权分配', '渠系优化配水',
  '渠系水动力', '灌溉决策预报', '水氮耦合优化',
  '作物生长模拟', '用水综合评价'
])

const archData = ref([
  '气象监测', '水文水资源', '土壤理化', '作物种植',
  '渠系工程', '用水计量', '水肥管控', '生态环境'
])

function scrollToModels() {
  document.getElementById('models-section')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.dashboard-container {
  min-height: calc(100vh - 84px);
  padding: 28px;
  background: var(--page-bg);
  display: flex;
  flex-direction: column;
  gap: 40px;
  width: 100%;
  max-width: none;
}

/* ---- Section Headers ---- */
.section-header {
  text-align: center;
  margin-bottom: 32px;
}

.section-title {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 10px;
}

.section-desc {
  font-size: 18px;
  color: var(--text-secondary);
  margin: 0;
}

/* ======= Hero ======= */
.hero-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 48px;
  padding: 56px 64px;
  min-height: 460px;
  border-radius: 32px;
  background: var(--hero-card-bg);
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow);
  overflow: hidden;
  align-items: center;
}

.hero-bg-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  border-radius: 32px;
}

.hero-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.18;
  animation: orb-float 12s ease-in-out infinite;
}

.hero-orb--1 {
  width: 400px;
  height: 400px;
  background: #0ea5e9;
  top: -100px;
  right: -50px;
  animation-delay: 0s;
}

.hero-orb--2 {
  width: 300px;
  height: 300px;
  background: #7c3aed;
  bottom: -80px;
  left: 30%;
  animation-delay: -4s;
}

.hero-orb--3 {
  width: 200px;
  height: 200px;
  background: #22c55e;
  top: 40%;
  left: -60px;
  animation-delay: -8s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(20px, -20px) scale(1.05); }
  66% { transform: translate(-15px, 15px) scale(0.95); }
}

.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(124, 58, 237, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(124, 58, 237, 0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse at center, rgba(0,0,0,0.6) 0%, transparent 70%);
}

.hero-left {
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px 6px 10px;
  border-radius: 9999px;
  background: var(--hero-badge-bg);
  color: var(--hero-badge-text);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 4px;
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--hero-badge-text);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

.hero-title {
  margin: 20px 0 18px;
  font-size: clamp(36px, 4.4vw, 60px);
  line-height: 1.1;
  letter-spacing: -0.03em;
  font-weight: 750;
  color: var(--text-primary);
}

.hero-subtitle {
  margin: 0 0 16px;
  font-size: 20px;
  line-height: 1.6;
  color: var(--text-regular);
  font-weight: 500;
}

.hero-desc {
  margin: 0 0 28px;
  font-size: 16px;
  line-height: 1.9;
  color: var(--text-secondary);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* ---- Hero 3D Visual ---- */
.hero-right {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-3d-container {
  position: relative;
  width: 320px;
  height: 320px;
}

.data-globe {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 0 auto;
  transform-style: preserve-3d;
  animation: globe-rotate 20s linear infinite;
}

@keyframes globe-rotate {
  from { transform: rotateY(0deg) rotateX(15deg); }
  to { transform: rotateY(360deg) rotateX(15deg); }
}

.globe-ring {
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(14, 165, 233, 0.3);
  animation: ring-pulse 4s ease-in-out infinite;
}

.globe-ring--1 {
  inset: -20px;
  transform: rotateX(70deg);
  border-color: rgba(124, 58, 237, 0.25);
  animation-delay: 0s;
}

.globe-ring--2 {
  inset: -40px;
  transform: rotateX(70deg) rotateY(30deg);
  border-color: rgba(14, 165, 233, 0.2);
  animation-delay: -1.3s;
}

.globe-ring--3 {
  inset: -60px;
  transform: rotateX(70deg) rotateY(60deg);
  border-color: rgba(34, 197, 94, 0.15);
  animation-delay: -2.6s;
}

@keyframes ring-pulse {
  0%, 100% { opacity: 0.5; transform: rotateX(70deg) scale(1); }
  50% { opacity: 1; transform: rotateX(70deg) scale(1.03); }
}

.globe-core {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.15), rgba(14, 165, 233, 0.15));
  border: 2px solid rgba(124, 58, 237, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(8px);
  box-shadow: 0 0 30px rgba(124, 58, 237, 0.15), inset 0 0 20px rgba(124, 58, 237, 0.1);
}

.globe-core svg {
  width: 32px;
  height: 32px;
  color: rgba(124, 58, 237, 0.7);
}

.orbit-node {
  position: absolute;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--surface-bg);
  border: 1.5px solid rgba(14, 165, 233, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  animation: node-float 4s ease-in-out infinite;
}

.orbit-node span {
  pointer-events: none;
}

.node-1 { top: -8px; left: 50%; transform: translateX(-50%); animation-delay: 0s; }
.node-2 { top: 20%; right: -8px; animation-delay: -0.66s; }
.node-3 { bottom: 20%; right: -8px; animation-delay: -1.33s; }
.node-4 { bottom: -8px; left: 50%; transform: translateX(-50%); animation-delay: -2s; }
.node-5 { bottom: 20%; left: -8px; animation-delay: -2.66s; }
.node-6 { top: 20%; left: -8px; animation-delay: -3.33s; }

@keyframes node-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

/* Floating stat cards */
.stat-card {
  position: absolute;
  padding: 12px 18px;
  border-radius: 16px;
  background: var(--surface-bg);
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow-soft);
  animation: stat-float 5s ease-in-out infinite;
  min-width: 90px;
}

.stat-card--tl { top: 0; left: 0; animation-delay: -1s; }
.stat-card--tr { top: 0; right: 0; animation-delay: -2.5s; }
.stat-card--bl { bottom: 10px; left: 10px; animation-delay: -4s; }

@keyframes stat-float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-8px) rotate(1deg); }
}

.stat-val {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ======= Stats Section ======= */
.stats-section {
  padding: 0 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stats-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 20px;
  background: var(--surface-bg);
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: default;
}

.stats-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.06);
}

.stats-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(124, 58, 237, 0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stats-icon svg {
  width: 22px;
  height: 22px;
  color: #7c3aed;
}

.stats-value {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  line-height: 1;
}

.stats-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 6px;
  font-weight: 500;
}

/* ======= Value Section ======= */
.value-section { padding: 0 4px; }

.value-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.value-card {
  padding: 28px 24px;
  border-radius: 24px;
  border: 1px solid var(--hairline-color);
  background: var(--surface-bg);
  box-shadow: var(--content-shadow-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: default;
}

.value-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.08);
}

.value-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0ea5e9, #7c3aed);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.value-icon svg {
  width: 24px;
  height: 24px;
  color: white;
}

.value-card h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 10px;
}

.value-card p {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text-secondary);
  margin: 0 0 16px;
}

.value-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.value-tags span {
  padding: 3px 10px;
  border-radius: 9999px;
  background: rgba(14, 165, 233, 0.08);
  border: 1px solid rgba(14, 165, 233, 0.2);
  font-size: 13px;
  font-weight: 600;
  color: #0ea5e9;
}

/* ======= Dataflow Section ======= */
.dataflow-section { padding: 0 4px; }

.dataflow-canvas {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  align-items: start;
  gap: 0;
  padding: 32px;
  border-radius: 28px;
  background: var(--surface-bg);
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow-soft);
  overflow: hidden;
}

.flow-line {
  position: absolute;
  height: 2px;
  background: linear-gradient(to right, rgba(14,165,233,0.3), rgba(124,58,237,0.3));
  top: 50%;
  animation: flow-move 3s linear infinite;
}

.flow-line--1 { width: 15%; left: 28%; top: calc(32px + 40px); }
.flow-line--2 { width: 8%; left: 55%; top: calc(32px + 40px); animation-delay: -1s; }
.flow-line--3 { width: 8%; left: 75%; top: calc(32px + 40px); animation-delay: -2s; }

@keyframes flow-move {
  from { opacity: 0.2; transform: scaleX(0.3); transform-origin: left; }
  50% { opacity: 0.8; }
  to { opacity: 0.2; transform: scaleX(1); transform-origin: left; }
}

.flow-stage {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage--sources { }
.stage--process { padding: 0 24px; }
.stage--models { padding: 0 24px; }
.stage--output { }

.stage-label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  text-align: center;
  padding: 3px 10px;
  border-radius: 9999px;
  background: var(--surface-soft-bg);
  border: 1px solid var(--hairline-soft-color);
  align-self: flex-start;
}

.source-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.source-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 12px;
  background: var(--surface-soft-bg);
  border: 1px solid var(--hairline-soft-color);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-regular);
  transition: transform 0.2s ease;
  cursor: default;
}

.source-node:hover { transform: scale(1.03); }

.source-node svg {
  width: 14px;
  height: 14px;
  color: #0ea5e9;
  flex-shrink: 0;
}

.process-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.08), rgba(14, 165, 233, 0.08));
  border: 1.5px solid rgba(124, 58, 237, 0.2);
  min-width: 160px;
}

.process-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #7c3aed, #0ea5e9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.process-icon svg {
  width: 24px;
  height: 24px;
  color: white;
}

.process-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  text-align: center;
  line-height: 1.6;
}

.model-pills {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-pill {
  padding: 6px 14px;
  border-radius: 9999px;
  background: rgba(14, 165, 233, 0.08);
  border: 1px solid rgba(14, 165, 233, 0.2);
  font-size: 13px;
  font-weight: 600;
  color: #0ea5e9;
  white-space: nowrap;
  cursor: default;
  transition: transform 0.15s ease, background 0.15s ease;
  text-align: center;
}

.model-pill:hover {
  transform: translateX(3px);
  background: rgba(14, 165, 233, 0.15);
}

.output-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.output-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 12px;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  font-size: 13px;
  font-weight: 600;
  color: #16a34a;
  cursor: default;
  transition: transform 0.15s ease;
}

.output-node:hover { transform: scale(1.03); }

.output-node svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

/* ======= Models Section ======= */
.models-section { padding: 0 4px; }

.models-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.model-card {
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid var(--hairline-color);
  background: var(--surface-bg);
  box-shadow: var(--content-shadow-soft);
  text-decoration: none;
  color: inherit;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
}

.model-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 40px rgba(0,0,0,0.1);
  border-color: var(--el-color-primary-light-5);
}

.model-card-icon {
  width: 52px;
  height: 52px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.model-card-icon svg {
  width: 26px;
  height: 26px;
  color: white;
}

.water-icon { background: linear-gradient(135deg, #0ea5e9, #06b6d4); }
.canal-icon { background: linear-gradient(135deg, #7c3aed, #a78bfa); }
.hydro-icon { background: linear-gradient(135deg, #f59e0b, #f97316); }
.resource-icon { background: linear-gradient(135deg, #22c55e, #10b981); }
.waterright-icon { background: linear-gradient(135deg, #3b82f6, #60a5fa); }
.crop-icon { background: linear-gradient(135deg, #84cc16, #a3e635); }
.fert-icon { background: linear-gradient(135deg, #ec4899, #f472b6); }
.eval-icon { background: linear-gradient(135deg, #ef4444, #f87171); }

.model-card h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 10px;
}

.model-card p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0 0 16px;
  flex: 1;
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
}

.model-tags span {
  padding: 4px 12px;
  border-radius: 9999px;
  background: var(--surface-soft-bg);
  border: 1px solid var(--hairline-soft-color);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
}

/* ======= Architecture Section ======= */
.arch-section { padding: 0 4px; margin-bottom: 12px; }

.arch-diagram {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.arch-layer {
  padding: 16px 20px 14px;
  border-radius: 20px;
  border: 1px solid var(--hairline-color);
  background: var(--surface-soft-bg);
}

.arch-layer--top {
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.06), rgba(124, 58, 237, 0.02));
  border-color: rgba(124, 58, 237, 0.15);
}

.arch-layer--mid {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.06), rgba(14, 165, 233, 0.02));
  border-color: rgba(14, 165, 233, 0.15);
}

.arch-layer--bot {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.06), rgba(34, 197, 94, 0.02));
  border-color: rgba(34, 197, 94, 0.15);
}

.arch-layer-label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 12px;
  padding: 3px 10px;
  border-radius: 9999px;
  display: inline-block;
}

.arch-layer--top .arch-layer-label { color: #7c3aed; background: rgba(124,58,237,0.1); }
.arch-layer--mid .arch-layer-label { color: #0ea5e9; background: rgba(14,165,233,0.1); }
.arch-layer--bot .arch-layer-label { color: #16a34a; background: rgba(34,197,94,0.1); }

.arch-apps-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.arch-app-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: 14px;
  background: var(--surface-bg);
  border: 1px solid rgba(124, 58, 237, 0.15);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
  text-align: center;
  cursor: default;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.arch-app-node:hover {
  transform: translateY(-2px);
  border-color: rgba(124, 58, 237, 0.35);
}

.arch-app-node svg {
  width: 22px;
  height: 22px;
  color: #7c3aed;
}

.arch-connector-v {
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.arch-connector-v::before {
  content: '';
  width: 2px;
  height: 100%;
  background: linear-gradient(to bottom, rgba(124,58,237,0.3), rgba(14,165,233,0.3), rgba(34,197,94,0.3));
}

.connector-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed, #0ea5e9);
  animation: dot-pulse 2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.arch-agents-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.arch-node {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 8px;
  border-radius: 12px;
  background: var(--surface-bg);
  border: 1px solid rgba(14, 165, 233, 0.15);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-regular);
  text-align: center;
  transition: transform 0.2s ease, border-color 0.2s ease;
  cursor: default;
}

.arch-node:hover {
  transform: translateY(-2px);
  border-color: rgba(14, 165, 233, 0.35);
}

.arch-data-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.arch-node--data {
  font-size: 13px;
  border-color: rgba(34, 197, 94, 0.15);
  padding: 8px 6px;
  min-height: 40px;
}

.arch-node--data:hover {
  border-color: rgba(34, 197, 94, 0.35);
}

/* ======= Responsive ======= */
@media (max-width: 1400px) {
  .models-grid { grid-template-columns: repeat(3, 1fr); }
  .value-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 1100px) {
  .hero-card { grid-template-columns: 1fr; padding: 28px; }
  .hero-right { display: none; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .dataflow-canvas { grid-template-columns: 1fr; gap: 24px; }
  .flow-line { display: none; }
}

@media (max-width: 900px) {
  .dashboard-container { padding: 20px; gap: 32px; }
  .models-grid { grid-template-columns: repeat(2, 1fr); }
  .arch-apps-grid { grid-template-columns: repeat(2, 1fr); }
  .arch-agents-grid { grid-template-columns: repeat(2, 1fr); }
  .arch-data-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 640px) {
  .models-grid { grid-template-columns: 1fr; }
  .value-grid { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: 1fr; }
  .hero-title { font-size: 30px; }
  .hero-subtitle { font-size: 16px; }
  .section-title { font-size: 24px; }
  .arch-apps-grid,
  .arch-agents-grid,
  .arch-data-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
