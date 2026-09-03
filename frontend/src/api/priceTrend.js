import axios from 'axios'
import { useUserStore } from '../stores/user'
import router from '../router'

const http = axios.create({ baseURL: 'http://localhost:8000/price-trend' })

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

export const getTrend = (params) => http.get('/trend', { params })
export const getComparison = (params) => http.get('/comparison', { params })
export const getSpotTrend = (params) => http.get('/spot-trend', { params })
export const getVolatility = (params) => http.get('/volatility', { params })
export const getSeasonal = (params) => http.get('/seasonal', { params })
export const getCorrelation = (params) => http.get('/correlation', { params })
