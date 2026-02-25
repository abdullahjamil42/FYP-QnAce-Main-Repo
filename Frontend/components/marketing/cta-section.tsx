'use client'

import * as React from 'react'
import { motion, Variants } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ArrowRight } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useReducedMotion } from '@/hooks/use-reduced-motion'
import { useAuth } from '@/hooks/use-auth'

export function CTASection() {
  const prefersReducedMotion = useReducedMotion()
  const router = useRouter()
  const { isAuthenticated, needsOnboarding } = useAuth()

  const handleGetStarted = () => {
    if (isAuthenticated) {
      if (needsOnboarding) {
        router.push('/onboarding')
      } else {
        router.push('/dashboard')
      }
    } else {
      router.push('/login')
    }
  }

  const variants: Variants = prefersReducedMotion
    ? {
        initial: { opacity: 1, y: 0 },
        whileInView: { opacity: 1, y: 0 },
      }
    : {
        initial: { opacity: 0, y: 20 },
        whileInView: { opacity: 1, y: 0 },
      }

  return (
    <section className="py-20 bg-gradient-to-br from-gradient-purple/30 via-gradient-blue/30 to-gradient-teal/30">
      <div className="container mx-auto px-4">
        <motion.div
          className="max-w-3xl mx-auto text-center"
          variants={variants}
          initial="initial"
          whileInView="whileInView"
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to <span className="gradient-text">Ace Your Interview</span>?
          </h2>
          <p className="text-xl text-foreground/80 mb-8">
            Join thousands of professionals preparing for their dream jobs with AI-powered feedback.
          </p>
          <Button 
            variant="primary" 
            size="lg" 
            className="group"
            onClick={handleGetStarted}
          >
            Start Practicing Now
            <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
          </Button>
        </motion.div>
      </div>
    </section>
  )
}

