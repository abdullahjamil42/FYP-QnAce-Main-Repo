'use client'

import * as React from 'react'
import { motion, Variants } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ArrowRight, Sparkles } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useReducedMotion } from '@/hooks/use-reduced-motion'
import { useAuth } from '@/hooks/use-auth'

export function Hero() {
  const prefersReducedMotion = useReducedMotion()
  const router = useRouter()
  const { isAuthenticated, needsOnboarding } = useAuth()

  const handleGetStarted = () => {
    if (isAuthenticated) {
      // User is logged in
      if (needsOnboarding) {
        router.push('/onboarding')
      } else {
        router.push('/dashboard')
      }
    } else {
      // User is not logged in
      router.push('/login')
    }
  }

  const containerVariants: Variants | undefined = prefersReducedMotion
    ? undefined
    : {
      initial: { opacity: 0 },
      animate: {
        opacity: 1,
        transition: {
          staggerChildren: 0.2,
          delayChildren: 0.1,
        },
      },
    }

  const itemVariants: Variants | undefined = prefersReducedMotion
    ? undefined
    : {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
    }

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden gradient-bg pt-20 md:pt-24">
      {/* Particle/Noise Layer */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255,255,255,0.15) 1px, transparent 0)`,
          backgroundSize: '40px 40px',
        }} />
      </div>

      <div className="relative z-10 container mx-auto px-4 py-20">
        <motion.div
          className="max-w-4xl mx-auto text-center"
          variants={containerVariants}
          initial="initial"
          animate="animate"
        >
          <motion.div variants={itemVariants} className="mb-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-2 backdrop-blur-sm">
              <Sparkles className="h-4 w-4 text-accent" />
              <span className="text-sm font-medium text-accent">AI-Powered Interview Coach</span>
            </div>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="text-5xl md:text-7xl font-bold mb-6 leading-tight"
          >
            <span className="gradient-text">Master Your Interview</span>
            <br />
            <span className="text-foreground">With AI Feedback</span>
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-xl md:text-2xl text-foreground/80 mb-10 max-w-2xl mx-auto"
          >
            Get real-time multi-modal feedback on your facial expressions, voice tone, and content
            to ace your next high-stakes interview.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Button 
              variant="primary" 
              size="lg" 
              className="group"
              onClick={handleGetStarted}
            >
              Get Started
              <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button 
              variant="ghost" 
              size="lg"
              onClick={() => {
                document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })
              }}
            >
              Watch Demo
            </Button>
          </motion.div>
        </motion.div>
      </div>

      {/* Gradient overlay at bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
    </section>
  )
}

