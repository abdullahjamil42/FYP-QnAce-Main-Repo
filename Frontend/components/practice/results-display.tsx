'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
    Eye,
    Mic,
    Brain,
    CheckCircle,
    TrendingUp,
    RefreshCw,
    ChevronRight,
    Award,
    MessageSquare,
    Volume2,
    Target,
    BarChart3,
    Sparkles,
    Lightbulb,
    PlayCircle
} from 'lucide-react'
import type { MultimodalAnalysisResult } from '@/lib/api'
import { STARBreakdown } from './star-breakdown'
import { CompetencyRadarChart } from './competency-radar-chart'
import { LLMJudgeFeedback } from './llm-judge-feedback'

export interface ResultsDisplayProps {
    result: MultimodalAnalysisResult
    question?: {
        id: string
        text: string
        category: string
    }
    onRetry?: () => void
    onNextQuestion?: () => void
    onSaveProgress?: () => void
    className?: string
}

type TabType = 'overview' | 'facial' | 'voice' | 'text' | 'detailed'


/**
 * Results Display Component
 * 
 * Restructured results page with:
 * 1. Overall Performance section
 * 2. Modality Breakdown tabs (Facial/Voice/Text)
 * 3. Detailed Analysis tab with new scoring visualizations
 * 4. Actionable Recommendations with Coaching insights
 */
