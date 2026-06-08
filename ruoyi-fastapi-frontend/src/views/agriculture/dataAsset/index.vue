<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">DATA ASSETS</span>
        <h1 class="agri-page__title">数据资产</h1>
        <p class="agri-page__desc">管理 GeoTIFF 和 Shapefile 等非表格空间文件资产，支持上传、下载和元数据浏览。</p>
      </div>
      <div class="agri-page__tags">
        <span>GeoTIFF</span>
        <span>Shapefile</span>
        <span>空间数据</span>
      </div>
    </section>

    <div class="agri-toolbar">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="文件名称" prop="assetName">
          <el-input v-model="queryParams.assetName" placeholder="请输入文件名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="相对路径" prop="relativePath">
          <el-input v-model="queryParams.relativePath" placeholder="请输入路径关键字" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="资产类型" prop="assetType">
          <el-select v-model="queryParams.assetType" placeholder="全部" clearable style="width: 120px">
            <el-option label="栅格" value="raster" />
            <el-option label="矢量" value="vector" />
            <el-option label="文件" value="file" />
          </el-select>
        </el-form-item>
        <el-form-item label="文件格式" prop="fileFormat">
          <el-select v-model="queryParams.fileFormat" placeholder="全部" clearable style="width: 120px">
            <el-option label="tif" value="tif" />
            <el-option label="tiff" value="tiff" />
            <el-option label="shp" value="shp" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据分类" prop="dataCategory">
          <el-select v-model="queryParams.dataCategory" placeholder="全部" clearable style="width: 140px">
            <el-option label="气象数据" value="气象数据" />
            <el-option label="自然地理数据" value="自然地理数据" />
            <el-option label="土壤数据" value="土壤数据" />
            <el-option label="作物数据" value="作物数据" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域" prop="regionName">
          <el-select v-model="queryParams.regionName" placeholder="全部" clearable style="width: 140px">
            <el-option label="鹤北小流域" value="鹤北小流域" />
            <el-option label="浓江农场" value="浓江农场" />
          </el-select>
        </el-form-item>
        <el-form-item label="变量名" prop="variableName">
          <el-input v-model="queryParams.variableName" placeholder="变量名" clearable style="width: 120px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="观测日期">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="-" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width: 240px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-row :gutter="10" class="mb8 agri-actions">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Upload" @click="handleUpload" v-hasPermi="['agriculture:dataAsset:upload']">上传</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete" v-hasPermi="['agriculture:dataAsset:remove']">删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <div class="agri-table-card">
      <el-table v-loading="loading" :data="dataList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="ID" prop="id" width="60" />
        <el-table-column label="文件名称" prop="assetName" min-width="160" show-overflow-tooltip />
        <el-table-column label="相对路径" prop="relativePath" min-width="260" show-overflow-tooltip />
        <el-table-column label="类型" prop="assetType" width="80" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.assetType === 'raster' ? 'success' : scope.row.assetType === 'vector' ? 'warning' : 'info'" size="small">
              {{ scope.row.assetType }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="格式" prop="fileFormat" width="70" align="center" />
        <el-table-column label="分类" prop="dataCategory" width="120" />
        <el-table-column label="区域" prop="regionName" width="110" />
        <el-table-column label="大小" prop="sizeBytes" width="100" align="right">
          <template #default="scope">
            {{ formatSize(scope.row.sizeBytes) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="createdAt" width="160" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" icon="Download" @click="handleDownload(scope.row)" v-hasPermi="['agriculture:dataAsset:download']">下载</el-button>
            <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['agriculture:dataAsset:remove']">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 上传对话框 -->
    <el-dialog title="上传数据资产" v-model="uploadOpen" width="520px" append-to-body>
      <el-form ref="uploadRef" :model="uploadForm" :rules="uploadRules" label-width="90px">
        <el-form-item label="数据分类" prop="dataCategory">
          <el-select v-model="uploadForm.dataCategory" placeholder="请选择分类" clearable>
            <el-option label="气象数据" value="气象数据" />
            <el-option label="自然地理数据" value="自然地理数据" />
            <el-option label="土壤数据" value="土壤数据" />
            <el-option label="作物数据" value="作物数据" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域" prop="regionName">
          <el-select v-model="uploadForm.regionName" placeholder="请选择区域" clearable>
            <el-option label="鹤北小流域" value="鹤北小流域" />
            <el-option label="浓江农场" value="浓江农场" />
          </el-select>
        </el-form-item>
        <el-form-item label="变量名" prop="variableName">
          <el-input v-model="uploadForm.variableName" placeholder="如 RAIN、DEM、土地利用" />
        </el-form-item>
        <el-form-item label="文件" prop="file">
          <el-upload
            ref="uploadElRef"
            :auto-upload="false"
            :limit="1"
            accept=".tif,.tiff,.zip"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-button type="primary" plain>选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 .tif / .tiff（GeoTIFF）和 .zip（Shapefile 压缩包）</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :loading="uploadLoading" @click="submitUpload">确 定</el-button>
          <el-button @click="uploadOpen = false">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { listDataAsset, downloadDataAsset, delDataAsset, uploadDataAsset } from '@/api/agriculture/dataAsset'
import { ElMessageBox, ElMessage } from 'element-plus'
import { saveAs } from 'file-saver'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const ids = ref([])
const multiple = ref(true)
const uploadOpen = ref(false)
const uploadLoading = ref(false)
const uploadElRef = ref(null)
const dateRange = ref([])

const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  assetName: undefined,
  relativePath: undefined,
  assetType: undefined,
  fileFormat: undefined,
  dataCategory: undefined,
  regionName: undefined,
  variableName: undefined,
  obsDateBegin: undefined,
  obsDateEnd: undefined
})

const uploadForm = ref({
  dataCategory: undefined,
  regionName: undefined,
  variableName: undefined,
  file: null
})

const uploadRules = reactive({
  file: [{ required: true, message: '请选择文件', trigger: 'change' }]
})

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

function getList() {
  loading.value = true
  const params = { ...queryParams.value }
  if (dateRange.value && dateRange.value.length === 2) {
    params.obsDateBegin = dateRange.value[0]
    params.obsDateEnd = dateRange.value[1]
  }
  listDataAsset(params).then(response => {
    dataList.value = response.rows
    total.value = response.total
    loading.value = false
  }).catch(() => {
    loading.value = false
  })
}

function handleQuery() {
  queryParams.value.pageNum = 1
  getList()
}

function resetQuery() {
  queryParams.value = {
    pageNum: 1,
    pageSize: 10,
    assetName: undefined,
    relativePath: undefined,
    assetType: undefined,
    fileFormat: undefined,
    dataCategory: undefined,
    regionName: undefined,
    variableName: undefined,
    obsDateBegin: undefined,
    obsDateEnd: undefined
  }
  dateRange.value = []
  handleQuery()
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id)
  multiple.value = !selection.length
}

