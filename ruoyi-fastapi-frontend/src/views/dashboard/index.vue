<template>
  <div class="dashboard-container">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">WATERSMART · IRRIGATION DECISION INTELLIGENCE</span>
        <h1 class="title">沃水数据与模型平台</h1>
        <p class="subtitle">面向灌区用水决策的专业小模型与寒区多源数据统一管理平台</p>
        <p class="description">
          聚焦灌区业务场景，围绕配水调度、需水预测、墒情评估、气象响应与田间试验分析等方向构建专业小模型，
          同时对寒区田间实验、气象观测、土壤传感、作物调查等多类型数据集进行统一汇聚、治理与共享。
        </p>

        <div class="feature-tags">
          <span>IRRIGATION MODELS</span>
          <span>FIELD EXPERIMENTS</span>
          <span>COLD-REGION DATASETS</span>
          <span>DECISION SUPPORT</span>
        </div>

        <div class="hero-actions">
          <el-button type="primary">进入工作台</el-button>
          <el-button>查看数据资产</el-button>
        </div>
      </div>

      <div class="hero-grid">
        <div class="stat-card coral">
          <span class="stat-label">Model Suite</span>
          <strong class="stat-value">8+</strong>
          <p class="stat-description">覆盖配水调度、需水预测与情景分析等专业模型能力</p>
        </div>
        <div class="stat-card magenta">
          <span class="stat-label">Dataset Center</span>
          <strong class="stat-value">Multi-Source</strong>
          <p class="stat-description">统一管理田间实验、气象、土壤、作物与灌区业务数据</p>
        </div>
        <div class="stat-card blue">
          <span class="stat-label">Cold-Region Focus</span>
          <strong class="stat-value">Heilongjiang</strong>
          <p class="stat-description">面向寒区农业与灌区环境特点沉淀可复用数据底座</p>
        </div>
        <div class="stat-card purple">
          <span class="stat-label">Decision Workflow</span>
          <strong class="stat-value">Data → Model → Action</strong>
          <p class="stat-description">支撑从数据接入、模型推演到用水决策辅助的完整链路</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
defineOptions({
  name: 'DashBoard'
})
</script>

<style scoped>
.dashboard-container {
  min-height: calc(100vh - 140px);
  padding: 32px;
  background: var(--page-bg);
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(320px, 1.35fr) minmax(280px, 1fr);
  gap: 24px;
  padding: 40px;
  border-radius: 32px;
  background: var(--hero-card-bg);
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 9999px;
  background: var(--hero-badge-bg);
  color: var(--hero-badge-text);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.title {
  margin: 18px 0 14px;
  font-size: clamp(40px, 5vw, 68px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  font-weight: 600;
  color: var(--text-primary);
}

.subtitle {
  margin: 0;
  max-width: 680px;
  font-size: 22px;
  line-height: 1.5;
  color: var(--text-regular);
}

.description {
  margin: 18px 0 0;
  max-width: 720px;
  font-size: 16px;
  line-height: 1.9;
  color: var(--text-secondary);
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 26px;
}

.feature-tags span {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--hero-badge-bg) 70%, transparent);
  color: var(--hero-badge-text);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 30px;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  min-height: 190px;
  padding: 24px;
  border-radius: 32px;
  color: #ffffff;
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 14px;
  font-weight: 500;
  opacity: 0.92;
}

.stat-value {
  display: block;
  margin-top: 18px;
  font-size: 28px;
  line-height: 1.15;
  letter-spacing: -0.03em;
  font-weight: 600;
}

.stat-description {
  margin: auto 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.88);
}

.coral {
  background: linear-gradient(135deg, #ff5530 0%, #ff7a59 100%);
}

.magenta {
  background: linear-gradient(135deg, #ea5ec1 0%, #f085d4 100%);
}

.blue {
  background: linear-gradient(135deg, #1456f0 0%, #3daeff 100%);
}

.purple {
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
}

@media (max-width: 1100px) {
  .hero-card {
    grid-template-columns: 1fr;
    padding: 28px;
  }
}

@media (max-width: 960px) {
  .dashboard-container {
    padding: 20px;
  }

  .hero-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }

  .title {
    font-size: 36px;
  }

  .subtitle {
    font-size: 18px;
  }
}
</style>
