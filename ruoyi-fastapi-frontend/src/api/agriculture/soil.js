import request from '@/utils/request'

// 获取传感器监测数据列表
export function listSensor(query) {
  return request({
    url: '/agriculture/soil/sensor/list',
    method: 'get',
    params: query
  })
}

// 获取土壤参数数据列表
export function listParameter(query) {
  return request({
    url: '/agriculture/soil/parameter/list',
    method: 'get',
    params: query
  })
}

// 获取地温数据列表
export function listGroundTemp(query) {
  return request({
    url: '/agriculture/soil/ground-temp/list',
    method: 'get',
    params: query
  })
}

// 获取黑土厚度数据列表
export function listThickness(query) {
  return request({
    url: '/agriculture/soil/thickness/list',
    method: 'get',
    params: query
  })
}

// 获取分层统计数据列表
export function listLayerStats(query) {
  return request({
    url: '/agriculture/soil/layer-stats/list',
    method: 'get',
    params: query
  })
}
