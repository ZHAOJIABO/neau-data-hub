import request from '@/utils/request'

function buildHeaders(apiKey) {
  return {
    'X-Irrigation-Api-Key': apiKey,
    isToken: false,
    repeatSubmit: false,
    interval: 0,
    encryptResponse: false,
    'Content-Type': 'application/json'
  }
}

function unwrap(response) {
  return response && Object.prototype.hasOwnProperty.call(response, 'data')
    ? response.data
    : response
}

export async function runFullHydro(payload, apiKey) {
  const response = await request({
    url: '/api/v1/irrigation/canal/hydro/full/standard',
    method: 'post',
    data: payload,
    timeout: 600000,
    headers: buildHeaders(apiKey)
  })
  return unwrap(response)
}

// ---------------------------------------------------------------------------
// 渠系数据管理（农业数据）
// ---------------------------------------------------------------------------

export function listCanal(query) {
  return request({
    url: '/agriculture/canal/list',
    method: 'get',
    params: query
  })
}

export function getCanal(canalId) {
  return request({
    url: `/agriculture/canal/${encodeURIComponent(canalId)}`,
    method: 'get'
  })
}

export function createCanal(data) {
  return request({
    url: '/agriculture/canal',
    method: 'post',
    data
  })
}

export function updateCanal(data) {
  return request({
    url: '/agriculture/canal',
    method: 'put',
    data
  })
}

export function deleteCanal(ids) {
  return request({
    url: `/agriculture/canal/${encodeURIComponent(ids)}`,
    method: 'delete'
  })
}

export function importCanalCSV(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/agriculture/canal/import',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function getManagementTopology() {
  return request({
    url: '/agriculture/canal/topology',
    method: 'get'
  })
}

