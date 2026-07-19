<template>
  <div class="app-container agri-page irrigation-page">
    <section class="agri-page__hero">
      <div>
        <span class="agri-page__eyebrow">IRRIGATION DECISION MODEL</span>
        <h1 class="agri-page__title">灌溉决策预测</h1>
        <p class="agri-page__desc">
          上传气象栅格文件并调用灌溉决策接口，生成灌溉量与土壤含水量时序结果，支持地图叠加、日期切换和播放。
        </p>
        <div class="agri-page__siblings">
          <router-link to="/model/canal/optimize" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系配水优化</span>
          </router-link>
          <router-link to="/model/canal/kinematic" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系水动力学</span>
          </router-link>
          <router-link to="/model/water-fertilizer" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>水肥调控</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span>模型推演</span>
        <span>栅格结果</span>
        <span>地图播放</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <el-col :xs="24" :lg="9">
        <el-card shadow="hover" class="main-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">灌溉决策预测</div>
                <div class="card-desc">一次性上传固定命名格式的 105 个气象 TIF 文件，调用后端灌溉决策接口生成灌溉量与土壤含水量结果。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'">
                {{ resultError ? '接口异常' : result ? '后端接口已接通' : '待提交预测' }}
              </el-tag>
            </div>
          </template>

          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="请一次性上传 15×7=105 个气象 .tif/.tiff 文件，文件名必须符合 IRRAD_YYYYMMDD.tif、TMAX_YYYYMMDD.tif 等固定格式；observed_sm 为可选。"
            class="mb16"
          />

          <el-form ref="formRef" :model="form" label-width="130px" class="irrigation-form">
            <el-form-item label="接口 API Key" required>
              <el-input
                v-model="form.apiKey"
                type="password"
                show-password
                clearable
                placeholder="请输入 X-Irrigation-Api-Key"
              />
            </el-form-item>

            <el-form-item label="预测起始日期" required>
              <el-date-picker
                v-model="form.startDate"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择起始日期"
                style="width: 100%"
              />
            </el-form-item>

            <el-row :gutter="16">
              <el-col :xs="24" :md="12">
                <el-form-item label="初始土壤含水量">
                  <el-input-number v-model="form.initialSm" :min="0" :max="1" :step="0.01" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="土壤水分阈值">
                  <el-input-number v-model="form.smThreshold" :min="0" :max="1" :step="0.01" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">气象栅格文件</el-divider>

            <div class="upload-item weather-upload">
              <div class="upload-title">
                <span>气象文件 weather_files</span>
                <el-tag :type="hasEnoughWeatherFiles() ? 'success' : 'warning'" size="small">
                  {{ form.files.weather_files.length }}/105
                </el-tag>
              </div>
              <el-upload
                :auto-upload="false"
                :show-file-list="false"
                multiple
                accept=".tif,.tiff"
                :file-list="[]"
                :on-exceed="() => proxy.$modal.msgWarning('重新选择文件会覆盖当前已选内容')"
                :on-change="(_uploadFile, uploadFiles) => handleWeatherFileChange(uploadFiles)"
                :on-remove="(_uploadFile, uploadFiles) => handleWeatherFileChange(uploadFiles)"
              >
                <el-button plain type="primary">选择气象文件</el-button>
              </el-upload>
              <div class="upload-hint">需一次性上传 105 个气象文件，文件名需为 IRRAD/TMAX/TMIN/VAP/WIND/RAIN/ET0_YYYYMMDD.tif</div>
              <div class="file-summary" :class="{ invalid: !hasEnoughWeatherFiles() && form.files.weather_files.length > 0 }">
                {{ getWeatherFileSummary() }}
              </div>
            </div>

            <el-divider content-position="left">可选输入</el-divider>

            <div class="upload-item optional-upload">
              <div class="upload-title">
                <span>实测土壤含水量 observed_sm</span>
                <el-tag :type="hasEnoughFiles('observed_sm', true) ? 'success' : 'info'" size="small">
                  {{ form.files.observed_sm.length }}/15（可选）
                </el-tag>
              </div>
              <el-upload
                :auto-upload="false"
                :show-file-list="false"
                multiple
                accept=".tif,.tiff"
                :file-list="[]"
                :on-exceed="() => proxy.$modal.msgWarning('重新选择文件会覆盖当前已选内容')"
                :on-change="(_uploadFile, uploadFiles) => handleObservedSmFileChange(uploadFiles)"
                :on-remove="(_uploadFile, uploadFiles) => handleObservedSmFileChange(uploadFiles)"
              >
                <el-button plain>选择文件</el-button>
              </el-upload>
              <div class="upload-hint">可不上传；若上传则建议提供 15 个文件。</div>
              <div class="file-summary" :class="{ invalid: !hasEnoughFiles('observed_sm', true) && form.files.observed_sm.length > 0 }">
                {{ getFileSummary('observed_sm', true) }}
              </div>
            </div>

            <div class="action-row">
              <el-button type="primary" :loading="submitting" @click="submitPrediction">开始预测</el-button>
              <el-button @click="resetFormState">重置表单</el-button>
            </div>
          </el-form>

          <el-divider content-position="left">接口说明</el-divider>

          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="接口地址">/api/v1/irrigation/predict</el-descriptions-item>
            <el-descriptions-item label="请求方式">POST / multipart-form-data</el-descriptions-item>
            <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="15">
        <el-card shadow="hover" class="map-card result-map-card">
          <template #header>
            <div class="map-header">
              <span class="card-title">结果地图</span>
              <div v-if="result && zipIndex" class="map-header-info">
                <el-tag v-if="currentLayer" type="primary" size="small">
                  {{ currentLayer.filename }}
                </el-tag>
              </div>
            </div>
          </template>

          <div class="map-wrapper result-map-wrapper">
            <IrrigationMap
              ref="mapRef"
              :image-url="mapImageUrl"
              :bounds="mapBounds"
              :opacity="overlayOpacity"
            />
            <div v-if="!result || resultError" class="map-placeholder-overlay">
              <div class="map-placeholder-card">
                <div class="map-placeholder-title">结果地图</div>
                <div class="map-placeholder-desc">
                  默认展示底图；提交预测后会在这里叠加灌溉量或土壤含水量栅格结果。
                </div>
              </div>
            </div>

            <div class="map-control-panel">
              <div class="map-panel-title">展示选项</div>

              <div v-if="result" class="map-panel-content result-section compact-result-section">
                <div class="result-brief">
                  <span>{{ selectedDate || result.start_date || form.startDate || '-' }}</span>
                  <span>{{ currentLayerTypeLabel }}</span>
                </div>

                <div v-if="zipParsing" class="parse-status compact-status">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>正在解析 ZIP...</span>
                </div>

                <div v-else-if="resultError" class="parse-status error compact-status">
                  <el-icon><WarningFilled /></el-icon>
                  <span>{{ resultError }}</span>
                </div>

                <div v-else-if="zipIndex" class="layer-controls compact-layer-controls">
                  <el-form label-width="80px" label-position="top" size="small" class="overlay-form compact-overlay-form">
                    <el-form-item label="日期">
                      <el-select v-model="selectedDate" placeholder="选择日期" style="width: 100%">
                        <el-option v-for="d in zipIndex.dates" :key="d" :label="d" :value="d" />
                      </el-select>
                    </el-form-item>

                    <el-form-item label="图层">
                      <el-radio-group v-model="selectedLayerType" size="small" class="overlay-radio-group">
                        <el-radio-button value="irrigation">灌溉量</el-radio-button>
                        <el-radio-button value="soil_moisture">土壤含水量</el-radio-button>
                      </el-radio-group>
                    </el-form-item>

                    <el-form-item label="透明度">
                      <el-slider v-model="overlayOpacity" :min="0" :max="1" :step="0.05" :show-tooltip="true" />
                    </el-form-item>
                  </el-form>

                  <!-- 播放控制 -->
                  <div class="playback-controls">
                    <div class="playback-header">
                      <span class="playback-title">时间序列播放</span>
                      <el-tag v-if="zipIndex && zipIndex.dates.length" size="small" type="info">
                        {{ zipIndex.dates.length }} 天
                      </el-tag>
                    </div>
                    <div class="playback-row">
                      <el-button
                        :type="isPlaying ? 'warning' : 'primary'"
                        size="small"
                        circle
                        @click="togglePlayback"
                      >
                        <el-icon><VideoPause v-if="isPlaying" /><VideoPlay v-else /></el-icon>
                      </el-button>
                      <el-button size="small" circle :disabled="!zipIndex" @click="stopPlayback">
                        <el-icon><RefreshRight /></el-icon>
                      </el-button>
                      <el-select v-model="playbackSpeed" size="small" style="width: 80px" :disabled="!zipIndex">
                        <el-option :value="1" label="1x" />
                        <el-option :value="2" label="2x" />
                        <el-option :value="4" label="4x" />
                      </el-select>
                    </div>
                    <div class="playback-progress">
                      <span class="playback-day-label">{{ currentDateLabel }}</span>
                      <el-slider
                        v-model="playbackFrame"
                        :min="0"
                        :max="playbackMaxFrame"
                        :show-tooltip="false"
                        :disabled="!zipIndex"
                        @change="seekToFrame"
                      />
                      <div class="playback-day-info">
                        <span>{{ playbackFrame + 1 }}</span>
                        <span>/</span>
                        <span>{{ zipIndex ? zipIndex.dates.length : 0 }}</span>
                      </div>
                    </div>
                  </div>

                  <div v-if="layerLoading" class="parse-status compact-status">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    <span>正在解析图层...</span>
                  </div>

                  <div v-else-if="layerError" class="parse-status error compact-status">
                    <el-icon><WarningFilled /></el-icon>
                    <span>{{ layerError }}</span>
                  </div>

                  <div v-else-if="currentLayer" class="legend-section overlay-legend compact-legend">
                    <div class="legend-range">
                      <span>{{ currentLayer.min?.toFixed(3) }}</span>
                      <span>{{ currentLayer.max?.toFixed(3) }}</span>
                    </div>
                    <div class="legend-bar">
                      <div
                        v-for="(stop, index) in currentLayer.legend"
                        :key="index"
                        class="legend-stop"
                        :style="{ background: stop.color }"
                        :title="`${stop.value}`"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="map-panel-content map-panel-empty">
                <div class="map-panel-empty-text">提交预测后在此切换日期、图层与透明度。</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { getCurrentInstance, reactive, ref, computed, watch, onUnmounted } from 'vue'
