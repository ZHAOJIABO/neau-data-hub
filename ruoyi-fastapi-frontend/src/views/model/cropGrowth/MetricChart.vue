<template>
  <article ref="hostRef" class="metric-chart" :style="{ '--metric-color': metric.color }">
    <header class="metric-chart__header">
      <div>
        <div class="metric-chart__title">{{ metric.label }}</div>
        <div class="metric-chart__name">{{ metric.name }} · {{ metric.unit }}</div>
      </div>
      <div class="metric-chart__latest">
        <span>末值</span>
        <strong>{{ formatValue(latestValue) }}</strong>
      </div>
    </header>
    <div v-if="!isVisible" class="metric-chart__placeholder">
      <el-skeleton animated>
        <template #template>
          <el-skeleton-item variant="rect" class="metric-chart__skeleton" />
        </template>
      </el-skeleton>
    </div>
    <div v-show="isVisible" ref="chartRef" class="metric-chart__canvas" />
  </article>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  TooltipComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
  CanvasRenderer
])

const props = defineProps({
  metric: { type: Object, required: true },
  rows: { type: Array, default: () => [] }
})

const hostRef = ref(null)
const chartRef = ref(null)
const isVisible = ref(false)
let chart = null
let intersectionObserver = null
let resizeObserver = null

const values = computed(() => props.rows.map(row => row[props.metric.key] ?? null))
const latestValue = computed(() => {
  for (let index = values.value.length - 1; index >= 0; index -= 1) {
    if (values.value[index] !== null) return values.value[index]
  }
  return null
})

function formatValue(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 3 })
}

function buildOption() {
  const isBar = props.metric.type === 'bar'
  return {
    animationDuration: 700,
    animationEasing: 'cubicOut',
    grid: { left: 14, right: 16, top: 18, bottom: 42, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.94)',
      borderWidth: 0,
      textStyle: { color: '#fff' },
      valueFormatter: value => `${formatValue(value)} ${props.metric.unit}`
    },
    xAxis: {
      type: 'category',
      boundaryGap: isBar,
      data: props.rows.map(row => row.day),
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisTick: { show: false },
      axisLabel: { color: '#64748b', hideOverlap: true, fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      scale: props.metric.scale !== false,
      splitNumber: 4,
      axisLabel: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e8edf3', type: 'dashed' } }
    },
    dataZoom: [{ type: 'inside', filterMode: 'none' }],
    series: [{
      type: isBar ? 'bar' : 'line',
      data: values.value,
      smooth: !isBar,
      showSymbol: false,
      connectNulls: true,
      lineStyle: { width: 2.5, color: props.metric.color },
      itemStyle: { color: props.metric.color, borderRadius: isBar ? [3, 3, 0, 0] : 0 },
      areaStyle: props.metric.area
        ? { color: props.metric.areaColor || props.metric.color, opacity: 0.12 }
        : undefined,
      emphasis: { focus: 'series' }
    }]
  }
}

async function renderChart() {
  if (!isVisible.value) return
  await nextTick()
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(), true)
}

onMounted(() => {
  intersectionObserver = new IntersectionObserver(entries => {
    if (!entries[0]?.isIntersecting) return
    isVisible.value = true
    intersectionObserver?.disconnect()
    renderChart()
  }, { rootMargin: '180px 0px' })
  intersectionObserver.observe(hostRef.value)

  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(hostRef.value)
})

watch(() => props.rows, renderChart, { deep: false })

onBeforeUnmount(() => {
  intersectionObserver?.disconnect()
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<style scoped lang="scss">
.metric-chart {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dce4ec;
  border-top: 3px solid var(--metric-color);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
}

.metric-chart__header {
  min-height: 68px;
  padding: 13px 16px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #eef2f6;
}

.metric-chart__title {
  color: #172033;
  font-size: 15px;
  font-weight: 700;
}

.metric-chart__name,
.metric-chart__latest span {
  color: #7a8798;
  font-size: 11px;
}

.metric-chart__name {
  margin-top: 3px;
}

.metric-chart__latest {
  flex: 0 0 auto;
  text-align: right;
}

.metric-chart__latest span,
.metric-chart__latest strong {
  display: block;
}

.metric-chart__latest strong {
  margin-top: 2px;
  color: var(--metric-color);
  font-size: 17px;
}

.metric-chart__canvas,
.metric-chart__placeholder {
  width: 100%;
  height: 270px;
}

.metric-chart__placeholder {
  padding: 22px 16px;
}

.metric-chart__skeleton {
  width: 100%;
  height: 226px;
}

@media (max-width: 640px) {
  .metric-chart__canvas,
  .metric-chart__placeholder {
    height: 250px;
  }
}
</style>
