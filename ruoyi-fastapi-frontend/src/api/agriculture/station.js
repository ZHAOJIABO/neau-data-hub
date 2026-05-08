import request from '@/utils/request'

// 获取站点列表
export function listStation(query) {
  return request({
    url: '/agriculture/station/list',
    method: 'get',
    params: query
  })
}

// 获取站点详情
export function getStation(id) {
  return request({
    url: '/agriculture/station/' + id,
    method: 'get'
  })
}

// 新增站点
export function addStation(data) {
  return request({
    url: '/agriculture/station',
    method: 'post',
    data: data
  })
}

// 修改站点
export function updateStation(data) {
  return request({
    url: '/agriculture/station',
    method: 'put',
    data: data
  })
}

// 删除站点
export function delStation(ids) {
  return request({
    url: '/agriculture/station/' + ids,
    method: 'delete'
  })
}
