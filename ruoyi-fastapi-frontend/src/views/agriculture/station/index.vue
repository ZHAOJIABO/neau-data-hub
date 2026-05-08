<template>
  <div class="app-container">
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch">
      <el-form-item label="站点编码" prop="stcd">
        <el-input v-model="queryParams.stcd" placeholder="请输入站点编码" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="站点名称" prop="name">
        <el-input v-model="queryParams.name" placeholder="请输入站点名称" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Plus" @click="handleAdd" v-hasPermi="['agriculture:station:add']">新增</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="success" plain icon="Edit" :disabled="single" @click="handleUpdate" v-hasPermi="['agriculture:station:edit']">修改</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete" v-hasPermi="['agriculture:station:remove']">删除</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
    </el-row>

    <el-table v-loading="loading" :data="dataList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="ID" prop="id" width="60" />
      <el-table-column label="站点编码" prop="stcd" width="100" />
      <el-table-column label="站点名称" prop="name" width="140" />
      <el-table-column label="纬度" prop="latitude" width="100" />
      <el-table-column label="经度" prop="longitude" width="100" />
      <el-table-column label="海拔(m)" prop="altitude" width="100" />
      <el-table-column label="描述" prop="description" />
      <el-table-column label="操作" width="150" align="center">
        <template #default="scope">
          <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)" v-hasPermi="['agriculture:station:edit']">修改</el-button>
          <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)" v-hasPermi="['agriculture:station:remove']">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="queryParams.pageNum"
      v-model:limit="queryParams.pageSize"
      @pagination="getList"
    />

    <!-- 添加/编辑对话框 -->
    <el-dialog :title="title" v-model="open" width="500px" append-to-body>
      <el-form ref="stationRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="站点编码" prop="stcd">
          <el-input v-model="form.stcd" placeholder="请输入站点编码" />
        </el-form-item>
        <el-form-item label="站点名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入站点名称" />
        </el-form-item>
        <el-form-item label="纬度" prop="latitude">
          <el-input v-model="form.latitude" placeholder="请输入纬度" />
        </el-form-item>
        <el-form-item label="经度" prop="longitude">
          <el-input v-model="form.longitude" placeholder="请输入经度" />
        </el-form-item>
        <el-form-item label="海拔" prop="altitude">
          <el-input v-model="form.altitude" placeholder="请输入海拔(m)" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { listStation, getStation, addStation, updateStation, delStation } from '@/api/agriculture/station'
import { ElMessageBox, ElMessage } from 'element-plus'

const loading = ref(false)
const showSearch = ref(true)
const dataList = ref([])
const total = ref(0)
const ids = ref([])
const single = ref(true)
const multiple = ref(true)
const open = ref(false)
const title = ref('')
const stationRef = ref(null)

const queryParams = ref({
  pageNum: 1,
  pageSize: 10,
  stcd: undefined,
  name: undefined
})

const form = ref({})
const rules = reactive({
  stcd: [{ required: true, message: '站点编码不能为空', trigger: 'blur' }],
  name: [{ required: true, message: '站点名称不能为空', trigger: 'blur' }]
})

function getList() {
  loading.value = true
  listStation(queryParams.value).then(response => {
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
  queryParams.value = { pageNum: 1, pageSize: 10, stcd: undefined, name: undefined }
  handleQuery()
}

function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id)
  single.value = selection.length !== 1
  multiple.value = !selection.length
}

function reset() {
  form.value = { id: undefined, stcd: undefined, name: undefined, latitude: undefined, longitude: undefined, altitude: undefined, description: undefined }
}

function handleAdd() {
  reset()
  open.value = true
  title.value = '新增站点'
}

function handleUpdate(row) {
  reset()
  const id = row.id || ids.value[0]
  getStation(id).then(response => {
    form.value = response.data
    open.value = true
    title.value = '修改站点'
  })
}

function submitForm() {
  stationRef.value.validate(valid => {
    if (valid) {
      if (form.value.id) {
        updateStation(form.value).then(() => {
          ElMessage.success('修改成功')
          open.value = false
          getList()
        })
      } else {
        addStation(form.value).then(() => {
          ElMessage.success('新增成功')
          open.value = false
          getList()
        })
      }
    }
  })
}

function cancel() {
  open.value = false
  reset()
}

function handleDelete(row) {
  const deleteIds = row.id ? [row.id] : ids.value
  ElMessageBox.confirm('是否确认删除选中的站点？').then(() => {
    return delStation(deleteIds.join(','))
  }).then(() => {
    getList()
    ElMessage.success('删除成功')
  }).catch(() => {})
}

onMounted(() => {
  getList()
})
</script>
