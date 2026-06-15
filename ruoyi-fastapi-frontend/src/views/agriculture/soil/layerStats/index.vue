<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">SOIL LAYER STATISTICS</span>
        <h1 class="agri-page__title">土层统计</h1>
        <p class="agri-page__desc">查看不同土层深度的最大值、最小值、均值、标准偏差与变异系数。</p>
      </div>
      <div class="agri-page__tags">
        <span>土层</span>
        <span>均值</span>
        <span>变异系数</span>
      </div>
    </section>

    <el-row :gutter="10" class="mb8 agri-actions">
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <div class="agri-table-card">
      <el-table v-loading="loading" :data="dataList">
        <el-table-column label="ID" prop="id" min-width="80" />
        <el-table-column label="土层深度" prop="layerDepth" min-width="120" />
        <el-table-column label="最大值" prop="maxValue" min-width="110" />
        <el-table-column label="最小值" prop="minValue" min-width="110" />
        <el-table-column label="均值" prop="meanValue" min-width="110" />
        <el-table-column label="标准偏差" prop="stdDev" min-width="110" />
        <el-table-column label="变异系数" prop="cv" min-width="110" />
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
