<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">PRECIPITATION DATA</span>
        <h1 class="agri-page__title">降水数据</h1>
        <p class="agri-page__desc">按站点和日期范围查看降水量记录，为作物需水和灌溉分析提供基础输入。</p>
      </div>
      <div class="agri-page__tags">
        <span>站点</span>
        <span>日期</span>
        <span>降水量</span>
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
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="站点编码" prop="stcd" width="100" />
        <el-table-column label="日期" prop="obsDate" width="120" />
        <el-table-column label="降水量(mm)" prop="precipitation" width="120" />
        <el-table-column label="创建时间" prop="createdAt" width="180" />
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
import { listPrecipitation } from '@/api/agriculture/weather'

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
  listPrecipitation(queryParams.value).then(response => {
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
