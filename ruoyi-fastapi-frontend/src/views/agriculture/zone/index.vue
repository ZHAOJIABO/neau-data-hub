<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">ZONE DATA</span>
        <h1 class="agri-page__title">分区数据</h1>
        <p class="agri-page__desc">维护灌区模型共用的分区面积、地表水和地下水基础数据，为水土资源配置、初始水权分配和农业水效评价提供统一数据源。</p>
      </div>
      <div class="agri-page__tags">
        <span>模型共用</span>
        <span>启用状态</span>
        <span>CSV 导入</span>
      </div>
    </section>

    <div class="agri-toolbar">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="灌区" prop="irrigationAreaCode">
          <el-select v-model="queryParams.irrigationAreaCode" filterable allow-create default-first-option style="width: 190px" @change="handleQuery">
            <el-option
              v-for="item in irrigationAreas"
              :key="item.irrigationAreaCode"
              :label="item.irrigationAreaName"
              :value="item.irrigationAreaCode"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="分区编号" prop="zoneId">
          <el-input v-model="queryParams.zoneId" placeholder="如 Z01" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="分区名称" prop="zoneName">
          <el-input v-model="queryParams.zoneName" placeholder="名称关键字" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 140px">
            <el-option label="启用" value="0" />
            <el-option label="停用" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-row :gutter="10" class="mb8 agri-actions">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Plus" @click="handleAdd">新增</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="warning" plain icon="Upload" @click="openImportDialog">CSV 导入</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete">删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <div class="agri-table-card">
      <el-table v-loading="loading" :data="dataList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="灌区" prop="irrigationAreaName" min-width="130" show-overflow-tooltip />
        <el-table-column label="分区编号" prop="zoneId" min-width="100" fixed />
        <el-table-column label="名称" prop="zoneName" min-width="120" />
        <el-table-column label="耕地面积 ha" prop="landArea" min-width="120" align="right" />
        <el-table-column label="地表水 m³" prop="surfaceWaterAvailable" min-width="140" align="right" />
        <el-table-column label="地下水 m³" prop="groundwaterAvailable" min-width="140" align="right" />
        <el-table-column label="IWUE" prop="iwue" min-width="90" align="right" />
        <el-table-column label="WUE kg/m³" prop="waterProductivityKgM3" min-width="110" align="right" />
        <el-table-column label="BEC 元/m³" prop="benefitYuanPerM3" min-width="110" align="right" />
        <el-table-column label="保证率" prop="irrigationReliability" min-width="90" align="right" />
        <el-table-column label="田间效率" prop="fieldEfficiency" min-width="90" align="right" />
        <el-table-column label="最小面积 ha" prop="minArea" min-width="120" align="right" />
        <el-table-column label="最大面积 ha" prop="maxArea" min-width="120" align="right" />
        <el-table-column label="排序" prop="sortOrder" min-width="80" align="center" />
        <el-table-column label="状态" prop="status" min-width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === '0' ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" prop="updatedAt" min-width="160" />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)">修改</el-button>
            <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
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

    <el-dialog :title="dialogTitle" v-model="formOpen" width="720px" append-to-body :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="140px">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="灌区编码" prop="irrigationAreaCode">
              <el-input v-model="form.irrigationAreaCode" placeholder="如 chahayang" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="灌区名称" prop="irrigationAreaName">
              <el-input v-model="form.irrigationAreaName" placeholder="如 查哈阳灌区" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="分区编号" prop="zoneId">
              <el-input v-model="form.zoneId" placeholder="如 Z01" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="分区名称" prop="zoneName">
              <el-input v-model="form.zoneName" placeholder="如 红河" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="耕地面积 (ha)" prop="landArea">
              <el-input-number v-model="form.landArea" :min="0.0001" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="地表水量 (m³)" prop="surfaceWaterAvailable">
              <el-input-number v-model="form.surfaceWaterAvailable" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="地下水量 (m³)" prop="groundwaterAvailable">
              <el-input-number v-model="form.groundwaterAvailable" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="IWUE" prop="iwue">
              <el-input-number v-model="form.iwue" :min="0" :max="1" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="WUE (kg/m³)" prop="waterProductivityKgM3">
              <el-input-number v-model="form.waterProductivityKgM3" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="BEC (元/m³)" prop="benefitYuanPerM3">
              <el-input-number v-model="form.benefitYuanPerM3" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="灌溉保证率" prop="irrigationReliability">
              <el-input-number v-model="form.irrigationReliability" :min="0" :max="1" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="田间水效率" prop="fieldEfficiency">
              <el-input-number v-model="form.fieldEfficiency" :min="0" :max="1" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="地表水利用率" prop="surfaceWaterUtilization">
              <el-input-number v-model="form.surfaceWaterUtilization" :min="0" :max="2" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="地下水利用率" prop="groundwaterUtilization">
              <el-input-number v-model="form.groundwaterUtilization" :min="0" :max="2" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="地下水依赖度" prop="groundwaterDependency">
              <el-input-number v-model="form.groundwaterDependency" :min="0" :max="1" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="最小面积 (ha)" prop="minArea">
              <el-input-number v-model="form.minArea" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="最大面积 (ha)" prop="maxArea">
              <el-input-number v-model="form.maxArea" :min="0.0001" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="排序" prop="sortOrder">
              <el-input-number v-model="form.sortOrder" :min="0" :precision="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="启用" value="0" />
                <el-option label="停用" value="1" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24">
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :loading="formLoading" @click="submitForm">确 定</el-button>
          <el-button @click="formOpen = false">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog title="从 CSV 导入分区数据" v-model="importOpen" width="520px" append-to-body>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="CSV 至少包含 zone_id / zone_name / land_area，可选 irrigation_area_code / irrigation_area_name / surface_water_available / groundwater_available / iwue / water_productivity_kg_m3 / benefit_yuan_per_m3 / irrigation_reliability / field_efficiency / surface_water_utilization / groundwater_utilization / groundwater_dependency / min_area / max_area / sort_order / status / remark。按 (灌区编码, 分区编号) upsert。"
        class="mb16"
      />
      <el-upload
        ref="importElRef"
        :auto-upload="false"
        :limit="1"
        accept=".csv"
        :on-change="handleImportFileChange"
        :on-remove="handleImportFileRemove"
      >
        <el-button type="primary" plain>选择 CSV 文件</el-button>
        <template #tip>
          <div class="el-upload__tip">仅支持 .csv 文件，UTF-8 编码</div>
        </template>
      </el-upload>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :loading="importLoading" @click="submitImport">开始导入</el-button>
          <el-button @click="importOpen = false">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listZone, listIrrigationAreas, createZone, updateZone, deleteZone, importZoneCSV } from '@/api/agriculture/zone'

