import request from '@/utils/request'

// 获取叶面积指数数据列表
export function listLeafArea(query) {
  return request({
    url: '/agriculture/crop/leaf-area/list',
    method: 'get',
    params: query
  })
}
