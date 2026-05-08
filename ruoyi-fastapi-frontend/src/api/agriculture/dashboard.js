import request from '@/utils/request'

// 获取数据概览统计
export function getDashboardStats() {
  return request({
    url: '/agriculture/dashboard/stats',
    method: 'get'
  })
}