const DEFAULT_AREA_CODE = 'chahayang'
const DEFAULT_AREA_NAME = '查哈阳灌区'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const ids = ref([])
const multiple = ref(true)
const irrigationAreas = ref([{ irrigationAreaCode: DEFAULT_AREA_CODE, irrigationAreaName: DEFAULT_AREA_NAME }])

const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  irrigationAreaCode: DEFAULT_AREA_CODE,
  zoneId: undefined,
  zoneName: undefined,
  status: undefined
})
const formOpen = ref(false)
const formLoading = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const dialogTitle = ref('新增分区')
const form = reactive(defaultForm())
const formRules = reactive({
  irrigationAreaCode: [{ required: true, message: '请输入灌区编码', trigger: 'blur' }],
  irrigationAreaName: [{ required: true, message: '请输入灌区名称', trigger: 'blur' }],
  zoneId: [{ required: true, message: '请输入分区编号', trigger: 'blur' }],
  zoneName: [{ required: true, message: '请输入分区名称', trigger: 'blur' }],
  landArea: [{ required: true, message: '请输入耕地面积', trigger: 'blur' }]
})

const importOpen = ref(false)
const importLoading = ref(false)
const importElRef = ref(null)
const importFile = ref(null)

function defaultForm() {
  const selectedArea = irrigationAreas.value?.find(item => item.irrigationAreaCode === queryParams.value?.irrigationAreaCode)
  return {
    irrigationAreaCode: queryParams.value?.irrigationAreaCode || DEFAULT_AREA_CODE,
    irrigationAreaName: selectedArea?.irrigationAreaName || DEFAULT_AREA_NAME,
    zoneId: '',
    zoneName: '',
    landArea: 1,
    surfaceWaterAvailable: 0,
    groundwaterAvailable: 0,
    iwue: 0,
    waterProductivityKgM3: 0,
    benefitYuanPerM3: 0,
    irrigationReliability: 0,
    fieldEfficiency: 0,
    surfaceWaterUtilization: 0,
    groundwaterUtilization: 0,
    groundwaterDependency: 0,
    minArea: 0,
    maxArea: 1,
    sortOrder: 0,
    status: '0',
    remark: ''
  }
}

