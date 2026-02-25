'use client'

import * as React from 'react'
import { useMediaRecorder } from '@/hooks/use-media-recorder'
import { formatDuration } from '@/lib/utils'
import { Button } from './button'
import { Play, Pause, Square, Video, VideoOff, Mic, MicOff } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface MediaRecorderProps {
  onRecordingComplete?: (blob: Blob) => void
  audio?: boolean
  video?: boolean
  className?: string
}

export function MediaRecorder({
  onRecordingComplete,
  audio = true,
  video = true,
  className,
}: MediaRecorderProps) {
  const [duration, setDuration] = React.useState(0)
  const intervalRef = React.useRef<NodeJS.Timeout | null>(null)
  const videoRef = React.useRef<HTMLVideoElement>(null)

  const {
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
  } = useMediaRecorder({
    audio,
    video,
    onRecordingComplete,
  })

  // Update video element when stream changes
  React.useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream
    }
  }, [stream])

  // Timer effect
  React.useEffect(() => {
    if (recording && !paused) {
      intervalRef.current = setInterval(() => {
        setDuration((prev) => prev + 1)
      }, 1000)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [recording, paused])

  const handleStart = async () => {
    setDuration(0)
    await startRecording()
  }

  const handleStop = () => {
    stopRecording()
    setDuration(0)
  }

  const handleReset = () => {
    reset()
    setDuration(0)
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Video Preview */}
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-gradient-to-br from-gradient-purple/20 to-gradient-blue/20">
        {video && (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={cn(
              'h-full w-full object-cover scale-x-[-1]',
              !stream && 'hidden'
            )}
          />
        )}
        {!stream && !blob && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <VideoOff className="mx-auto h-12 w-12 text-foreground/40" />
              <p className="mt-2 text-sm text-foreground/60">Camera preview will appear here</p>
            </div>
          </div>
        )}
        {blob && (
          <video
            src={URL.createObjectURL(blob)}
            controls
            className="h-full w-full object-cover"
          />
        )}
        {/* Recording indicator */}
        {recording && (
          <div className="absolute top-4 left-4 flex items-center gap-2 rounded-lg bg-red-500/90 px-3 py-1.5 backdrop-blur-sm">
            <div className="h-2 w-2 animate-pulse rounded-full bg-white" />
            <span className="text-xs font-medium text-white">Recording</span>
          </div>
        )}
        {/* Timer */}
        {(recording || paused) && (
          <div className="absolute top-4 right-4 rounded-lg bg-background/80 px-3 py-1.5 backdrop-blur-sm">
            <span className="text-sm font-mono font-medium text-foreground">
              {formatDuration(duration)}
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-3">
        {!recording && !blob && (
          <Button onClick={handleStart} variant="primary" size="lg">
            <Video className="mr-2 h-5 w-5" />
            Start Recording
          </Button>
        )}

        {recording && (
          <>
            {paused ? (
              <Button onClick={resumeRecording} variant="primary" size="lg">
                <Play className="mr-2 h-5 w-5" />
                Resume
              </Button>
            ) : (
              <Button onClick={pauseRecording} variant="secondary" size="lg">
                <Pause className="mr-2 h-5 w-5" />
                Pause
              </Button>
            )}
            <Button onClick={handleStop} variant="danger" size="lg">
              <Square className="mr-2 h-5 w-5" />
              Stop
            </Button>
          </>
        )}

        {blob && (
          <>
            <Button onClick={handleReset} variant="ghost" size="lg">
              Record Again
            </Button>
          </>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="rounded-lg bg-red-500/20 border border-red-500/50 p-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Status indicators */}
      <div className="flex items-center justify-center gap-4 text-sm text-foreground/60">
        {audio && (
          <div className="flex items-center gap-2">
            {stream ? (
              <Mic className="h-4 w-4 text-green-400" />
            ) : (
              <MicOff className="h-4 w-4" />
            )}
            <span>Microphone</span>
          </div>
        )}
        {video && (
          <div className="flex items-center gap-2">
            {stream ? (
              <Video className="h-4 w-4 text-green-400" />
            ) : (
              <VideoOff className="h-4 w-4" />
            )}
            <span>Camera</span>
          </div>
        )}
      </div>
    </div>
  )
}