function handleUpload() {
  uploadForm.value = { dataCategory: undefined, regionName: undefined, variableName: undefined, file: null }
  uploadOpen.value = true
}

function handleFileChange(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['tif', 'tiff', 'zip'].includes(ext)) {
    ElMessage.error('不支持的文件类型')
    uploadElRef.value?.clearFiles()
    return
  }
  uploadForm.value.file = file.raw
}

function handleFileRemove() {
  uploadForm.value.file = null
}

function submitUpload() {
  if (!uploadForm.value.file) {
    ElMessage.warning('请选择文件')
    return
  }
  uploadLoading.value = true
  const formData = new FormData()
  formData.append('file', uploadForm.value.file)
  if (uploadForm.value.dataCategory) formData.append('dataCategory', uploadForm.value.dataCategory)
  if (uploadForm.value.regionName) formData.append('regionName', uploadForm.value.regionName)
  if (uploadForm.value.variableName) formData.append('variableName', uploadForm.value.variableName)

  uploadDataAsset(formData).then(() => {
    ElMessage.success('上传成功')
    uploadOpen.value = false
    getList()
  }).catch(() => {}).finally(() => {
    uploadLoading.value = false
  })
}

function handleDownload(row) {
  downloadDataAsset(row.id).then(response => {
    const disposition = response.headers?.['content-disposition']
    let filename = row.originalFilename || row.assetName || 'download'
    if (disposition) {
      const match = disposition.match(/filename\*=UTF-8''(.+)/)
      if (match) filename = decodeURIComponent(match[1])
    }
    const blob = new Blob([response.data || response])
    saveAs(blob, filename)
  }).catch(() => {
    ElMessage.error('下载失败')
  })
}

function handleDelete(row) {
  const deleteIds = row.id ? [row.id] : ids.value
  ElMessageBox.confirm('是否确认删除选中的数据资产？').then(() => {
    return delDataAsset(deleteIds.join(','))
  }).then(() => {
    getList()
    ElMessage.success('删除成功')
  }).catch(() => {})
}

onMounted(() => {
  getList()
})
</script>
