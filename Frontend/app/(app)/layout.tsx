'use client'

import * as React from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import { hasCompletedOnboarding } from '@/lib/auth'
import Link from 'next/link'
import {
  LayoutDashboard,
  Video,
  FileText,
  BookOpen,
  Briefcase,
  Settings,
  LogOut,
  Menu,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ApiStatus } from '@/components/ui/api-status'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Practice', href: '/practice', icon: Video },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Resources', href: '/resources', icon: BookOpen },
  { name: 'Jobs', href: '/jobs', icon: Briefcase },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, logout, loading, isAuthenticated } = useAuth()
  const [sidebarOpen, setSidebarOpen] = React.useState(false)

  React.useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        // Not logged in - redirect to login with return URL
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`)
      } else if (!hasCompletedOnboarding()) {
        // Logged in but hasn't completed onboarding
        router.push('/onboarding')
      }
    }
  }, [isAuthenticated, loading, router, pathname])

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

  if (!isAuthenticated || !user) {
    return null
  }

  const handleLogout = () => {
    logout()
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="lg:hidden">
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              className="fixed inset-0 bg-background/80 backdrop-blur-sm"
              onClick={() => setSidebarOpen(false)}
              aria-hidden="true"
            />
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              className="fixed inset-y-0 left-0 z-50 w-64 bg-gradient-to-b from-gradient-purple/30 to-gradient-blue/30 border-r border-foreground/10 backdrop-blur-md"
            >
              <SidebarContent
                pathname={pathname}
                user={user}
                onLogout={handleLogout}
                onClose={() => setSidebarOpen(false)}
              />
            </motion.div>
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:block lg:w-64">
        <div className="h-full bg-gradient-to-b from-gradient-purple/30 to-gradient-blue/30 border-r border-foreground/10 backdrop-blur-md">
          <SidebarContent pathname={pathname} user={user} onLogout={handleLogout} />
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-30 bg-background/80 backdrop-blur-sm border-b border-foreground/10 px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold">Q&Ace</h1>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
          </div>
        </header>

        <main className="min-h-screen">{children}</main>
      </div>
    </div>
  )
}

function SidebarContent({
  pathname,
  user,
  onLogout,
  onClose,
}: {
  pathname: string
  user: { name: string; email: string }
  onLogout: () => void
  onClose?: () => void
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center justify-between px-6 border-b border-foreground/10">
        <Link href="/dashboard" className="text-xl font-bold gradient-text hover:opacity-80 transition-opacity">
          Q&Ace
        </Link>
        <div className="flex items-center gap-2">
          <ApiStatus />
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close menu">
              <X className="h-5 w-5" />
            </Button>
          )}
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                isActive
                  ? 'bg-accent/20 text-accent'
                  : 'text-foreground/60 hover:bg-foreground/10 hover:text-foreground'
              )}
            >
              <Icon className="h-5 w-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-foreground/10 p-4">
        <div className="mb-3 px-3">
          <p className="text-sm font-medium text-foreground">{user.name}</p>
          <p className="text-xs text-foreground/60">{user.email}</p>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start"
          onClick={onLogout}
          aria-label="Log out"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Log Out
        </Button>
      </div>
    </div>
  )
}

