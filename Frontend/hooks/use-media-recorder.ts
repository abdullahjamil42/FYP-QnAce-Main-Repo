'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

export interface UseMediaRecorderOptions {
  audio?: boolean
  video?: boolean
  onRecordingComplete?: (blob: Blob) => void
}

export interface UseMediaRecorderReturn {
  stream: MediaStream | null
  recording: boolean
  paused: boolean
  blob: Blob | null
  error: string | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  pauseRecording: () => void
  resumeRecording: () => void
  reset: () => void
}

export function useMediaRecorder({
  audio = true,
  video = false,
  onRecordingComplete,
}: UseMediaRecorderOptions = {}): UseMediaRecorderReturn {
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [recording, setRecording] = useState(false)
  const [paused, setPaused] = useState(false)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const requestPermissions = useCallback(async () => {
    try {
      const constraints: MediaStreamConstraints = {
        audio,
        video: video ? { facingMode: 'user' } : false,
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
      setStream(mediaStream)
      setError(null)
      return mediaStream
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access media devices'
      setError(errorMessage)
      throw err
    }
  }, [audio, video])

  const startRecording = useCallback(async () => {
    try {
      let mediaStream = stream
      if (!mediaStream) {
        mediaStream = await requestPermissions()
      }

      if (!mediaStream) {
        throw new Error('No media stream available')
      }

      const mimeType = MediaRecorder.isTypeSupported('video/webm')
        ? 'video/webm'
        : MediaRecorder.isTypeSupported('video/mp4')
        ? 'video/mp4'
        : ''

      if (!mimeType) {
        throw new Error('No supported MIME type found')
      }

      const recorder = new MediaRecorder(mediaStream, {
        mimeType,
      })

      chunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const recordedBlob = new Blob(chunksRef.current, { type: mimeType })
        setBlob(recordedBlob)
        if (onRecordingComplete) {
          onRecordingComplete(recordedBlob)
        }
      }

      recorder.onerror = (event) => {
        setError('Recording error occurred')
        console.error('MediaRecorder error:', event)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
      setPaused(false)
      setError(null)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start recording'
      setError(errorMessage)
      setRecording(false)
    }
  }, [stream, requestPermissions, onRecordingComplete])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop()
      setRecording(false)
      setPaused(false)

      // Stop all tracks
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
        setStream(null)
      }
    }
  }, [recording, stream])

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && recording && !paused) {
      mediaRecorderRef.current.pause()
      setPaused(true)
    }
  }, [recording, paused])

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && recording && paused) {
      mediaRecorderRef.current.resume()
      setPaused(false)
    }
  }, [recording, paused])

  const reset = useCallback(() => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop()
    }
    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
    }
    setStream(null)
    setRecording(false)
    setPaused(false)
    setBlob(null)
    setError(null)
    chunksRef.current = []
    mediaRecorderRef.current = null
  }, [recording, stream])

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [stream])

  return {
    stream,
    recording,
    paused,
    blob,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    reset,
  }
}

