import request from '@/utils/request'

function parseContentDispositionFilename(contentDisposition) {
  if (!contentDisposition) {
    return ''
  }
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match) {
    return decodeURIComponent(utf8Match[1])
  }
  const asciiMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return asciiMatch ? asciiMatch[1] : ''
}

export async function predictIrrigation(formData, apiKey) {
  const response = await request({
    url: '/api/v1/irrigation/predict',
    method: 'post',
    data: formData,
    timeout: 600000,
    responseType: 'blob',
    isToken: false,
    repeatSubmit: false,
    interval: 0,
    headers: {
      'Content-Type': 'multipart/form-data',
      'X-Irrigation-Api-Key': apiKey
    }
  })

  const contentType = response.type || ''
  if (contentType.includes('application/json')) {
    const text = await response.text()
    const payload = JSON.parse(text)
    throw new Error(payload.msg || payload.message || '预测请求失败')
  }

  return {
    blob: response,
    filename: parseContentDispositionFilename(response.headers?.['content-disposition'])
  }
}
