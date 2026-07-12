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

/**
 * 灌区农业水效综合评价（熵权-TOPSIS，支持多时段对比）
 * @param {Object} payload - 评价请求体
 * @param {string} [apiKey] - API Key
 * @returns {Promise<Object>} 评价结果
 */
export async function runWaterEfficiencyEvaluate(payload, apiKey = IRRIGATION_API_KEY) {
  const response = await request({
    url: '/api/v1/irrigation/water-efficiency/evaluate',
    method: 'post',
    data: payload,
    ...buildRequestConfig(apiKey)
  })
  return unwrap(response)
}
