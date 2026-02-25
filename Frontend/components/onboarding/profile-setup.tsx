'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

export interface ProfileData {
  name: string
  role: string
  experienceLevel: 'entry' | 'mid' | 'senior' | 'executive'
}

export interface ProfileSetupProps {
  data?: ProfileData
  onSubmit: (data: ProfileData) => void
  onBack?: () => void
}

// Consistent input styles for onboarding
const inputStyles = `
  w-full px-4 py-3 rounded-xl 
  bg-white text-black 
  border border-gray-300 
  placeholder:text-gray-400
  hover:border-gray-400
  focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent/50 
  transition-all duration-200
`

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

export function ProfileSetup({ data, onSubmit, onBack }: ProfileSetupProps) {
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileData>({
    defaultValues: data,
  })

  const onFormSubmit = async (formData: ProfileData) => {
    setIsSubmitting(true)
    // Small delay for UX feedback
    await new Promise(resolve => setTimeout(resolve, 300))
    onSubmit(formData)
  }

  return (
    <Card hoverable={false}>
      <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">Tell Us About Yourself</h2>
          <p className="text-foreground/60">Let's start with some basic information</p>
        </div>

        <div className="space-y-1">
          <label htmlFor="name" className="block text-sm font-medium text-foreground/80">
            Full Name
          </label>
          <input
            id="name"
            type="text"
            {...register('name', { required: 'Name is required' })}
            className={inputStyles}
            placeholder="John Doe"
            aria-invalid={errors.name ? 'true' : 'false'}
            aria-describedby={errors.name ? 'name-error' : undefined}
            disabled={isSubmitting}
          />
          {errors.name && (
            <p id="name-error" className="mt-1 text-sm text-red-400" role="alert">
              {errors.name.message}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="role" className="block text-sm font-medium text-foreground/80">
            Current Role
          </label>
          <input
            id="role"
            type="text"
            {...register('role', { required: 'Role is required' })}
            className={inputStyles}
            placeholder="e.g., Software Engineer"
            aria-invalid={errors.role ? 'true' : 'false'}
            aria-describedby={errors.role ? 'role-error' : undefined}
            disabled={isSubmitting}
          />
          {errors.role && (
            <p id="role-error" className="mt-1 text-sm text-red-400" role="alert">
              {errors.role.message}
            </p>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="experienceLevel" className="block text-sm font-medium text-foreground/80">
            Experience Level
          </label>
          <select
            id="experienceLevel"
            {...register('experienceLevel', { required: 'Experience level is required' })}
            className={selectStyles}
            aria-invalid={errors.experienceLevel ? 'true' : 'false'}
            aria-describedby={errors.experienceLevel ? 'experience-error' : undefined}
            disabled={isSubmitting}
          >
            <option value="">Select experience level</option>
            <option value="entry">Entry Level (0-2 years)</option>
            <option value="mid">Mid Level (3-5 years)</option>
            <option value="senior">Senior Level (6+ years)</option>
            <option value="executive">Executive</option>
          </select>
          {errors.experienceLevel && (
            <p id="experience-error" className="mt-1 text-sm text-red-400" role="alert">
              {errors.experienceLevel.message}
            </p>
          )}
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
                Saving...
              </>
            ) : (
              'Continue'
            )}
          </Button>
        </div>
      </form>
    </Card>
  )
}

