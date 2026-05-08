<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="小区编号" prop="plot">
        <el-input v-model="queryParams.plot" placeholder="请输入小区编号" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="dataList">
      <el-table-column label="ID" prop="id" width="80" />
      <el-table-column label="小区编号" prop="plot" width="120" />
      <el-table-column label="观测日期" prop="obsDate" width="100" />
      <el-table-column label="植株序号" prop="plantNo" width="100" />
      <el-table-column label="密度(株)" prop="density" width="100" />
      <el-table-column label="叶面积1" prop="leafArea1" width="110" />
      <el-table-column label="叶面积2" prop="leafArea2" width="110" />
      <el-table-column label="叶面积3" prop="leafArea3" width="110" />
    </el-table>

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
import { listLeafArea } from '@/api/agriculture/crop'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  plot: undefined
})

function getList() {
  loading.value = true
  listLeafArea(queryParams.value).then(response => {
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
  queryParams.value = { pageNum: 1, pageSize: 10, plot: undefined }
  handleQuery()
}

onMounted(() => {
  getList()
})
</script>
