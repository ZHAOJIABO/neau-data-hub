import request from '@/utils/request'

const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

function buildRequestConfig(apiKey) {
  return {
    timeout: 600000,
    isToken: false,
    repeatSubmit: false,
    interval: 0,
    headers: {
      'X-Irrigation-Api-Key': apiKey,
      'Content-Type': 'application/json'
    }
  }
}

function unwrap(response) {
  return response && Object.prototype.hasOwnProperty.call(response, 'data')
    ? response.data
    : response
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

export async function runFullOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/full',
    method: 'post',
    data: payload,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function runTrunkBranchOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/trunk-branch',
    method: 'post',
    data: payload,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function runBranchLateralOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/branch-lateral',
    method: 'post',
    data: payload,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

// ---------------------------------------------------------------------------
// Kinematic Wave 水动力学仿真
// ---------------------------------------------------------------------------

export async function runKinematicSim(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/hydro/kinematic',
    method: 'post',
    data: payload,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}
