<template>
  <div class="app-container agri-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">CANAL DATA</span>
        <h1 class="agri-page__title">渠系数据</h1>
        <p class="agri-page__desc">管理多级渠系的基础参数、闸门尺寸与需水量；支持新增、修改、删除、CSV 导入；为渠系配水与水动力学模型提供只读数据源。</p>
      </div>
      <div class="agri-page__tags">
        <span>干/支/斗/农</span>
        <span>闸门参数</span>
        <span>CSV 导入</span>
      </div>
    </section>

    <div class="agri-toolbar">
      <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
        <el-form-item label="渠段编号" prop="canalId">
          <el-input v-model="queryParams.canalId" placeholder="如 1 / 1-1 / 1-1-1" clearable style="width: 200px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="渠段名称" prop="canalName">
          <el-input v-model="queryParams.canalName" placeholder="名称关键字" clearable style="width: 200px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="级别" prop="level">
          <el-select v-model="queryParams.level" placeholder="全部" clearable style="width: 180px">
            <el-option label="1 干渠" value="1" />
            <el-option label="2 支渠" value="2" />
            <el-option label="3 斗渠" value="3" />
            <el-option label="4 农渠" value="4" />
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
        <el-table-column label="渠段编号" prop="canalId" min-width="120" show-overflow-tooltip />
        <el-table-column label="名称" prop="canalName" min-width="180" show-overflow-tooltip />
        <el-table-column label="级别" prop="level" min-width="180" show-overflow-tooltip />
        <el-table-column label="长度 m" prop="length" min-width="100" align="right" />
        <el-table-column label="设计流量 m³/s" prop="designFlow" min-width="120" align="right" />
        <el-table-column label="设计水深 m" prop="designDepth" min-width="110" align="right" />
        <el-table-column label="闸门" min-width="100" align="center">
          <template #default="scope">
            <el-tag :type="(scope.row.gateHeight && scope.row.gateWidth) ? 'success' : 'info'" size="small">
              {{ (scope.row.gateHeight && scope.row.gateWidth) ? '有闸' : '无闸' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="需水量 m³" prop="waterDemand" min-width="130" align="right" />
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

    <!-- 新增 / 修改对话框 -->
    <el-dialog
      :title="dialogTitle"
      v-model="formOpen"
      width="780px"
      append-to-body
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="140px">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="渠段编号" prop="canalId">
              <el-input v-model="form.canalId" placeholder="如 1 / 1-1 / 1-1-1" :disabled="isEdit" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="渠段名称" prop="canalName">
              <el-input v-model="form.canalName" placeholder="如 Main Canal" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="级别" prop="level">
              <el-select v-model="form.level" placeholder="选择级别" clearable style="width: 100%">
                <el-option label="1 干渠" value="1" />
                <el-option label="2 支渠" value="2" />
                <el-option label="3 斗渠" value="3" />
                <el-option label="4 农渠" value="4" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="长度 (m)" prop="length">
              <el-input-number v-model="form.length" :min="0" :precision="3" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设计流量 (m³/s)" prop="designFlow">
              <el-input-number v-model="form.designFlow" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设计水深 (m)" prop="designDepth">
              <el-input-number v-model="form.designDepth" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设计渠顶宽 (m)" prop="topWidth">
              <el-input-number v-model="form.topWidth" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设计渠底宽 (m)" prop="bottomWidth">
              <el-input-number v-model="form.bottomWidth" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="设计纵坡" prop="slope">
              <el-input-number v-model="form.slope" :min="0" :precision="10" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="边坡系数 (1:m)" prop="sideSlope">
              <el-input-number v-model="form.sideSlope" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="糙率 Manning n" prop="roughness">
              <el-input-number v-model="form.roughness" :min="0" :precision="5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="闸门高度 (m)" prop="gateHeight">
              <el-input-number v-model="form.gateHeight" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="闸门宽度 (m)" prop="gateWidth">
              <el-input-number v-model="form.gateWidth" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="最小开度 (m)" prop="minGateOpening">
              <el-input-number v-model="form.minGateOpening" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="最大开度 (m)" prop="maxGateOpening">
              <el-input-number v-model="form.maxGateOpening" :min="0" :precision="4" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="需水量 (m³)" prop="waterDemand">
              <el-input-number v-model="form.waterDemand" :min="0" :precision="4" style="width: 100%" />
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

    <!-- CSV 导入对话框 -->
    <el-dialog title="从 CSV 导入渠系数据" v-model="importOpen" width="520px" append-to-body>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="支持标准渠系 CSV 格式（包含 Channel No. / Channel Name / Length(m) / Design Flow(m³/s) 等列）。按 canal_id 唯一键 upsert，重复行会被更新。"
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
import {
  listCanal,
  createCanal,
  updateCanal,
  deleteCanal,
  importCanalCSV
} from '@/api/agriculture/canal'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const ids = ref([])
const multiple = ref(true)

const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  canalId: undefined,
  canalName: undefined,
  level: undefined
})

