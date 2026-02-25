'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface ChartProps extends React.SVGProps<SVGSVGElement> {
  data: number[]
  width?: number
  height?: number
  color?: string
  className?: string
  'aria-label'?: string
  'aria-describedby'?: string
}

export function SparklineChart({
  data,
  width = 100,
  height = 30,
  color = 'var(--color-accent)',
  className,
  'aria-label': ariaLabel,
  'aria-describedby': ariaDescribedBy,
  ...props
}: ChartProps) {
  if (data.length === 0) return null

  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1 || 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <svg
      width={width}
      height={height}
      className={cn('overflow-visible', className)}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      role="img"
      {...props}
    >
      <title>{ariaLabel || 'Sparkline chart'}</title>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export interface GaugeProps {
  value: number
  max?: number
  size?: number
  strokeWidth?: number
  color?: string
  className?: string
  'aria-label'?: string
}

export function Gauge({
  value,
  max = 100,
  size = 60,
  strokeWidth = 6,
  color = 'var(--color-accent)',
  className,
  'aria-label': ariaLabel,
}: GaugeProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  const offset = circumference - (percentage / 100) * circumference

  return (
    <svg
      width={size}
      height={size}
      className={cn('transform -rotate-90', className)}
      aria-label={ariaLabel || `Gauge showing ${percentage.toFixed(0)}%`}
      role="img"
    >
      <title>{ariaLabel || `Gauge: ${percentage.toFixed(0)}%`}</title>
      {/* Background circle */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        className="text-foreground/10"
      />
      {/* Value circle */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-500"
      />
    </svg>
  )
}

