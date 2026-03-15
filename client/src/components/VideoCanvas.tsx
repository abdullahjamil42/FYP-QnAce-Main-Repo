/**
 * Q&Ace — VideoCanvas Component.
 *
 * Renders the user's webcam feed with MediaPipe Face Mesh overlay,
 * and manages the face crop canvas for WebRTC video track transmission.
 *
 * This component integrates:
 *   - Webcam video display
 *   - MediaPipe Face Mesh landmark overlay
 *   - Face crop extraction → 224×224 canvas stream
 *   - AU extraction and telemetry dispatch
 */

"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import MediaPipeFaceMesh, { FaceMeshResult } from "./MediaPipeFaceMesh";
import { extractAUs, packAUTelemetry, AUValues } from "@/lib/au-extractor";
import { createFaceCropCanvas, drawFaceCrop } from "@/lib/face-crop";

interface VideoCanvasProps {
  videoStream: MediaStream | null;
  onFaceCropStream?: (stream: MediaStream) => void;
  onAUTelemetry?: (buffer: ArrayBuffer) => void;
  showOverlay?: boolean;
  containerClassName?: string;
  videoClassName?: string;
  showStats?: boolean;
}

export default function VideoCanvas({
  videoStream,
  onFaceCropStream,
  onAUTelemetry,
  showOverlay = true,
  containerClassName,
  videoClassName,
  showStats = true,
}: VideoCanvasProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cropRef = useRef<{
    canvas: HTMLCanvasElement;
    ctx: CanvasRenderingContext2D;
    stream: MediaStream;
  } | null>(null);
  const [latestAUs, setLatestAUs] = useState<AUValues | null>(null);
  const [blinks, setBlinks] = useState(0);

  // Initialize face crop canvas
  useEffect(() => {
    const crop = createFaceCropCanvas();
    cropRef.current = crop;

    // Notify parent of the face crop stream
    onFaceCropStream?.(crop.stream);

    return () => {
      // Stop all tracks on cleanup
      crop.stream.getTracks().forEach((t) => t.stop());
    };
  }, [onFaceCropStream]);

  // Attach video stream to hidden video element (for crop extraction)
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !videoStream) return;

    video.srcObject = videoStream;
    video.play().catch(() => {});

    return () => {
      video.srcObject = null;
    };
  }, [videoStream]);

  // Handle MediaPipe Face Mesh results
  const handleFaceMeshResults = useCallback(
    (result: FaceMeshResult | null) => {
      const video = videoRef.current;
      const crop = cropRef.current;
      if (!video || !crop) return;

      // Update face crop
      drawFaceCrop(crop.ctx, video, result?.boundingBox ?? null);

      // Extract AUs and send telemetry
      if (result?.landmarks) {
        const aus = extractAUs(result.landmarks);
        setLatestAUs(aus);

        // Count blinks
        if (aus.blinkDetected) {
          setBlinks((prev) => prev + 1);
        }

        // Pack and send telemetry
        if (onAUTelemetry) {
          const packed = packAUTelemetry(aus);
          onAUTelemetry(packed);
        }
      }
    },
    [onAUTelemetry]
  );

  return (
    <div className={containerClassName ?? "flex flex-col items-center gap-2"}>
      {/* Hidden video element for crop extraction */}
      <video
        ref={videoRef}
        className="hidden"
        autoPlay
        playsInline
        muted
      />

      {/* Visible MediaPipe overlay */}
      <MediaPipeFaceMesh
        videoStream={videoStream}
        onResults={handleFaceMeshResults}
        showOverlay={showOverlay}
        fps={10}
        videoClassName={videoClassName}
      />

      {/* AU telemetry display */}
      {showStats && latestAUs && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-lg bg-qace-surface px-3 py-2 text-xs text-qace-muted">
          <div className="flex justify-between gap-2">
            <span>Brow</span>
            <span className="font-mono">{latestAUs.au4.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-2">
            <span>Smile</span>
            <span className="font-mono">{latestAUs.au12.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-2">
            <span>Blink</span>
            <span className="font-mono">{latestAUs.au45.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-2">
            <span>Eye</span>
            <span className="font-mono">
              {latestAUs.eyeContact.toFixed(2)}
            </span>
          </div>
          <div className="col-span-2 text-center text-qace-muted/60">
            {blinks} blinks
          </div>
        </div>
      )}
    </div>
  );
}
