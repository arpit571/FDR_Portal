import React, { createContext, useContext, useState, useEffect } from 'react'
import { getMe } from '../api/client'

interface User {
  id: string
  name: string
  email: string
  roles: string[]
  institution_id: string | null
}

interface AuthCtx {
  user: User | null
  token: string | null
  login: (token: string, user: User) => void
  logout: () => void
  hasRole: (...roles: string[]) => boolean
  isAdmin: boolean
  isAICTE: boolean
  isAuditor: boolean
  isFinance: boolean
  isReviewer: boolean
}

const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null }
  })
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))

  useEffect(() => {
    if (token && !user) {
      getMe().then(setUser).catch(() => logout())
    }
  }, [token])

  const login = (tok: string, usr: User) => {
    localStorage.setItem('token', tok)
    localStorage.setItem('user', JSON.stringify(usr))
    setToken(tok)
    setUser(usr)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  const hasRole = (...roles: string[]) =>
    !!user?.roles?.some(r => roles.includes(r))

  return (
    <AuthContext.Provider value={{
      user, token, login, logout, hasRole,
      isAdmin: hasRole('SUPER_ADMIN'),
      isAICTE: hasRole('AICTE_OFFICER', 'SUPER_ADMIN'),
      isAuditor: hasRole('AUDITOR', 'SUPER_ADMIN'),
      isFinance: hasRole('FINANCE_OFFICER', 'SUPER_ADMIN'),
      isReviewer: hasRole('REVIEWER', 'SUPER_ADMIN'),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
