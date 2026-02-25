'use client'

import * as React from 'react'
import { motion, Variants } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Video, Mic, Brain, TrendingUp, Shield, Zap } from 'lucide-react'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

const features = [
  {
    icon: Video,
    title: 'Facial Analysis',
    description: 'Real-time feedback on eye contact, posture, and expressions to build confidence.',
  },
  {
    icon: Mic,
    title: 'Vocal Analysis',
    description: 'Improve your tone, pace, and clarity with AI-powered voice analysis.',
  },
  {
    icon: Brain,
    title: 'Content Analysis',
    description: 'Get NLP-powered insights on your responses structure and relevance.',
  },
  {
    icon: TrendingUp,
    title: 'Progress Tracking',
    description: 'Visualize your improvement over time with detailed progress charts.',
  },
  {
    icon: Shield,
    title: 'Privacy First',
    description: 'Your recordings are processed securely and never shared without consent.',
  },
  {
    icon: Zap,
    title: 'Instant Feedback',
    description: 'Get comprehensive analysis results within seconds of completing your practice.',
  },
]

export function Features() {
  const prefersReducedMotion = useReducedMotion()

  const containerVariants: Variants | undefined = prefersReducedMotion
    ? undefined
    : {
        initial: { opacity: 0 },
        animate: {
          opacity: 1,
          transition: {
            staggerChildren: 0.1,
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
    <section id="features" className="py-20 bg-background scroll-mt-20">
      <div className="container mx-auto px-4">
        <motion.div
          className="text-center mb-16"
          variants={itemVariants}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true }}
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Everything You Need to <span className="gradient-text">Succeed</span>
          </h2>
          <p className="text-xl text-foreground/60 max-w-2xl mx-auto">
            Comprehensive interview preparation powered by advanced AI analysis
          </p>
        </motion.div>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          variants={containerVariants}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true }}
        >
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <motion.div key={index} variants={itemVariants}>
                <Card hoverable className="h-full">
                  <div className="flex flex-col items-start">
                    <div className="mb-4 p-3 rounded-lg bg-accent/10">
                      <Icon className="h-6 w-6 text-accent" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                    <p className="text-foreground/60">{feature.description}</p>
                  </div>
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      </div>
    </section>
  )
}

