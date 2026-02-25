'use client'

import * as React from 'react'
import { qnaceApi, HealthStatus } from '@/lib/api'
import { cn } from '@/lib/utils'

interface ApiStatusProps {
  variant?: 'full' | 'minimal'
}

export function ApiStatus({ variant = 'minimal' }: ApiStatusProps) {
  const [status, setStatus] = React.useState<'loading' | 'connected' | 'disconnected'>('loading')
  const [health, setHealth] = React.useState<HealthStatus | null>(null)

  React.useEffect(() => {
    const checkHealth = async () => {
      try {
        const result = await qnaceApi.checkHealth()
        setHealth(result)
        setStatus('connected')
      } catch {
        setStatus('disconnected')
      }
    }

    checkHealth()
    // Re-check every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  // Minimal variant - just a dot with tooltip
  if (variant === 'minimal') {
    return (
      <div 
        className="relative group cursor-default"
        title={status === 'connected' ? `API Connected (${health?.device || 'ready'})` : status === 'loading' ? 'Connecting...' : 'API Offline'}
      >
        <div className={cn(
          'h-2.5 w-2.5 rounded-full',
          status === 'connected' && 'bg-green-500',
          status === 'disconnected' && 'bg-red-500',
          status === 'loading' && 'bg-yellow-500 animate-pulse'
        )} />
        {/* Tooltip on hover */}
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 hidden group-hover:block z-50">
          <div className="bg-background border border-foreground/10 rounded-lg px-2 py-1 text-xs whitespace-nowrap shadow-lg">
            {status === 'connected' && `Connected (${health?.device || 'ready'})`}
            {status === 'disconnected' && 'API Offline'}
            {status === 'loading' && 'Connecting...'}
          </div>
        </div>
      </div>
    )
  }

  // Full variant - badge style
  return (
    <div className={cn(
      'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium',
      status === 'connected' && 'bg-green-500/20 text-green-400',
      status === 'disconnected' && 'bg-red-500/20 text-red-400',
      status === 'loading' && 'bg-yellow-500/20 text-yellow-400'
    )}>
      <div className={cn(
        'h-2 w-2 rounded-full',
        status === 'connected' && 'bg-green-500',
        status === 'disconnected' && 'bg-red-500',
        status === 'loading' && 'bg-yellow-500 animate-pulse'
      )} />
      {status === 'loading' && <span>Connecting...</span>}
      {status === 'connected' && <span>Connected</span>}
      {status === 'disconnected' && <span>Offline</span>}
    </div>
  )
}
