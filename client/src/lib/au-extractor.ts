/**
 * Q&Ace — Action Unit (AU) Extractor.
 *
 * Extracts interview-relevant facial Action Units from MediaPipe Face Mesh landmarks.
 * Uses geometry-based calculations on 478 face landmarks.
 *
 * Extracted AUs:
 *   - AU4:  Brow Lowerer (frown intensity)
 *   - AU12: Lip Corner Puller (smile intensity)
 *   - AU45: Blink (eye closure ratio)
 *   - Eye Contact: gaze direction relative to camera center
 *   - Blink Rate: blinks per minute
 *
 * Per ADR-010: AU data is sent to server via DataChannel at ~10Hz.
 * Binary format: [timestamp:uint32][AU4:f32][AU12:f32][AU45:f32][eye_contact:f32]
 */

interface FaceLandmark {
  x: number;
  y: number;
  z: number;
}

export interface AUValues {
  au4: number; // 0-1 brow lowerer
  au12: number; // 0-1 lip corner puller (smile)
  au45: number; // 0-1 blink (1 = fully closed)
  eyeContact: number; // 0-1 looking at camera
  blinkDetected: boolean; // instantaneous blink event
}

// MediaPipe Face Mesh landmark indices
// Reference: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png

// Eyebrow landmarks
const LEFT_BROW_INNER = 105;
const LEFT_BROW_MID = 66;
const LEFT_BROW_OUTER = 46;
const RIGHT_BROW_INNER = 334;
const RIGHT_BROW_MID = 296;
const RIGHT_BROW_OUTER = 276;

// Eye landmarks
const LEFT_EYE_TOP = 159;
const LEFT_EYE_BOTTOM = 145;
const LEFT_EYE_INNER = 133;
const LEFT_EYE_OUTER = 33;
const RIGHT_EYE_TOP = 386;
const RIGHT_EYE_BOTTOM = 374;
const RIGHT_EYE_INNER = 362;
const RIGHT_EYE_OUTER = 263;

// Iris landmarks (from Face Mesh with iris tracking)
const LEFT_IRIS_CENTER = 468;
const RIGHT_IRIS_CENTER = 473;

// Mouth landmarks
const MOUTH_LEFT = 61;
const MOUTH_RIGHT = 291;
const MOUTH_TOP = 13;
const MOUTH_BOTTOM = 14;
const UPPER_LIP = 0;
const LOWER_LIP = 17;

// Reference points
const NOSE_TIP = 1;
const FOREHEAD = 10;
const CHIN = 152;

/**
 * Euclidean distance between two landmarks.
 */
function dist(a: FaceLandmark, b: FaceLandmark): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  // Use 2D distance (z is noisy in face mesh)
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Vertical distance (y only).
 */
function yDist(a: FaceLandmark, b: FaceLandmark): number {
  return Math.abs(a.y - b.y);
}

/**
 * Face height for normalization.
 */
function faceHeight(landmarks: FaceLandmark[]): number {
  return dist(landmarks[FOREHEAD], landmarks[CHIN]);
}

/**
 * AU4 — Brow Lowerer.
 * Measures how much eyebrows are lowered relative to eye level.
 * Lower brows → higher AU4 value.
 */
function computeAU4(landmarks: FaceLandmark[]): number {
  const fh = faceHeight(landmarks);
  if (fh < 0.001) return 0;

  // Distance from mid-brow to corresponding eye top
  const leftBrowDrop =
    yDist(landmarks[LEFT_BROW_MID], landmarks[LEFT_EYE_TOP]) / fh;
  const rightBrowDrop =
    yDist(landmarks[RIGHT_BROW_MID], landmarks[RIGHT_EYE_TOP]) / fh;

  const avgDrop = (leftBrowDrop + rightBrowDrop) / 2;

  // Normalize: typical brow-eye distance is ~0.05-0.12 of face height
  // Low distance → brows lowered → high AU4
  const neutral = 0.08;
  const lowered = 0.04;

  const intensity = 1.0 - Math.min(1.0, Math.max(0.0, (avgDrop - lowered) / (neutral - lowered)));
  return intensity;
}

/**
 * AU12 — Lip Corner Puller (Smile).
 * Measures horizontal stretch of mouth relative to resting width.
 */
function computeAU12(landmarks: FaceLandmark[]): number {
  const fh = faceHeight(landmarks);
  if (fh < 0.001) return 0;

  const mouthWidth = dist(landmarks[MOUTH_LEFT], landmarks[MOUTH_RIGHT]);
  const mouthHeight = dist(landmarks[MOUTH_TOP], landmarks[MOUTH_BOTTOM]);

  // Mouth width-to-height ratio — smile widens and flattens the mouth
  const ratio = mouthWidth / Math.max(mouthHeight, 0.001);

  // Also check if corners are pulled up (y of corners relative to center)
  const cornerY = (landmarks[MOUTH_LEFT].y + landmarks[MOUTH_RIGHT].y) / 2;
  const centerY = (landmarks[MOUTH_TOP].y + landmarks[MOUTH_BOTTOM].y) / 2;
  const cornerLift = (centerY - cornerY) / fh; // positive = corners above center

  // Combine width ratio and corner lift
  const widthScore = Math.min(1.0, Math.max(0.0, (ratio - 1.5) / 2.5)); // 1.5-4.0 range
  const liftScore = Math.min(1.0, Math.max(0.0, cornerLift * 20)); // subtle lift

  return Math.min(1.0, widthScore * 0.6 + liftScore * 0.4);
}

/**
 * AU45 — Blink (Eye Closure).
 * Uses Eye Aspect Ratio (EAR).
 */
