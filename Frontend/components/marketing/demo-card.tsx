'use client'

import * as React from 'react'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useReducedMotion } from '@/hooks/use-reduced-motion'
import { useAuth } from '@/hooks/use-auth'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Play } from 'lucide-react'

const demoSnippets = [
  {
    id: 1,
    face: '😊',
    waveform: [20, 45, 30, 60, 40, 55, 35, 50, 45, 40, 35, 48, 42, 52, 38, 45],
    transcript: 'I have been working as a software engineer for the past five years, focusing primarily on backend development and system architecture.',
    score: 85,
  },
  {
    id: 2,
    face: '🤔',
    waveform: [30, 50, 35, 55, 45, 50, 40, 45, 50, 45, 42, 48, 40, 52, 45, 48],
    transcript: 'In my previous role, I led a team of developers to deliver a distributed system that handled millions of requests per day.',
    score: 78,
  },
  {
    id: 3,
    face: '😌',
    waveform: [25, 40, 35, 50, 45, 55, 40, 50, 45, 40, 38, 48, 42, 52, 40, 46],
    transcript: 'I believe my experience with distributed systems makes me well-suited for this role, as I understand scalability challenges.',
    score: 82,
  },
]

export function DemoCard() {
  const [currentIndex, setCurrentIndex] = React.useState(0)
  const prefersReducedMotion = useReducedMotion()
  const { isAuthenticated, needsOnboarding } = useAuth()
  const router = useRouter()

  React.useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % demoSnippets.length)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const currentSnippet = demoSnippets[currentIndex]

  const handleTryDemo = () => {
    if (isAuthenticated) {
      // Logged in user - go to practice
      if (needsOnboarding) {
        router.push('/onboarding')
      } else {
        router.push('/practice')
      }
    } else {
      // Not logged in - go to demo mode
      router.push('/demo')
    }
  }

  const variants: Variants | undefined = prefersReducedMotion
    ? undefined
    : {
        initial: { opacity: 0, y: 10, scale: 0.98 },
        animate: { opacity: 1, y: 0, scale: 1 },
        exit: { opacity: 0, y: -10, scale: 0.98 },
      }

  return (
    <Card className="overflow-hidden relative border-2 border-foreground/20 bg-gradient-to-br from-gradient-purple/30 via-gradient-blue/30 to-gradient-teal/20 backdrop-blur-sm">
      {/* Subtle glow effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-accent/5 via-transparent to-accent-purple/5 pointer-events-none" />
      
      <div className="relative p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            <h3 className="text-lg font-semibold">Live Demo</h3>
          </div>
          <div className="px-3 py-1 rounded-full bg-accent/10 border border-accent/30">
            <span className="text-xs font-medium text-accent">{currentSnippet.score}% Score</span>
          </div>
        </div>

        <div className="space-y-6">
          {/* Face indicator with animated container */}
          <div className="flex items-center justify-center">
            <motion.div
              className="relative"
              whileHover={prefersReducedMotion ? {} : { scale: 1.1 }}
              transition={{ duration: 0.2 }}
            >
              <div className="absolute inset-0 bg-accent/20 rounded-full blur-xl" />
              <div className="relative flex items-center justify-center h-24 w-24 rounded-full bg-gradient-to-br from-accent/20 to-accent-purple/20 border border-accent/30">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentSnippet.id}
                    className="text-5xl"
                    variants={variants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                  >
                    {currentSnippet.face}
                  </motion.div>
                </AnimatePresence>
              </div>
            </motion.div>
          </div>

          {/* Enhanced Waveform */}
          <div className="relative">
            <div className="flex items-end justify-center gap-1 h-20 px-4">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentSnippet.id}
                  className="flex items-end justify-center gap-1.5 w-full"
                  variants={variants}
                  initial="initial"
                  animate="animate"
                  exit="exit"
                  transition={{ duration: 0.4, ease: 'easeOut' }}
                >
                  {currentSnippet.waveform.map((height, i) => (
                    <motion.div
                      key={i}
                      className="bg-gradient-to-t from-accent to-accent-purple rounded-t flex-1 min-w-[3px]"
                      style={{
                        height: `${height}%`,
                      }}
                      initial={prefersReducedMotion ? {} : { height: 0 }}
                      animate={{ height: `${height}%` }}
                      transition={{
                        duration: 0.5,
                        delay: i * 0.03,
                        ease: 'easeOut',
                      }}
                    />
                  ))}
                </motion.div>
              </AnimatePresence>
            </div>
            {/* Waveform baseline */}
            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
          </div>

          {/* Transcript with better styling */}
          <div className="min-h-[80px] flex items-center">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentSnippet.id}
                className="w-full"
                variants={variants}
                initial="initial"
                animate="animate"
                exit="exit"
                transition={{ duration: 0.4, ease: 'easeOut' }}
              >
                <p className="text-base text-foreground/80 text-center leading-relaxed px-4">
                  "{currentSnippet.transcript}"
                </p>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Enhanced Indicators */}
        <div className="flex items-center justify-center gap-3 mt-8 pt-6 border-t border-foreground/10">
          {demoSnippets.map((snippet, index) => (
            <button
              key={index}
              onClick={() => setCurrentIndex(index)}
              className={cn(
                'relative h-2 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                index === currentIndex
                  ? 'w-10 bg-accent shadow-glow'
                  : 'w-2 bg-foreground/20 hover:bg-foreground/30'
              )}
              aria-label={`View demo ${index + 1}: ${snippet.score}% score`}
              aria-current={index === currentIndex ? 'true' : 'false'}
            >
              {index === currentIndex && (
                <motion.div
                  className="absolute inset-0 rounded-full bg-accent"
                  layoutId="activeIndicator"
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                />
              )}
            </button>
          ))}
        </div>

        {/* Try Demo Button */}
        <div className="mt-6 flex justify-center">
          <Button 
            variant="primary" 
            size="lg" 
            className="group"
            onClick={handleTryDemo}
          >
            <Play className="mr-2 h-5 w-5" />
            Try It Yourself
          </Button>
        </div>
      </div>
    </Card>
  )
}

