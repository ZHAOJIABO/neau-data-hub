<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">TEMPERATURE DATA</span>
        <h1 class="agri-page__title">温度数据</h1>
        <p class="agri-page__desc">按站点和日期检索最高温、最低温与平均温观测记录。</p>
      </div>
      <div class="agri-page__tags">
        <span>最高温</span>
        <span>最低温</span>
        <span>平均温</span>
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
      <el-col :span="1.5">
        <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete" v-hasPermi="['agriculture:weather:temperature:remove']">删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <div class="agri-table-card">
      <el-table v-loading="loading" :data="dataList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="站点编码" prop="stcd" width="100" />
        <el-table-column label="日期" prop="obsDate" width="120" />
        <el-table-column label="最高温(℃)" prop="tmax" width="110" />
        <el-table-column label="最低温(℃)" prop="tmin" width="110" />
        <el-table-column label="平均温(℃)" prop="tmean" width="110" />
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
import { listTemperature, delTemperature } from '@/api/agriculture/weather'
import { ElMessageBox, ElMessage } from 'element-plus'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const ids = ref([])
const multiple = ref(true)
const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  stcd: undefined,
  startDate: undefined,
  endDate: undefined
})

function getList() {
  loading.value = true
  listTemperature(queryParams.value).then(response => {
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

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id)
  multiple.value = !selection.length
}

function handleDelete() {
  ElMessageBox.confirm('是否确认删除选中的数据？').then(() => {
    return delTemperature(ids.value.join(','))
  }).then(() => {
    getList()
    ElMessage.success('删除成功')
  }).catch(() => {})
}

onMounted(() => {
  getList()
})
</script>
