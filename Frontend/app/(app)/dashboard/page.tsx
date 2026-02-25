'use client'

import * as React from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'
import Link from 'next/link'
import { Video, TrendingUp, Target, Clock } from 'lucide-react'
import { SparklineChart } from '@/components/ui/chart'

interface StoredReport {
  id: string
  sessionId: string
  analysis: {
    overallScore: number
  }
  createdAt: string
}

interface StoredSession {
  id: string
  questionId: string
  status: string
  createdAt: string
}

// Get questions from localStorage
function getQuestions() {
  if (typeof window === 'undefined') return []
  const stored = localStorage.getItem('qace_questions')
  if (stored) {
    return JSON.parse(stored)
  }
  return []
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = React.useState({
    totalSessions: 0,
    avgScore: 0,
    totalTime: 0,
    recentSessions: [] as Array<{
      id: string
      question: string
      score: number
      date: string
    }>,
    progressData: [] as number[],
  })

  React.useEffect(() => {
    // Load data from localStorage
    const reports: StoredReport[] = JSON.parse(localStorage.getItem('qace_reports') || '[]')
    const sessions: StoredSession[] = JSON.parse(localStorage.getItem('qace_sessions') || '[]')
    const questions = getQuestions()
    
    // Calculate stats - use reports count as fallback if sessions weren't tracked
    const totalSessions = Math.max(sessions.length, reports.length)
    const scores = reports.map(r => r.analysis?.overallScore || 0).filter(s => s > 0)
    const avgScore = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
    
    // Estimate total practice time (2 minutes per session average)
    const totalTimeMinutes = totalSessions * 2 // in minutes
    
    // Get recent sessions with scores
    const recentSessions = reports.slice(-5).reverse().map(report => {
      const session = sessions.find(s => s.id === report.sessionId)
      const question = questions.find((q: any) => q.id === session?.questionId)
      return {
        id: report.id,
        question: question?.text || 'Practice Session',
        score: report.analysis?.overallScore || 0,
        date: new Date(report.createdAt).toLocaleDateString(),
      }
    })
    
    // Get progress data (last 7 scores)
    const progressData = scores.slice(-7)
    if (progressData.length === 0) {
      // No data yet
    }
    
    setStats({
      totalSessions,
      avgScore,
      totalTime: totalTimeMinutes,
      recentSessions,
      progressData,
    })
  }, [])

  // Format time display
  const formatTime = (minutes: number) => {
    if (minutes >= 60) {
      const hours = Math.floor(minutes / 60)
      const mins = minutes % 60
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
    }
    return `${minutes}m`
  }

  const statsDisplay = [
    { label: 'Practice Sessions', value: stats.totalSessions.toString(), icon: Video, trend: stats.totalSessions > 0 ? `${stats.totalSessions} completed` : 'Start practicing!' },
    { label: 'Average Score', value: stats.avgScore > 0 ? `${stats.avgScore}%` : '--', icon: TrendingUp, trend: stats.avgScore > 0 ? 'Keep improving!' : 'No scores yet' },
    { label: 'Goals Progress', value: stats.totalSessions >= 5 ? '✓' : `${stats.totalSessions}/5`, icon: Target, trend: stats.totalSessions >= 5 ? 'Goal reached!' : `${5 - stats.totalSessions} more to go` },
    { label: 'Time Practiced', value: formatTime(stats.totalTime), icon: Clock, trend: 'Keep it up!' },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Welcome back, {user?.name}!</h1>
        <p className="text-foreground/60">Here&apos;s your interview preparation overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsDisplay.map((stat, index) => {
          const Icon = stat.icon
          return (
            <Card key={index} hoverable>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-foreground/60 mb-1">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-xs text-foreground/40 mt-1">{stat.trend}</p>
                </div>
                <div className="p-2 rounded-lg bg-accent/10">
                  <Icon className="h-5 w-5 text-accent" />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Quick Actions & Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Button asChild variant="primary" className="w-full justify-start">
              <Link href="/practice">
                <Video className="mr-2 h-5 w-5" />
                Start New Practice Session
              </Link>
            </Button>
            <Button asChild variant="secondary" className="w-full justify-start">
              <Link href="/reports">
                View Latest Report
              </Link>
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-xl font-semibold mb-4">Progress Overview</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-foreground/60">Overall Score</span>
                <span className="text-sm font-semibold">{stats.avgScore > 0 ? `${stats.avgScore}%` : '--'}</span>
              </div>
              <div className="h-2 bg-foreground/10 rounded-full overflow-hidden">
                <div className="h-full bg-accent rounded-full" style={{ width: `${stats.avgScore}%` }} />
              </div>
            </div>
            {stats.progressData.length > 0 && (
              <div>
                <p className="text-sm text-foreground/60 mb-2">Trend (Recent Sessions)</p>
                <SparklineChart data={stats.progressData} width={300} height={40} />
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Recent Sessions */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Recent Practice Sessions</h2>
          <Button asChild variant="ghost" size="sm">
            <Link href="/practice">View All</Link>
          </Button>
        </div>
        {stats.recentSessions.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-foreground/60 mb-4">No practice sessions yet</p>
            <Button asChild variant="primary">
              <Link href="/practice">Start Your First Session</Link>
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {stats.recentSessions.map((session) => (
              <div
                key={session.id}
                className="flex items-center justify-between p-3 rounded-lg bg-foreground/5 border border-foreground/10"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium mb-1 line-clamp-1">{session.question}</p>
                  <p className="text-xs text-foreground/60">{session.date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={session.score >= 80 ? 'success' : session.score >= 70 ? 'info' : 'warning'}>
                    {session.score}%
                  </Badge>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/reports/${session.id}`}>View</Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

