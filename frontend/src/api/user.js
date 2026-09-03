import axios from 'axios'
import { useUserStore } from '../stores/user'
import router from '../router'

const http = axios.create({ baseURL: 'http://localhost:8000/users' })

// 请求拦截：自动带 token
http.interceptors.request.use(config => {
  const store = useUserStore()
  if (store.token) config.headers.Authorization = `Bearer ${store.token}`
  return config
})

// 响应拦截：401 跳登录
http.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      const store = useUserStore()
      store.logout()
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

export const sendCode = phone => http.post('/send-code', { phone })
export const register = data => http.post('/register', data)
export const login = data => http.post('/login', data)
export const loginPhone = data => http.post('/login-phone', data)
export const getHome = () => http.get('/home')
export const listUsers = () => http.get('/')
export const setUserRole = (userId, role) => http.put(`/${userId}/role`, { role })
