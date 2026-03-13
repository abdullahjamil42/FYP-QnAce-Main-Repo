/**
 * Q&Ace — Face Crop Utility.
 *
 * Crops a 224×224 RGB face region from a video frame using the bounding box
 * provided by MediaPipe Face Mesh, then makes it available as a video track
 * for WebRTC transmission to the server.
 *
 * Architecture per ADR-007/ADR-010:
 *   - Only 224×224 face crops are sent (not full webcam frames).
 *   - Transmitted at 10 FPS via a second WebRTC video track.
 *   - Uses canvas.captureStream(10) for the track.
 */

const CROP_SIZE = 224;

interface BoundingBox {
  xMin: number;
  yMin: number;
  width: number;
  height: number;
}

/**
 * Create a face crop canvas and return the capture stream.
 */
export function createFaceCropCanvas(): {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  stream: MediaStream;
} {
  const canvas = document.createElement("canvas");
  canvas.width = CROP_SIZE;
  canvas.height = CROP_SIZE;

  const ctx = canvas.getContext("2d")!;

  // Fill with gray initially (no face detected state)
  ctx.fillStyle = "#404040";
  ctx.fillRect(0, 0, CROP_SIZE, CROP_SIZE);

  // captureStream(10) = 10 FPS video track
  const stream = canvas.captureStream(10);

  return { canvas, ctx, stream };
}

/**
 * Draw a face crop from a video element onto the crop canvas.
 *
 * The bounding box comes from MediaPipe Face Mesh landmark analysis.
 * The crop is resized to 224×224 to match EfficientNet-B2 input.
 */
export function drawFaceCrop(
  ctx: CanvasRenderingContext2D,
  videoElement: HTMLVideoElement,
  boundingBox: BoundingBox | null
): void {
  if (!boundingBox || !videoElement.videoWidth) {
    // No face detected — draw gray placeholder
    ctx.fillStyle = "#404040";
    ctx.fillRect(0, 0, CROP_SIZE, CROP_SIZE);
    return;
  }

  const { xMin, yMin, width, height } = boundingBox;

  // Make the crop square (use the larger dimension)
  const side = Math.max(width, height);
  const centerX = xMin + width / 2;
  const centerY = yMin + height / 2;

  const srcX = Math.max(0, centerX - side / 2);
  const srcY = Math.max(0, centerY - side / 2);
  const srcW = Math.min(side, videoElement.videoWidth - srcX);
  const srcH = Math.min(side, videoElement.videoHeight - srcY);

  try {
    ctx.drawImage(
      videoElement,
      srcX,
      srcY,
      srcW,
      srcH,
      0,
      0,
      CROP_SIZE,
      CROP_SIZE
    );
  } catch {
    // Video may not be ready — fill with gray
    ctx.fillStyle = "#404040";
    ctx.fillRect(0, 0, CROP_SIZE, CROP_SIZE);
  }
}

/**
 * Get pixel data from the crop canvas as a Uint8ClampedArray (RGBA).
 */
export function getCropPixelData(
  ctx: CanvasRenderingContext2D
): Uint8ClampedArray {
  return ctx.getImageData(0, 0, CROP_SIZE, CROP_SIZE).data;
}
