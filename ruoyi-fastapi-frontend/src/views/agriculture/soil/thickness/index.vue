<template>
  <div class="app-container">
    <el-row :gutter="10" class="mb8">
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="dataList">
      <el-table-column label="ID" prop="id" width="80" />
      <el-table-column label="监测点编号" prop="pointId" width="120" />
      <el-table-column label="经度" prop="pointX" width="130" />
      <el-table-column label="纬度" prop="pointY" width="130" />
      <el-table-column label="黑土厚度(cm)" prop="blackSoilDepthCm" width="130" />
      <el-table-column label="创建时间" prop="createdAt" width="180" />
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
import { listThickness } from '@/api/agriculture/soil'

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
  listThickness(queryParams.value).then(response => {
    dataList.value = response.rows
    total.value = response.total
    loading.value = false
  })
}

onMounted(() => {
  getList()
})
</script>
