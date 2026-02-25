'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info'
  children: React.ReactNode
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const variants = {
      default: 'bg-foreground/10 text-foreground',
      success: 'bg-green-500/20 text-green-400',
      warning: 'bg-yellow-500/20 text-yellow-400',
      error: 'bg-red-500/20 text-red-400',
      info: 'bg-accent/20 text-accent',
    }

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'

export { Badge }

