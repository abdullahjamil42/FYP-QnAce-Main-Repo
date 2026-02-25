import { renderHook, act, waitFor } from '@testing-library/react'
import { useAnalysis } from '@/hooks/use-analysis'
import { qnaceApi } from '@/lib/api'

jest.mock('@/lib/api')

const mockQnaceApi = qnaceApi as jest.Mocked<typeof qnaceApi>

describe('useAnalysis', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('initializes with default state', () => {
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: {
        facial: true,
        voice: true,
        bert: true,
      },
    })

    const { result } = renderHook(() => useAnalysis())

    expect(result.current.isAnalyzing).toBe(false)
    expect(result.current.facialResult).toBeNull()
    expect(result.current.voiceResult).toBeNull()
    expect(result.current.textResult).toBeNull()
    expect(result.current.multimodalResult).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('checks API health on mount', async () => {
    const mockHealth = {
      status: 'ok',
      device: 'cpu',
      models: {
        facial: true,
        voice: true,
        bert: true,
      },
    }

    mockQnaceApi.checkHealth.mockResolvedValue(mockHealth)

    renderHook(() => useAnalysis())

    await waitFor(() => {
      expect(mockQnaceApi.checkHealth).toHaveBeenCalled()
    })
  })

  it('analyzes facial emotions', async () => {
    const mockResult = {
      success: true,
      emotions: { happy: 0.8, neutral: 0.2 },
      dominant_emotion: 'happy',
      confidence: 0.85,
      face_detected: true,
    }

    mockQnaceApi.analyzeFacial.mockResolvedValue(mockResult)
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const { result } = renderHook(() => useAnalysis())

    await act(async () => {
      await result.current.analyzeFacial('base64image')
    })

    await waitFor(() => {
      expect(result.current.facialResult).toEqual(mockResult)
      expect(result.current.isAnalyzing).toBe(false)
    })
  })

  it('analyzes voice emotions', async () => {
    const mockResult = {
      success: true,
      emotions: { calm: 0.7, neutral: 0.3 },
      dominant_emotion: 'calm',
      confidence: 0.75,
    }

    const mockBlob = new Blob(['audio data'], { type: 'audio/wav' })

    mockQnaceApi.analyzeVoice.mockResolvedValue(mockResult)
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const { result } = renderHook(() => useAnalysis())

    await act(async () => {
      await result.current.analyzeVoice(mockBlob)
    })

    await waitFor(() => {
      expect(result.current.voiceResult).toEqual(mockResult)
      expect(result.current.isAnalyzing).toBe(false)
    })
  })

  it('analyzes text', async () => {
    const mockResult = {
      success: true,
      quality_score: 0.85,
      quality_label: 'Excellent' as const,
      probabilities: { excellent: 0.85, average: 0.15 },
      feedback: 'Great answer!',
    }

    mockQnaceApi.analyzeText.mockResolvedValue(mockResult)
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const { result } = renderHook(() => useAnalysis())

    await act(async () => {
      await result.current.analyzeText('This is a test answer', 'Test question')
    })

    await waitFor(() => {
      expect(result.current.textResult).toEqual(mockResult)
      expect(result.current.isAnalyzing).toBe(false)
    })
  })

  it('analyzes multimodal', async () => {
    const mockResult = {
      success: true,
      overall_confidence: 0.8,
      overall_emotion: 'confident',
      facial: {
        success: true,
        emotions: { happy: 0.8 },
        dominant_emotion: 'happy',
        confidence: 0.85,
        face_detected: true,
      },
      voice: {
        success: true,
        emotions: { calm: 0.7 },
        dominant_emotion: 'calm',
        confidence: 0.75,
      },
      text: {
        success: true,
        quality_score: 0.85,
        quality_label: 'Excellent' as const,
        probabilities: { excellent: 0.85 },
        feedback: 'Great answer!',
      },
      fused_emotions: { confident: 0.8 },
      confidence_score: 0.8,
      clarity_score: 0.85,
      engagement_score: 0.75,
      recommendations: ['Keep up the good work'],
      timestamp: new Date().toISOString(),
    }

    mockQnaceApi.analyzeMultimodal.mockResolvedValue(mockResult)
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const { result } = renderHook(() => useAnalysis())

    await act(async () => {
      await result.current.analyzeMultimodal({
        image: 'base64image',
        audio: new Blob(['audio'], { type: 'audio/wav' }),
        text: 'Test answer',
        question: 'Test question',
      })
    })

    await waitFor(() => {
      expect(result.current.multimodalResult).toEqual(mockResult)
      expect(result.current.facialResult).toEqual(mockResult.facial)
      expect(result.current.voiceResult).toEqual(mockResult.voice)
      expect(result.current.textResult).toEqual(mockResult.text)
      expect(result.current.isAnalyzing).toBe(false)
    })
  })

  it('handles errors', async () => {
    const mockError = new Error('Analysis failed')
    mockQnaceApi.analyzeFacial.mockRejectedValue(mockError)
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const onError = jest.fn()
    const { result } = renderHook(() => useAnalysis({ onError }))

    await act(async () => {
      try {
        await result.current.analyzeFacial('base64image')
      } catch (e) {
        // Expected error
      }
    })

    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
      expect(result.current.isAnalyzing).toBe(false)
      expect(onError).toHaveBeenCalled()
    })
  })

  it('resets state', () => {
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const { result } = renderHook(() => useAnalysis())

    act(() => {
      result.current.reset()
    })

    expect(result.current.facialResult).toBeNull()
    expect(result.current.voiceResult).toBeNull()
    expect(result.current.textResult).toBeNull()
    expect(result.current.multimodalResult).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('calls callbacks on result', async () => {
    const mockResult = {
      success: true,
      emotions: { happy: 0.8 },
      dominant_emotion: 'happy',
      confidence: 0.85,
      face_detected: true,
    }

    const onFacialResult = jest.fn()
    mockQnaceApi.analyzeFacial.mockResolvedValue(mockResult)
    mockQnaceApi.checkHealth.mockResolvedValue({
      status: 'ok',
      device: 'cpu',
      models: { facial: true, voice: true, bert: true },
    })

    const { result } = renderHook(() => useAnalysis({ onFacialResult }))

    await act(async () => {
      await result.current.analyzeFacial('base64image')
    })

    await waitFor(() => {
      expect(onFacialResult).toHaveBeenCalledWith(mockResult)
    })
  })
})

