import { useUserStore } from '../stores/user'

// 统一的错误提示：提取后端 detail，处理 401 登出
export function showError(e) {
  let msg = '请求失败，请稍后重试'
  if (e?.response?.status === 401) {
    try { useUserStore().logout() } catch { /* store 未初始化 */ }
    msg = '登录已失效，请重新登录'
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    return msg
  }
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string' && detail) {
    msg = detail
  } else if (detail && detail.errors) {
    msg = '请求参数校验失败'
  } else if (e?.response?.status) {
    msg = `请求失败（${e.response.status}）`
  }
  alert(msg)
  return msg
}