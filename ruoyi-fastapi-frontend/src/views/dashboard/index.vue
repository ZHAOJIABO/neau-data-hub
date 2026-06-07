<template>
  <div class="dashboard-container">
    <div class="hero-card">
      <div class="hero-copy">
        <span class="eyebrow">Agriculture Data Hub</span>
        <h1 class="title">农业数据管理平台</h1>
        <p class="subtitle">东北农业大学农业数据综合管理系统</p>
        <div class="hero-actions">
          <el-button type="primary">进入工作台</el-button>
          <el-button>查看数据概览</el-button>
        </div>
      </div>
      <div class="hero-grid">
        <div class="stat-card coral">
          <span class="stat-label">灌溉监测</span>
          <strong class="stat-value">24/7</strong>
        </div>
        <div class="stat-card magenta">
          <span class="stat-label">气象数据</span>
          <strong class="stat-value">128 万</strong>
        </div>
        <div class="stat-card blue">
          <span class="stat-label">土壤传感</span>
          <strong class="stat-value">96 节点</strong>
        </div>
        <div class="stat-card purple">
          <span class="stat-label">作物分析</span>
          <strong class="stat-value">12 模型</strong>
        </div>
      </div>
    </div>
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
  grid-template-columns: minmax(320px, 1.4fr) minmax(280px, 1fr);
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
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.title {
  margin: 18px 0 16px;
  font-size: clamp(40px, 5vw, 72px);
  line-height: 1.1;
  letter-spacing: -0.04em;
  font-weight: 600;
  color: var(--text-primary);
}

.subtitle {
  margin: 0;
  max-width: 560px;
  font-size: 18px;
  line-height: 1.6;
  color: var(--text-regular);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  min-height: 180px;
  padding: 24px;
  border-radius: 32px;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.stat-label {
  font-size: 14px;
  font-weight: 500;
  opacity: 0.92;
}

.stat-value {
  font-size: 32px;
  line-height: 1.1;
  letter-spacing: -0.03em;
  font-weight: 600;
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

@media (max-width: 960px) {
  .dashboard-container {
    padding: 20px;
  }

  .hero-card {
    grid-template-columns: 1fr;
    padding: 24px;
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
}
</style>
