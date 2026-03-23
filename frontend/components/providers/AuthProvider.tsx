'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { getMe } from '@/lib/api/auth'
import { ApiError } from '@/lib/api/client'
import type { User } from '@/lib/types/api'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
}

const AuthContext = createContext<AuthContextValue>({ user: null, isLoading: true })

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    getMe('')
      .then(setUser)
      .catch((err) => {
        if (err instanceof ApiError && err.isUnauthorized) {
          setUser(null)
        }
      })
      .finally(() => setIsLoading(false))
  }, [])

  return <AuthContext.Provider value={{ user, isLoading }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
