'use client'

import * as React from 'react'

/**
 * Session record stored in localStorage
 */
export interface SessionRecord {
    id: string
    timestamp: number
    question: {
        id: string
        text: string
        category: string
        difficulty: string
    }
    mode: 'practice' | 'mock'
    scores: {
        confidence: number
        clarity: number
        engagement: number
        textQuality: string
    }
    duration: number
}

const STORAGE_KEY = 'qnace_session_history'

/**
 * useSessionHistory Hook
 * 
 * Manages session history using localStorage for:
 * - Saving completed interview sessions
 * - Retrieving history for progress tracking
 * - Clearing history
 * 
 * Design: Client-side storage for simplicity and privacy.
 * Can be migrated to server-side if multi-device access is needed.
 */
export function useSessionHistory() {
    const [sessions, setSessions] = React.useState<SessionRecord[]>([])
    const [isLoaded, setIsLoaded] = React.useState(false)

    // Load sessions from localStorage on mount
    React.useEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY)
            if (stored) {
                const parsed = JSON.parse(stored) as SessionRecord[]
                setSessions(parsed)
            }
        } catch (error) {
            console.warn('Failed to load session history:', error)
        }
        setIsLoaded(true)
    }, [])

    // Save sessions to localStorage whenever they change
    React.useEffect(() => {
        if (isLoaded) {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
            } catch (error) {
                console.warn('Failed to save session history:', error)
            }
        }
    }, [sessions, isLoaded])

    /**
     * Save a new session to history
     */
    const saveSession = React.useCallback((session: Omit<SessionRecord, 'id' | 'timestamp'>) => {
        const newRecord: SessionRecord = {
            ...session,
            id: `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
            timestamp: Date.now(),
        }

        setSessions((prev) => [newRecord, ...prev].slice(0, 50)) // Keep only last 50
        return newRecord.id
    }, [])

    /**
     * Get a specific session by ID
     */
    const getSession = React.useCallback(
        (id: string) => sessions.find((s) => s.id === id),
        [sessions]
    )

    /**
     * Get sessions for a specific question
     */
    const getSessionsForQuestion = React.useCallback(
        (questionId: string) => sessions.filter((s) => s.question.id === questionId),
        [sessions]
    )

    /**
     * Get the most recent sessions
     */
    const getRecentSessions = React.useCallback(
        (limit: number = 10) => sessions.slice(0, limit),
        [sessions]
    )

    /**
     * Delete a specific session
     */
    const deleteSession = React.useCallback((id: string) => {
        setSessions((prev) => prev.filter((s) => s.id !== id))
    }, [])

    /**
     * Clear all session history
     */
    const clearHistory = React.useCallback(() => {
        setSessions([])
        localStorage.removeItem(STORAGE_KEY)
    }, [])

    /**
     * Calculate progress stats
     */
    const getProgressStats = React.useCallback(() => {
        if (sessions.length === 0) {
            return {
                totalSessions: 0,
                averageConfidence: 0,
                averageClarity: 0,
                averageEngagement: 0,
                improvement: 0,
                questionsAttempted: 0,
            }
        }

        const total = sessions.length
        const avgConfidence = sessions.reduce((sum, s) => sum + s.scores.confidence, 0) / total
        const avgClarity = sessions.reduce((sum, s) => sum + s.scores.clarity, 0) / total
        const avgEngagement = sessions.reduce((sum, s) => sum + s.scores.engagement, 0) / total

        // Calculate improvement (compare last 5 vs first 5 sessions)
        let improvement = 0
        if (sessions.length >= 5) {
            const recent = sessions.slice(0, 5)
            const older = sessions.slice(-5)
            const recentAvg = recent.reduce((sum, s) => sum + s.scores.confidence, 0) / recent.length
            const olderAvg = older.reduce((sum, s) => sum + s.scores.confidence, 0) / older.length
            improvement = recentAvg - olderAvg
        }

        const uniqueQuestions = new Set(sessions.map((s) => s.question.id))

        return {
            totalSessions: total,
            averageConfidence: Math.round(avgConfidence),
            averageClarity: Math.round(avgClarity),
            averageEngagement: Math.round(avgEngagement),
            improvement: Math.round(improvement),
            questionsAttempted: uniqueQuestions.size,
        }
    }, [sessions])

    return {
        sessions,
        isLoaded,
        saveSession,
        getSession,
        getSessionsForQuestion,
        getRecentSessions,
        deleteSession,
        clearHistory,
        getProgressStats,
    }
}
