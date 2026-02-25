'use client'

import * as React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  const prefersReducedMotion = useReducedMotion()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = ''
      }
    }
    return undefined
  }, [isOpen])

  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }

  const backdropVariants = prefersReducedMotion
    ? {}
    : {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
      }

  const modalVariants = prefersReducedMotion
    ? {}
    : {
        initial: { opacity: 0, scale: 0.95, y: 20 },
        animate: { opacity: 1, scale: 1, y: 0 },
        exit: { opacity: 0, scale: 0.95, y: 20 },
      }

  if (!mounted) return null

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
            {...backdropVariants}
            transition={{ duration: 0.2 }}
          />

          {/* Modal */}
          <motion.div
            className={cn(
              'relative z-50 w-full rounded-xl border border-foreground/10 bg-gradient-to-br from-gradient-purple/30 to-gradient-blue/30 p-6 shadow-2xl',
              'backdrop-blur-md inner-glow',
              sizes[size]
            )}
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? 'modal-title' : undefined}
            {...modalVariants}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            onClick={(e) => e.stopPropagation()}
          >
            {title && (
              <div className="mb-4 flex items-center justify-between">
                <h2 id="modal-title" className="text-xl font-semibold text-foreground">
                  {title}
                </h2>
                <button
                  onClick={onClose}
                  className="rounded-lg p-1 text-foreground/60 hover:bg-foreground/10 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label="Close modal"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            )}
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