import { Loading, WarningFilled, VideoPlay, VideoPause, RefreshRight, Promotion } from '@element-plus/icons-vue'
import { predictIrrigation } from '@/api/model/irrigation'
import { createIrrigationZipIndex, decodeIrrigationLayer, getAvailableLayerTypes } from '@/utils/irrigationZip'
import IrrigationMap from '@/components/IrrigationMap.vue'

defineOptions({
  name: 'IrrigationPredict'
})

const { proxy } = getCurrentInstance()
const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'
const DEFAULT_START_DATE = '2023-05-31'
const REQUIRED_WEATHER_PREFIXES = ['IRRAD', 'TMAX', 'TMIN', 'VAP', 'WIND', 'RAIN', 'ET0']
const REQUIRED_WEATHER_FILE_COUNT = 105
const REQUIRED_FILES_PER_PREFIX = 15

function createEmptyFiles() {
  return {
    weather_files: [],
    observed_sm: []
  }
}

const formRef = ref()
const submitting = ref(false)
const result = ref(null)
const resultError = ref('')
const zipIndex = ref(null)
const zipParsing = ref(false)
const selectedDate = ref('')
const selectedLayerType = ref('irrigation')
const overlayOpacity = ref(0.7)
const currentLayer = ref(null)
const layerLoading = ref(false)
const layerError = ref('')
const mapImageUrl = ref('')
const mapBounds = ref(null)
const layerCache = new Map()
const mapRef = ref(null)

