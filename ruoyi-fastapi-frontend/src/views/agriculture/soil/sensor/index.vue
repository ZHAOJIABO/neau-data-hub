<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">SOIL SENSOR DATA</span>
        <h1 class="agri-page__title">土壤传感器数据</h1>
        <p class="agri-page__desc">查看设备上报的土壤温度、湿度、电导率与深度信息，支持按设备和时间范围检索。</p>
      </div>
      <div class="agri-page__tags">
        <span>设备</span>
        <span>深度</span>
        <span>温湿度</span>
      </div>
    </section>

    <div class="agri-toolbar">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="设备名称" prop="deviceName">
          <el-input v-model="queryParams.deviceName" placeholder="请输入设备名称" clearable style="width: 200px" @keyup.enter="handleQuery" />
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
        <el-table-column label="ID" prop="id" min-width="80" />
        <el-table-column label="设备名称" prop="deviceName" min-width="140" />
        <el-table-column label="深度(cm)" prop="depthCm" min-width="100" />
        <el-table-column label="温度(℃)" prop="temperature" min-width="100" />
        <el-table-column label="湿度(%)" prop="humidity" min-width="100" />
        <el-table-column label="电导率(μs/cm)" prop="conductivity" min-width="130" />
        <el-table-column label="上报时间" prop="obsTime" min-width="180" />
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
import { listSensor } from '@/api/agriculture/soil'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  deviceName: undefined,
  startDate: undefined,
  endDate: undefined
})

function getList() {
  loading.value = true
  listSensor(queryParams.value).then(response => {
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
  queryParams.value = { pageNum: 1, pageSize: 10, deviceName: undefined, startDate: undefined, endDate: undefined }
  handleQuery()
}

onMounted(() => {
  getList()
})
</script>
