import request from '@/utils/request'

export { listCanal } from '@/api/agriculture/canal'

const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

function buildRequestConfig(apiKey) {
  return {
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

export async function runFullOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/full',
    method: 'post',
    data: payload,
    timeout: 600000,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function runTrunkBranchOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/trunk-branch',
    method: 'post',
    data: payload,
    timeout: 600000,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function runBranchLateralOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/branch-lateral',
    method: 'post',
    data: payload,
    timeout: 600000,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function runKinematicSim(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/canal/hydro/kinematic',
    method: 'post',
    data: payload,
    timeout: 600000,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}
