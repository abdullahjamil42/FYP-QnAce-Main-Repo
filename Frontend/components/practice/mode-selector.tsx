'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Briefcase, GraduationCap, Eye, EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Interview mode types:
 * - 'practice': Real-time hints enabled (eye contact, speaking pace)
 * - 'mock': No real-time feedback, final report only
 */
export type InterviewMode = 'practice' | 'mock'

export interface ModeSelectorProps {
  onModeSelect: (mode: InterviewMode) => void
  selectedMode?: InterviewMode
}

/**
 * Mode Selector Component
 * 
 * Allows users to choose between Practice Mode and Mock Interview Mode
 * before starting their recording session.
 * 
 * - Practice Mode: Shows real-time hints during recording
 * - Mock Interview Mode: No hints, simulates real interview conditions
 */
export function ModeSelector({ onModeSelect, selectedMode }: ModeSelectorProps) {
  const [mode, setMode] = React.useState<InterviewMode | null>(selectedMode || null)

  const handleSelectMode = (selectedMode: InterviewMode) => {
    setMode(selectedMode)
  }

  const handleConfirm = () => {
    if (mode) {
      onModeSelect(mode)
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Choose Your Mode</h2>
        <p className="text-foreground/60">
          Select how you want to practice this interview question
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Practice Mode Card */}
        <Card
          className={cn(
            'cursor-pointer transition-all hover:border-accent/50',
            mode === 'practice' && 'border-accent ring-2 ring-accent/20'
          )}
          onClick={() => handleSelectMode('practice')}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-lg bg-gradient-to-r from-green-500/20 to-emerald-500/20">
                <GraduationCap className="h-6 w-6 text-green-400" />
              </div>
              <Badge variant="success">Recommended for beginners</Badge>
            </div>

            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Practice Mode
              </h3>
              <p className="text-sm text-foreground/60 mt-1">
                Get real-time feedback while practicing
              </p>
            </div>

            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                Live emotion feedback
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                Eye contact indicators
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                Speaking pace guidance
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                Full analysis report
              </li>
            </ul>
          </div>
        </Card>

        {/* Mock Interview Mode Card */}
        <Card
          className={cn(
            'cursor-pointer transition-all hover:border-accent/50',
            mode === 'mock' && 'border-accent ring-2 ring-accent/20'
          )}
          onClick={() => handleSelectMode('mock')}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-lg bg-gradient-to-r from-blue-500/20 to-purple-500/20">
                <Briefcase className="h-6 w-6 text-blue-400" />
              </div>
              <Badge variant="info">Simulates real interview</Badge>
            </div>

            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <EyeOff className="h-5 w-5" />
                Mock Interview Mode
              </h3>
              <p className="text-sm text-foreground/60 mt-1">
                No distractions, like a real interview
              </p>
            </div>

            <ul className="space-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="text-blue-400">✓</span>
                No real-time hints
              </li>
              <li className="flex items-center gap-2">
                <span className="text-blue-400">✓</span>
                Focus on natural delivery
              </li>
              <li className="flex items-center gap-2">
                <span className="text-blue-400">✓</span>
                Timer-only recording
              </li>
              <li className="flex items-center gap-2">
                <span className="text-blue-400">✓</span>
                Full analysis report after
              </li>
            </ul>
          </div>
        </Card>
      </div>

      {/* Confirm Button */}
      <div className="flex justify-center">
        <Button
          onClick={handleConfirm}
          disabled={!mode}
          variant="primary"
          size="lg"
          className="min-w-[200px]"
        >
          {mode ? `Start ${mode === 'practice' ? 'Practice' : 'Mock Interview'}` : 'Select a Mode'}
        </Button>
      </div>
    </div>
  )
}
