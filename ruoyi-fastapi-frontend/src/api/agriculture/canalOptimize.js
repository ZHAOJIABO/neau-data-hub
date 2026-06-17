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

export async function runFullOptimize(payload, apiKey) {
  const response = await request({
    url: '/api/v1/irrigation/canal/optimize/full',
    method: 'post',
    data: payload,
    timeout: 600000,
    headers: buildHeaders(apiKey)
  })
  return unwrap(response)
}