// 播放控制
const isPlaying = ref(false)
const playbackFrame = ref(0)
const playbackSpeed = ref(1)
let playbackTimer = null

const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  startDate: DEFAULT_START_DATE,
  initialSm: 0.29,
  smThreshold: 0.32,
  files: createEmptyFiles()
})

const currentLayerTypeLabel = computed(() => {
  if (selectedLayerType.value === 'soil_moisture') {
    return '土壤含水量'
  }
  return '灌溉量'
})

const playbackMaxFrame = computed(() => {
  return zipIndex.value ? zipIndex.value.dates.length - 1 : 0
})

const currentDateLabel = computed(() => {
  if (!zipIndex.value || !zipIndex.value.dates.length) return ''
  return zipIndex.value.dates[playbackFrame.value] || ''
})

function startPlayback() {
  if (!zipIndex.value || !zipIndex.value.dates.length) return
  isPlaying.value = true
  scheduleNextFrame()
}

function scheduleNextFrame() {
  clearTimeout(playbackTimer)
  if (!isPlaying.value) return
  playbackTimer = setTimeout(() => {
    const nextFrame = playbackFrame.value + 1
    if (nextFrame > playbackMaxFrame.value) {
      playbackFrame.value = 0
    } else {
      playbackFrame.value = nextFrame
    }
    const date = zipIndex.value.dates[playbackFrame.value]
    if (date) {
      selectedDate.value = date
    }
    scheduleNextFrame()
  }, 1500 / playbackSpeed.value)
}

