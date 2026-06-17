<template>
  <div v-if="!item.hidden">
    <template v-if="hasOneShowingChild(item.children, item) && (!onlyOneChild.children || onlyOneChild.noShowingChildren) && !item.alwaysShow">
      <app-link v-if="onlyOneChild.meta" :to="resolvePath(onlyOneChild.path, onlyOneChild.query)">
        <el-menu-item :index="resolvePath(onlyOneChild.path)" :class="{ 'submenu-title-noDropdown': !isNest }">
          <svg-icon :icon-class="getMenuIcon(onlyOneChild.meta.icon || (item.meta && item.meta.icon), onlyOneChild.meta.title)"/>
          <template #title><span class="menu-title" :title="hasTitle(onlyOneChild.meta.title)">{{ onlyOneChild.meta.title }}</span></template>
        </el-menu-item>
      </app-link>
    </template>

    <el-sub-menu v-else ref="subMenu" :index="resolvePath(item.path)" teleported>
      <template v-if="item.meta" #title>
        <svg-icon :icon-class="getMenuIcon(item.meta && item.meta.icon, item.meta.title)" />
        <span class="menu-title" :title="hasTitle(item.meta.title)">{{ item.meta.title }}</span>
      </template>

      <sidebar-item
        v-for="(child, index) in item.children"
        :key="child.path + index"
        :is-nest="true"
        :item="child"
        :base-path="resolvePath(child.path)"
        class="nest-menu"
      />
    </el-sub-menu>
  </div>
</template>

<script setup>
import { isExternal } from '@/utils/validate'
import AppLink from './Link'
import { getNormalPath } from '@/utils/ruoyi'

const iconModules = import.meta.glob('../../../assets/icons/svg/*.svg')
const availableIcons = new Set(
  Object.keys(iconModules).map(path => path.split('/').pop().replace('.svg', ''))
)

const props = defineProps({
  // route object
  item: {
    type: Object,
    required: true
  },
  isNest: {
    type: Boolean,
    default: false
  },
  basePath: {
    type: String,
    default: ''
  }
})

const onlyOneChild = ref({});

function hasOneShowingChild(children = [], parent) {
  if (!children) {
    children = [];
  }
  const showingChildren = children.filter(item => {
    if (item.hidden) {
      return false
    }
    onlyOneChild.value = item
    return true
  })

  // When there is only one child router, the child router is displayed by default
  if (showingChildren.length === 1) {
    return true
  }

  // Show parent if there are no child router to display
  if (showingChildren.length === 0) {
    onlyOneChild.value = { ...parent, path: '', noShowingChildren: true }
    return true
  }

  return false
};

function resolvePath(routePath, routeQuery) {
  if (isExternal(routePath)) {
    return routePath
  }
  if (isExternal(props.basePath)) {
    return props.basePath
  }
  if (routeQuery) {
    let query = JSON.parse(routeQuery);
    return { path: getNormalPath(props.basePath + '/' + routePath), query: query }
  }
  return getNormalPath(props.basePath + '/' + routePath)
}

function hasTitle(title){
  if (title.length > 5) {
    return title;
  } else {
    return "";
  }
}

function getMenuIcon(icon, title) {
  const fallbackIcons = {
    '首页': 'dashboard',
    '模型平台': 'dashboard',
    '灌溉决策': 'dashboard',
    '渠系配水': 'tree-table',
    '渠系水动力学': 'monitor',
    '农业数据': 'chart',
    '数据概览': 'dashboard',
    '气象数据': 'dashboard',
    '气象综合': 'list',
    '温度数据': 'sunny',
    '湿度数据': 'monitor',
    '降水数据': 'download',
    '土壤数据': 'tree-table',
    '作物数据': 'documentation',
    '叶面积指数': 'chart',
    '站点管理': 'international',
    '渠系数据': 'tree'
  }
  if (icon && availableIcons.has(icon)) {
    return icon
  }
  return fallbackIcons[title] || 'dashboard'
}
</script>
