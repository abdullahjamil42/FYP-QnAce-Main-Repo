'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { hasCompletedOnboarding } from '@/lib/auth'

interface AuthGuardProps {
  children: React.ReactNode
  requireOnboarding?: boolean
  redirectTo?: string
}

/**
 * AuthGuard component to protect routes
 * 
 * Usage:
 * <AuthGuard>
 *   <ProtectedContent />
 * </AuthGuard>
 * 
 * Options:
 * - requireOnboarding: If true, also requires onboarding to be completed (default: true)
 * - redirectTo: Custom redirect URL if not authenticated (default: '/login')
 */
export function AuthGuard({ 
  children, 
  requireOnboarding = true,
  redirectTo = '/login' 
}: AuthGuardProps) {
  const router = useRouter()
  const { isAuthenticated, loading } = useAuth()
  const [isAuthorized, setIsAuthorized] = React.useState(false)

  React.useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        // Not logged in
        const currentPath = window.location.pathname
        router.push(`${redirectTo}?redirect=${encodeURIComponent(currentPath)}`)
      } else if (requireOnboarding && !hasCompletedOnboarding()) {
        // Logged in but needs onboarding
        router.push('/onboarding')
      } else {
        // Fully authorized
        setIsAuthorized(true)
      }
    }
  }, [isAuthenticated, loading, router, redirectTo, requireOnboarding])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center gradient-bg">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-foreground/60">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isAuthorized) {
    return null
  }

  return <>{children}</>
}

/**
 * Hook version for more control
 */
export function useAuthGuard(options?: { requireOnboarding?: boolean }) {
  const { isAuthenticated, loading, user } = useAuth()
  const requireOnboarding = options?.requireOnboarding ?? true

  const isAuthorized = React.useMemo(() => {
    if (loading) return false
    if (!isAuthenticated) return false
    if (requireOnboarding && !hasCompletedOnboarding()) return false
    return true
  }, [isAuthenticated, loading, requireOnboarding])

  return {
    isAuthorized,
    isLoading: loading,
    user,
  }
}
