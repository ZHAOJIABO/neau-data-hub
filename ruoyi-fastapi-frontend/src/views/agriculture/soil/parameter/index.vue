<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">SOIL PARAMETER DATA</span>
        <h1 class="agri-page__title">土壤参数</h1>
        <p class="agri-page__desc">管理土壤有机碳、颗粒组成、容重、K 值、含水量与田间持水量等基础参数。</p>
      </div>
      <div class="agri-page__tags">
        <span>网格</span>
        <span>理化参数</span>
        <span>持水量</span>
      </div>
    </section>

    <div class="agri-toolbar">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="数据来源" prop="source">
          <el-select v-model="queryParams.source" placeholder="选择来源" clearable style="width: 200px">
            <el-option label="k" value="k" />
            <el-option label="k1" value="k1" />
            <el-option label="k2" value="k2" />
          </el-select>
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
        <el-table-column label="ID" prop="id" min-width="70" />
        <el-table-column label="来源" prop="source" min-width="70" />
        <el-table-column label="网格ID" prop="gridId" min-width="80" />
        <el-table-column label="有机碳" prop="oc05" min-width="90" />
        <el-table-column label="砂粒" prop="sand05" min-width="90" />
        <el-table-column label="粘粒" prop="clay05" min-width="90" />
        <el-table-column label="粉粒" prop="silt05" min-width="90" />
        <el-table-column label="容重" prop="bulkDensity" min-width="90" />
        <el-table-column label="K值" prop="kValue" min-width="100" />
        <el-table-column label="含水量" prop="moistureContent" min-width="90" />
        <el-table-column label="田间持水量" prop="fieldCapacity" min-width="110" />
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
import { listParameter } from '@/api/agriculture/soil'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  source: undefined
})

function getList() {
  loading.value = true
  listParameter(queryParams.value).then(response => {
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
  queryParams.value = { pageNum: 1, pageSize: 10, source: undefined }
  handleQuery()
}

onMounted(() => {
  getList()
})
</script>
