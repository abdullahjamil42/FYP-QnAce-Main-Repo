'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

export interface GoalsData {
  targetCompanies?: string[]
  timeline?: string
  focusAreas?: string[]
}

export interface GoalsPreferencesProps {
  data?: GoalsData
  onSubmit: (data: GoalsData) => void
  onBack?: () => void
}

const commonCompanies = ['Google', 'Meta', 'Amazon', 'Microsoft', 'Apple', 'Netflix', 'Airbnb', 'Uber']
const focusAreas = [
  'System Design',
  'Algorithms',
  'Data Structures',
  'System Architecture',
  'Distributed Systems',
  'API Design',
]

// Consistent select styles
const selectStyles = `
  w-full px-4 py-3 rounded-xl 
  bg-white text-black 
  border border-gray-300 
  hover:border-gray-400
  focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent/50 
  transition-all duration-200
  appearance-none cursor-pointer
  bg-[url('data:image/svg+xml;charset=UTF-8,%3csvg%20xmlns%3d%22http%3a%2f%2fwww.w3.org%2f2000%2fsvg%22%20width%3d%2224%22%20height%3d%2224%22%20viewBox%3d%220%200%2024%2024%22%20fill%3d%22none%22%20stroke%3d%22%23888%22%20stroke-width%3d%222%22%20stroke-linecap%3d%22round%22%20stroke-linejoin%3d%22round%22%3e%3cpolyline%20points%3d%226%209%2012%2015%2018%209%22%3e%3c%2fpolyline%3e%3c%2fsvg%3e')]
  bg-[length:20px] bg-[right_12px_center] bg-no-repeat
`

export function GoalsPreferences({ data, onSubmit, onBack }: GoalsPreferencesProps) {
  const [targetCompanies, setTargetCompanies] = React.useState<string[]>(
    data?.targetCompanies || []
  )
  const [focusAreasSelected, setFocusAreasSelected] = React.useState<string[]>(
    data?.focusAreas || []
  )
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const {
    register,
    handleSubmit,
  } = useForm<{ timeline: string }>({
    defaultValues: { timeline: data?.timeline },
  })

  const toggleCompany = (company: string) => {
    if (isSubmitting) return
    setTargetCompanies((prev) =>
      prev.includes(company) ? prev.filter((c) => c !== company) : [...prev, company]
    )
  }

  const toggleFocusArea = (area: string) => {
    if (isSubmitting) return
    setFocusAreasSelected((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    )
  }

  const onFormSubmit = async (formData: { timeline: string }) => {
    setIsSubmitting(true)
    await new Promise(resolve => setTimeout(resolve, 500))
    onSubmit({
      targetCompanies,
      timeline: formData.timeline,
      focusAreas: focusAreasSelected,
    })
  }

  return (
    <Card hoverable={false}>
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">Set Your Goals</h2>
          <p className="text-foreground/60">Help us personalize your interview preparation</p>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-foreground/80">
            Target Companies <span className="text-foreground/40">(Optional)</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {commonCompanies.map((company) => {
              const isSelected = targetCompanies.includes(company)
              return (
                <button
                  key={company}
                  type="button"
                  onClick={() => toggleCompany(company)}
                  disabled={isSubmitting}
                  className={cn(
                    'px-4 py-2 rounded-full text-sm font-medium transition-all duration-200',
                    'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-background',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    isSelected
                      ? 'bg-accent text-background shadow-[0_0_15px_rgba(0,217,255,0.3)]'
                      : 'bg-foreground/5 text-foreground border border-foreground/10 hover:bg-foreground/10 hover:border-foreground/20'
                  )}
                  aria-pressed={isSelected}
                >
                  {company}
                </button>
              )
            })}
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="timeline" className="block text-sm font-medium text-foreground/80">
            Timeline
          </label>
          <select
            id="timeline"
            {...register('timeline')}
            className={selectStyles}
            disabled={isSubmitting}
          >
            <option value="">Select timeline</option>
            <option value="1 month">1 month</option>
            <option value="3 months">3 months</option>
            <option value="6 months">6 months</option>
            <option value="1 year">1 year</option>
          </select>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-foreground/80">
            Focus Areas <span className="text-foreground/40">(Optional)</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {focusAreas.map((area) => {
              const isSelected = focusAreasSelected.includes(area)
              return (
                <button
                  key={area}
                  type="button"
                  onClick={() => toggleFocusArea(area)}
                  disabled={isSubmitting}
                  className={cn(
                    'px-4 py-2 rounded-full text-sm font-medium transition-all duration-200',
                    'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-background',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    isSelected
                      ? 'bg-accent text-background shadow-[0_0_15px_rgba(0,217,255,0.3)]'
                      : 'bg-foreground/5 text-foreground border border-foreground/10 hover:bg-foreground/10 hover:border-foreground/20'
                  )}
                  aria-pressed={isSelected}
                >
                  {area}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex gap-4 pt-2">
          {onBack && (
            <Button type="button" variant="ghost" onClick={onBack} disabled={isSubmitting}>
              Back
            </Button>
          )}
          <Button type="submit" variant="primary" className="flex-1" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Completing Setup...
              </>
            ) : (
              'Complete Setup'
            )}
          </Button>
        </div>
      </form>
    </Card>
  )
}

