import request from '@/utils/request'

export function listZone(query) {
  return request({
    url: '/agriculture/zone/list',
    method: 'get',
    params: query
  })
}

export function getZone(zoneId) {
  return request({
    url: `/agriculture/zone/${encodeURIComponent(zoneId)}`,
    method: 'get'
  })
}

export function listIrrigationAreas() {
  return request({
    url: '/agriculture/zone/areas',
    method: 'get'
  })
}

export function listEnabledZones(irrigationAreaCode = 'chahayang') {
  return request({
    url: '/agriculture/zone/enabled',
    method: 'get',
    params: { irrigationAreaCode }
  })
}

export function createZone(data) {
  return request({
    url: '/agriculture/zone',
    method: 'post',
    data
  })
}

export function updateZone(data) {
  return request({
    url: '/agriculture/zone',
    method: 'put',
    data
  })
}

export function deleteZone(ids) {
  return request({
    url: `/agriculture/zone/${encodeURIComponent(ids)}`,
    method: 'delete'
  })
}

export function importZoneCSV(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/agriculture/zone/import',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
