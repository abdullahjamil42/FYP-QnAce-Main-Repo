/**
 * Q&Ace — MediaPipe Face Mesh Component.
 *
 * Runs MediaPipe Face Mesh (WASM backend) on the webcam feed in real-time.
 * Exposes face landmarks for AU extraction and face cropping.
 *
 * Architecture per ADR-010:
 *   - Face mesh runs client-side (WASM, no server load).
 *   - Landmarks fed to AU extractor at ~10 Hz.
 *   - Face bounding box used for 224×224 crop.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// MediaPipe Face Mesh types
interface FaceLandmark {
  x: number; // 0..1 normalized
  y: number;
  z: number;
}

export interface FaceMeshResult {
  landmarks: FaceLandmark[];
  boundingBox: {
    xMin: number;
    yMin: number;
    width: number;
    height: number;
  } | null;
  timestamp: number;
}

interface MediaPipeFaceMeshProps {
  videoStream: MediaStream | null;
  onResults?: (result: FaceMeshResult | null) => void;
  showOverlay?: boolean;
  fps?: number;
  videoClassName?: string;
}

/**
 * Compute bounding box from face landmarks.
 */
function computeBoundingBox(
  landmarks: FaceLandmark[],
  videoWidth: number,
  videoHeight: number,
  padding: number = 0.15
) {
  if (landmarks.length === 0) return null;

  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;

  for (const lm of landmarks) {
    if (lm.x < minX) minX = lm.x;
    if (lm.y < minY) minY = lm.y;
    if (lm.x > maxX) maxX = lm.x;
    if (lm.y > maxY) maxY = lm.y;
  }

  // Add padding
  const w = maxX - minX;
  const h = maxY - minY;
  const padX = w * padding;
  const padY = h * padding;

  return {
    xMin: Math.max(0, (minX - padX) * videoWidth),
    yMin: Math.max(0, (minY - padY) * videoHeight),
    width: Math.min(videoWidth, (w + 2 * padX) * videoWidth),
    height: Math.min(videoHeight, (h + 2 * padY) * videoHeight),
  };
}

/**
 * Draw face mesh landmarks on a canvas overlay.
 */
function drawLandmarks(
  ctx: CanvasRenderingContext2D,
  landmarks: FaceLandmark[],
  canvasWidth: number,
  canvasHeight: number
) {
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  ctx.fillStyle = "rgba(99, 102, 241, 0.6)"; // qace-primary with alpha

  for (const lm of landmarks) {
    const x = lm.x * canvasWidth;
    const y = lm.y * canvasHeight;
    ctx.beginPath();
    ctx.arc(x, y, 1, 0, 2 * Math.PI);
    ctx.fill();
  }
}

export default function MediaPipeFaceMesh({
  videoStream,
  onResults,
  showOverlay = true,
  fps = 10,
  videoClassName = "h-64 w-64 rounded-2xl",
}: MediaPipeFaceMeshProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const faceMeshRef = useRef<any>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize MediaPipe Face Mesh
  useEffect(() => {
    let cancelled = false;

    async function initFaceMesh() {
      try {
        // Dynamic import to avoid SSR issues
        const vision = await import("@mediapipe/tasks-vision");

        const { FaceLandmarker, FilesetResolver } = vision;

        const filesetResolver = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );

        const faceLandmarker = await FaceLandmarker.createFromOptions(
          filesetResolver,
          {
            baseOptions: {
              modelAssetPath:
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
              delegate: "GPU",
            },
            runningMode: "VIDEO",
            numFaces: 1,
            outputFaceBlendshapes: true,
            outputFacialTransformationMatrixes: false,
            minFaceDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5,
          }
        );

        if (!cancelled) {
          faceMeshRef.current = faceLandmarker;
          setLoaded(true);
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error("MediaPipe Face Mesh init error:", err);
          setError(err?.message ?? "Failed to load face mesh");
        }
      }
    }

    initFaceMesh();

    return () => {
      cancelled = true;
      if (faceMeshRef.current) {
        faceMeshRef.current.close();
        faceMeshRef.current = null;
      }
    };
  }, []);

  // Attach video stream
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !videoStream) return;

    video.srcObject = videoStream;
    video.play().catch(() => {});

    return () => {
      video.srcObject = null;
    };
  }, [videoStream]);

  // Run face mesh detection loop
  useEffect(() => {
    if (!loaded || !videoStream) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const intervalMs = 1000 / fps;
    let lastTime = 0;

    function detect(timestamp: number) {
      animFrameRef.current = requestAnimationFrame(detect);

      if (timestamp - lastTime < intervalMs) return;
      lastTime = timestamp;

      const faceMesh = faceMeshRef.current;
      if (!faceMesh || video!.readyState < 2) return;

      try {
        const results = faceMesh.detectForVideo(video!, timestamp);

        if (
          results?.faceLandmarks &&
          results.faceLandmarks.length > 0
        ) {
          const landmarks: FaceLandmark[] = results.faceLandmarks[0];
          const bbox = computeBoundingBox(
            landmarks,
            video!.videoWidth,
            video!.videoHeight
          );

          const meshResult: FaceMeshResult = {
            landmarks,
            boundingBox: bbox,
            timestamp,
          };

          if (showOverlay && ctx) {
            canvas!.width = video!.videoWidth;
            canvas!.height = video!.videoHeight;
            drawLandmarks(ctx, landmarks, canvas!.width, canvas!.height);
          }

          onResults?.(meshResult);
        } else {
          if (showOverlay && ctx) {
            ctx.clearRect(0, 0, canvas!.width, canvas!.height);
          }
          onResults?.(null);
        }
      } catch (err) {
        // Face mesh inference errors are non-fatal
        console.debug("Face mesh detect error:", err);
      }
    }

    animFrameRef.current = requestAnimationFrame(detect);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [loaded, videoStream, fps, showOverlay, onResults]);

  return (
    <div className="relative">
      <video
        ref={videoRef}
        className={`${videoClassName} bg-qace-surface object-contain shadow-lg`}
        autoPlay
        playsInline
        muted
      />
      {showOverlay && (
        <canvas
          ref={canvasRef}
          className={`pointer-events-none absolute inset-0 object-contain ${videoClassName}`}
        />
      )}
      {error && (
        <div className="absolute bottom-2 left-2 right-2 rounded bg-red-900/80 px-2 py-1 text-xs text-red-300">
          {error}
        </div>
      )}
      {!loaded && !error && (
        <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-qace-dark/50">
          <span className="animate-pulse text-sm text-qace-muted">
            Loading face mesh…
          </span>
        </div>
      )}
    </div>
  );
}
