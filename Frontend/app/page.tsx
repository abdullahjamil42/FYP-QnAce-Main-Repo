'use client'

import { motion } from 'framer-motion'
import { Navbar } from '@/components/marketing/navbar'
import { Hero } from '@/components/marketing/hero'
import { Features } from '@/components/marketing/features'
import { DemoCard } from '@/components/marketing/demo-card'
import { CTASection } from '@/components/marketing/cta-section'

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <Navbar />
      <Hero />
      <section id="demo" className="py-24 bg-background relative overflow-hidden scroll-mt-20">
        {/* Subtle background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-gradient-purple/5 to-transparent pointer-events-none" />
        
        <div className="container mx-auto px-4 relative z-10">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center mb-12"
            >
              <h2 className="text-4xl md:text-5xl font-bold mb-4">
                See It In <span className="gradient-text">Action</span>
              </h2>
              <p className="text-lg text-foreground/60 max-w-2xl mx-auto">
                Watch how Q&Ace analyzes your interview responses in real-time with multi-modal feedback
              </p>
            </motion.div>
            <DemoCard />
          </div>
        </div>
      </section>
      <Features />
      <CTASection />
    </main>
  )
}

