'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface TimerBarProps {
    duration: number // current duration in seconds
    maxDuration?: number // optional max duration for progress calculation
    isRecording: boolean
    className?: string
}

/**
 * Timer Bar Component
 * 
 * A visible timer progress bar that shows:
 * - Current recording time
 * - Visual progress indicator
 * - Color changes as time progresses
 */
export function TimerBar({
    duration,
    maxDuration = 300, // default 5 minutes max
    isRecording,
    className,
}: TimerBarProps) {
    const progress = Math.min((duration / maxDuration) * 100, 100)

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }

    // Color based on duration thresholds
    const getProgressColor = () => {
        if (duration < 30) return 'bg-yellow-500' // Warming up
        if (duration < 120) return 'bg-green-500' // Good range
        if (duration < 180) return 'bg-blue-500' // Getting long
        return 'bg-orange-500' // Too long
    }

    const getStatusMessage = () => {
        if (!isRecording) return 'Ready to record'
        if (duration < 30) return '🎤 Keep going...'
        if (duration < 60) return '✓ Good length'
        if (duration < 120) return '✓ Great detail'
        if (duration < 180) return '⏱ Consider wrapping up'
        return '⚠️ Very long response'
    }

    return (
        <div className={cn('space-y-1', className)}>
            {/* Timer display */}
            <div className="flex items-center justify-between text-sm">
                <span
                    className={cn(
                        'font-mono text-lg font-semibold',
                        isRecording ? 'text-red-400' : 'text-foreground/60'
                    )}
                >
                    {isRecording && (
                        <span className="inline-block w-2 h-2 mr-2 bg-red-500 rounded-full animate-pulse" />
                    )}
                    {formatTime(duration)}
                </span>
                <span className="text-foreground/60">{getStatusMessage()}</span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-background rounded-full overflow-hidden border border-border/50">
                <div
                    className={cn(
                        'h-full transition-all duration-300 ease-out',
                        getProgressColor(),
                        !isRecording && 'opacity-50'
                    )}
                    style={{ width: `${Math.max(progress, isRecording ? 2 : 0)}%` }}
                />
            </div>

            {/* Time markers */}
            <div className="flex justify-between text-xs text-foreground/40">
                <span>0:00</span>
                <span>1:00</span>
                <span>2:00</span>
                <span>3:00</span>
                <span>5:00</span>
            </div>
        </div>
    )
}

/**
 * Circular Timer Component
 * Alternative timer visualization using a circular progress indicator
 */
export function CircularTimer({
    duration,
    maxDuration = 300,
    isRecording,
    size = 80,
    className,
}: TimerBarProps & { size?: number }) {
    const progress = Math.min((duration / maxDuration) * 100, 100)
    const circumference = 2 * Math.PI * 35 // r=35
    const strokeDashoffset = circumference - (progress / 100) * circumference

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    return (
        <div
            className={cn('relative inline-flex items-center justify-center', className)}
            style={{ width: size, height: size }}
        >
            <svg
                className="transform -rotate-90"
                width={size}
                height={size}
                viewBox="0 0 80 80"
            >
                {/* Background circle */}
                <circle
                    cx="40"
                    cy="40"
                    r="35"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="6"
                    className="text-background/50"
                />
                {/* Progress circle */}
                <circle
                    cx="40"
                    cy="40"
                    r="35"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="6"
                    strokeLinecap="round"
                    className={cn(
                        'transition-all duration-300',
                        isRecording ? 'text-red-500' : 'text-accent/50'
                    )}
                    style={{
                        strokeDasharray: circumference,
                        strokeDashoffset: strokeDashoffset,
                    }}
                />
            </svg>
            {/* Time display */}
            <div className="absolute inset-0 flex items-center justify-center">
                <span
                    className={cn(
                        'font-mono text-sm font-semibold',
                        isRecording ? 'text-red-400' : 'text-foreground/60'
                    )}
                >
                    {formatTime(duration)}
                </span>
            </div>
        </div>
    )
}