function stopPlayback() {
  clearTimeout(playbackTimer)
  isPlaying.value = false
  playbackFrame.value = 0
}

function togglePlayback() {
  if (isPlaying.value) {
    stopPlayback()
  } else {
    startPlayback()
  }
}

function seekToFrame(frame) {
  if (!zipIndex.value) return
  playbackFrame.value = frame
  const date = zipIndex.value.dates[frame]
  if (date) {
    selectedDate.value = date
  }
}

function normalizeFiles(uploadFiles) {
  return uploadFiles
    .map(item => item.raw)
    .filter(Boolean)
    .filter(file => /\.(tif|tiff)$/i.test(file.name))
}

function isValidWeatherFilename(filename) {
  const match = filename.match(/^([A-Za-z0-9]+)_(\d{8})\.(tif|tiff)$/i)
  if (!match) {
    return false
  }
  return REQUIRED_WEATHER_PREFIXES.includes(match[1].toUpperCase())
}

function getInvalidWeatherFilenames(files) {
  return files.filter(file => !isValidWeatherFilename(file.name)).map(file => file.name)
}

function getWeatherPrefixCounts(files) {
  const counts = Object.fromEntries(REQUIRED_WEATHER_PREFIXES.map(prefix => [prefix, 0]))
  for (const file of files) {
    const match = file.name.match(/^([A-Za-z0-9]+)_(\d{8})\.(tif|tiff)$/i)
    if (!match) {
      continue
    }
    const prefix = match[1].toUpperCase()
    if (prefix in counts) {
      counts[prefix] += 1
    }
  }
  return counts
}

function getWeatherPrefixIssues(files) {
  const counts = getWeatherPrefixCounts(files)
  return REQUIRED_WEATHER_PREFIXES.flatMap(prefix => {
    const count = counts[prefix] || 0
    if (count === REQUIRED_FILES_PER_PREFIX) {
      return []
    }
    if (count < REQUIRED_FILES_PER_PREFIX) {
      return `${prefix} 缺少 ${REQUIRED_FILES_PER_PREFIX - count} 个`
    }
    return `${prefix} 多了 ${count - REQUIRED_FILES_PER_PREFIX} 个`
  })
}

function handleWeatherFileChange(uploadFiles) {
  const files = normalizeFiles(uploadFiles)
  if (files.length !== uploadFiles.length) {
    proxy.$modal.msgWarning('仅支持上传 .tif 或 .tiff 文件')
  }
  form.files.weather_files = files
}

function handleObservedSmFileChange(uploadFiles) {
  const files = normalizeFiles(uploadFiles)
  if (files.length !== uploadFiles.length) {
    proxy.$modal.msgWarning('仅支持上传 .tif 或 .tiff 文件')
  }
  form.files.observed_sm = files
}

function hasEnoughWeatherFiles() {
  return form.files.weather_files.length === REQUIRED_WEATHER_FILE_COUNT
}

function hasEnoughFiles(fieldKey, optional) {
  const count = form.files[fieldKey].length
  if (optional) {
    return count === 0 || count === 15
  }
  return count === 15
}

function getWeatherFileSummary() {
  const count = form.files.weather_files.length
  if (count === 0) {
    return '尚未选择气象文件'
  }
  const issues = getWeatherPrefixIssues(form.files.weather_files)
  if (issues.length) {
    return `已选择 ${count} 个文件；${issues.join('，')}`
  }
  return '已选择 105 个气象文件，且 7 类文件各 15 个'
}

function getFileSummary(fieldKey, optional) {
  const count = form.files[fieldKey].length
  if (count === 0) {
    return optional ? '未上传' : '尚未选择文件'
  }
  if (optional) {
    return count === 15 ? '已选择 15 个文件' : `已选择 ${count} 个文件，建议补齐到 15 个`
  }
  return count === 15 ? '已选择 15 个文件' : `已选择 ${count} 个文件，还需 ${15 - count} 个`
}

