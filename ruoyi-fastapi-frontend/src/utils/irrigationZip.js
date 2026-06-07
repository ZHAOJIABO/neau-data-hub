import JSZip from 'jszip'
import { fromArrayBuffer } from 'geotiff'

const ZIP_TIF_PATTERN = /\.tiff?$/i
const DATE_TOKEN_PATTERN = /(\d{4})[-_]?(\d{2})[-_]?(\d{2})/

function normalizeZipPath(path) {
  return path.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
}

function toIsoDateFromMatch(match) {
  return `${match[1]}-${match[2]}-${match[3]}`
}

function getEntryDate(path) {
  const match = path.match(DATE_TOKEN_PATTERN)
  return match ? toIsoDateFromMatch(match) : ''
}

function detectLayerType(path) {
  const normalizedPath = normalizeZipPath(path).toLowerCase()
  const fileName = normalizedPath.split('/').pop() || ''

  if (normalizedPath.includes('/soil_moisture/') || normalizedPath.startsWith('soil_moisture/') || fileName.startsWith('sm_') || fileName.includes('soil_moisture')) {
    return 'soil_moisture'
  }

  if (normalizedPath.includes('/irrigation/') || normalizedPath.startsWith('irrigation/') || fileName.startsWith('irrigation_')) {
    return 'irrigation'
  }

  return ''
}

function clampByte(value) {
  return Math.max(0, Math.min(255, Math.round(value)))
}

function interpolateColor(stops, ratio) {
  if (ratio <= stops[0].value) {
    return stops[0].color
  }
  if (ratio >= stops[stops.length - 1].value) {
    return stops[stops.length - 1].color
  }

  for (let index = 1; index < stops.length; index += 1) {
    const prev = stops[index - 1]
    const next = stops[index]
    if (ratio <= next.value) {
      const span = next.value - prev.value || 1
      const localRatio = (ratio - prev.value) / span
      return [0, 1, 2].map(channel => clampByte(prev.color[channel] + (next.color[channel] - prev.color[channel]) * localRatio))
    }
  }

  return stops[stops.length - 1].color
}

function buildColorRamp(type) {
  if (type === 'soil_moisture') {
    return [
      { value: 0, color: [113, 63, 18] },
      { value: 0.33, color: [245, 158, 11] },
      { value: 0.66, color: [59, 130, 246] },
      { value: 1, color: [12, 74, 110] }
    ]
  }

  return [
    { value: 0, color: [255, 255, 255] },
    { value: 0.25, color: [191, 219, 254] },
    { value: 0.5, color: [59, 130, 246] },
    { value: 0.75, color: [37, 99, 235] },
    { value: 1, color: [30, 64, 175] }
  ]
}

function createLegend(type, min, max) {
  const ramp = buildColorRamp(type)
  return ramp.map(stop => ({
    color: `rgb(${stop.color.join(',')})`,
    value: Number((min + (max - min) * stop.value).toFixed(3))
  }))
}

async function decodeGeoTiff(arrayBuffer, type) {
  const tiff = await fromArrayBuffer(arrayBuffer)
  const image = await tiff.getImage()
  const rasters = await image.readRasters({ interleave: true })
  const width = image.getWidth()
  const height = image.getHeight()
  const bbox = image.getBoundingBox()
  const noDataValue = image.getGDALNoData()

  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY

  for (let index = 0; index < rasters.length; index += 1) {
    const value = rasters[index]
    if (!Number.isFinite(value)) {
      continue
    }
    if (noDataValue !== null && noDataValue !== undefined && value === Number(noDataValue)) {
      continue
    }
    min = Math.min(min, value)
    max = Math.max(max, value)
  }

  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    min = 0
    max = 1
  }

  if (min === max) {
    max = min + 1
  }

  const ramp = buildColorRamp(type)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  const imageData = context.createImageData(width, height)
  const span = max - min

  for (let index = 0; index < rasters.length; index += 1) {
    const value = rasters[index]
    const offset = index * 4
    const invalid = !Number.isFinite(value) || (noDataValue !== null && noDataValue !== undefined && value === Number(noDataValue))

    if (invalid) {
      imageData.data[offset + 3] = 0
      continue
    }

    const ratio = (value - min) / span
    const [red, green, blue] = interpolateColor(ramp, ratio)
    imageData.data[offset] = red
    imageData.data[offset + 1] = green
    imageData.data[offset + 2] = blue
    imageData.data[offset + 3] = 180
  }

  context.putImageData(imageData, 0, 0)

  return {
    bounds: [
      [bbox[1], bbox[0]],
      [bbox[3], bbox[2]]
    ],
    width,
    height,
    min,
    max,
    legend: createLegend(type, min, max),
    imageUrl: canvas.toDataURL('image/png')
  }
}

export async function createIrrigationZipIndex(blob) {
  const zip = await JSZip.loadAsync(blob)
  const entries = {}
  const dates = new Set()

  zip.forEach((relativePath, zipEntry) => {
    if (zipEntry.dir) {
      return
    }

    const normalizedPath = normalizeZipPath(relativePath)
    if (!ZIP_TIF_PATTERN.test(normalizedPath)) {
      return
    }

    const layerType = detectLayerType(normalizedPath)
    if (!layerType) {
      return
    }

    const filename = normalizedPath.split('/').pop() || normalizedPath
    const date = getEntryDate(filename) || getEntryDate(normalizedPath)
    if (!date) {
      return
    }

    dates.add(date)
    if (!entries[date]) {
      entries[date] = {}
    }

    entries[date][layerType] = {
      path: normalizedPath,
      filename,
      type: layerType
    }
  })

  return {
    dates: Array.from(dates).sort(),
    entries,
    zip
  }
}

export async function decodeIrrigationLayer(zipIndex, date, type, cache = new Map()) {
  const cacheKey = `${date}:${type}`
  if (cache.has(cacheKey)) {
    return cache.get(cacheKey)
  }

  const entry = zipIndex.entries?.[date]?.[type]
  if (!entry) {
    throw new Error(`未找到 ${date} 的 ${type} 结果栅格`)
  }

  const zipEntry = zipIndex.zip.file(entry.path)
  if (!zipEntry) {
    throw new Error(`ZIP 中缺少文件：${entry.path}`)
  }

  const arrayBuffer = await zipEntry.async('arraybuffer')
  const decoded = await decodeGeoTiff(arrayBuffer, type)
  const layer = {
    ...decoded,
    date,
    type,
    filename: entry.filename
  }

  cache.set(cacheKey, layer)
  return layer
}

export function getAvailableLayerTypes(zipIndex, date) {
  return Object.keys(zipIndex.entries?.[date] || {})
}
