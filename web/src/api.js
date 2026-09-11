import axios from 'axios'
import { ElMessage } from 'element-plus'
import { clearToken, getToken } from './auth'

const http = axios.create({ baseURL: '/api', timeout: 15000 })

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (err.message || '请求失败')
    if (err.response?.status === 401 && location.hash !== '#/login') {
      clearToken()
      location.hash = '#/login'
    }
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

export default http
