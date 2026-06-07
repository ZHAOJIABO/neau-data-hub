<template>
  <div ref="mapContainerRef" class="tianditu-map-container" />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  imageUrl: {
    type: String,
    default: ''
  },
  bounds: {
    type: Array,
    default: null
  },
  opacity: {
    type: Number,
    default: 0.7
  },
  center: {
    type: Array,
    default: () => [35.0, 105.0]
  },
  zoom: {
    type: Number,
    default: 5
  },
  minZoom: {
    type: Number,
    default: 3
  },
  maxZoom: {
    type: Number,
    default: 18
  }
})

const emit = defineEmits(['ready'])

const mapContainerRef = ref(null)
let mapInstance = null
let imageOverlay = null
let resizeObserver = null
let lastOverlayKey = ''

function buildTdtTileLayer() {
  const key = import.meta.env.VITE_TIANDITU_TOKEN || '2434374ddd3f9498666dab04536503dc'
  const urls = [
    `https://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${key}`,
    `https://t1.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${key}`,
    `https://t2.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${key}`,
    `https://t7.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${key}`
  ]

  return L.tileLayer(urls[0], {
    minZoom: props.minZoom,
    maxZoom: props.maxZoom,
    subdomains: [0, 1, 2, 7],
    attribution: '&copy; <a href="https://www.tianditu.gov.cn">天地图</a>'
  })
}

function updateOverlay() {
  if (!mapInstance) {
    return
  }

  if (imageOverlay) {
    mapInstance.removeLayer(imageOverlay)
    imageOverlay = null
  }

  if (!props.imageUrl || !props.bounds) {
    lastOverlayKey = ''
    return
  }

  try {
    const parsedBounds = L.latLngBounds(
      L.latLng(props.bounds[0][0], props.bounds[0][1]),
      L.latLng(props.bounds[1][0], props.bounds[1][1])
    )

    imageOverlay = L.imageOverlay(props.imageUrl, parsedBounds, {
      opacity: props.opacity,
      interactive: false
    })

    imageOverlay.addTo(mapInstance)

    const overlayKey = JSON.stringify(props.bounds)
    if (lastOverlayKey !== overlayKey) {
      mapInstance.fitBounds(parsedBounds, { padding: [20, 20] })
      lastOverlayKey = overlayKey
    }
  } catch (error) {
    console.warn('[TianDiTuMap] Failed to add overlay:', error)
  }
}

onMounted(async () => {
  if (!mapContainerRef.value) {
    return
  }

  mapInstance = L.map(mapContainerRef.value, {
    center: props.center,
    zoom: props.zoom,
    minZoom: props.minZoom,
    maxZoom: props.maxZoom,
    zoomControl: true,
    attributionControl: true
  })

  buildTdtTileLayer().addTo(mapInstance)

  await nextTick()
  mapInstance.invalidateSize()

  resizeObserver = new ResizeObserver(() => {
    if (mapInstance) {
      mapInstance.invalidateSize()
    }
  })
  resizeObserver.observe(mapContainerRef.value)

  emit('ready', mapInstance)

  if (props.imageUrl && props.bounds) {
    updateOverlay()
  }
})

onBeforeUnmount(() => {
  if (resizeObserver && mapContainerRef.value) {
    resizeObserver.unobserve(mapContainerRef.value)
    resizeObserver.disconnect()
    resizeObserver = null
  }

  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})

watch(() => [props.imageUrl, props.bounds], () => {
  updateOverlay()
}, { deep: true })

watch(() => props.opacity, (newOpacity) => {
  if (imageOverlay) {
    imageOverlay.setOpacity(newOpacity)
  }
})

defineExpose({
  getMap: () => mapInstance,
  fitBounds: (bounds) => {
    if (mapInstance) {
      mapInstance.fitBounds(bounds, { padding: [20, 20] })
    }
  }
})
</script>

<style scoped>
.tianditu-map-container {
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 0;
  overflow: hidden;
}
</style>
