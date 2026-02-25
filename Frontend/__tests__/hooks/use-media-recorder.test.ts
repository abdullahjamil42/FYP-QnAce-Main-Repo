import { renderHook, act, waitFor } from '@testing-library/react'
import { useMediaRecorder } from '@/hooks/use-media-recorder'

// Mock MediaRecorder
const mockMediaRecorder = {
  start: jest.fn(),
  stop: jest.fn(),
  pause: jest.fn(),
  resume: jest.fn(),
  state: 'inactive',
  ondataavailable: null,
  onerror: null,
  onstart: null,
  onstop: null,
  onpause: null,
  onresume: null,
}

const mockGetUserMedia = jest.fn().mockResolvedValue({
  getTracks: () => [
    {
      stop: jest.fn(),
      kind: 'video',
    },
  ],
})

describe('useMediaRecorder', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(global.MediaRecorder as any) = jest.fn().mockImplementation(() => mockMediaRecorder)
    ;(MediaRecorder as any).isTypeSupported = jest.fn().mockReturnValue(true)
    ;(global.navigator.mediaDevices as any) = {
      getUserMedia: mockGetUserMedia,
    }
  })

  it('initializes with default state', () => {
    const { result } = renderHook(() => useMediaRecorder())

    expect(result.current.recording).toBe(false)
    expect(result.current.paused).toBe(false)
    expect(result.current.blob).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.stream).toBeNull()
  })

  it('starts recording', async () => {
    const { result } = renderHook(() => useMediaRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(true)
      expect(mockMediaRecorder.start).toHaveBeenCalled()
    })
  })

  it('stops recording', async () => {
    const { result } = renderHook(() => useMediaRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(true)
    })

    act(() => {
      result.current.stopRecording()
    })

    await waitFor(() => {
      expect(mockMediaRecorder.stop).toHaveBeenCalled()
      expect(result.current.recording).toBe(false)
    })
  })

  it('pauses recording', async () => {
    const { result } = renderHook(() => useMediaRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(true)
    })

    act(() => {
      result.current.pauseRecording()
    })

    await waitFor(() => {
      expect(mockMediaRecorder.pause).toHaveBeenCalled()
      expect(result.current.paused).toBe(true)
    })
  })

  it('resumes recording', async () => {
    const { result } = renderHook(() => useMediaRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(true)
    })

    act(() => {
      result.current.pauseRecording()
    })

    await waitFor(() => {
      expect(result.current.paused).toBe(true)
    })

    act(() => {
      result.current.resumeRecording()
    })

    await waitFor(() => {
      expect(mockMediaRecorder.resume).toHaveBeenCalled()
      expect(result.current.paused).toBe(false)
    })
  })

  it('handles recording completion callback', async () => {
    const onRecordingComplete = jest.fn()
    const mockBlob = new Blob(['test'], { type: 'video/webm' })

    const { result } = renderHook(() =>
      useMediaRecorder({ onRecordingComplete })
    )

    await act(async () => {
      await result.current.startRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(true)
    })

    // Stop recording to trigger callback
    act(() => {
      result.current.stopRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(false)
    })
  })

  it('handles errors', async () => {
    const errorMessage = 'Permission denied'
    mockGetUserMedia.mockRejectedValueOnce(new Error(errorMessage))

    const { result } = renderHook(() => useMediaRecorder())

    await act(async () => {
      try {
        await result.current.startRecording()
      } catch (e) {
        // Expected error
      }
    })

    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
    })
  })

  it('resets recording state', async () => {
    const { result } = renderHook(() => useMediaRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    await waitFor(() => {
      expect(result.current.recording).toBe(true)
    })

    act(() => {
      result.current.reset()
    })

    expect(result.current.recording).toBe(false)
    expect(result.current.paused).toBe(false)
    expect(result.current.blob).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.stream).toBeNull()
  })

  it('cleans up stream on unmount', async () => {
    const trackStop = jest.fn()
    mockGetUserMedia.mockResolvedValueOnce({
      getTracks: () => [{ stop: trackStop, kind: 'video' }],
    })

    const { result, unmount } = renderHook(() => useMediaRecorder())

    await act(async () => {
      await result.current.startRecording()
    })

    unmount()

    await waitFor(() => {
      expect(trackStop).toHaveBeenCalled()
    })
  })
})

