import request from '@/utils/request'

export async function simulateRiceGrowth(data) {
  const response = await request({
    url: '/agriculture/crop-growth/rice/simulate',
    method: 'post',
    data,
    timeout: 180000,
    headers: {
      repeatSubmit: false,
      interval: 0
    }
  })
  return response && Object.prototype.hasOwnProperty.call(response, 'data')
    ? response.data
    : response
}
