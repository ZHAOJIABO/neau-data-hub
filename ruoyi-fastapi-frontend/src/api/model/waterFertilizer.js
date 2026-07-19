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

export async function listWaterFertilizerRegulation(params, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/water-fertilizer/regulation/list',
    method: 'get',
    params,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function getWaterFertilizerRegulationSummary(apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/water-fertilizer/regulation/summary',
    method: 'get',
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}

export async function runWaterFertilizerOptimize(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/water-fertilizer/optimize',
    method: 'post',
    data: payload,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}
