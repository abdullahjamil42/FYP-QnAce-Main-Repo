'use client'

/**
 * Q&ACE API Client
 * 
 * Handles all communication with the backend FastAPI server.
 * Provides types and methods for facial, voice, text, and multimodal analysis.
 */

// Types matching backend models
export interface FacialAnalysisResult {
  success: boolean
  emotions: Record<string, number>
  dominant_emotion: string
  confidence: number
  face_detected: boolean
  error?: string
}

export interface VoiceAnalysisResult {
  success: boolean
  emotions: Record<string, number>
  dominant_emotion: string
  confidence: number
  error?: string
}

export interface TextAnalysisResult {
  success: boolean
  quality_score: number
  quality_label: string
  probabilities: Record<string, number>
  feedback: string
  reason?: string
  error?: string
}

export interface SpeechToTextResult {
  success: boolean
  transcription: string
  language?: string
  segments?: any[]
  text_analysis?: TextAnalysisResult
  filler_word_count?: number
  filler_words?: string[]
  speech_rate?: string
  error?: string
}

// ============================================
// Coaching Types (NEW)
// ============================================

export interface CoachingTip {
  what_went_well: string
  what_to_improve: string
  reason: string  // Explainability - why this recommendation
}

export interface CoachingDiagnosis {
  issue: string
  description: string
  reason: string
  severity: string  // 'low' | 'medium' | 'high'
}

export interface CoachingResult {
  success: boolean

  // Sentence-BERT Similarity Scores
  sbert_similarities: {
    poor: number
    average: number
    excellent: number
  }
  closest_tier: string  // Which reference the answer is most similar to
  excellent_gap: number  // Gap between user answer and excellent

  // Combined Text Score (BERT + SBERT)
  combined_text_score: number  // 0-100
  bert_component: number
  sbert_component: number

  // Diagnoses (deterministic)
  content_diagnosis: CoachingDiagnosis
  voice_diagnosis: CoachingDiagnosis
  facial_diagnosis: CoachingDiagnosis

  // Recommendations (template-based)
  content_tip: CoachingTip
  voice_tip: CoachingTip
  facial_tip: CoachingTip

  // Human-readable interpretation
  quality_interpretation: string  // Single verdict label
  quality_description: string  // User-friendly explanation
  progress_position: number  // 0-100 position on Poor→Excellent scale
  improvement_tips?: string[]  // GenAI-powered or fallback tips

  // Optional GenAI-rephrased feedback
  generated_feedback?: string

  // NEW: BERTScore (Semantic Accuracy)
  bert_score_f1?: number  // 0-1 scale, display as percentage
  bert_score_precision?: number
  bert_score_recall?: number

  // NEW: LLM Judge
  llm_judge_score?: number  // 1-10 scale
  llm_judge_rationale?: string  // Explanation for the score
  llm_actionable_tips?: string[]  // Specific improvement tips

  // NEW: STAR Structure Breakdown
  star_breakdown?: {
    situation: number  // 0-100
    task: number
    action: number
    result: number
  }
  content_relevance?: number  // 1-5 rubric
  coherence_score?: number  // 1-5 rubric

  timestamp: string
  error?: string
}

export interface MultimodalAnalysisResult {
  success: boolean
  overall_confidence: number
  overall_emotion: string
  facial?: FacialAnalysisResult
  voice?: VoiceAnalysisResult
  text?: TextAnalysisResult
  fused_emotions: Record<string, number>
  confidence_score: number
  clarity_score: number
  engagement_score: number
  recommendations: string[]

  // NEW: Structured coaching data
  coaching?: CoachingResult

  timestamp: string
  error?: string
}

export interface HealthStatus {
  status: string
  message?: string
}

class QnaceApiClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    console.log(" Q&ACE API Client initialized with baseUrl:", this.baseUrl)
  }

  /**
   * Check if the backend API is healthy and reachable.
   */
  async checkHealth(): Promise<HealthStatus> {
    try {
      const res = await fetch(`${this.baseUrl}/health`)
      if (!res.ok) throw new Error("API Health Check failed")
      return res.json()
    } catch (error) {
      console.warn(" Backend API unreachable:", error)
      return { status: "error", message: String(error) }
    }
  }

  /**
   * Analyze facial emotions from a base64 image frame.
   */
  async analyzeFacial(imageBase64: string): Promise<FacialAnalysisResult> {
    const formData = new FormData()
    formData.append("image", imageBase64)

    try {
      const res = await fetch(`${this.baseUrl}/analyze/facial`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) throw new Error("Facial analysis failed")
      return res.json()
    } catch (error) {
      return {
        success: false,
        emotions: {},
        dominant_emotion: "neutral",
        confidence: 0,
        face_detected: false,
        error: String(error)
      }
    }
  }

  /**
   * Analyze voice emotions from an audio blob.
   */
  async analyzeVoice(audioBlob: Blob): Promise<VoiceAnalysisResult> {
    const formData = new FormData()
    formData.append("audio", audioBlob, "audio.webm")

    try {
      const res = await fetch(`${this.baseUrl}/analyze/voice`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) throw new Error("Voice analysis failed")
      return res.json()
    } catch (error) {
      return {
        success: false,
        emotions: {},
        dominant_emotion: "neutral",
        confidence: 0,
        error: String(error)
      }
    }
  }

  /**
   * Analyze answer quality using BERT.
   */
  async analyzeText(text: string, question?: string): Promise<TextAnalysisResult> {
    try {
      const res = await fetch(`${this.baseUrl}/analyze/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, question }),
      })
      if (!res.ok) throw new Error("Text analysis failed")
      return res.json()
    } catch (error) {
      return {
        success: false,
        quality_score: 0,
        quality_label: "Average",
        probabilities: {},
        feedback: "Could not analyze text content.",
        error: String(error)
      }
    }
  }

  /**
   * Transcribe speech to text using Whisper.
   * Maps to /analyze/speech backend endpoint.
   */
  async transcribeSpeech(audioBlob: Blob): Promise<SpeechToTextResult> {
    const formData = new FormData()
    formData.append("audio", audioBlob, "audio.webm")
    formData.append("analyze_text", "false") // Just transcription

    try {
      const res = await fetch(`${this.baseUrl}/analyze/speech`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) throw new Error("Transcription failed")
      return res.json()
    } catch (error) {
      console.error(" Transcription API error:", error)
      return {
        success: false,
        transcription: "",
        error: String(error)
      }
    }
  }

  /**
   * Full multimodal analysis (Facial, Voice, and Text together).
   */
  async analyzeMultimodal(params: {
    image?: string
    audio?: Blob
    text?: string
    question?: string
  }): Promise<MultimodalAnalysisResult> {
    const formData = new FormData()
    if (params.image) formData.append("image", params.image)
    if (params.audio) formData.append("audio", params.audio, "audio.webm")
    if (params.text) formData.append("text", params.text)
    if (params.question) formData.append("question", params.question)

    try {
      const res = await fetch(`${this.baseUrl}/analyze/multimodal`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) throw new Error("Multimodal analysis failed")
      return res.json()
    } catch (error) {
      return {
        success: false,
        overall_confidence: 0,
        overall_emotion: "neutral",
        fused_emotions: {},
        confidence_score: 0,
        clarity_score: 0,
        engagement_score: 0,
        recommendations: ["Check backend connection."],
        timestamp: new Date().toISOString(),
        error: String(error)
      }
    }
  }

  /**
   * Utility to capture a frame from a live video element as base64.
   */
  captureFrameAsBase64(videoElement: HTMLVideoElement): string {
    try {
      const canvas = document.createElement("canvas")
      canvas.width = videoElement.videoWidth
      canvas.height = videoElement.videoHeight
      const ctx = canvas.getContext("2d")
      if (!ctx) return ""

      ctx.drawImage(videoElement, 0, 0)
      // Get only the base64 data portion (after the comma)
      return canvas.toDataURL("image/jpeg", 0.8).split(",")[1]
    } catch (error) {
      console.error("Failed to capture frame:", error)
      return ""
    }
  }
}

export const qnaceApi = new QnaceApiClient()
