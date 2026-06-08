<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">WEATHER OBSERVATION</span>
        <h1 class="agri-page__title">气象综合数据</h1>
        <p class="agri-page__desc">查看站点级温度、湿度、降水、日照与风速等综合气象观测记录。</p>
      </div>
      <div class="agri-page__tags">
        <span>温度</span>
        <span>湿度</span>
        <span>降水</span>
      </div>
    </section>

    <div class="agri-toolbar">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="站点编码" prop="stcd">
          <el-input v-model="queryParams.stcd" placeholder="请输入站点编码" clearable style="width: 200px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="开始日期" prop="startDate">
          <el-date-picker v-model="queryParams.startDate" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item label="结束日期" prop="endDate">
          <el-date-picker v-model="queryParams.endDate" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-row :gutter="10" class="mb8 agri-actions">
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <div class="agri-table-card">
      <el-table v-loading="loading" :data="dataList">
        <el-table-column label="站点名称" prop="stationName" width="120" />
        <el-table-column label="站点编码" prop="stcd" width="100" />
        <el-table-column label="日期" prop="obsDate" width="120" />
        <el-table-column label="最高温(℃)" prop="tmax" width="100" />
        <el-table-column label="最低温(℃)" prop="tmin" width="100" />
        <el-table-column label="平均温(℃)" prop="tmean" width="100" />
        <el-table-column label="湿度(%)" prop="rhMean" width="90" />
        <el-table-column label="降水(mm)" prop="precipitation" width="100" />
        <el-table-column label="日照(h)" prop="sunshineHours" width="90" />
        <el-table-column label="风速(m/s)" prop="windSpeed" width="100" />
      </el-table>
    </div>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listWeatherOverview } from '@/api/agriculture/weather'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  stcd: undefined,
  startDate: undefined,
  endDate: undefined
})

function getList() {
  loading.value = true
  listWeatherOverview(queryParams.value).then(response => {
    dataList.value = response.rows
    total.value = response.total
    loading.value = false
  })
}

function handleQuery() {
  queryParams.value.pageNum = 1
  getList()
}

function resetQuery() {
  queryParams.value = { pageNum: 1, pageSize: 10, stcd: undefined, startDate: undefined, endDate: undefined }
  handleQuery()
}

onMounted(() => {
  getList()
})
</script>
