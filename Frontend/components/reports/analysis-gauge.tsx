'use client'

import * as React from 'react'
import { Gauge } from '@/components/ui/chart'

export interface AnalysisGaugeProps {
  score: number
  label: string
  size?: number
}

export function AnalysisGauge({ score, label, size = 80 }: AnalysisGaugeProps) {
  return (
    <div className="flex flex-col items-center space-y-2">
      <Gauge value={score} max={100} size={size} aria-label={`${label} score: ${score}%`} />
      <div className="text-center">
        <p className="text-2xl font-bold">{score}%</p>
        <p className="text-sm text-foreground/60">{label}</p>
      </div>
    </div>
  )
}

