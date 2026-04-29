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

export function AuthProvider({
  children,
  initialUser = null,
}: {
  children: React.ReactNode
  initialUser?: User | null
}) {
  const [user, setUser] = useState<User | null>(initialUser)
  const [isLoading, setIsLoading] = useState(initialUser ? false : true)

  useEffect(() => {
    if (initialUser) {
      return
    }

    getMe('')
      .then(setUser)
      .catch((err) => {
        if (err instanceof ApiError && err.isUnauthorized) {
          setUser(null)
        }
      })
      .finally(() => setIsLoading(false))
  }, [initialUser])

  return <AuthContext.Provider value={{ user, isLoading }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
