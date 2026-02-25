'use client'

import * as React from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

export interface CardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode
  hoverable?: boolean
  className?: string
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, hoverable = true, className, ...props }, ref) => {
    const prefersReducedMotion = useReducedMotion()

    const motionProps = prefersReducedMotion || !hoverable
      ? {}
      : {
          whileHover: { scale: 1.02, y: -4 },
          transition: { duration: 0.2, ease: 'easeOut' },
        }

    return (
      <motion.div
        ref={ref}
        className={cn(
          'relative rounded-xl border border-foreground/10 bg-gradient-to-br from-gradient-purple/20 to-gradient-blue/20 p-6',
          'backdrop-blur-sm inner-glow',
          hoverable && 'cursor-pointer transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
          className
        )}
        tabIndex={hoverable ? 0 : undefined}
        role={hoverable ? 'button' : undefined}
        {...motionProps}
        {...props}
      >
        {hoverable && (
          <div className="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-accent to-accent-purple opacity-0 transition-opacity duration-200 group-hover:opacity-100" />
        )}
        {children}
      </motion.div>
    )
  }
)

Card.displayName = 'Card'

export { Card }