function resetForm() {
  Object.assign(form, defaultForm())
}

function normalizeForm() {
  if (!form.minArea && form.landArea) form.minArea = Number((form.landArea * 0.75).toFixed(4))
  if (!form.maxArea && form.landArea) form.maxArea = form.landArea
}

function getList() {
  loading.value = true
  listZone(queryParams.value).then(response => {
    dataList.value = response.rows
    total.value = response.total
  }).finally(() => {
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
    irrigationAreaCode: DEFAULT_AREA_CODE,
    zoneId: undefined,
    zoneName: undefined,
    status: undefined
  }
  handleQuery()
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => `${item.irrigationAreaCode || DEFAULT_AREA_CODE}:${item.zoneId}`)
  multiple.value = !selection.length
}

function handleAdd() {
  resetForm()
  isEdit.value = false
  dialogTitle.value = '新增分区'
  formOpen.value = true
}

function handleUpdate(row) {
  resetForm()
  isEdit.value = true
  dialogTitle.value = '修改分区'
  Object.assign(form, {
    irrigationAreaCode: row.irrigationAreaCode || DEFAULT_AREA_CODE,
    irrigationAreaName: row.irrigationAreaName || DEFAULT_AREA_NAME,
    zoneId: row.zoneId,
    zoneName: row.zoneName,
    landArea: Number(row.landArea ?? 1),
    surfaceWaterAvailable: Number(row.surfaceWaterAvailable ?? 0),
    groundwaterAvailable: Number(row.groundwaterAvailable ?? 0),
    iwue: Number(row.iwue ?? 0),
    waterProductivityKgM3: Number(row.waterProductivityKgM3 ?? 0),
    benefitYuanPerM3: Number(row.benefitYuanPerM3 ?? 0),
    irrigationReliability: Number(row.irrigationReliability ?? 0),
    fieldEfficiency: Number(row.fieldEfficiency ?? 0),
    surfaceWaterUtilization: Number(row.surfaceWaterUtilization ?? 0),
    groundwaterUtilization: Number(row.groundwaterUtilization ?? 0),
    groundwaterDependency: Number(row.groundwaterDependency ?? 0),
    minArea: Number(row.minArea ?? 0),
    maxArea: Number(row.maxArea ?? row.landArea ?? 1),
    sortOrder: Number(row.sortOrder ?? 0),
    status: row.status || '0',
    remark: row.remark || ''
  })
  formOpen.value = true
}

function submitForm() {
  normalizeForm()
  if (form.maxArea < form.minArea) {
    ElMessage.error('最大面积不能小于最小面积')
    return
  }
  formRef.value?.validate((valid) => {
    if (!valid) return
    formLoading.value = true
    const action = isEdit.value ? updateZone({ ...form }) : createZone({ ...form })
    action.then(() => {
      ElMessage.success(isEdit.value ? '修改成功' : '新增成功')
      formOpen.value = false
      getList()
    }).finally(() => {
      formLoading.value = false
    })
  })
}

function handleDelete(row) {
  const target = row ? [`${row.irrigationAreaCode || DEFAULT_AREA_CODE}:${row.zoneId}`] : ids.value
  if (!target.length) return
  ElMessageBox.confirm(`是否确认删除分区 ${target.join(', ')} ？`).then(() => {
    return deleteZone(target.join(','))
  }).then(() => {
    ElMessage.success('删除成功')
    getList()
  }).catch(() => {})
}

function openImportDialog() {
  importFile.value = null
  importOpen.value = true
}

function handleImportFileChange(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (ext !== 'csv') {
    ElMessage.error('仅支持 .csv 文件')
    importElRef.value?.clearFiles()
    return
  }
  importFile.value = file.raw
}

function handleImportFileRemove() {
  importFile.value = null
}

function submitImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择 CSV 文件')
    return
  }
  importLoading.value = true
  importZoneCSV(importFile.value).then(response => {
    const result = response?.data || response?.result
    const msg = result ? `导入完成：新增 ${result.inserted} 条，更新 ${result.updated} 条` : '导入成功'
    ElMessage.success(msg)
    importOpen.value = false
    getList()
  }).finally(() => {
    importLoading.value = false
  })
}

onMounted(() => {
  listIrrigationAreas().then(response => {
    const rows = Array.isArray(response?.data) ? response.data : response
    if (Array.isArray(rows) && rows.length) irrigationAreas.value = rows
  }).finally(() => {
    getList()
  })
})
</script>
