import axios from 'axios'
import { useUserStore } from '../stores/user'
import router from '../router'

const http = axios.create({ baseURL: 'http://localhost:8000/load-forecast' })

http.interceptors.request.use(config => {
  const store = useUserStore()
  if (store.token) config.headers.Authorization = `Bearer ${store.token}`
  return config
})

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

export const getHistory = (params) => http.get('/history', { params })
export const getPredict = (params) => http.get('/predict', { params })
export const getPredictWeather = (params) => http.get('/predict-weather', { params })
