'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/hooks/use-auth'
import Link from 'next/link'
import { Plus, Play } from 'lucide-react'

// Get questions from localStorage or use defaults
function getQuestions() {
  if (typeof window === 'undefined') return []
  const stored = localStorage.getItem('qace_questions')
  if (stored) {
    return JSON.parse(stored)
  }
  // Default questions
  const defaultQuestions = [
    {
      id: 'q-1',
      text: 'Tell me about yourself and your background.',
      category: 'behavioral',
      difficulty: 'easy',
      tags: ['introduction', 'background'],
      createdAt: new Date().toISOString(),
    },
    {
      id: 'q-2',
      text: 'Describe a challenging project you worked on and how you handled it.',
      category: 'behavioral',
      difficulty: 'medium',
      tags: ['problem-solving', 'experience'],
      createdAt: new Date().toISOString(),
    },
    {
      id: 'q-3',
      text: 'What are your greatest strengths and weaknesses?',
      category: 'behavioral',
      difficulty: 'easy',
      tags: ['self-awareness', 'growth'],
      createdAt: new Date().toISOString(),
    },
    {
      id: 'q-4',
      text: 'Where do you see yourself in 5 years?',
      category: 'behavioral',
      difficulty: 'medium',
      tags: ['goals', 'career'],
      createdAt: new Date().toISOString(),
    },
    {
      id: 'q-5',
      text: 'Explain a time when you had to work under pressure.',
      category: 'behavioral',
      difficulty: 'medium',
      tags: ['pressure', 'time-management'],
      createdAt: new Date().toISOString(),
    },
  ]
  localStorage.setItem('qace_questions', JSON.stringify(defaultQuestions))
  return defaultQuestions
}

interface Question {
  id: string
  text: string
  category: string
  difficulty: string
  tags: string[]
  createdAt: string
}

interface Session {
  id: string
  questionId: string
  question: Question
  status: string
  createdAt: string
}

export default function PracticePage() {
  const router = useRouter()
  useAuth() // Ensure user is authenticated
  const [sessions, setSessions] = React.useState<Session[]>([])

  React.useEffect(() => {
    // Load questions
    const loadedQuestions = getQuestions()
    
    // Load sessions from localStorage
    const storedSessions = JSON.parse(localStorage.getItem('qace_sessions') || '[]')
    
    // Map sessions to include question data
    const sessionsWithQuestions = storedSessions.map((session: any) => {
      const question = loadedQuestions.find((q: Question) => q.id === session.questionId) || loadedQuestions[0]
      return {
        ...session,
        question,
      }
    })
    
    setSessions(sessionsWithQuestions)
  }, [])

  const handleNewSession = () => {
    const loadedQuestions = getQuestions()
    const randomQuestion = loadedQuestions[Math.floor(Math.random() * loadedQuestions.length)]
    const newSession = {
      id: `session-${Date.now()}`,
      questionId: randomQuestion.id,
      status: 'pending',
      createdAt: new Date().toISOString(),
    }
    
    // Save to localStorage
    const existingSessions = JSON.parse(localStorage.getItem('qace_sessions') || '[]')
    existingSessions.unshift(newSession)
    localStorage.setItem('qace_sessions', JSON.stringify(existingSessions))
    
    // Navigate to session
    router.push(`/practice/${newSession.id}?questionId=${randomQuestion.id}`)
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Practice Sessions</h1>
          <p className="text-foreground/60">Practice with AI-powered feedback</p>
        </div>
        <Button onClick={handleNewSession} variant="primary">
          <Plus className="mr-2 h-5 w-5" />
          New Session
        </Button>
      </div>

      {sessions.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <Play className="h-12 w-12 text-foreground/40 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Practice Sessions Yet</h3>
            <p className="text-foreground/60 mb-4">
              Start your first practice session to get AI-powered feedback.
            </p>
            <Button onClick={handleNewSession} variant="primary">
              <Plus className="mr-2 h-5 w-5" />
              Start Your First Session
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sessions.map((session) => (
            <Card key={session.id} hoverable>
              <div className="space-y-4">
                <div>
                  <div className="flex items-start justify-between mb-2">
                    <Badge
                      variant={
                        session.status === 'completed'
                          ? 'success'
                          : session.status === 'recording'
                            ? 'error'
                            : 'default'
                      }
                    >
                      {session.status}
                    </Badge>
                    <span className="text-xs text-foreground/60">
                      {new Date(session.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 className="font-semibold mb-2 line-clamp-2">{session.question?.text || 'Practice Session'}</h3>
                  <div className="flex items-center gap-2">
                    <Badge variant="info" className="text-xs">
                      {session.question?.category || 'general'}
                    </Badge>
                    <Badge variant="default" className="text-xs">
                      {session.question?.difficulty || 'medium'}
                    </Badge>
                  </div>
                </div>
                <Button asChild variant="primary" className="w-full">
                  <Link href={`/practice/${session.id}?questionId=${session.questionId}`}>
                    <Play className="mr-2 h-4 w-4" />
                    {session.status === 'completed' ? 'Review' : 'Start'}
                  </Link>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

