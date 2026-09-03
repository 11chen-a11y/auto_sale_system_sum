import axios from 'axios'
import { useUserStore } from '../stores/user'
import router from '../router'

const http = axios.create({ baseURL: 'http://localhost:8000/analysis' })

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

export const getLoadVsPrice = (params) => http.get('/load-vs-price', { params })
export const getLoadVsNewEnergy = (params) => http.get('/load-vs-new-energy', { params })
export const getLoadVsWeather = (params) => http.get('/load-vs-weather', { params })
export const getCustomerConsumption = (params) => http.get('/customer-consumption', { params })
export const getFullChain = (params) => http.get('/full-chain', { params })