export function ResultsDisplay({
    result,
    question,
    onRetry,
    onNextQuestion,
    onSaveProgress,
    className,
}: ResultsDisplayProps) {
    const [activeTab, setActiveTab] = React.useState<TabType>('overview')

    // Check if coaching data is available
    const coaching = result.coaching

    // Check if advanced scoring is available
    const hasAdvancedScoring = coaching && (
        coaching.star_breakdown ||
        coaching.llm_judge_score !== undefined ||
        coaching.bert_score_f1 !== undefined
    )

    const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
        { id: 'overview', label: 'Overview', icon: <Award className="h-4 w-4" /> },
        { id: 'facial', label: 'Facial', icon: <Eye className="h-4 w-4" /> },
        { id: 'voice', label: 'Voice', icon: <Volume2 className="h-4 w-4" /> },
        { id: 'text', label: 'Answer', icon: <Brain className="h-4 w-4" /> },
        ...(hasAdvancedScoring ? [{
            id: 'detailed' as TabType,
            label: 'Deep Analysis',
            icon: <BarChart3 className="h-4 w-4" />
        }] : []),
    ]

    // Generate tips - use coaching data if available, fallback to legacy logic
    const generateTips = () => {
        const tips: { type: 'facial' | 'voice' | 'text'; tip: string }[] = []

        if (coaching && coaching.success) {
            // Use coaching-provided tips
            if (coaching.content_tip) {
                tips.push({ type: 'text', tip: coaching.content_tip.what_to_improve })
            }
            if (coaching.voice_tip) {
                tips.push({ type: 'voice', tip: coaching.voice_tip.what_to_improve })
            }
            if (coaching.facial_tip) {
                tips.push({ type: 'facial', tip: coaching.facial_tip.what_to_improve })
            }
        } else {
            // Fallback to legacy tip generation
            // Facial tip
            if (result.facial) {
                if (result.facial.dominant_emotion === 'fear' || result.facial.dominant_emotion === 'sad') {
                    tips.push({ type: 'facial', tip: 'Try to relax your facial muscles and maintain a calm, confident expression.' })
                } else if (!result.facial.face_detected) {
                    tips.push({ type: 'facial', tip: 'Make sure your face is clearly visible and well-lit for accurate analysis.' })
                } else {
                    tips.push({ type: 'facial', tip: 'Maintain consistent eye contact with the camera to appear more engaged.' })
                }
            }

            // Voice tip
            if (result.voice) {
                if (result.voice.dominant_emotion === 'fear') {
                    tips.push({ type: 'voice', tip: 'Practice speaking more slowly and take deep breaths to sound calmer.' })
                } else if (result.voice.dominant_emotion === 'sad') {
                    tips.push({ type: 'voice', tip: 'Add more energy and enthusiasm to your voice to engage the interviewer.' })
                } else {
                    tips.push({ type: 'voice', tip: 'Vary your pitch and pace to keep your delivery engaging and natural.' })
                }
            }

            // Text tip
            if (result.text) {
                if (result.text.quality_label === 'Poor') {
                    tips.push({ type: 'text', tip: 'Use the STAR method (Situation, Task, Action, Result) to structure your answers.' })
                } else if (result.text.quality_label === 'Average') {
                    tips.push({ type: 'text', tip: 'Include more specific examples and quantifiable achievements.' })
                } else {
                    tips.push({ type: 'text', tip: 'Great content! Keep providing detailed, well-structured responses.' })
                }
            }
        }

        return tips
    }

    // Generate "What went well" items from coaching data
    const getWhatWentWell = () => {
        if (!coaching || !coaching.success) return []

        const items: { type: 'facial' | 'voice' | 'text'; tip: string }[] = []

        if (coaching.content_tip?.what_went_well) {
            items.push({ type: 'text', tip: coaching.content_tip.what_went_well })
        }
        if (coaching.voice_tip?.what_went_well) {
            items.push({ type: 'voice', tip: coaching.voice_tip.what_went_well })
        }
        if (coaching.facial_tip?.what_went_well) {
            items.push({ type: 'facial', tip: coaching.facial_tip.what_went_well })
        }

        return items
    }

    const tips = generateTips()

    const getScoreColor = (score: number) => {
        if (score >= 70) return 'text-green-400'
        if (score >= 40) return 'text-amber-400'
        return 'text-red-400'
    }

    const getScoreBg = (score: number) => {
        if (score >= 70) return 'bg-green-500'
        if (score >= 40) return 'bg-amber-500'
        return 'bg-red-500'
    }

    return (
        <Card
            className={cn(
                'bg-slate-900/50 border-slate-800 backdrop-blur-md overflow-hidden',
                className
            )}
        >
            {/* AI Synthesis Header - Prominent Brief */}
            {coaching?.generated_feedback && (
                <div className="bg-gradient-to-r from-indigo-500/20 via-purple-500/20 to-blue-500/20 p-6 border-b border-indigo-500/20">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-indigo-500/20 rounded-xl text-indigo-400">
                            <Sparkles className="h-6 w-6" />
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-sm font-bold uppercase tracking-wider text-indigo-300">AI Synthesis</h4>
                            <p className="text-lg text-white font-medium leading-relaxed italic">
                                "{coaching.generated_feedback}"
                            </p>
                        </div>
                    </div>
                </div>
            )}

            <div className="p-6 space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                            Performance Analysis
                        </h3>
                        {question && (
                            <p className="text-sm text-slate-400">{question.category} Question</p>
                        )}
                    </div>
                    {result.text && (
                        <div className="text-right">
                            <Badge
                                variant={
                                    result.text.quality_label === 'Excellent'
                                        ? 'success'
                                        : result.text.quality_label === 'Average'
                                            ? 'info'
                                            : 'error'
                                }
                                className="px-3 py-1 text-sm font-bold"
                            >
                                {result.text.quality_label}
                            </Badge>
                        </div>
                    )}
                </div>

                {/* Tab Navigation */}
                <div className="flex gap-2 p-1 bg-background/50 rounded-lg">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={cn(
                                'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                                activeTab === tab.id
                                    ? 'bg-accent text-accent-foreground'
                                    : 'text-foreground/60 hover:text-foreground hover:bg-background/50'
                            )}
                        >
                            {tab.icon}
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="min-h-[200px]">
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            {/* Answer Quality Verdict & Progress Bar */}
                            {coaching && (
                                <div className="p-6 rounded-2xl bg-slate-800/40 border border-slate-700/50 space-y-6">
                                    <div className="text-center space-y-2">
                                        <div className="inline-flex items-center justify-center p-2 bg-accent/10 rounded-lg text-accent mb-2">
                                            <Target className="h-5 w-5" />
                                        </div>
                                        <h4 className={cn("text-xl font-bold", getScoreColor(coaching.progress_position || 50))}>
                                            {coaching.quality_interpretation || 'On the Right Track'}
                                        </h4>
                                        <p className="text-slate-300 max-w-lg mx-auto leading-relaxed">
                                            {coaching.quality_description}
                                        </p>
                                    </div>

                                    {/* Segmented Progress Bar */}
                                    <div className="space-y-3">
                                        <div className="flex justify-between items-end mb-1">
                                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Mastery Level</span>
                                            <span className={cn("text-lg font-black", getScoreColor(coaching.progress_position || 50))}>
                                                {coaching.progress_position?.toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="flex gap-1.5 h-3">
                                            {[1, 2, 3, 4, 5].map((segment) => {
                                                const threshold = segment * 20
                                                const score = coaching.progress_position || 0
                                                const isActive = score >= threshold - 10 // Show partial fill
                                                const isFullyActive = score >= threshold

                                                return (
                                                    <div
                                                        key={segment}
                                                        className={cn(
                                                            "flex-1 rounded-sm transition-all duration-700",
                                                            isFullyActive ? getScoreBg(score) :
                                                                isActive ? `${getScoreBg(score)}/40` : "bg-slate-700/30"
                                                        )}
                                                    />
                                                )
                                            })}
                                        </div>
                                        <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase">
                                            <span>Needs Work</span>
                                            <span className="text-center">Developing</span>
                                            <span>Excellent</span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* What could improve - Insight Cards */}
                            {coaching?.improvement_tips && coaching.improvement_tips.length > 0 && (
                                <div className="space-y-4 pt-4">
                                    <h5 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                        <Lightbulb className="h-4 w-4 text-amber-400" />
                                        Key Insights to Improve
                                    </h5>
                                    <div className="grid grid-cols-1 gap-4">
                                        {coaching.improvement_tips.slice(0, 3).map((tip, i) => {
                                            // Determine icon/color based on keywords
                                            let Icon = MessageSquare
                                            let colorClass = "bg-blue-500/10 text-blue-400"
                                            let borderColor = "border-blue-500/20"

                                            if (tip.toLowerCase().includes('star') || tip.toLowerCase().includes('structure')) {
                                                Icon = BarChart3
                                                colorClass = "bg-purple-500/10 text-purple-400"
                                                borderColor = "border-purple-500/20"
                                            } else if (tip.toLowerCase().includes('impact') || tip.toLowerCase().includes('result')) {
                                                Icon = TrendingUp
                                                colorClass = "bg-green-500/10 text-green-400"
                                                borderColor = "border-green-500/20"
                                            } else if (tip.toLowerCase().includes('context') || tip.toLowerCase().includes('problem')) {
                                                Icon = Target
                                                colorClass = "bg-amber-500/10 text-amber-400"
                                                borderColor = "border-amber-500/20"
                                            }

                                            return (
                                                <div
                                                    key={i}
                                                    className={cn("group flex gap-4 p-5 rounded-xl border transition-all hover:translate-x-1 bg-slate-800/20", borderColor)}
                                                >
                                                    <div className={cn("p-2.5 rounded-lg h-fit", colorClass)}>
                                                        <Icon className="h-5 w-5" />
                                                    </div>
                                                    <div className="space-y-2 flex-1">
                                                        <div className="text-sm text-slate-200 leading-relaxed font-medium">
                                                            {tip.split(':').map((part, idx) => (
                                                                idx === 0 ? <span key={idx} className="block text-white font-bold mb-1 text-base">{part}</span> : <span key={idx}>{part}</span>
                                                            ))}
                                                        </div>
                                                        <div className="flex gap-2 pt-2">
                                                            {tip.toLowerCase().includes('star') && (
                                                                <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase font-bold tracking-tight bg-white/5 hover:bg-white/10">
                                                                    <PlayCircle className="mr-1 h-3 w-3" /> See Example
                                                                </Button>
                                                            )}
                                                            <Button variant="ghost" size="sm" className="h-7 text-[10px] uppercase font-bold tracking-tight text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10">
                                                                <Sparkles className="mr-1 h-3 w-3" /> Fix This with AI
                                                            </Button>
                                                        </div>
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Facial Tab */}
                    {activeTab === 'facial' && result.facial && (
                        <div className="space-y-4">
                            <div className="p-4 rounded-lg bg-background/50">
                                <h4 className="font-medium mb-3 flex items-center gap-2">
                                    <Eye className="h-5 w-5" />
                                    Facial Expression Analysis
                                </h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <span className="text-sm text-foreground/60">Dominant Emotion</span>
                                        <p className="text-lg font-semibold capitalize">
                                            {result.facial.dominant_emotion}
                                        </p>
                                    </div>
                                    <div>
                                        <span className="text-sm text-foreground/60">Confidence</span>
                                        <p className="text-lg font-semibold">
                                            {(result.facial.confidence * 100).toFixed(0)}%
                                        </p>
                                    </div>
                                </div>
                                {result.facial.emotions && (
                                    <div className="mt-4 space-y-2">
                                        <span className="text-sm text-foreground/60">Emotion Breakdown</span>
                                        <div className="space-y-2">
                                            {Object.entries(result.facial.emotions)
                                                .sort(([, a], [, b]) => (b as number) - (a as number))
                                                .slice(0, 3)
                                                .map(([emotion, value]) => (
                                                    <EmotionBar
                                                        key={emotion}
                                                        emotion={emotion}
                                                        value={value as number}
                                                    />
                                                ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Voice Tab */}
                    {activeTab === 'voice' && result.voice && (
                        <div className="space-y-4">
                            <div className="p-4 rounded-lg bg-background/50">
                                <h4 className="font-medium mb-3 flex items-center gap-2">
                                    <Volume2 className="h-5 w-5" />
                                    Voice Analysis
                                </h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <span className="text-sm text-foreground/60">Dominant Emotion</span>
                                        <p className="text-lg font-semibold capitalize">
                                            {result.voice.dominant_emotion}
                                        </p>
                                    </div>
                                    <div>
                                        <span className="text-sm text-foreground/60">Confidence</span>
                                        <p className="text-lg font-semibold">
                                            {(result.voice.confidence * 100).toFixed(0)}%
                                        </p>
                                    </div>
                                </div>
                                {result.voice.emotions && (
                                    <div className="mt-4 space-y-2">
                                        <span className="text-sm text-foreground/60">Emotion Breakdown</span>
                                        <div className="space-y-2">
                                            {Object.entries(result.voice.emotions)
                                                .sort(([, a], [, b]) => (b as number) - (a as number))
                                                .slice(0, 3)
                                                .map(([emotion, value]) => (
                                                    <EmotionBar
                                                        key={emotion}
                                                        emotion={emotion}
                                                        value={value as number}
                                                    />
                                                ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Text Tab */}
                    {activeTab === 'text' && result.text && (
                        <div className="space-y-4">
                            <div className="p-4 rounded-lg bg-background/50">
                                <h4 className="font-medium mb-3 flex items-center gap-2">
                                    <Brain className="h-5 w-5" />
                                    Answer Quality Analysis
                                </h4>
                                <div className="grid grid-cols-2 gap-4 mb-4">
                                    <div>
                                        <span className="text-sm text-foreground/60">Quality</span>
                                        <p className="text-lg font-semibold">{result.text.quality_label}</p>
                                    </div>
                                    <div>
                                        <span className="text-sm text-foreground/60">Score</span>
                                        <p className="text-lg font-semibold">
                                            {result.text.quality_score.toFixed(0)}%
                                        </p>
                                    </div>
                                </div>
                                {result.text.reason && (
                                    <div className="p-3 rounded-lg bg-background/50 border border-border/50">
                                        <span className="text-sm text-foreground/60">Analysis</span>
                                        <p className="mt-1">{result.text.reason}</p>
                                    </div>
                                )}
                                <div className="mt-4">
                                    <span className="text-sm text-foreground/60">Feedback</span>
                                    <p className="mt-1 text-foreground/80">{result.text.feedback}</p>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Coaching Insights - What Went Well */}
                {coaching && coaching.success && (
                    <div className="space-y-3">
                        <h4 className="font-semibold flex items-center gap-2 text-green-400">
                            <CheckCircle className="h-5 w-5" />
                            What Went Well
                        </h4>
                        <div className="grid grid-cols-1 gap-2">
                            {getWhatWentWell().map((item, i) => (
                                <div
                                    key={i}
                                    className="flex items-start gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/20"
                                >
                                    <div
                                        className={cn(
                                            'p-1.5 rounded-lg',
                                            item.type === 'facial' && 'bg-blue-500/20 text-blue-400',
                                            item.type === 'voice' && 'bg-green-500/20 text-green-400',
                                            item.type === 'text' && 'bg-purple-500/20 text-purple-400'
                                        )}
                                    >
                                        {item.type === 'facial' && <Eye className="h-4 w-4" />}
                                        {item.type === 'voice' && <Mic className="h-4 w-4" />}
                                        {item.type === 'text' && <MessageSquare className="h-4 w-4" />}
                                    </div>
                                    <p className="text-sm text-foreground/80">{item.tip}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* What to Improve Next */}
                <div className="space-y-3">
                    <h4 className="font-semibold flex items-center gap-2 text-yellow-400">
                        <TrendingUp className="h-5 w-5" />
                        {coaching && coaching.success ? 'What to Improve Next' : 'Recommendations'}
                    </h4>
                    <div className="grid grid-cols-1 gap-2">
                        {tips.map((tip, i) => (
                            <div
                                key={i}
                                className={cn(
                                    "flex items-start gap-3 p-3 rounded-lg",
                                    coaching && coaching.success
                                        ? "bg-yellow-500/10 border border-yellow-500/20"
                                        : "bg-background/50"
                                )}
                            >
                                <div
                                    className={cn(
                                        'p-1.5 rounded-lg',
                                        tip.type === 'facial' && 'bg-blue-500/20 text-blue-400',
                                        tip.type === 'voice' && 'bg-green-500/20 text-green-400',
                                        tip.type === 'text' && 'bg-purple-500/20 text-purple-400'
                                    )}
                                >
                                    {tip.type === 'facial' && <Eye className="h-4 w-4" />}
                                    {tip.type === 'voice' && <Mic className="h-4 w-4" />}
                                    {tip.type === 'text' && <MessageSquare className="h-4 w-4" />}
                                </div>
                                <div className="flex-1">
                                    <p className="text-sm text-foreground/80">{tip.tip}</p>
                                    {/* Show reason if from coaching */}
                                    {coaching && coaching.success && (
                                        <p className="text-xs text-foreground/50 mt-1">
                                            {tip.type === 'text' && coaching.content_tip?.reason}
                                            {tip.type === 'voice' && coaching.voice_tip?.reason}
                                            {tip.type === 'facial' && coaching.facial_tip?.reason}
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Disclaimer */}
                <p className="text-xs text-slate-500 text-center italic mt-4">
                    Our AI models compare your answer to thousands of high-quality reference responses to identify specific competency gaps.
                </p>

                {/* Deep Analysis Tab */}
                {activeTab === 'detailed' && coaching && (
                    <div className="space-y-6">
                        {/* Competency Radar */}
                        {(coaching.bert_score_f1 !== undefined || coaching.star_breakdown) && (
                            <CompetencyRadarChart
                                data={{
                                    semanticAccuracy: (coaching.bert_score_f1 || 0) * 100,
                                    qualityScore: (coaching.llm_judge_score || 5) * 10,
                                    structureScore: coaching.star_breakdown
                                        ? (coaching.star_breakdown.situation +
                                            coaching.star_breakdown.task +
                                            coaching.star_breakdown.action +
                                            coaching.star_breakdown.result) / 4
                                        : 50,
                                    relevance: (coaching.content_relevance || 3) * 20,
                                    coherence: (coaching.coherence_score || 3) * 20
                                }}
                            />
                        )}

                        {/* LLM Judge Feedback */}
                        {coaching.llm_judge_score !== undefined && (
                            <LLMJudgeFeedback
                                score={coaching.llm_judge_score}
                                rationale={coaching.llm_judge_rationale || ''}
                                actionableTips={coaching.llm_actionable_tips}
                            />
                        )}

                        {/* STAR Structure Breakdown */}
                        {coaching.star_breakdown && (
                            <STARBreakdown
                                breakdown={coaching.star_breakdown}
                                contentRelevance={coaching.content_relevance}
                                coherenceScore={coaching.coherence_score}
                            />
                        )}

                        {/* BERTScore Details */}
                        {coaching.bert_score_f1 !== undefined && (
                            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-5 border border-slate-700/50">
                                <div className="flex items-center gap-2 mb-4">
                                    <Brain className="w-5 h-5 text-cyan-400" />
                                    <h3 className="text-lg font-semibold text-white">Semantic Similarity</h3>
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="text-center p-3 rounded-lg bg-slate-900/50">
                                        <p className="text-2xl font-bold text-cyan-400">
                                            {Math.round((coaching.bert_score_f1 || 0) * 100)}%
                                        </p>
                                        <p className="text-xs text-slate-400">F1 Score</p>
                                    </div>
                                    <div className="text-center p-3 rounded-lg bg-slate-900/50">
                                        <p className="text-2xl font-bold text-blue-400">
                                            {Math.round((coaching.bert_score_precision || 0) * 100)}%
                                        </p>
                                        <p className="text-xs text-slate-400">Precision</p>
                                    </div>
                                    <div className="text-center p-3 rounded-lg bg-slate-900/50">
                                        <p className="text-2xl font-bold text-purple-400">
                                            {Math.round((coaching.bert_score_recall || 0) * 100)}%
                                        </p>
                                        <p className="text-xs text-slate-400">Recall</p>
                                    </div>
                                </div>
                                <p className="text-xs text-slate-400 mt-3 text-center">
                                    How closely your answer matches the semantic meaning of excellent reference answers.
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4 border-t border-border/50">
                    {onRetry && (
                        <Button
                            onClick={onRetry}
                            variant="primary" // Changed from outline to primary/secondary based on project UI-kit
                            className="flex-1 bg-white/5 border-white/10 hover:bg-white/10"
                        >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Retry Question
                        </Button>
                    )}
                    {onNextQuestion && (
                        <Button onClick={onNextQuestion} variant="primary" className="flex-1">
                            Try Another
                            <ChevronRight className="ml-2 h-4 w-4" />
                        </Button>
                    )}
                    {onSaveProgress && (
                        <Button onClick={onSaveProgress} variant="ghost" size="sm">
                            Save Progress
                        </Button>
                    )}
                </div>
            </div>
        </Card>
    )
}

// Helper Components



function EmotionBar({ emotion, value }: { emotion: string; value: number }) {
    return (
        <div className="flex items-center gap-2">
            <span className="w-20 text-sm capitalize truncate">{emotion}</span>
            <div className="flex-1 h-2 bg-background rounded-full overflow-hidden">
                <div
                    className="h-full bg-accent transition-all"
                    style={{ width: `${value * 100}%` }}
                />
            </div>
            <span className="text-sm text-foreground/60 w-12 text-right">
                {(value * 100).toFixed(0)}%
            </span>
        </div>
    )
}
