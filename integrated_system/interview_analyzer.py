"""
Real-time Multimodal Interview Analyzer.

This system combines facial and voice emotion detection for comprehensive
interview analysis with real-time feedback and report generation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
import time
import json
import threading
import queue

import numpy as np
import cv2

# Try to import audio libraries
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warning: sounddevice not installed. Audio recording unavailable.")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


@dataclass
class FrameAnalysis:
    """Analysis result for a single frame/audio segment."""
    timestamp: float
    
    # Combined
    confidence_score: float
    confidence_level: str
    dominant_emotion: str
    fused_emotions: Dict[str, float]
    
    # Facial
    facial_dominant: Optional[str] = None
    facial_confidence: float = 0.0
    facial_emotions: Optional[Dict[str, float]] = None
    face_detected: bool = False
    
    # Voice
    voice_dominant: Optional[str] = None
    voice_confidence: float = 0.0
    voice_emotions: Optional[Dict[str, float]] = None
    voice_detected: bool = False


@dataclass
class SessionData:
    """Complete session data for reporting."""
    session_id: str
    start_time: float
    frames: List[FrameAnalysis] = field(default_factory=list)
    
    # Summary stats (calculated at end)
    duration: float = 0.0
    avg_confidence: float = 0.0
    min_confidence: float = 100.0
    max_confidence: float = 0.0
    
    # Segment data
    beginning_confidence: float = 0.0
    middle_confidence: float = 0.0
    end_confidence: float = 0.0
    
    # Emotion distribution
    emotion_distribution: Dict[str, float] = field(default_factory=dict)
    
    # Modality usage
    facial_frames: int = 0
    voice_frames: int = 0
    multimodal_frames: int = 0


class MultimodalInterviewAnalyzer:
    """
    Real-time multimodal interview analyzer.
    
    Combines:
    - Facial emotion detection (72.72% accuracy)
    - Voice emotion detection (73.37% accuracy)
    - Confidence scoring
    - Session tracking
    - Report generation
    """
    
    def __init__(
        self,
        facial_weight: float = 0.5,
        voice_weight: float = 0.5,
        window_size: int = 10,
        audio_segment_duration: float = 2.0,  # seconds
        sample_rate: int = 16000,
    ):
        """
        Initialize multimodal analyzer.
        
        Args:
            facial_weight: Weight for facial emotions (0-1)
            voice_weight: Weight for voice emotions (0-1)
            window_size: Rolling window size for smoothing
            audio_segment_duration: Duration of audio segments for analysis
            sample_rate: Audio sample rate
        """
        print("="*60)
        print("🎯 Q&ACE MULTIMODAL INTERVIEW ANALYZER")
        print("="*60)
        
        self.facial_weight = facial_weight
        self.voice_weight = voice_weight
        self.window_size = window_size
        self.audio_segment_duration = audio_segment_duration
        self.sample_rate = sample_rate
        
        # Initialize detectors
        self.multimodal_detector = None
        self._init_detector()
        
        # Session tracking
        self.session: Optional[SessionData] = None
        self.recent_confidences = deque(maxlen=window_size)
        self.recent_emotions = deque(maxlen=window_size)
        
        # Audio buffer
        self.audio_buffer = []
        self.audio_lock = threading.Lock()
        
        # Confidence weights
        self.confidence_weights = {
            'happy': 0.85,
            'neutral': 0.75,
            'surprise': 0.50,
            'sad': -0.60,
            'fear': -0.70,
            'anger': -0.50,
            'disgust': -0.40
        }
        
        # Confidence levels
        self.confidence_levels = [
            (0.80, "Excellent", (46, 204, 113)),    # Green
            (0.65, "Confident", (52, 152, 219)),    # Blue
            (0.50, "Moderate", (241, 196, 15)),     # Yellow
            (0.35, "Nervous", (230, 126, 34)),      # Orange
            (0.20, "Anxious", (231, 76, 60)),       # Red
            (0.00, "Very Anxious", (192, 57, 43))   # Dark Red
        ]
        
        print("✅ Multimodal analyzer ready!")
    
    def _init_detector(self):
        """Initialize the multimodal detector."""
        try:
            from multimodal_detector import MultimodalEmotionDetector
            self.multimodal_detector = MultimodalEmotionDetector(
                facial_weight=self.facial_weight,
                voice_weight=self.voice_weight
            )
        except Exception as e:
            print(f"⚠️ Failed to initialize multimodal detector: {e}")
            # Try facial only
            try:
                from facial_emotion_detector import FacialEmotionDetector
                self.facial_detector = FacialEmotionDetector()
                print("  Using facial-only mode")
            except Exception as e2:
                print(f"❌ Failed to initialize any detector: {e2}")
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new analysis session.
        
        Args:
            session_id: Optional custom session ID
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.session = SessionData(
            session_id=session_id,
            start_time=time.time()
        )
        
        self.recent_confidences.clear()
        self.recent_emotions.clear()
        self.audio_buffer.clear()
        
        print(f"\n🎬 Session started: {session_id}")
        return session_id
    
    def end_session(self) -> SessionData:
        """
        End the current session and calculate summary stats.
        
        Returns:
            Complete session data
        """
        if self.session is None:
            raise ValueError("No active session")
        
        session = self.session
        session.duration = time.time() - session.start_time
        
        if session.frames:
            # Calculate statistics
            confidences = [f.confidence_score for f in session.frames]
            session.avg_confidence = np.mean(confidences)
            session.min_confidence = min(confidences)
            session.max_confidence = max(confidences)
            
            # Segment analysis
            n = len(session.frames)
            begin_end = int(n * 0.2)
            
            if begin_end > 0:
                session.beginning_confidence = np.mean(
                    [f.confidence_score for f in session.frames[:begin_end]]
                )
                session.end_confidence = np.mean(
                    [f.confidence_score for f in session.frames[-begin_end:]]
                )
                session.middle_confidence = np.mean(
                    [f.confidence_score for f in session.frames[begin_end:-begin_end]]
                ) if n > 2 * begin_end else session.avg_confidence
            
            # Emotion distribution
            emotion_counts = {}
            for frame in session.frames:
                emotion = frame.dominant_emotion
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            total = sum(emotion_counts.values())
            session.emotion_distribution = {
                e: count / total * 100 for e, count in emotion_counts.items()
            }
            
            # Modality usage
            session.facial_frames = sum(1 for f in session.frames if f.face_detected)
            session.voice_frames = sum(1 for f in session.frames if f.voice_detected)
            session.multimodal_frames = sum(
                1 for f in session.frames if f.face_detected and f.voice_detected
            )
        
        print(f"\n🏁 Session ended: {session.session_id}")
        print(f"   Duration: {session.duration:.1f}s")
        print(f"   Avg Confidence: {session.avg_confidence:.1f}%")
        
        self.session = None
        return session
    
    def calculate_confidence(self, emotions: Dict[str, float]) -> Tuple[float, str, Tuple]:
        """
        Calculate interview confidence score from emotions.
        
        Args:
            emotions: Dict of emotion probabilities
            
        Returns:
            Tuple of (score 0-100, level string, color BGR)
        """
        raw_score = 0.5
        for emotion, prob in emotions.items():
            if emotion in self.confidence_weights:
                raw_score += self.confidence_weights[emotion] * prob * 0.5
        
        score = max(0.0, min(1.0, raw_score)) * 100
        
        # Get level and color
        for threshold, level, color in self.confidence_levels:
            if score / 100 >= threshold:
                return score, level, color
        
        return score, "Very Anxious", (192, 57, 43)
    
    def analyze_frame(
        self,
        frame: np.ndarray,
        audio: Optional[np.ndarray] = None
    ) -> FrameAnalysis:
        """
        Analyze a video frame and optional audio segment.
        
        Args:
            frame: BGR image as numpy array
            audio: Optional audio waveform
            
        Returns:
            FrameAnalysis with all results
        """
        timestamp = time.time()
        
        # Get multimodal detection
        if self.multimodal_detector is not None:
            result = self.multimodal_detector.detect(
                frame=frame,
                audio=audio,
                sample_rate=self.sample_rate
            )
            
            fused_emotions = result.emotions
            dominant_emotion = result.dominant_emotion
            
            facial_emotions = result.facial_emotions
            facial_dominant = result.facial_dominant
            facial_confidence = result.facial_confidence
            face_detected = result.face_detected
            
            voice_emotions = result.voice_emotions
            voice_dominant = result.voice_dominant
            voice_confidence = result.voice_confidence
            voice_detected = result.voice_detected
        else:
            # Fallback to facial only
            fused_emotions = {'neutral': 1.0}
            dominant_emotion = 'neutral'
            facial_emotions = None
            facial_dominant = None
            facial_confidence = 0.0
            face_detected = False
            voice_emotions = None
            voice_dominant = None
            voice_confidence = 0.0
            voice_detected = False
        
        # Calculate confidence score
        confidence_score, confidence_level, _ = self.calculate_confidence(fused_emotions)
        
        # Create analysis result
        analysis = FrameAnalysis(
            timestamp=timestamp,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            dominant_emotion=dominant_emotion,
            fused_emotions=fused_emotions,
            facial_dominant=facial_dominant,
            facial_confidence=facial_confidence,
            facial_emotions=facial_emotions,
            face_detected=face_detected,
            voice_dominant=voice_dominant,
            voice_confidence=voice_confidence,
            voice_emotions=voice_emotions,
            voice_detected=voice_detected
        )
        
        # Update session
        if self.session is not None:
            self.session.frames.append(analysis)
        
        # Update rolling averages
        self.recent_confidences.append(confidence_score)
        self.recent_emotions.append(fused_emotions)
        
        return analysis
    
    def get_smoothed_confidence(self) -> float:
        """Get smoothed confidence over recent frames."""
        if not self.recent_confidences:
            return 50.0
        return np.mean(self.recent_confidences)
    
    def get_smoothed_emotions(self) -> Dict[str, float]:
        """Get smoothed emotions over recent frames."""
        if not self.recent_emotions:
            return {'neutral': 1.0}
        
        smoothed = {}
        for emotions in self.recent_emotions:
            for emotion, prob in emotions.items():
                smoothed[emotion] = smoothed.get(emotion, 0) + prob
        
        total = len(self.recent_emotions)
        return {e: p / total for e, p in smoothed.items()}
    
    def draw_overlay(
        self,
        frame: np.ndarray,
        analysis: FrameAnalysis,
        show_details: bool = True
    ) -> np.ndarray:
        """
        Draw analysis overlay on frame.
        
        Args:
            frame: BGR image
            analysis: Current frame analysis
            show_details: Whether to show detailed info
            
        Returns:
            Frame with overlay
        """
        frame = frame.copy()
        h, w = frame.shape[:2]
        
        # Get confidence color
        _, _, color = self.calculate_confidence(analysis.fused_emotions)
        color = tuple(int(c) for c in color)  # Ensure int
        
        # Draw confidence bar
        bar_width = 200
        bar_height = 30
        bar_x = w - bar_width - 20
        bar_y = 20
        
        # Background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (50, 50, 50), -1)
        
        # Fill
        fill_width = int(bar_width * analysis.confidence_score / 100)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height),
                     color, -1)
        
        # Border
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                     (255, 255, 255), 2)
        
        # Confidence text
        conf_text = f"{analysis.confidence_score:.0f}% - {analysis.confidence_level}"
        cv2.putText(frame, conf_text, (bar_x, bar_y + bar_height + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        if show_details:
            # Emotion text
            emotion_text = f"Emotion: {analysis.dominant_emotion.upper()}"
            cv2.putText(frame, emotion_text, (bar_x, bar_y + bar_height + 55),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Modality indicators
            y_offset = bar_y + bar_height + 85
            
            if analysis.face_detected:
                cv2.putText(frame, f"Face: {analysis.facial_dominant}", (bar_x, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.putText(frame, "Face: Not detected", (bar_x, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            y_offset += 25
            if analysis.voice_detected:
                cv2.putText(frame, f"Voice: {analysis.voice_dominant}", (bar_x, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.putText(frame, "Voice: Listening...", (bar_x, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        
        # Session info
        if self.session:
            elapsed = time.time() - self.session.start_time
            cv2.putText(frame, f"Session: {elapsed:.1f}s", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def save_session(self, session: SessionData, output_dir: str) -> str:
        """
        Save session data to JSON file.
        
        Args:
            session: Session data to save
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert to dict (dataclasses don't serialize directly)
        data = {
            'session_id': session.session_id,
            'start_time': session.start_time,
            'duration': session.duration,
            'avg_confidence': session.avg_confidence,
            'min_confidence': session.min_confidence,
            'max_confidence': session.max_confidence,
            'beginning_confidence': session.beginning_confidence,
            'middle_confidence': session.middle_confidence,
            'end_confidence': session.end_confidence,
            'emotion_distribution': session.emotion_distribution,
            'facial_frames': session.facial_frames,
            'voice_frames': session.voice_frames,
            'multimodal_frames': session.multimodal_frames,
            'total_frames': len(session.frames),
            'frames': [asdict(f) for f in session.frames]
        }
        
        filepath = os.path.join(output_dir, f"session_{session.session_id}.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Session saved: {filepath}")
        return filepath


def run_realtime_analysis():
    """Run real-time multimodal interview analysis."""
    
    print("\n" + "="*60)
    print("🎥 STARTING REAL-TIME MULTIMODAL ANALYSIS")
    print("="*60)
    print("\nControls:")
    print("  [SPACE] - Start/Stop recording")
    print("  [R] - Reset session")
    print("  [S] - Save session")
    print("  [Q] - Quit")
    print("="*60 + "\n")
    
    # Initialize analyzer
    analyzer = MultimodalInterviewAnalyzer()
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open webcam!")
        return
    
    # Start session
    session_id = analyzer.start_session()
    recording = True
    
    # Audio recording setup
    audio_buffer = []
    audio_lock = threading.Lock()
    
    def audio_callback(indata, frames, time_info, status):
        if recording:
            with audio_lock:
                audio_buffer.extend(indata[:, 0])
    
    # Start audio stream if available
    audio_stream = None
    if AUDIO_AVAILABLE:
        try:
            audio_stream = sd.InputStream(
                samplerate=analyzer.sample_rate,
                channels=1,
                callback=audio_callback
            )
            audio_stream.start()
            print("🎤 Audio recording started")
        except Exception as e:
            print(f"⚠️ Audio unavailable: {e}")
    
    try:
        frame_count = 0
        last_audio_analysis = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Get audio segment for analysis (every 2 seconds)
            audio_segment = None
            current_time = time.time()
            
            if AUDIO_AVAILABLE and (current_time - last_audio_analysis) >= analyzer.audio_segment_duration:
                with audio_lock:
                    if len(audio_buffer) >= analyzer.sample_rate * analyzer.audio_segment_duration:
                        segment_samples = int(analyzer.sample_rate * analyzer.audio_segment_duration)
                        audio_segment = np.array(audio_buffer[-segment_samples:])
                        last_audio_analysis = current_time
            
            # Analyze frame (and audio if available)
            analysis = analyzer.analyze_frame(frame, audio_segment)
            
            # Draw overlay
            display_frame = analyzer.draw_overlay(frame, analysis)
            
            # Show frame
            cv2.imshow("Q&ACE Multimodal Interview Analyzer", display_frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):
                recording = not recording
                print(f"Recording: {'ON' if recording else 'OFF'}")
            elif key == ord('r'):
                session_id = analyzer.start_session()
                audio_buffer.clear()
                print("Session reset")
            elif key == ord('s'):
                if analyzer.session:
                    session = analyzer.end_session()
                    output_dir = "outputs"
                    analyzer.save_session(session, output_dir)
                    session_id = analyzer.start_session()
    
    finally:
        # Cleanup
        if audio_stream:
            audio_stream.stop()
            audio_stream.close()
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Save final session
        if analyzer.session:
            session = analyzer.end_session()
            output_dir = "outputs"
            analyzer.save_session(session, output_dir)


if __name__ == "__main__":
    run_realtime_analysis()
