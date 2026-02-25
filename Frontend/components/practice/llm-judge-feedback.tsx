'use client'

/**
 * LLM Judge Feedback Component
 * 
 * Displays the LLM-as-a-Judge evaluation results:
 * - Overall quality score (1-10)
 * - Detailed rationale
 * - Actionable improvement tips
 */

import React from 'react'
import { Brain, Lightbulb, MessageSquare, Star } from 'lucide-react'

interface LLMJudgeFeedbackProps {
    score: number           // 1-10
    rationale: string       // Explanation for the score
    actionableTips?: string[]  // Specific improvement tips
    className?: string
}

function getScoreColor(score: number): string {
    if (score >= 8) return 'from-green-400 to-emerald-500'
    if (score >= 6) return 'from-amber-400 to-orange-500'
    if (score >= 4) return 'from-orange-400 to-red-500'
    return 'from-red-400 to-rose-600'
}

function getScoreLabel(score: number): string {
    if (score >= 9) return 'Excellent'
    if (score >= 7) return 'Good'
    if (score >= 5) return 'Fair'
    if (score >= 3) return 'Needs Work'
    return 'Poor'
}

function ScoreMeter({ score }: { score: number }) {
    const percentage = (score / 10) * 100

    return (
        <div className="relative flex items-center justify-center">
            {/* Background circle */}
            <svg className="w-24 h-24 transform -rotate-90">
                <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="rgba(100, 116, 139, 0.3)"
                    strokeWidth="8"
                />
                <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke={score >= 6 ? '#34d399' : score >= 4 ? '#fbbf24' : '#f87171'}
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={`${percentage * 2.51} 251`}
                    className="transition-all duration-700"
                />
            </svg>
            {/* Score in center */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-2xl font-bold bg-gradient-to-r ${getScoreColor(score)} bg-clip-text text-transparent`}>
                    {score}
                </span>
                <span className="text-xs text-slate-400">/10</span>
            </div>
        </div>
    )
}

export function LLMJudgeFeedback({
    score,
    rationale,
    actionableTips = [],
    className = ''
}: LLMJudgeFeedbackProps) {
    return (
        <div className={`bg-slate-800/50 backdrop-blur-sm rounded-xl p-5 border border-slate-700/50 ${className}`}>
            <div className="flex items-center gap-2 mb-4">
                <Brain className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-semibold text-white">AI Quality Assessment</h3>
            </div>

            {/* Score Section */}
            <div className="flex items-center gap-6 mb-5">
                <ScoreMeter score={score} />
                <div className="flex-1">
                    <div className={`text-xl font-semibold bg-gradient-to-r ${getScoreColor(score)} bg-clip-text text-transparent mb-1`}>
                        {getScoreLabel(score)}
                    </div>
                    <div className="flex items-center gap-1">
                        {Array.from({ length: 10 }, (_, i) => (
                            <Star
                                key={i}
                                className={`w-4 h-4 ${i < score
                                    ? 'text-amber-400 fill-amber-400'
                                    : 'text-slate-600'
                                    }`}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* Rationale */}
            {rationale && (
                <div className="mb-5">
                    <div className="flex items-center gap-2 mb-2">
                        <MessageSquare className="w-4 h-4 text-slate-400" />
                        <span className="text-sm font-medium text-slate-300">Why this score?</span>
                    </div>
                    <p className="text-sm text-slate-400 leading-relaxed bg-slate-900/50 rounded-lg p-3 border border-slate-700/30">
                        {rationale}
                    </p>
                </div>
            )}

            {/* Actionable Tips */}
            {actionableTips && actionableTips.length > 0 && (
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <Lightbulb className="w-4 h-4 text-amber-400" />
                        <span className="text-sm font-medium text-slate-300">How to improve</span>
                    </div>
                    <ul className="space-y-2">
                        {actionableTips.map((tip, index) => (
                            <li key={index} className="flex items-start gap-3">
                                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs text-white font-medium">
                                    {index + 1}
                                </span>
                                <span className="text-sm text-slate-300 leading-relaxed">{tip}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    )
}

export default LLMJudgeFeedback
