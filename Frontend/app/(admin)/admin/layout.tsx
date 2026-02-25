'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/use-auth'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, loading } = useAuth()

  React.useEffect(() => {
    if (!loading && !user) {
      router.push('/onboarding')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-foreground/60">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-foreground/10 px-6 py-4">
        <div className="flex items-center gap-4">
          <Button asChild variant="ghost" size="sm">
            <Link href="/app/dashboard">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to App
            </Link>
          </Button>
          <h1 className="text-xl font-semibold">Admin Panel</h1>
        </div>
      </div>
      <main>{children}</main>
    </div>
  )
}

