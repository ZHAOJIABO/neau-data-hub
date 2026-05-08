<template>
  <div class="app-container">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <template #header><span>监测站点</span></template>
          <div class="stat-value">{{ stats.stationCount || 0 }}</div>
          <div class="stat-label">个站点</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <template #header><span>温度记录</span></template>
          <div class="stat-value">{{ stats.weatherStats?.temperatureCount || 0 }}</div>
          <div class="stat-label">条记录</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <template #header><span>传感器数据</span></template>
          <div class="stat-value">{{ stats.soilStats?.sensorCount || 0 }}</div>
          <div class="stat-label">条记录</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <template #header><span>作物数据</span></template>
          <div class="stat-value">{{ stats.cropCount || 0 }}</div>
          <div class="stat-label">条记录</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>气象数据统计</span></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="温度记录">{{ stats.weatherStats?.temperatureCount || 0 }} 条</el-descriptions-item>
            <el-descriptions-item label="湿度记录">{{ stats.weatherStats?.humidityCount || 0 }} 条</el-descriptions-item>
            <el-descriptions-item label="降水记录">{{ stats.weatherStats?.precipitationCount || 0 }} 条</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>土壤数据统计</span></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="传感器监测">{{ stats.soilStats?.sensorCount || 0 }} 条</el-descriptions-item>
            <el-descriptions-item label="土壤参数">{{ stats.soilStats?.parameterCount || 0 }} 条</el-descriptions-item>
            <el-descriptions-item label="地温数据">{{ stats.soilStats?.groundTempCount || 0 }} 条</el-descriptions-item>
            <el-descriptions-item label="黑土厚度">{{ stats.soilStats?.thicknessCount || 0 }} 条</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '@/api/agriculture/dashboard'

const stats = ref({})

function getStats() {
  getDashboardStats().then(response => {
    stats.value = response.data
  })
}

onMounted(() => {
  getStats()
})
</script>

<style scoped>
.stat-card {
  text-align: center;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
</style>
