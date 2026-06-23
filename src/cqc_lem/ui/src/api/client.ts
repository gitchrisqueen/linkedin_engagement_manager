import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Build-time API access token. Empty in local/dev (gate disabled server-side);
// set via VITE_API_TOKEN for deployments that enforce bearer auth on /api.
const apiToken = import.meta.env.VITE_API_TOKEN

api.interceptors.request.use((config) => {
  if (apiToken) {
    config.headers['Authorization'] = `Bearer ${apiToken}`
  }
  const token = localStorage.getItem('lem_session')
  if (token) {
    config.headers['X-Session-Token'] = token
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('lem_session')
      localStorage.removeItem('lem_email')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export default api
