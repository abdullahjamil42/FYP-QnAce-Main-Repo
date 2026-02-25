'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

interface EmotionSample {
  timestamp: number  // seconds
  emotions: Record<string, number>
  confidence: number
  faceDetected: boolean
}

export interface EmotionTimelineProps {
  samples: EmotionSample[]
  totalDuration: number
  className?: string
}

const EMOTION_COLORS: Record<string, string> = {
  happy: '#22c55e',      // green
  neutral: '#3b82f6',    // blue
  surprise: '#eab308',   // yellow
  sad: '#a855f7',        // purple
  fear: '#f97316',       // orange
  angry: '#ef4444',      // red
  disgust: '#84cc16',    // lime
}

const EMOTION_LABELS: Record<string, string> = {
  happy: '😊 Happy',
  neutral: '😐 Neutral',
  surprise: '😮 Surprise',
  sad: '😢 Sad',
  fear: '😰 Fear',
  angry: '😠 Angry',
  disgust: '🤢 Disgust',
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function EmotionTimeline({ samples, totalDuration, className }: EmotionTimelineProps) {
  if (!samples || samples.length === 0) {
    return (
      <div className={cn('p-4 text-center text-foreground/60', className)}>
        No emotion timeline data available
      </div>
    )
  }

  // Get dominant emotion for each sample
  const getDominantEmotion = (emotions: Record<string, number>) => {
    return Object.entries(emotions).reduce((a, b) =>
      (b[1] > a[1]) ? b : a
    )
  }

  // Calculate statistics
  const emotionTotals: Record<string, number> = {}
  const emotionCounts: Record<string, number> = {}

  samples.forEach(sample => {
    if (sample.faceDetected) {
      Object.entries(sample.emotions).forEach(([emotion, prob]) => {
        emotionTotals[emotion] = (emotionTotals[emotion] || 0) + prob
        emotionCounts[emotion] = (emotionCounts[emotion] || 0) + 1
      })
    }
  })

  const emotionAverages = Object.entries(emotionTotals).map(([emotion, total]) => ({
    emotion,
    average: total / (emotionCounts[emotion] || 1),
  })).sort((a, b) => b.average - a.average)

  // Find significant changes (for insights)
  const insights: string[] = []

  // Check for emotion shifts
  if (samples.length >= 3) {
    const firstThird = samples.slice(0, Math.floor(samples.length / 3))
    const lastThird = samples.slice(-Math.floor(samples.length / 3))

    const avgFirstHappy = firstThird.reduce((sum, s) => sum + (s.emotions.happy || 0), 0) / firstThird.length
    const avgLastHappy = lastThird.reduce((sum, s) => sum + (s.emotions.happy || 0), 0) / lastThird.length

    const avgFirstFear = firstThird.reduce((sum, s) => sum + (s.emotions.fear || 0), 0) / firstThird.length
    const avgLastFear = lastThird.reduce((sum, s) => sum + (s.emotions.fear || 0), 0) / lastThird.length

    if (avgLastHappy > avgFirstHappy + 0.05) {
      insights.push('✨ You became more confident as the answer progressed')
    }
    if (avgFirstFear > avgLastFear + 0.05) {
      insights.push('👍 Initial nervousness decreased over time')
    }
    if (avgLastFear > avgFirstFear + 0.08) {
      insights.push('⚠️ You seemed more nervous towards the end')
    }
    if (avgFirstHappy > avgLastHappy + 0.05) {
      insights.push('💡 Try to maintain enthusiasm throughout your answer')
    }
  }

  // Find peak moments
  const maxHappySample = samples.reduce((max, s) =>
    (s.emotions.happy || 0) > (max.emotions.happy || 0) ? s : max
    , samples[0])

  if ((maxHappySample.emotions.happy || 0) > 0.08) {
    insights.push(`😊 Most confident moment: ${formatTime(maxHappySample.timestamp)} into your answer`)
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Timeline Visualization */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-foreground/70">Emotion Flow During Answer</h4>

        {/* Timeline bars */}
        <div className="relative">
          {/* Time markers */}
          <div className="flex justify-between text-xs text-foreground/50 mb-2">
            <span>0:00</span>
            <span>{formatTime(totalDuration / 2)}</span>
            <span>{formatTime(totalDuration)}</span>
          </div>

          {/* Stacked emotion bars */}
          <div className="h-12 rounded-lg overflow-hidden flex bg-background-tertiary">
            {samples.map((sample, idx) => {
              const width = 100 / samples.length
              const [dominantEmotion, dominantProb] = getDominantEmotion(sample.emotions)

              return (
                <div
                  key={idx}
                  className="relative group cursor-pointer transition-all hover:opacity-80"
                  style={{
                    width: `${width}%`,
                    backgroundColor: sample.faceDetected
                      ? EMOTION_COLORS[dominantEmotion] || '#6b7280'
                      : '#374151',
                    opacity: sample.faceDetected ? 0.7 + (dominantProb * 0.3) : 0.3,
                  }}
                >
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                    <div className="bg-background-secondary border border-border rounded-lg p-2 shadow-lg text-xs whitespace-nowrap">
                      <div className="font-medium mb-1">{formatTime(sample.timestamp)}</div>
                      {sample.faceDetected ? (
                        <>
                          <div className="flex items-center gap-1">
                            <span>{EMOTION_LABELS[dominantEmotion]}</span>
                            <span className="text-foreground/60">
                              ({Math.round(dominantProb * 100)}%)
                            </span>
                          </div>
                          <div className="text-foreground/50 mt-1">
                            Confidence: {Math.round(sample.confidence * 100)}%
                          </div>
                        </>
                      ) : (
                        <div className="text-foreground/50">Face not detected</div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mt-3 text-xs">
            {emotionAverages.slice(0, 4).map(({ emotion, average }) => (
              <div key={emotion} className="flex items-center gap-1.5">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: EMOTION_COLORS[emotion] }}
                />
                <span className="text-foreground/70">
                  {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                </span>
                <span className="text-foreground/50">
                  ({Math.round(average * 100)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Segment Analysis */}
      <div className="grid grid-cols-3 gap-3">
        {['Beginning', 'Middle', 'End'].map((segment, idx) => {
          const start = Math.floor((idx / 3) * samples.length)
          const end = Math.floor(((idx + 1) / 3) * samples.length)
          const segmentSamples = samples.slice(start, end).filter(s => s.faceDetected)

          if (segmentSamples.length === 0) {
            return (
              <div key={segment} className="p-3 rounded-lg bg-background-tertiary">
                <div className="text-xs font-medium text-foreground/50 mb-1">{segment}</div>
                <div className="text-sm text-foreground/40">No data</div>
              </div>
            )
          }

          const avgEmotions: Record<string, number> = {}
          segmentSamples.forEach(s => {
            Object.entries(s.emotions).forEach(([e, p]) => {
              avgEmotions[e] = (avgEmotions[e] || 0) + p / segmentSamples.length
            })
          })

          const [dominant, prob] = getDominantEmotion(avgEmotions)
          const happy = avgEmotions.happy || 0
          const fear = avgEmotions.fear || 0

          let mood = '😐'
          if (happy > 0.1) mood = '😊'
          else if (fear > 0.15) mood = '😰'
          else if ((avgEmotions.angry || 0) > 0.2) mood = '😤'

          return (
            <div key={segment} className="p-3 rounded-lg bg-background-tertiary">
              <div className="text-xs font-medium text-foreground/50 mb-2">{segment}</div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{mood}</span>
                <div>
                  <div className="text-sm font-medium capitalize">{dominant}</div>
                  <div className="text-xs text-foreground/50">{Math.round(prob * 100)}%</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-foreground/70">Timeline Insights</h4>
          <div className="space-y-1.5">
            {insights.map((insight, idx) => (
              <div
                key={idx}
                className="text-sm text-foreground/80 bg-background-tertiary rounded-lg px-3 py-2"
              >
                {insight}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sample count info */}
      <div className="text-xs text-foreground/40 text-center">
        Based on {samples.filter(s => s.faceDetected).length} emotion samples captured during {formatTime(totalDuration)}
      </div>
    </div>
  )
}
