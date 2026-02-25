'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { MediaRecorder } from '@/components/ui/media-recorder'
import { useToast } from '@/components/ui/toast'
import { useAuth } from '@/hooks/use-auth'
import { qnaceApi, MultimodalAnalysisResult } from '@/lib/api'
import { 
  ArrowLeft, 
  Sparkles, 
  Lock, 
  TrendingUp,
  Clock,
  BarChart3,
  CheckCircle2,
} from 'lucide-react'

// Single demo question
const DEMO_QUESTION = {
  id: 'demo-q-1',
  text: 'Tell me about yourself and your background.',
  category: 'behavioral',
  difficulty: 'easy',
}

type DemoState = 'ready' | 'recording' | 'analyzing' | 'result'

export default function DemoPage() {
  const router = useRouter()
  const { addToast } = useToast()
  const { isAuthenticated, needsOnboarding } = useAuth()
  
  const [state, setState] = React.useState<DemoState>('ready')
  const [result, setResult] = React.useState<{
    overallScore: number
    confidence: string
    emotion: string
  } | null>(null)

  // If already logged in, redirect to practice
  React.useEffect(() => {
    if (isAuthenticated && !needsOnboarding) {
      router.push('/practice')
    }
  }, [isAuthenticated, needsOnboarding, router])

  const handleRecordingComplete = async (audioBlob: Blob) => {
    setState('analyzing')
    
    try {
      // For demo, we analyze voice only (no face capture available from MediaRecorder)
      const analysisResult: MultimodalAnalysisResult = await qnaceApi.analyzeMultimodal({
        audio: audioBlob,
        question: DEMO_QUESTION.text,
      })

      if (analysisResult.success) {
        // Calculate simplified score for demo
        const facialConfidence = analysisResult.facial?.confidence || 0.5
        const voiceConfidence = analysisResult.voice?.confidence || 0.5
        const textScore = analysisResult.text?.quality_score || 70
        
        const overallScore = Math.round(
          (facialConfidence * 100 * 0.3) +
          (voiceConfidence * 100 * 0.3) +
          (textScore * 0.4)
        )

        setResult({
          overallScore: Math.min(95, Math.max(40, overallScore)),
          confidence: analysisResult.facial?.face_detected 
            ? (facialConfidence > 0.6 ? 'High' : facialConfidence > 0.4 ? 'Medium' : 'Low')
            : 'No face detected',
          emotion: analysisResult.overall_emotion || 'neutral',
        })
        setState('result')
      } else {
        throw new Error(analysisResult.error || 'Analysis failed')
      }
    } catch (error) {
      console.error('Demo analysis error:', error)
      addToast({
        type: 'error',
        message: 'Analysis failed. Please try again.',
      })
      setState('ready')
    }
  }

  const handleTryAgain = () => {
    setResult(null)
    setState('ready')
  }

  // Features locked in demo
  const lockedFeatures = [
    { icon: TrendingUp, text: 'Progress tracking over time' },
    { icon: Clock, text: 'Detailed emotion timeline' },
    { icon: BarChart3, text: 'Full analysis reports' },
    { icon: CheckCircle2, text: 'Personalized recommendations' },
  ]

  return (
    <div className="min-h-screen gradient-bg">
      {/* Header */}
      <header className="p-4 border-b border-foreground/10 backdrop-blur-sm bg-background/50">
        <div className="container mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-xl font-bold">
            <Sparkles className="h-6 w-6 text-accent" />
            <span className="gradient-text">Q&Ace</span>
          </Link>
          <div className="flex items-center gap-2 text-sm text-foreground/60">
            <span className="px-2 py-1 rounded-full bg-accent/10 border border-accent/30 text-accent text-xs font-medium">
              Demo Mode
            </span>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Back button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/')}
            className="mb-6"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Button>

          {/* Demo info banner */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 rounded-lg bg-accent/10 border border-accent/30"
          >
            <p className="text-sm text-foreground/80">
              <strong className="text-accent">Demo Mode:</strong> Try one practice question for free. 
              Sign up to save your progress, access all questions, and get detailed feedback.
            </p>
          </motion.div>

          {state === 'result' && result ? (
            /* Result View */
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-6"
            >
              {/* Score Card */}
              <Card hoverable={false} className="p-8 text-center">
                <h2 className="text-xl font-semibold mb-4">Your Demo Score</h2>
                <div className="relative inline-flex items-center justify-center w-32 h-32 mb-4">
                  <svg className="w-full h-full -rotate-90">
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      strokeWidth="8"
                      fill="none"
                      className="stroke-foreground/10"
                    />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      strokeWidth="8"
                      fill="none"
                      strokeLinecap="round"
                      className="stroke-accent"
                      style={{
                        strokeDasharray: `${(result.overallScore / 100) * 352} 352`,
                      }}
                    />
                  </svg>
                  <span className="absolute text-3xl font-bold">{result.overallScore}%</span>
                </div>
                <p className="text-foreground/60 mb-2">
                  Confidence: <span className="text-foreground">{result.confidence}</span>
                </p>
                <p className="text-foreground/60">
                  Detected Emotion: <span className="text-foreground capitalize">{result.emotion}</span>
                </p>
              </Card>

              {/* Locked Features */}
              <Card hoverable={false} className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Lock className="h-5 w-5 text-accent" />
                  <h3 className="text-lg font-semibold">Unlock Full Features</h3>
                </div>
                <p className="text-foreground/60 text-sm mb-4">
                  Sign up for free to access:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
                  {lockedFeatures.map((feature, index) => (
                    <div 
                      key={index}
                      className="flex items-center gap-2 text-sm text-foreground/70"
                    >
                      <feature.icon className="h-4 w-4 text-accent" />
                      {feature.text}
                    </div>
                  ))}
                </div>
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    variant="primary"
                    className="flex-1"
                    onClick={() => router.push('/signup')}
                  >
                    Sign Up Free
                  </Button>
                  <Button
                    variant="ghost"
                    className="flex-1"
                    onClick={handleTryAgain}
                  >
                    Try Again
                  </Button>
                </div>
              </Card>
            </motion.div>
          ) : (
            /* Recording View */
            <Card hoverable={false} className="overflow-hidden">
              <div className="p-6 border-b border-foreground/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-accent uppercase tracking-wider">
                    Demo Question
                  </span>
                  <span className="text-xs text-foreground/40">
                    {DEMO_QUESTION.category} • {DEMO_QUESTION.difficulty}
                  </span>
                </div>
                <h2 className="text-xl font-semibold">{DEMO_QUESTION.text}</h2>
              </div>
              
              <div className="p-6">
                <MediaRecorder
                  onRecordingComplete={handleRecordingComplete}
                  audio={true}
                  video={true}
                />
                
                {state === 'analyzing' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-6 text-center"
                  >
                    <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                    <p className="text-foreground/60">Analyzing your response...</p>
                  </motion.div>
                )}
              </div>
            </Card>
          )}

          {/* Sign up CTA */}
          {state !== 'result' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-8 text-center"
            >
              <p className="text-foreground/60 mb-3">
                Want to save your progress and get detailed feedback?
              </p>
              <Button
                variant="ghost"
                onClick={() => router.push('/signup')}
              >
                Create Free Account
              </Button>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  )
}
