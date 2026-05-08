import request from '@/utils/request'

// 获取气象综合数据列表
export function listWeatherOverview(query) {
  return request({
    url: '/agriculture/weather/overview/list',
    method: 'get',
    params: query
  })
}

// 获取温度数据列表
export function listTemperature(query) {
  return request({
    url: '/agriculture/weather/temperature/list',
    method: 'get',
    params: query
  })
}

// 新增温度数据
export function addTemperature(data) {
  return request({
    url: '/agriculture/weather/temperature',
    method: 'post',
    data: data
  })
}

// 删除温度数据
export function delTemperature(ids) {
  return request({
    url: '/agriculture/weather/temperature/' + ids,
    method: 'delete'
  })
}

// 获取湿度数据列表
export function listHumidity(query) {
  return request({
    url: '/agriculture/weather/humidity/list',
    method: 'get',
    params: query
  })
}

// 获取降水数据列表
export function listPrecipitation(query) {
  return request({
    url: '/agriculture/weather/precipitation/list',
    method: 'get',
    params: query
  })
}
