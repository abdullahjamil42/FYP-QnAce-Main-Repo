'use client'

import * as React from 'react'
import { motion, AnimatePresence, Variants } from 'framer-motion'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useReducedMotion } from '@/hooks/use-reduced-motion'

export interface Recommendation {
  id: string
  priority: 'high' | 'medium' | 'low'
  title: string
  description: string
  details?: string
}

export interface RecommendationCardProps {
  recommendation: Recommendation
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const [expanded, setExpanded] = React.useState(false)
  const prefersReducedMotion = useReducedMotion()

  const variants: Variants | undefined = prefersReducedMotion
    ? undefined
    : {
        initial: { height: 0, opacity: 0 },
        animate: { height: 'auto', opacity: 1 },
        exit: { height: 0, opacity: 0 },
      }

  return (
    <Card hoverable>
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={recommendation.priority === 'high' ? 'error' : recommendation.priority === 'medium' ? 'warning' : 'info'}>
                {recommendation.priority}
              </Badge>
              <h3 className="font-semibold">{recommendation.title}</h3>
            </div>
            <p className="text-sm text-foreground/70">{recommendation.description}</p>
          </div>
          {recommendation.details && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 rounded hover:bg-foreground/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-expanded={expanded}
              aria-label={expanded ? 'Collapse details' : 'Expand details'}
            >
              {expanded ? (
                <ChevronUp className="h-5 w-5" />
              ) : (
                <ChevronDown className="h-5 w-5" />
              )}
            </button>
          )}
        </div>

        <AnimatePresence>
          {expanded && recommendation.details && (
            <motion.div
              variants={variants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="pt-3 border-t border-foreground/10">
                <p className="text-sm text-foreground/60">{recommendation.details}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  )
}

