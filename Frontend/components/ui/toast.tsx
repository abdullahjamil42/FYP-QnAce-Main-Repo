'use client'

import * as React from 'react'
import { createContext, useContext, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(7)
    setToasts((prev) => [...prev, { ...toast, id }])

    const duration = toast.duration ?? 5000
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, duration)
    }
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  const prefersReducedMotion = useReducedMotion()

  const icons = {
    success: CheckCircle,
    error: AlertCircle,
    info: Info,
    warning: AlertTriangle,
  }

  const styles = {
    success: 'bg-green-500/20 border-green-500/50 text-green-400',
    error: 'bg-red-500/20 border-red-500/50 text-red-400',
    info: 'bg-accent/20 border-accent/50 text-accent',
    warning: 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400',
  }

  const variants = prefersReducedMotion
    ? {}
    : {
        initial: { opacity: 0, y: -20, scale: 0.95 },
        animate: { opacity: 1, y: 0, scale: 1 },
        exit: { opacity: 0, y: -20, scale: 0.95 },
      }

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = icons[toast.type]
          return (
            <motion.div
              key={toast.id}
              className={cn(
                'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg backdrop-blur-sm',
                styles[toast.type]
              )}
              {...variants}
              transition={{ duration: 0.2 }}
            >
              <Icon className="h-5 w-5" />
              <p className="flex-1 text-sm font-medium">{toast.message}</p>
              <button
                onClick={() => removeToast(toast.id)}
                className="rounded p-1 hover:bg-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                aria-label="Close toast"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

