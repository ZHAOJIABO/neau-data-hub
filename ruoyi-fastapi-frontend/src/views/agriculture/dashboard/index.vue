<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">AGRICULTURE DATA CENTER</span>
        <h1 class="agri-page__title">农业数据总览</h1>
        <p class="agri-page__desc">
          汇聚监测站点、气象观测、土壤传感与作物调查数据，形成面向寒区农业试验与灌溉决策的数据资产看板。
        </p>
      </div>
      <div class="agri-page__tags">
        <span>站点</span>
        <span>气象</span>
        <span>土壤</span>
        <span>作物</span>
      </div>
    </section>

    <section class="agri-stat-grid">
      <div class="agri-stat-card agri-gradient-coral">
        <span class="agri-stat-card__label">监测站点</span>
        <strong class="agri-stat-card__value">{{ stats.stationCount || 0 }}</strong>
        <p class="agri-stat-card__desc">支撑田间观测、气象采集与灌区数据关联</p>
      </div>
      <div class="agri-stat-card agri-gradient-blue">
        <span class="agri-stat-card__label">温度记录</span>
        <strong class="agri-stat-card__value">{{ stats.weatherStats?.temperatureCount || 0 }}</strong>
        <p class="agri-stat-card__desc">覆盖最高温、最低温与日均温等气象指标</p>
      </div>
      <div class="agri-stat-card agri-gradient-magenta">
        <span class="agri-stat-card__label">传感器数据</span>
        <strong class="agri-stat-card__value">{{ stats.soilStats?.sensorCount || 0 }}</strong>
        <p class="agri-stat-card__desc">沉淀土壤温度、湿度、电导率等连续监测数据</p>
      </div>
      <div class="agri-stat-card agri-gradient-purple">
        <span class="agri-stat-card__label">作物数据</span>
        <strong class="agri-stat-card__value">{{ stats.cropCount || 0 }}</strong>
        <p class="agri-stat-card__desc">记录作物叶面积、密度与田间调查结果</p>
      </div>
    </section>

    <section class="agri-insight-grid">
      <div class="agri-insight-card">
        <h2 class="agri-insight-card__title">气象数据统计</h2>
        <div class="agri-metric-list">
          <div class="agri-metric-item">
            <span>温度记录</span>
            <strong>{{ stats.weatherStats?.temperatureCount || 0 }} 条</strong>
          </div>
          <div class="agri-metric-item">
            <span>湿度记录</span>
            <strong>{{ stats.weatherStats?.humidityCount || 0 }} 条</strong>
          </div>
          <div class="agri-metric-item">
            <span>降水记录</span>
            <strong>{{ stats.weatherStats?.precipitationCount || 0 }} 条</strong>
          </div>
        </div>
      </div>

      <div class="agri-insight-card">
        <h2 class="agri-insight-card__title">土壤数据统计</h2>
        <div class="agri-metric-list">
          <div class="agri-metric-item">
            <span>传感器监测</span>
            <strong>{{ stats.soilStats?.sensorCount || 0 }} 条</strong>
          </div>
          <div class="agri-metric-item">
            <span>土壤参数</span>
            <strong>{{ stats.soilStats?.parameterCount || 0 }} 条</strong>
          </div>
          <div class="agri-metric-item">
            <span>地温数据</span>
            <strong>{{ stats.soilStats?.groundTempCount || 0 }} 条</strong>
          </div>
          <div class="agri-metric-item">
            <span>黑土厚度</span>
            <strong>{{ stats.soilStats?.thicknessCount || 0 }} 条</strong>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '@/api/agriculture/dashboard'
import cache from '@/plugins/cache'

const stats = ref({})
const statsCacheKey = 'agricultureDashboardStats'

function getStats() {
  const cachedStats = cache.local.getJSON(statsCacheKey)
  if (cachedStats) {
    stats.value = cachedStats.data || {}
  }

  getDashboardStats().then(response => {
    stats.value = response.data || {}
    cache.local.setJSON(statsCacheKey, {
      data: stats.value,
      time: Date.now()
    })
  })
}

onMounted(() => {
  getStats()
})
</script>
