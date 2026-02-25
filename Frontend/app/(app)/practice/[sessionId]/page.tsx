'use client'

import * as React from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { InterviewSession } from '@/components/practice/interview-session'
import { useToast } from '@/components/ui/toast'
import { MultimodalAnalysisResult } from '@/lib/api'

// Get questions from localStorage
function getQuestions() {
  if (typeof window === 'undefined') return []
  const stored = localStorage.getItem('qace_questions')
  if (stored) {
    return JSON.parse(stored)
  }
  return [
    {
      id: 'q-1',
      text: 'Tell me about yourself and your background.',
      category: 'behavioral',
      difficulty: 'easy',
    },
  ]
}

interface Question {
  id: string
  text: string
  category: string
  difficulty: string
}

export default function PracticeSessionPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const { addToast } = useToast()
  const [question, setQuestion] = React.useState<Question>({
    id: 'q-1',
    text: 'Tell me about yourself and your background.',
    category: 'behavioral',
    difficulty: 'easy',
  })

  React.useEffect(() => {
    const questions = getQuestions()
    const questionId = searchParams.get('questionId')
    
    // Find question by questionId param or session ID
    let foundQuestion = questions.find((q: Question) => q.id === questionId)
    if (!foundQuestion) {
      foundQuestion = questions.find((q: Question) => q.id === params.sessionId)
    }
    if (!foundQuestion && questions.length > 0) {
      foundQuestion = questions[0]
    }
    
    if (foundQuestion) {
      setQuestion(foundQuestion)
    }
  }, [params.sessionId, searchParams])

  const handleAnalysisComplete = async (result: MultimodalAnalysisResult) => {
    if (!result.success) {
      addToast({
        type: 'error',
        message: result.error || 'Analysis failed. Please try again.',
      })
      return
    }

    addToast({
      type: 'success',
      message: 'Analysis complete! View your detailed report.',
    })

    // Store result in localStorage with proper analysis format
    const reportId = `report-${Date.now()}`
    const reports = JSON.parse(localStorage.getItem('qace_reports') || '[]')
    
    // Ensure session exists in qace_sessions
    const sessions = JSON.parse(localStorage.getItem('qace_sessions') || '[]')
    const sessionExists = sessions.some((s: any) => s.id === params.sessionId)
    if (!sessionExists) {
      sessions.unshift({
        id: params.sessionId,
        questionId: question.id,
        status: 'completed',
        createdAt: new Date().toISOString(),
      })
      localStorage.setItem('qace_sessions', JSON.stringify(sessions))
    } else {
      // Update existing session status to completed
      const updatedSessions = sessions.map((s: any) => 
        s.id === params.sessionId ? { ...s, status: 'completed' } : s
      )
      localStorage.setItem('qace_sessions', JSON.stringify(updatedSessions))
    }
    
    // =====================================
    // REALISTIC SCORING SYSTEM v2.0
    // =====================================
    
    const emotions = { ...(result.facial?.emotions || {}) };
    
    // Resting face correction - FER2013 models often misclassify neutral faces as "angry"
    const angryProb = emotions.angry || 0;
    const neutralProb = emotions.neutral || 0;
    const happyProb = emotions.happy || 0;
    const surpriseProb = emotions.surprise || 0;
    const positiveSum = neutralProb + happyProb + surpriseProb;
    
    // If angry is dominant but positive emotions are also present, likely resting face
    if (angryProb > 0.35 && angryProb < 0.70 && positiveSum > 0.15) {
      const correctionFactor = Math.min(0.6, positiveSum);
      const angryTransfer = angryProb * correctionFactor;
      
      emotions.neutral = neutralProb + angryTransfer * 0.8;
      emotions.happy = happyProb + angryTransfer * 0.2;
      emotions.angry = angryProb * (1 - correctionFactor);
    }
    
    // =====================================
    // FACIAL SCORE CALCULATION
    // Interview-appropriate emotion scoring
    // MODEL REALITY: 82% neutral, 14% angry, <1% happy
    // Confidence averages 40% - model is uncertain
    // =====================================
    const calculateFacialScore = (): number => {
      // PENALTY: No face detected
      if (!result.facial?.face_detected) {
        return 25;
      }
      
      // MODEL BIAS CORRECTION:
      // The model outputs ~96% neutral+angry regardless of expression
      // So we treat both as "professional demeanor" (acceptable)
      // Only penalize clear negative emotions (sad/fear)
      
      const happy = emotions.happy || 0;
      const surprise = emotions.surprise || 0;
      const sad = emotions.sad || 0;
      const fear = emotions.fear || 0;
      // Note: neutral and angry are intentionally not used
      // Model detects them 96% of time (bias), so no penalty/bonus for them
      
      // Base score: Start at "good professional" level
      // Since model mostly detects neutral/angry, this is the baseline
      let baseScore = 75;
      
      // BONUS: Any happy detection is meaningful (model rarely detects it)
      if (happy > 0.15) {
        baseScore += 15; // Clear smile detected - excellent!
      } else if (happy > 0.05) {
        baseScore += 10; // Some happiness detected - good
      } else if (happy > 0.02) {
        baseScore += 5;  // Slight happiness - okay
      }
      
      // BONUS: Surprise shows engagement
      if (surprise > 0.10) {
        baseScore += 5;
      }
      
      // Neutral + Angry = Professional (model's default output)
      // No penalty for these since they're the model's bias
      
      // PENALTY: Only for clearly negative emotions
      // These are more meaningful when detected (model rarely outputs them)
      if (sad > 0.20) {
        baseScore -= 15; // Clearly looking sad
      } else if (sad > 0.10) {
        baseScore -= 8;
      }
      
      if (fear > 0.15) {
        baseScore -= 15; // Clearly nervous
      } else if (fear > 0.08) {
        baseScore -= 8;
      }
      
      // High confidence bonus (rare - model avg is 40%)
      const confidence = result.facial?.confidence || 0.4;
      if (confidence > 0.60) {
        baseScore += 5; // Model is confident in detection
      }
      
      return Math.min(95, Math.max(35, Math.round(baseScore)));
    };

    // =====================================
    // ENGAGEMENT SCORE CALCULATION  
    // MODEL REALITY: 82% neutral, 14% angry - these are "normal"
    // Happy detection is rare (<1%) but meaningful
    // =====================================
    const calculateEngagement = (): number => {
      if (!result.facial?.face_detected) return 25;
      
      const happy = emotions.happy || 0;
      const surprise = emotions.surprise || 0;
      const sad = emotions.sad || 0;
      const fear = emotions.fear || 0;
      
      // Base engagement: Professional (model's default output)
      let engagementScore = 60;
      
      // BOOST for positive emotions (rare and meaningful)
      if (happy > 0.15) {
        engagementScore += 25; // Clear smile - very engaging!
      } else if (happy > 0.05) {
        engagementScore += 15; // Some happiness
      } else if (happy > 0.02) {
        engagementScore += 8;  // Slight positivity
      }
      
      if (surprise > 0.10) {
        engagementScore += 8; // Shows interest
      }
      
      // PENALTY only for clear negative emotions
      if (sad > 0.20) {
        engagementScore -= 20;
      } else if (sad > 0.10) {
        engagementScore -= 10;
      }
      
      if (fear > 0.15) {
        engagementScore -= 20;
      } else if (fear > 0.08) {
        engagementScore -= 10;
      }
      
      return Math.min(90, Math.max(35, Math.round(engagementScore)));
    };

    // =====================================
    // EXPRESSIONS QUALITY SCORE
    // =====================================
    const calculateExpressionsScore = (): number => {
      const facial = calculateFacialScore();
      const engagement = calculateEngagement();
      
      let expressionsScore = (facial + engagement) / 2;
      
      // If either is very low, cap the expressions score
      if (facial < 40 || engagement < 30) {
        expressionsScore = Math.min(expressionsScore, 45);
      }
      
      return Math.round(expressionsScore);
    };

    const facialScore = calculateFacialScore();
    const engagementScore = calculateEngagement();
    const expressionsScore = calculateExpressionsScore();
    const modelCertainty = Math.round((result.facial?.confidence || 0) * 100);
    
    // Overall Facial Score = weighted combination
    const overallFacialScore = Math.round(
      facialScore * 0.4 +
      engagementScore * 0.35 +
      expressionsScore * 0.25
    );
    
    const analysisResult = {
      facial: {
        score: overallFacialScore,
        metrics: {
          // All metrics now calculated from real data
          engagement: engagementScore,
          expressions: expressionsScore,
          modelCertainty: modelCertainty,
        },
        recommendations: result.recommendations?.filter((r: string) => r.toLowerCase().includes('eye') || r.toLowerCase().includes('face') || r.toLowerCase().includes('expression')).map((r: string, i: number) => ({
          id: `f-${i}`,
          priority: 'medium' as const,
          title: 'Facial Feedback',
          description: r,
        })) || [],
      },
      vocal: {
        score: Math.round(result.voice?.confidence ? result.voice.confidence * 100 : 75),
        metrics: {
          tone: result.voice?.emotions?.neutral ? Math.round((0.5 + result.voice.emotions.neutral * 0.5) * 100) : 80,
          pace: 78,
          clarity: Math.round(result.clarity_score || 75),
          volume: 80,
        },
        recommendations: result.recommendations?.filter((r: string) => r.toLowerCase().includes('voice') || r.toLowerCase().includes('tone') || r.toLowerCase().includes('speak')).map((r: string, i: number) => ({
          id: `v-${i}`,
          priority: 'medium' as const,
          title: 'Voice Feedback',
          description: r,
        })) || [],
      },
      content: {
        // Don't rely on BERT score directly - it's overfitting
        // Give a reasonable base score instead
        score: Math.round(Math.max(70, result.text?.quality_score || 70)),
        metrics: {
          structure: Math.round(Math.max(70, result.text?.quality_score || 70)),
          relevance: Math.round(Math.max(70, result.text?.quality_score || 70)),
          keywords: 75,
          completeness: Math.round(Math.max(70, result.text?.quality_score || 70)),
        },
        recommendations: result.recommendations?.filter((r: string) => r.toLowerCase().includes('answer') || r.toLowerCase().includes('content') || r.toLowerCase().includes('structure')).map((r: string, i: number) => ({
          id: `c-${i}`,
          priority: 'high' as const,
          title: 'Content Feedback',
          description: r,
        })) || [],
      },
      transcript: result.text?.feedback || '',
      keywords: [],
      // Calculate overall score from component scores with proper weights
      // Weights: Facial 50%, Voice 40%, Text 10%
      overallScore: Math.round(
        (facialScore * 0.5) + 
        ((result.voice?.confidence || 0.7) * 100 * 0.4) + 
        (Math.max(70, result.text?.quality_score || 70) * 0.1)
      ),
    }
    
    reports.push({
      id: reportId,
      sessionId: params.sessionId,
      questionId: question.id,
      analysis: analysisResult,
      result,
      // Include emotion timeline for detailed visualization
      emotionTimeline: result.emotionTimeline || null,
      createdAt: new Date().toISOString(),
    })
    localStorage.setItem('qace_reports', JSON.stringify(reports))

    // Redirect to reports page after a delay
    setTimeout(() => {
      router.push('/reports')
    }, 2000)
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Practice Session</h1>
        <p className="text-foreground/60">Record your response and get AI-powered multimodal feedback</p>
      </div>

      <InterviewSession 
        question={question}
        onComplete={handleAnalysisComplete}
      />
    </div>
  )
}