function validateForm() {
  if (!form.apiKey.trim()) {
    proxy.$modal.msgError('请输入接口 API Key')
    return false
  }
  if (!form.startDate) {
    proxy.$modal.msgError('请选择预测起始日期')
    return false
  }
  if (!hasEnoughWeatherFiles()) {
    proxy.$modal.msgError(`气象文件需要恰好上传 ${REQUIRED_WEATHER_FILE_COUNT} 个`)
    return false
  }
  const invalidWeatherNames = getInvalidWeatherFilenames(form.files.weather_files)
  if (invalidWeatherNames.length) {
    proxy.$modal.msgError('气象文件存在无效文件名，请使用 IRRAD/TMAX/TMIN/VAP/WIND/RAIN/ET0_YYYYMMDD.tif 格式')
    return false
  }
  const weatherPrefixIssues = getWeatherPrefixIssues(form.files.weather_files)
  if (weatherPrefixIssues.length) {
    proxy.$modal.msgError(`气象文件分类数量不正确：${weatherPrefixIssues.join('，')}`)
    return false
  }
  if (!hasEnoughFiles('observed_sm', true)) {
    proxy.$modal.msgError('observed_sm 若上传，则需要提供 15 个文件')
    return false
  }
  const invalidObservedNames = getInvalidWeatherFilenames(form.files.observed_sm)
  if (invalidObservedNames.length) {
    proxy.$modal.msgError('observed_sm 存在无效文件名，请使用 *_YYYYMMDD.tif 格式')
    return false
  }
  return true
}

function buildFormData() {
  const formData = new FormData()
  formData.append('start_date', form.startDate)
  formData.append('initial_sm', String(form.initialSm))
  formData.append('sm_threshold', String(form.smThreshold))

  form.files.weather_files.forEach(file => {
    formData.append('weather_files', file)
  })

  form.files.observed_sm.forEach(file => {
    formData.append('observed_sm', file)
  })

  return formData
}

async function loadLayer(date, type) {
  if (!zipIndex.value) {
    return
  }

  layerLoading.value = true
  layerError.value = ''

  try {
    const layer = await decodeIrrigationLayer(zipIndex.value, date, type, layerCache)
    currentLayer.value = layer
    mapImageUrl.value = layer.imageUrl
    mapBounds.value = layer.bounds
  } catch (error) {
    layerError.value = error.message || '图层解析失败'
    currentLayer.value = null
    mapImageUrl.value = ''
    mapBounds.value = null
  } finally {
    layerLoading.value = false
  }
}

async function submitPrediction() {
  if (!validateForm()) {
    return
  }

  result.value = null
  resultError.value = ''
  zipIndex.value = null
  zipParsing.value = false
  currentLayer.value = null
  layerError.value = ''
  mapImageUrl.value = ''
  mapBounds.value = null
  selectedDate.value = ''
  selectedLayerType.value = 'irrigation'
  layerCache.clear()
  stopPlayback()

  submitting.value = true
  try {
    const { blob } = await predictIrrigation(buildFormData(), form.apiKey.trim())

    zipParsing.value = true
    const index = await createIrrigationZipIndex(blob)

    if (!index.dates.length) {
      throw new Error('ZIP 文件中未找到任何有效的灌溉或土壤含水量栅格结果')
    }

    zipIndex.value = index

    const availableTypes = getAvailableLayerTypes(index, index.dates[0])
    if (!availableTypes.includes(selectedLayerType.value)) {
      selectedLayerType.value = availableTypes[0] || 'irrigation'
    }

    selectedDate.value = index.dates[0]

    result.value = { start_date: form.startDate }
    proxy.$modal.msgSuccess('预测完成，结果已加载到地图')
  } catch (error) {
    resultError.value = error.message || '预测请求失败'
  } finally {
    submitting.value = false
    zipParsing.value = false
  }
}

function resetFormState() {
  stopPlayback()
  form.apiKey = DEFAULT_IRRIGATION_API_KEY
  form.startDate = DEFAULT_START_DATE
  form.initialSm = 0.29
  form.smThreshold = 0.32
  form.files = createEmptyFiles()
  result.value = null
  resultError.value = ''
  zipIndex.value = null
  zipParsing.value = false
  currentLayer.value = null
  layerError.value = ''
  mapImageUrl.value = ''
  mapBounds.value = null
  selectedDate.value = ''
  selectedLayerType.value = 'irrigation'
  overlayOpacity.value = 0.7
  layerCache.clear()
}

