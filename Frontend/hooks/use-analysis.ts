'use client'

import * as React from 'react'
import { 
  qnaceApi, 
  FacialAnalysisResult, 
  VoiceAnalysisResult, 
  TextAnalysisResult,
  MultimodalAnalysisResult,
  HealthStatus 
} from '@/lib/api'

export interface UseAnalysisOptions {
  onFacialResult?: (result: FacialAnalysisResult) => void
  onVoiceResult?: (result: VoiceAnalysisResult) => void
  onTextResult?: (result: TextAnalysisResult) => void
  onMultimodalResult?: (result: MultimodalAnalysisResult) => void
  onError?: (error: Error) => void
}

export interface AnalysisState {
  isAnalyzing: boolean
  facialResult: FacialAnalysisResult | null
  voiceResult: VoiceAnalysisResult | null
  textResult: TextAnalysisResult | null
  multimodalResult: MultimodalAnalysisResult | null
  error: Error | null
  apiHealth: HealthStatus | null
}

export function useAnalysis(options: UseAnalysisOptions = {}) {
  const [state, setState] = React.useState<AnalysisState>({
    isAnalyzing: false,
    facialResult: null,
    voiceResult: null,
    textResult: null,
    multimodalResult: null,
    error: null,
    apiHealth: null,
  })

  // Check API health on mount
  React.useEffect(() => {
    qnaceApi.checkHealth()
      .then(health => {
        setState(prev => ({ ...prev, apiHealth: health }))
      })
      .catch(err => {
        console.warn('API health check failed:', err)
      })
  }, [])

  const analyzeFacial = React.useCallback(async (imageBase64: string) => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }))
    
    try {
      const result = await qnaceApi.analyzeFacial(imageBase64)
      setState(prev => ({ ...prev, facialResult: result, isAnalyzing: false }))
      options.onFacialResult?.(result)
      return result
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setState(prev => ({ ...prev, error, isAnalyzing: false }))
      options.onError?.(error)
      throw error
    }
  }, [options])

  const analyzeVoice = React.useCallback(async (audioBlob: Blob) => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }))
    
    try {
      const result = await qnaceApi.analyzeVoice(audioBlob)
      setState(prev => ({ ...prev, voiceResult: result, isAnalyzing: false }))
      options.onVoiceResult?.(result)
      return result
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setState(prev => ({ ...prev, error, isAnalyzing: false }))
      options.onError?.(error)
      throw error
    }
  }, [options])

  const analyzeText = React.useCallback(async (text: string, question?: string) => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }))
    
    try {
      const result = await qnaceApi.analyzeText(text, question)
      setState(prev => ({ ...prev, textResult: result, isAnalyzing: false }))
      options.onTextResult?.(result)
      return result
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setState(prev => ({ ...prev, error, isAnalyzing: false }))
      options.onError?.(error)
      throw error
    }
  }, [options])

  const analyzeMultimodal = React.useCallback(async (params: {
    image?: string
    audio?: Blob
    text?: string
    question?: string
  }) => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }))
    
    try {
      const result = await qnaceApi.analyzeMultimodal(params)
      setState(prev => ({ 
        ...prev, 
        multimodalResult: result,
        facialResult: result.facial || null,
        voiceResult: result.voice || null,
        textResult: result.text || null,
        isAnalyzing: false 
      }))
      options.onMultimodalResult?.(result)
      return result
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      setState(prev => ({ ...prev, error, isAnalyzing: false }))
      options.onError?.(error)
      throw error
    }
  }, [options])

  const reset = React.useCallback(() => {
    setState(prev => ({
      ...prev,
      facialResult: null,
      voiceResult: null,
      textResult: null,
      multimodalResult: null,
      error: null,
    }))
  }, [])

  return {
    ...state,
    analyzeFacial,
    analyzeVoice,
    analyzeText,
    analyzeMultimodal,
    reset,
    isApiAvailable: state.apiHealth?.status === 'ok',
  }
}