function computeAU45(landmarks: FaceLandmark[]): number {
  // EAR = (vertical1 + vertical2) / (2 * horizontal)
  const leftV = yDist(landmarks[LEFT_EYE_TOP], landmarks[LEFT_EYE_BOTTOM]);
  const leftH = dist(landmarks[LEFT_EYE_INNER], landmarks[LEFT_EYE_OUTER]);
  const leftEAR = leftH > 0.001 ? leftV / leftH : 0;

  const rightV = yDist(landmarks[RIGHT_EYE_TOP], landmarks[RIGHT_EYE_BOTTOM]);
  const rightH = dist(landmarks[RIGHT_EYE_INNER], landmarks[RIGHT_EYE_OUTER]);
  const rightEAR = rightH > 0.001 ? rightV / rightH : 0;

  const avgEAR = (leftEAR + rightEAR) / 2;

  // EAR ~0.25-0.35 when open, <0.15 when closed
  // Invert so 1 = fully closed (blink)
  const openThreshold = 0.28;
  const closedThreshold = 0.12;

  const closure =
    1.0 -
    Math.min(
      1.0,
      Math.max(0.0, (avgEAR - closedThreshold) / (openThreshold - closedThreshold))
    );

  return closure;
}

/**
 * Eye Contact — How centered the iris is (looking at camera).
 * Uses iris landmarks relative to eye corners.
 */
function computeEyeContact(landmarks: FaceLandmark[]): number {
  // Check if iris landmarks are available (478+ landmarks)
  if (landmarks.length < 474) {
    // No iris tracking — estimate from head pose
    // Nose tip deviation from face center as proxy
    const noseX = landmarks[NOSE_TIP].x;
    const faceCenterX = (landmarks[LEFT_EYE_INNER].x + landmarks[RIGHT_EYE_INNER].x) / 2;
    const deviation = Math.abs(noseX - faceCenterX);

    // Also use forehead-chin alignment for pitch
    const foreheadX = landmarks[FOREHEAD].x;
    const chinX = landmarks[CHIN].x;
    const pitchDeviation = Math.abs(foreheadX - chinX);

    const totalDeviation = deviation + pitchDeviation * 0.5;
    return Math.max(0, 1.0 - totalDeviation * 10);
  }

  // With iris tracking — measure iris position relative to eye center
  const leftIris = landmarks[LEFT_IRIS_CENTER];
  const leftCenter = {
    x: (landmarks[LEFT_EYE_INNER].x + landmarks[LEFT_EYE_OUTER].x) / 2,
    y: (landmarks[LEFT_EYE_TOP].y + landmarks[LEFT_EYE_BOTTOM].y) / 2,
    z: 0,
  };
  const leftEyeWidth = dist(landmarks[LEFT_EYE_INNER], landmarks[LEFT_EYE_OUTER]);
  const leftDeviation = dist(leftIris, leftCenter) / Math.max(leftEyeWidth, 0.001);

  const rightIris = landmarks[RIGHT_IRIS_CENTER];
  const rightCenter = {
    x: (landmarks[RIGHT_EYE_INNER].x + landmarks[RIGHT_EYE_OUTER].x) / 2,
    y: (landmarks[RIGHT_EYE_TOP].y + landmarks[RIGHT_EYE_BOTTOM].y) / 2,
    z: 0,
  };
  const rightEyeWidth = dist(landmarks[RIGHT_EYE_INNER], landmarks[RIGHT_EYE_OUTER]);
  const rightDeviation = dist(rightIris, rightCenter) / Math.max(rightEyeWidth, 0.001);

  const avgDeviation = (leftDeviation + rightDeviation) / 2;

  // Centered iris → high eye contact
  return Math.max(0, Math.min(1, 1.0 - avgDeviation * 3));
}

// Blink detection state
let prevAU45 = 0;
let blinkCooldown = 0;

/**
 * Extract all Action Unit values from face landmarks.
 */
export function extractAUs(landmarks: FaceLandmark[]): AUValues {
  if (!landmarks || landmarks.length < 468) {
    return {
      au4: 0,
      au12: 0,
      au45: 0,
      eyeContact: 0,
      blinkDetected: false,
    };
  }

  const au4 = computeAU4(landmarks);
  const au12 = computeAU12(landmarks);
  const au45 = computeAU45(landmarks);
  const eyeContact = computeEyeContact(landmarks);

  // Detect blink events (au45 crosses threshold)
  let blinkDetected = false;
  if (blinkCooldown > 0) {
    blinkCooldown--;
  } else if (au45 > 0.6 && prevAU45 < 0.4) {
    blinkDetected = true;
    blinkCooldown = 3; // ~300ms cooldown at 10Hz
  }
  prevAU45 = au45;

  return { au4, au12, au45, eyeContact, blinkDetected };
}

/**
 * Pack AU values into a 20-byte binary buffer for DataChannel transmission.
 * Format: [timestamp:uint32][AU4:f32][AU12:f32][AU45:f32][eye_contact:f32]
 */
export function packAUTelemetry(aus: AUValues): ArrayBuffer {
  const buffer = new ArrayBuffer(20);
  const view = new DataView(buffer);
  const timestamp = (Date.now() & 0xffffffff) >>> 0; // uint32 wrap

  view.setUint32(0, timestamp, true); // little-endian
  view.setFloat32(4, aus.au4, true);
  view.setFloat32(8, aus.au12, true);
  view.setFloat32(12, aus.au45, true);
  view.setFloat32(16, aus.eyeContact, true);

  return buffer;
}
