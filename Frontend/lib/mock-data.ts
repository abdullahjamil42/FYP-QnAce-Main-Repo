export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  interviewType?: string
  targetRole?: string
  experience?: string
  goals?: string[]
  createdAt: string
}

export interface Question {
  id: string
  text: string
  category: string
  difficulty: 'easy' | 'medium' | 'hard'
  type: 'behavioral' | 'technical' | 'situational'
  tips?: string[]
}

export interface AnalysisResult {
  id: string
  sessionId: string
  question: Question
  answer: string
  facialEmotions: Record<string, number>
  voiceEmotions: Record<string, number>
  textScore: number
  feedback: string
  timestamp: string
}

export const mockQuestions: Question[] = [
  {
    id: '1',
    text: 'Tell me about yourself.',
    category: 'General',
    difficulty: 'easy',
    type: 'behavioral',
    tips: ['Keep it concise', 'Focus on relevant experience']
  }
]