const formOpen = ref(false)
const formLoading = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const dialogTitle = ref('新增渠系')
const form = reactive({
  canalId: '',
  canalName: '',
  level: '',
  length: 0,
  designFlow: 0,
  designDepth: 0,
  topWidth: 0,
  bottomWidth: 0,
  slope: 0.0002,
  sideSlope: 1.5,
  roughness: 0.015,
  gateHeight: 0,
  gateWidth: 0,
  minGateOpening: 0,
  maxGateOpening: 1.0,
  waterDemand: 0
})
const formRules = reactive({
  canalId: [{ required: true, message: '请输入渠段编号', trigger: 'blur' }]
})

const importOpen = ref(false)
const importLoading = ref(false)
const importElRef = ref(null)
const importFile = ref(null)

function resetForm() {
  Object.assign(form, {
    canalId: '',
    canalName: '',
    level: '',
    length: 0,
    designFlow: 0,
    designDepth: 0,
    topWidth: 0,
    bottomWidth: 0,
    slope: 0.0002,
    sideSlope: 1.5,
    roughness: 0.015,
    gateHeight: 0,
    gateWidth: 0,
    minGateOpening: 0,
    maxGateOpening: 1.0,
    waterDemand: 0
  })
}

function getList() {
  loading.value = true
  listCanal(queryParams.value).then(response => {
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
    canalId: undefined,
    canalName: undefined,
    level: undefined
  }
  handleQuery()
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.canalId)
  multiple.value = !selection.length
}

function handleAdd() {
  resetForm()
  isEdit.value = false
  dialogTitle.value = '新增渠系'
  formOpen.value = true
}

function handleUpdate(row) {
  resetForm()
  isEdit.value = true
  dialogTitle.value = '修改渠系'
  Object.assign(form, {
    canalId: row.canalId,
    canalName: row.canalName,
    level: row.level,
    length: Number(row.length ?? 0),
    designFlow: Number(row.designFlow ?? 0),
    designDepth: Number(row.designDepth ?? 0),
    topWidth: Number(row.topWidth ?? 0),
    bottomWidth: Number(row.bottomWidth ?? 0),
    slope: Number(row.slope ?? 0.0002),
    sideSlope: Number(row.sideSlope ?? 1.5),
    roughness: Number(row.roughness ?? 0.015),
    gateHeight: Number(row.gateHeight ?? 0),
    gateWidth: Number(row.gateWidth ?? 0),
    minGateOpening: Number(row.minGateOpening ?? 0),
    maxGateOpening: Number(row.maxGateOpening ?? 1.0),
    waterDemand: Number(row.waterDemand ?? 0)
  })
  formOpen.value = true
}

function submitForm() {
  formRef.value?.validate((valid) => {
    if (!valid) return
    formLoading.value = true
    const payload = { ...form }
    const action = isEdit.value ? updateCanal(payload) : createCanal(payload)
    action.then(() => {
      ElMessage.success(isEdit.value ? '修改成功' : '新增成功')
      formOpen.value = false
      getList()
    }).catch(() => {}).finally(() => {
      formLoading.value = false
    })
  })
}

function handleDelete(row) {
  const target = row ? [row.canalId] : ids.value
  if (!target.length) return
  ElMessageBox.confirm(`是否确认删除渠段 ${target.join(', ')} ？`).then(() => {
    return deleteCanal(target.join(','))
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
  importCanalCSV(importFile.value).then(response => {
    const result = response?.data || response?.result
    const msg = result
      ? `导入完成：新增 ${result.inserted} 条，更新 ${result.updated} 条`
      : '导入成功'
    ElMessage.success(msg)
    importOpen.value = false
    getList()
  }).catch(() => {}).finally(() => {
    importLoading.value = false
  })
}

onMounted(() => {
  getList()
})
</script>
