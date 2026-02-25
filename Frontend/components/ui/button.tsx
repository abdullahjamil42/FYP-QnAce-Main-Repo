'use client'

import * as React from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { Slot } from '@radix-ui/react-slot'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
  disabled?: boolean
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', disabled = false, asChild = false, children, ...props }, ref) => {
    const prefersReducedMotion = useReducedMotion()

    const baseStyles = 'relative inline-flex items-center justify-center rounded-lg font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50'

    const variants = {
      primary: 'bg-accent text-background hover:bg-accent/90 hover:scale-[1.02] active:scale-[0.98] hover:shadow-glow',
      secondary: 'bg-gradient-to-r from-gradient-purple to-gradient-blue text-foreground hover:from-gradient-purple/90 hover:to-gradient-blue/90 hover:scale-[1.02] active:scale-[0.98]',
      ghost: 'text-foreground hover:bg-foreground/10 hover:scale-[1.02] active:scale-[0.98]',
      danger: 'bg-red-600 text-white hover:bg-red-700 hover:scale-[1.02] active:scale-[0.98]',
    }

    const sizes = {
      sm: 'h-8 px-3 text-sm',
      md: 'h-10 px-4 text-base',
      lg: 'h-12 px-6 text-lg',
    }

    const motionProps = prefersReducedMotion
      ? {}
      : {
          whileHover: { scale: disabled ? 1 : 1.02 },
          whileTap: { scale: disabled ? 1 : 0.98 },
          transition: { duration: 0.12, ease: 'easeOut' },
        }

    const combinedClassName = cn(baseStyles, variants[variant], sizes[size], className)

    if (asChild) {
      return (
        <Slot
          ref={ref as React.Ref<HTMLElement>}
          className={combinedClassName}
          aria-disabled={disabled}
          {...(props as React.HTMLAttributes<HTMLElement>)}
        >
          {children}
        </Slot>
      )
    }

    return (
      <motion.button
        ref={ref}
        className={combinedClassName}
        disabled={disabled}
        aria-disabled={disabled}
        {...motionProps}
        {...props}
      >
        {children}
      </motion.button>
    )
  }
)

Button.displayName = 'Button'

export { Button }

