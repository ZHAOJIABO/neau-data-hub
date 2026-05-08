<template>
  <div class="app-container">
    <el-row :gutter="10" class="mb8">
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="dataList">
      <el-table-column label="ID" prop="id" width="80" />
      <el-table-column label="土层深度" prop="layerDepth" width="120" />
      <el-table-column label="最大值" prop="maxValue" width="110" />
      <el-table-column label="最小值" prop="minValue" width="110" />
      <el-table-column label="均值" prop="meanValue" width="110" />
      <el-table-column label="标准偏差" prop="stdDev" width="110" />
      <el-table-column label="变异系数" prop="cv" width="110" />
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
import { listLayerStats } from '@/api/agriculture/soil'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const queryParams = ref({
  pageNum: 1,
  pageSize: 10
})

function getList() {
  loading.value = true
  listLayerStats(queryParams.value).then(response => {
    dataList.value = response.rows
    total.value = response.total
    loading.value = false
  })
}

onMounted(() => {
  getList()
})
</script>
