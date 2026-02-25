'use client'

/**
 * STAR Breakdown Component
 * 
 * Displays a visual breakdown of the STAR method components:
 * - Situation (20% ideal)
 * - Task (10% ideal)  
 * - Action (60% ideal)
 * - Result (10% ideal)
 * 
 * Each component shows a progress bar with color coding based on score.
 */

import React from 'react'
import { AlertCircle, CheckCircle2, Target, Zap, TrendingUp } from 'lucide-react'

interface STARBreakdownProps {
    breakdown: {
        situation: number
        task: number
        action: number
        result: number
    }
    contentRelevance?: number  // 1-5
    coherenceScore?: number    // 1-5
    className?: string
}

const starLabels = {
    situation: {
        label: 'Situation',
        description: 'Context setting',
        icon: Target,
        idealWeight: 20,
        color: 'from-blue-500 to-blue-600'
    },
    task: {
        label: 'Task',
        description: 'Challenge faced',
        icon: AlertCircle,
        idealWeight: 10,
        color: 'from-amber-500 to-amber-600'
    },
    action: {
        label: 'Action',
        description: 'Steps taken',
        icon: Zap,
        idealWeight: 60,
        color: 'from-green-500 to-green-600'
    },
    result: {
        label: 'Result',
        description: 'Outcome & impact',
        icon: TrendingUp,
        idealWeight: 10,
        color: 'from-purple-500 to-purple-600'
    }
}

function getScoreColor(score: number): string {
    if (score >= 70) return 'text-green-400'
    if (score >= 40) return 'text-amber-400'
    return 'text-red-400'
}

function getBarColor(score: number): string {
    if (score >= 70) return 'from-green-500 to-green-600'
    if (score >= 40) return 'from-amber-500 to-amber-600'
    return 'from-red-500 to-red-600'
}

function RubricScore({ label, score, maxScore = 5 }: { label: string; score: number; maxScore?: number }) {
    const normalizedScore = Math.min(score, maxScore)
    const percentage = (normalizedScore / maxScore) * 100

    return (
        <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400 min-w-[100px]">{label}</span>
            <div className="flex gap-1">
                {Array.from({ length: maxScore }, (_, i) => (
                    <div
                        key={i}
                        className={`w-3 h-3 rounded-full transition-colors ${i < normalizedScore
                            ? 'bg-gradient-to-br from-indigo-400 to-purple-500'
                            : 'bg-slate-700'
                            }`}
                    />
                ))}
            </div>
            <span className={`text-sm font-medium ${getScoreColor(percentage)}`}>
                {normalizedScore}/{maxScore}
            </span>
        </div>
    )
}

export function STARBreakdown({
    breakdown,
    contentRelevance = 3,
    coherenceScore = 3,
    className = ''
}: STARBreakdownProps) {
    const components = ['situation', 'task', 'action', 'result'] as const

    return (
        <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-5 border border-slate-700/50 ${className}`}>
            <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-5 h-5 text-indigo-400" />
                <h3 className="text-lg font-semibold text-white">STAR Structure Analysis</h3>
            </div>

            {/* STAR Component Bars */}
            <div className="space-y-4 mb-6">
                {components.map((key) => {
                    const config = starLabels[key]
                    const score = breakdown[key]
                    const Icon = config.icon

                    return (
                        <div key={key} className="space-y-1.5">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Icon className="w-4 h-4 text-slate-400" />
                                    <span className="text-sm font-medium text-white">{config.label}</span>
                                    <span className="text-xs text-slate-500">({config.description})</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`text-sm font-semibold ${getScoreColor(score)}`}>
                                        {Math.round(score)}%
                                    </span>
                                    <span className="text-xs text-slate-500">
                                        (ideal: {config.idealWeight}%)
                                    </span>
                                </div>
                            </div>

                            {/* Progress bar container */}
                            <div className="relative h-2.5 bg-slate-700/50 rounded-full overflow-hidden">
                                {/* Ideal position marker */}
                                <div
                                    className="absolute top-0 bottom-0 w-0.5 bg-white/30 z-10"
                                    style={{ left: `${config.idealWeight}%` }}
                                />

                                {/* Score bar */}
                                <div
                                    className={`h-full bg-gradient-to-r ${getBarColor(score)} rounded-full transition-all duration-500`}
                                    style={{ width: `${Math.min(score, 100)}%` }}
                                />
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* Divider */}
            <div className="border-t border-slate-700/50 pt-4">
                <h4 className="text-sm font-medium text-slate-300 mb-3">Quality Rubrics</h4>
                <div className="space-y-2">
                    <RubricScore label="Content Relevance" score={contentRelevance} />
                    <RubricScore label="Coherence & Logic" score={coherenceScore} />
                </div>
            </div>
        </div>
    )
}

export default STARBreakdown
