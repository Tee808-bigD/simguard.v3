import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    return Promise.reject(new Error(Array.isArray(msg) ? msg.map(e => e.msg).join('; ') : msg))
  }
)

export const submitTransaction = (data) => api.post('/transactions', data)
export const listTransactions = (params = {}) => api.get('/transactions', { params })
export const getDashboardStats = () => api.get('/dashboard/stats')
export const getTimeline = (hours = 24) => api.get('/dashboard/timeline', { params: { hours } })
export const getRiskDistribution = () => api.get('/dashboard/risk-distribution')
export const listAlerts = (params = {}) => api.get('/fraud/alerts', { params })
export const quickCheck = (data) => api.post('/fraud/check', data)

export default api
