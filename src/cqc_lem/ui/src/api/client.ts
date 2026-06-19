import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
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
