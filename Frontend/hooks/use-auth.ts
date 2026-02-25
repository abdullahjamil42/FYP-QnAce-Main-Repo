'use client'

import { useState, useEffect, useCallback } from 'react'
import { User } from '@/lib/mock-data'
import { 
  getUser, 
  login as authLogin, 
  signup as authSignup,
  logout as authLogout, 
  isAuthenticated as checkAuth,
  hasCompletedOnboarding,
  completeOnboarding as completeUserOnboarding,
  SignupData,
  AuthResult
} from '@/lib/auth'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Load user on mount
  useEffect(() => {
    const currentUser = getUser()
    setUser(currentUser)
    setIsAuthenticated(checkAuth())
    setLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<AuthResult> => {
    setLoading(true)
    try {
      const result = await authLogin(email, password)
      if (result.success && result.user) {
        setUser(result.user)
        setIsAuthenticated(true)
      }
      return result
    } finally {
      setLoading(false)
    }
  }, [])

  const signup = useCallback(async (data: SignupData): Promise<AuthResult> => {
    setLoading(true)
    try {
      const result = await authSignup(data)
      // Don't auto-login after signup - user should log in manually
      return result
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    authLogout()
    setUser(null)
    setIsAuthenticated(false)
  }, [])

  const completeOnboarding = useCallback((profileData: Partial<User>) => {
    completeUserOnboarding(profileData)
    const updatedUser = getUser()
    if (updatedUser) {
      setUser(updatedUser)
    }
  }, [])

  const needsOnboarding = useCallback(() => {
    return isAuthenticated && !hasCompletedOnboarding()
  }, [isAuthenticated])

  return {
    user,
    loading,
    isAuthenticated,
    needsOnboarding: needsOnboarding(),
    login,
    signup,
    logout,
    completeOnboarding,
  }
}

