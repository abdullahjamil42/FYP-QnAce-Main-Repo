'use client'

import * as React from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

export interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function Logo({ className, size = 'md' }: LogoProps) {
  const prefersReducedMotion = useReducedMotion()

  const sizes = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl',
  }

  const motionProps = prefersReducedMotion
    ? {}
    : {
        whileHover: { scale: 1.05 },
        whileTap: { scale: 0.95 },
        transition: { duration: 0.2 },
      }

  return (
    <Link href="/" className={`flex items-center gap-2 group ${className ?? ''}`} aria-label="Q&Ace Home">
      <motion.div className="relative" {...motionProps}>
        {/* Glow effect */}
        <div className="absolute inset-0 bg-accent/20 rounded-lg blur-md group-hover:blur-lg transition-all duration-300" />
        
        {/* Logo container */}
        <div className="relative px-3 py-1.5 rounded-lg bg-gradient-to-br from-accent/20 to-accent-purple/20 border border-accent/30 backdrop-blur-sm">
          <span className={`font-bold gradient-text ${sizes[size]}`}>
            Q&Ace
          </span>
        </div>
      </motion.div>
    </Link>
  )
}