watch([selectedDate, selectedLayerType], ([newDate, newType]) => {
  if (newDate && newType && zipIndex.value) {
    loadLayer(newDate, newType)
  }
})

onUnmounted(() => {
  clearTimeout(playbackTimer)
})
</script>

<style scoped>
.irrigation-page {
  padding-bottom: 28px;
}

.agri-page__siblings {
  display: flex;
  gap: 12px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.sibling-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--surface-soft-bg);
  border: 1px solid var(--hairline-color);
  color: var(--text-primary);
  font-size: 13px;
  text-decoration: none;
  transition: all 0.2s ease;
}

.sibling-link:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
  color: var(--el-color-primary);
}

.page-layout {
  align-items: stretch;
}

.main-card,
.map-card {
  border-radius: 24px;
  border: 1px solid var(--hairline-color);
  box-shadow: var(--content-shadow-soft);
  overflow: hidden;
}

.result-map-card {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 650;
  color: var(--text-primary);
}

.card-desc {
  margin-top: 6px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.mb16 {
  margin-bottom: 16px;
}

.upload-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.upload-item {
  padding: 18px;
  border: 1px solid var(--hairline-color);
  border-radius: 18px;
  background: var(--surface-soft-bg);
}

.upload-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--text-primary);
  font-weight: 650;
}

.upload-hint {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.file-summary {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-color-success);
  word-break: break-all;
}

.file-summary.invalid {
  color: var(--el-color-warning);
}

.optional-upload {
  margin-bottom: 20px;
}

.action-row {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.parse-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 14px;
  background: var(--surface-soft-bg);
  font-size: 14px;
  color: var(--text-secondary);
}

.parse-status.error {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.layer-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.current-filename {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  word-break: break-all;
}

.legend-section {
  padding: 12px;
  border-radius: 14px;
  background: var(--surface-bg);
  border: 1px solid var(--hairline-soft-color);
}

.legend-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.legend-range {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

.legend-bar {
  display: flex;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
}

.legend-stop {
  flex: 1;
}

.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.map-header-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 18px;
  overflow: hidden;
}

.map-control-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1000;
  width: min(280px, calc(100% - 24px));
  max-height: calc(100% - 24px);
  display: flex;
  flex-direction: column;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(6px);
  overflow: hidden;
}

.map-panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.map-panel-content {
  margin-top: 8px;
  min-height: 0;
  overflow: auto;
}

.compact-result-section {
  gap: 10px;
}

.playback-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-radius: 14px;
  background: var(--surface-soft-bg);
  border: 1px solid var(--hairline-soft-color);
}

.playback-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.playback-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.playback-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.playback-progress {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.playback-day-label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.playback-day-info {
  display: flex;
  justify-content: center;
  gap: 4px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.result-brief {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.compact-layer-controls {
  gap: 10px;
}

.compact-overlay-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.compact-overlay-form :deep(.el-form-item__label) {
  padding-bottom: 2px;
  font-size: 12px;
}

.compact-status {
  padding: 8px 10px;
  font-size: 12px;
}

.compact-legend {
  padding: 8px 10px;
}

.map-panel-empty {
  display: flex;
  align-items: center;
}

.map-panel-empty-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-regular);
}

.overlay-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.overlay-radio-group {
  display: flex;
  flex-wrap: wrap;
}

.overlay-descriptions,
.overlay-legend {
  background: rgba(255, 255, 255, 0.72);
}

.map-placeholder-overlay {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 392px;
  display: flex;
  justify-content: flex-start;
  pointer-events: none;
  z-index: 10;
}

.map-placeholder-card {
  max-width: 360px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(8px);
}

.map-placeholder-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.map-placeholder-desc {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.map-card :deep(.el-card__body) {
  padding: 0;
  height: 100%;
}

@media (max-width: 992px) {
  .upload-grid {
    grid-template-columns: 1fr;
  }

  .card-header {
    flex-direction: column;
  }

  .result-map-wrapper {
    height: 560px;
    min-height: 560px;
  }

  .map-control-panel {
    top: auto;
    right: 12px;
    bottom: 12px;
    left: auto;
    width: min(260px, calc(100% - 24px));
    max-height: 50%;
    padding: 10px;
  }

  .map-placeholder-overlay {
    top: 12px;
    left: 12px;
    right: 12px;
  }

  .map-placeholder-card {
    max-width: none;
  }
}
</style>
