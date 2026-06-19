import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import api from '../api/client'

interface AuthUser {
  email: string
  userId?: number
}

interface AuthContextValue {
  user: AuthUser | null
  sessionToken: string | null
  isLoading: boolean
  login: (token: string, email: string) => void
  logout: () => Promise<void>
  openLoginModal: () => void
  closeLoginModal: () => void
  isLoginModalOpen: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

const SESSION_KEY = 'lem_session'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [sessionToken, setSessionToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)

  useEffect(() => {
    const storedToken = localStorage.getItem(SESSION_KEY)
    if (!storedToken) {
      setIsLoading(false)
      return
    }
    api
      .get(`/auth/session?session_token=${encodeURIComponent(storedToken)}`)
      .then((r) => {
        const { email, user_id } = r.data.detail
        setSessionToken(storedToken)
        setUser({ email, userId: user_id })
      })
      .catch(() => {
        localStorage.removeItem(SESSION_KEY)
        localStorage.removeItem('lem_email')
      })
      .finally(() => setIsLoading(false))
  }, [])

  function login(token: string, email: string) {
    localStorage.setItem(SESSION_KEY, token)
    localStorage.setItem('lem_email', email)
    setSessionToken(token)
    setUser({ email })
    setIsLoginModalOpen(false)
  }

  async function logout() {
    const token = sessionToken
    if (token) {
      await api.post('/auth/logout', { session_token: token }).catch(() => {})
    }
    localStorage.removeItem(SESSION_KEY)
    localStorage.removeItem('lem_email')
    localStorage.removeItem('lem_li_connected')
    localStorage.removeItem('lem_blog_url')
    localStorage.removeItem('lem_sitemap_url')
    setSessionToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        sessionToken,
        isLoading,
        login,
        logout,
        openLoginModal: () => setIsLoginModalOpen(true),
        closeLoginModal: () => setIsLoginModalOpen(false),
        isLoginModalOpen,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
