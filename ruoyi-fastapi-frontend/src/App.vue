<template>
  <router-view />
</template>

<script setup>
import { watch } from 'vue'
import useAppStore from '@/store/modules/app'
import useSettingsStore from '@/store/modules/settings'
import { handleThemeStyle } from '@/utils/theme'

// Element Plus 三个尺寸对应的全局基准字号（同步 root + Element Plus 变量 + body 继承字号）
const SIZE_BASE_FONT = {
  small: 13,
  default: 15,
  large: 17,
}

function applyAppSize(size) {
  const base = SIZE_BASE_FONT[size] || SIZE_BASE_FONT.default
  const root = document.documentElement
  root.style.setProperty('--app-font-size', `${base}px`)
  root.style.setProperty('--el-font-size-base', `${base}px`)
  root.style.setProperty('--el-font-size-small', `${base - 1}px`)
  root.style.setProperty('--el-font-size-large', `${base + 1}px`)
  root.style.setProperty('--el-font-size-extra-large', `${base + 3}px`)
  root.style.setProperty('--el-font-size-medium', `${base + 1}px`)
  document.body.style.fontSize = `${base}px`
}

const appStore = useAppStore()
applyAppSize(appStore.size)
watch(() => appStore.size, (size) => applyAppSize(size))

onMounted(() => {
  nextTick(() => {
    // 初始化主题样式
    handleThemeStyle(useSettingsStore().theme)
  })
})
</script>
