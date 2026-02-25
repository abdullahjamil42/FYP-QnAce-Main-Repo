'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Check, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface InterviewTypeData {
  interviewTypes: string[]
}

const interviewTypes = [
  { id: 'technical', label: 'Technical', description: 'Coding challenges and system design' },
  { id: 'behavioral', label: 'Behavioral', description: 'STAR method and situational questions' },
  { id: 'system-design', label: 'System Design', description: 'Architecture and scalability' },
  { id: 'leadership', label: 'Leadership', description: 'Team management and decision-making' },
  { id: 'product', label: 'Product', description: 'Product thinking and strategy' },
  { id: 'culture-fit', label: 'Culture Fit', description: 'Values and team alignment' },
]

export interface InterviewTypeProps {
  data?: InterviewTypeData
  onSubmit: (data: InterviewTypeData) => void
  onBack?: () => void
}

export function InterviewType({ data, onSubmit, onBack }: InterviewTypeProps) {
  const [selected, setSelected] = React.useState<string[]>(data?.interviewTypes || [])
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const toggleSelection = (id: string) => {
    if (isSubmitting) return
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const handleSubmit = async () => {
    if (selected.length > 0) {
      setIsSubmitting(true)
      await new Promise(resolve => setTimeout(resolve, 300))
      onSubmit({ interviewTypes: selected })
    }
  }

  return (
    <Card hoverable={false}>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">What Are You Preparing For?</h2>
          <p className="text-foreground/60">Select the types of interviews you want to practice</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {interviewTypes.map((type) => {
            const isSelected = selected.includes(type.id)
            return (
              <button
                key={type.id}
                type="button"
                onClick={() => toggleSelection(type.id)}
                disabled={isSubmitting}
                className={cn(
                  'relative p-4 rounded-xl border-2 text-left transition-all duration-200',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-background',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  isSelected
                    ? 'border-accent bg-accent/10 shadow-[0_0_20px_rgba(0,217,255,0.15)]'
                    : 'border-foreground/10 bg-foreground/5 hover:border-foreground/20 hover:bg-foreground/[0.07]'
                )}
                aria-pressed={isSelected}
              >
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <div className="rounded-full bg-accent p-1 shadow-[0_0_10px_rgba(0,217,255,0.5)]">
                      <Check className="h-3.5 w-3.5 text-background" />
                    </div>
                  </div>
                )}
                <h3 className="font-semibold mb-1 pr-8">{type.label}</h3>
                <p className="text-sm text-foreground/60">{type.description}</p>
              </button>
            )
          })}
        </div>

        {selected.length === 0 && (
          <p className="text-sm text-amber-400" role="alert">
            Please select at least one interview type
          </p>
        )}

        <div className="flex gap-4 pt-2">
          {onBack && (
            <Button type="button" variant="ghost" onClick={onBack} disabled={isSubmitting}>
              Back
            </Button>
          )}
          <Button
            type="button"
            variant="primary"
            className="flex-1"
            onClick={handleSubmit}
            disabled={selected.length === 0 || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Continue'
            )}
          </Button>
        </div>
      </div>
    </Card>
  )
}

