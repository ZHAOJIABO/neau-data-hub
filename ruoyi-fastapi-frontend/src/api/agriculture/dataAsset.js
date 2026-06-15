import request from '@/utils/request'

export function listDataAsset(query) {
  return request({
    url: '/agriculture/dataAsset/list',
    method: 'get',
    params: query
  })
}

export function getDataAsset(id) {
  return request({
    url: '/agriculture/dataAsset/' + id,
    method: 'get'
  })
}

export function uploadDataAsset(data) {
  return request({
    url: '/agriculture/dataAsset/upload',
    method: 'post',
    headers: { 'Content-Type': 'multipart/form-data' },
    data: data
  })
}

export function downloadDataAsset(id) {
  return request({
    url: '/agriculture/dataAsset/download/' + id,
    method: 'get',
    responseType: 'blob'
  })
}

export function delDataAsset(ids) {
  return request({
    url: '/agriculture/dataAsset/' + ids,
    method: 'delete'
  })
}
