import axios from 'axios'
import { useUserStore } from '../stores/user'
import router from '../router'

const http = axios.create({ baseURL: 'http://localhost:8000/node-price' })

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

export const getNodes = () => http.get('/nodes')
export const getTypes = () => http.get('/types')
export const getDates = () => http.get('/dates')
export const listPrices = (params) => http.get('/list', { params })
export const getChartData = (params) => http.get('/chart', { params })
export const createPrice = (data) => http.post('/create', data)
export const updatePrice = (id, data) => http.put(`/update/${id}`, data)
export const deletePrice = (id) => http.delete(`/delete/${id}`)
export const exportRecords = (params) => http.get('/export', { params, responseType: 'blob' })
