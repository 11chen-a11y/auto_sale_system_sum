import axios from 'axios'
import { useUserStore } from '../stores/user'
import router from '../router'

const http = axios.create({ baseURL: 'http://localhost:8000/contract' })

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

export const getTypes = () => http.get('/types')
export const listRecords = (params) => http.get('/list', { params })
export const createRecord = (data) => http.post('/create', data)
export const updateRecord = (id, data) => http.put(`/update/${id}`, data)
export const deleteRecord = (id) => http.delete(`/delete/${id}`)
export const exportRecords = (params) => http.get('/export', { params, responseType: 'blob' })
