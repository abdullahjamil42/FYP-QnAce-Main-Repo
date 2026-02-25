'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { AnalysisGauge } from './analysis-gauge'
import { RecommendationCard } from './recommendation-card'
import { SparklineChart } from '@/components/ui/chart'
import { AnalysisResult } from '@/lib/mock-data'
import { Eye, Mic, Brain } from 'lucide-react'

export interface ReportSummaryProps {
  analysis: AnalysisResult
  progress?: {
    facial: number[]
    vocal: number[]
    content: number[]
    dates: string[]
  }
}

export function ReportSummary({ analysis, progress }: ReportSummaryProps) {
  const sections = [
    {
      icon: Eye,
      title: 'Facial Analysis',
      score: analysis.facial.score,
      metrics: analysis.facial.metrics,
      recommendations: analysis.facial.recommendations,
      progress: progress?.facial,
    },
    {
      icon: Mic,
      title: 'Vocal Analysis',
      score: analysis.vocal.score,
      metrics: analysis.vocal.metrics,
      recommendations: analysis.vocal.recommendations,
      progress: progress?.vocal,
    },
    {
      icon: Brain,
      title: 'Content Analysis',
      score: analysis.content.score,
      metrics: analysis.content.metrics,
      recommendations: analysis.content.recommendations,
      progress: progress?.content,
    },
  ]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {sections.map((section, index) => {
        const Icon = section.icon
        return (
          <Card key={index} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-accent/10">
                <Icon className="h-5 w-5 text-accent" />
              </div>
              <h2 className="text-xl font-semibold">{section.title}</h2>
            </div>

            <AnalysisGauge score={section.score} label="Overall Score" />

            {section.progress && section.progress.length > 0 && (
              <div>
                <p className="text-sm text-foreground/60 mb-2">Progress Trend</p>
                <SparklineChart data={section.progress} width={200} height={40} />
              </div>
            )}

            <div>
              <h3 className="text-sm font-semibold mb-2">Key Metrics</h3>
              <div className="space-y-2">
                {Object.entries(section.metrics).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm text-foreground/60 capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </span>
                    <span className="text-sm font-medium">{value}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-2">Recommendations</h3>
              <div className="space-y-2">
                {section.recommendations.map((rec) => (
                  <RecommendationCard key={rec.id} recommendation={rec} />
                ))}
              </div>
            </div>
          </Card>
        )
      })}
    </div>
  )
}

