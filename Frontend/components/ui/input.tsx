'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

type InputProps = React.InputHTMLAttributes<HTMLInputElement>

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-11 w-full rounded-xl border border-foreground/20 bg-white px-4 py-2 text-sm text-gray-900',
          'placeholder:text-gray-400',
          'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/50',
          'hover:border-foreground/30',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'transition-all duration-200',
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Input.displayName = 'Input'

export { Input }
