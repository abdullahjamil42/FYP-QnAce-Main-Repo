'use client'

import * as React from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { RefreshCw, ChevronRight, Save, History, Trash2 } from 'lucide-react'
import { useSessionHistory, SessionRecord } from '@/hooks/use-session-history'

export interface SessionActionsProps {
    onRetry: () => void
    onNextQuestion: () => void
    onSaveProgress: () => void
    isSaving?: boolean
    className?: string
}

/**
 * Session Actions Component
 * 
 * Provides action buttons after completing an interview session:
 * - Retry same question
 * - Try similar/next question
 * - Save to progress history
 */
export function SessionActions({
    onRetry,
    onNextQuestion,
    onSaveProgress,
    isSaving = false,
    className,
}: SessionActionsProps) {
    return (
        <div className={cn('flex flex-wrap gap-3', className)}>
            <Button onClick={onRetry} variant="outline" className="flex-1 min-w-[140px]">
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry Question
            </Button>
            <Button onClick={onNextQuestion} variant="primary" className="flex-1 min-w-[140px]">
                Try Another
                <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
            <Button
                onClick={onSaveProgress}
                variant="ghost"
                disabled={isSaving}
                className="min-w-[120px]"
            >
                {isSaving ? (
                    <>
                        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                    </>
                ) : (
                    <>
                        <Save className="mr-2 h-4 w-4" />
                        Save Progress
                    </>
                )}
            </Button>
        </div>
    )
}

/**
 * Session History Panel
 * 
 * Displays recent session history with progress stats
 */
export function SessionHistoryPanel({ className }: { className?: string }) {
    const { sessions, getProgressStats, clearHistory, isLoaded } = useSessionHistory()
    const [showHistory, setShowHistory] = React.useState(false)

    const stats = getProgressStats()

    if (!isLoaded) return null

    return (
        <Card className={cn('p-4', className)}>
            <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <h3 className="font-semibold flex items-center gap-2">
                        <History className="h-5 w-5" />
                        Your Progress
                    </h3>
                    {sessions.length > 0 && (
                        <button
                            onClick={() => setShowHistory(!showHistory)}
                            className="text-sm text-accent hover:underline"
                        >
                            {showHistory ? 'Hide' : 'View'} History
                        </button>
                    )}
                </div>

                {/* Stats */}
                {sessions.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <StatCard label="Sessions" value={stats.totalSessions} />
                        <StatCard label="Avg Confidence" value={`${stats.averageConfidence}%`} />
                        <StatCard label="Avg Clarity" value={`${stats.averageClarity}%`} />
                        <StatCard
                            label="Improvement"
                            value={`${stats.improvement >= 0 ? '+' : ''}${stats.improvement}%`}
                            highlight={stats.improvement > 0}
                        />
                    </div>
                ) : (
                    <div className="text-center py-4 text-foreground/60">
                        <p>No sessions recorded yet. Complete an interview to start tracking your progress!</p>
                    </div>
                )}

                {/* History List */}
                {showHistory && sessions.length > 0 && (
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                        {sessions.slice(0, 10).map((session) => (
                            <SessionHistoryItem key={session.id} session={session} />
                        ))}
                        {sessions.length > 10 && (
                            <p className="text-center text-sm text-foreground/60">
                                ... and {sessions.length - 10} more sessions
                            </p>
                        )}
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                                if (confirm('Clear all session history?')) {
                                    clearHistory()
                                }
                            }}
                            className="w-full text-red-400 hover:text-red-300"
                        >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Clear History
                        </Button>
                    </div>
                )}
            </div>
        </Card>
    )
}

function StatCard({
    label,
    value,
    highlight = false,
}: {
    label: string
    value: string | number
    highlight?: boolean
}) {
    return (
        <div className="p-3 rounded-lg bg-background/50 text-center">
            <p
                className={cn('text-xl font-bold', highlight ? 'text-green-400' : 'text-foreground')}
            >
                {value}
            </p>
            <p className="text-xs text-foreground/60">{label}</p>
        </div>
    )
}

function SessionHistoryItem({ session }: { session: SessionRecord }) {
    const date = new Date(session.timestamp)
    const formattedDate = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    })

    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-background/30 hover:bg-background/50 transition-colors">
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{session.question.text}</p>
                <p className="text-xs text-foreground/60">
                    {formattedDate} • {session.mode} mode
                </p>
            </div>
            <div className="flex items-center gap-2 ml-4">
                <span className="text-sm font-semibold">{session.scores.confidence}%</span>
                <span
                    className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        session.scores.textQuality === 'Excellent' && 'bg-green-500/20 text-green-400',
                        session.scores.textQuality === 'Average' && 'bg-blue-500/20 text-blue-400',
                        session.scores.textQuality === 'Poor' && 'bg-red-500/20 text-red-400'
                    )}
                >
                    {session.scores.textQuality}
                </span>
            </div>
        </div>
    )
}
