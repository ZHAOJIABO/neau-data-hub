import request from '@/utils/request'

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
