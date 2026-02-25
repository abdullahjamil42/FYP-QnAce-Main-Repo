'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { ProfileSetup, type ProfileData } from '@/components/onboarding/profile-setup'
import { InterviewType, type InterviewTypeData } from '@/components/onboarding/interview-type'
import { GoalsPreferences, type GoalsData } from '@/components/onboarding/goals-preferences'
import { useAuth } from '../../hooks/use-auth'
import { useToast } from '@/components/ui/toast'
import { useReducedMotion } from '../../hooks/use-reduced-motion'
import { hasCompletedOnboarding } from '../../lib/auth'
import { Loader2 } from 'lucide-react'

type Step = 'profile' | 'interview-type' | 'goals'

export default function OnboardingPage() {
  const router = useRouter()
  const { user, isAuthenticated, loading, completeOnboarding } = useAuth()
  const { addToast } = useToast()
  const prefersReducedMotion = useReducedMotion()

  const [currentStep, setCurrentStep] = React.useState<Step>('profile')
  const [isReady, setIsReady] = React.useState(false)
  const [formData, setFormData] = React.useState<{
    profile?: ProfileData
    interviewType?: InterviewTypeData
    goals?: GoalsData
  }>({})

  // Redirect logic - only after auth state is loaded
  React.useEffect(() => {
    // Wait for auth to load
    if (loading) return

    // If not logged in, redirect to login
    if (!isAuthenticated) {
      router.replace('/login')
      return
    }
    
    // If already completed onboarding, redirect to dashboard
    if (hasCompletedOnboarding()) {
      router.replace('/dashboard')
      return
    }

    // Auth is ready and user needs onboarding
    setIsReady(true)
  }, [isAuthenticated, loading, router])

  // Pre-fill profile data if user exists
  React.useEffect(() => {
    if (user && !formData.profile) {
      setFormData(prev => ({
        ...prev,
        profile: {
          name: user.name || '',
          role: user.role || '',
          experienceLevel: user.experienceLevel || 'entry',
        }
      }))
    }
  }, [user, formData.profile])

  const handleProfileSubmit = (data: ProfileData) => {
    setFormData((prev) => ({ ...prev, profile: data }))
    setCurrentStep('interview-type')
  }

  const handleInterviewTypeSubmit = (data: InterviewTypeData) => {
    setFormData((prev) => ({ ...prev, interviewType: data }))
    setCurrentStep('goals')
  }

  const handleGoalsSubmit = async (data: GoalsData) => {
    // Compile all onboarding data
    const profileData = {
      name: formData.profile!.name,
      role: formData.profile!.role,
      experienceLevel: formData.profile!.experienceLevel,
      interviewTypes: formData.interviewType!.interviewTypes,
      goals: data,
    }

    // Save to user profile and mark onboarding as complete
    completeOnboarding(profileData)
    
    addToast({
      type: 'success',
      message: 'Welcome to Q&Ace! Your profile has been set up.',
    })
    router.push('/dashboard')
  }

  const steps: Step[] = ['profile', 'interview-type', 'goals']
  const currentStepIndex = steps.indexOf(currentStep)

  const variants: Variants = prefersReducedMotion
    ? {}
    : {
      initial: { opacity: 0, x: 20 },
      animate: { opacity: 1, x: 0 },
      exit: { opacity: 0, x: -20 },
    }

  // Show loading while checking auth state
  if (!isReady) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    )
  }

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            {steps.map((step, index) => (
              <div
                key={step}
                className={`flex-1 h-2 rounded-full ${index <= currentStepIndex ? 'bg-accent' : 'bg-foreground/10'
                  }`}
              />
            ))}
          </div>
          <p className="text-sm text-foreground/60 text-center">
            Step {currentStepIndex + 1} of {steps.length}
          </p>
        </div>

        {/* Step content */}
        <AnimatePresence mode="wait">
          {currentStep === 'profile' && (
            <motion.div
              key="profile"
              variants={variants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.3 }}
            >
              <ProfileSetup
                data={formData.profile}
                onSubmit={handleProfileSubmit}
              />
            </motion.div>
          )}

          {currentStep === 'interview-type' && (
            <motion.div
              key="interview-type"
              variants={variants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.3 }}
            >
              <InterviewType
                data={formData.interviewType}
                onSubmit={handleInterviewTypeSubmit}
                onBack={() => setCurrentStep('profile')}
              />
            </motion.div>
          )}

          {currentStep === 'goals' && (
            <motion.div
              key="goals"
              variants={variants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.3 }}
            >
              <GoalsPreferences
                data={formData.goals}
                onSubmit={handleGoalsSubmit}
                onBack={() => setCurrentStep('interview-type')}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

