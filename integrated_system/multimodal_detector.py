"""
Multimodal Emotion Detector for Q&ACE.

This module combines facial and voice emotion detection for a comprehensive
interview analysis system.

Combined accuracy approach:
- Facial: 72.72% (EfficientNet-B2)
- Voice: 73.37% (Wav2Vec2)
- Fusion: Weighted average with confidence-based weighting
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import torch

# Emotion mappings between facial and voice models
# Facial: angry, disgust, fear, happy, sad, surprise, neutral
# Voice:  anger, fear, happy, neutral, sad, surprise

FACIAL_EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
VOICE_EMOTIONS = ["anger", "fear", "happy", "neutral", "sad", "surprise"]

# Mapping from facial to unified emotions
EMOTION_MAPPING = {
    'angry': 'anger',
    'anger': 'anger',
    'disgust': 'disgust',  # Voice doesn't have this
    'fear': 'fear',
    'happy': 'happy',
    'sad': 'sad',
    'surprise': 'surprise',
    'neutral': 'neutral'
}

# Unified emotion set
UNIFIED_EMOTIONS = ['anger', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']


@dataclass
class MultimodalResult:
    """Result from multimodal emotion detection."""
    # Combined results
    emotions: Dict[str, float]
    dominant_emotion: str
    confidence: float
    
    # Individual modality results
    facial_emotions: Optional[Dict[str, float]] = None
    facial_dominant: Optional[str] = None
    facial_confidence: float = 0.0
    face_detected: bool = False
    
    voice_emotions: Optional[Dict[str, float]] = None
    voice_dominant: Optional[str] = None
    voice_confidence: float = 0.0
    voice_detected: bool = False
    
    # Metadata
    timestamp: float = 0.0
    fusion_method: str = "weighted_average"


class MultimodalEmotionDetector:
    """
    Multimodal emotion detector combining facial and voice analysis.
    
    This class provides:
    - Real-time facial emotion detection from video frames
    - Voice emotion detection from audio segments
    - Fusion of both modalities for robust emotion estimation
    """
    
    def __init__(
        self,
        device: Optional[str] = None,
        facial_weight: float = 0.5,
        voice_weight: float = 0.5,
    ):
        """
        Initialize multimodal detector.
        
        Args:
            device: Device for inference
            facial_weight: Weight for facial emotions in fusion (0-1)
            voice_weight: Weight for voice emotions in fusion (0-1)
        """
        # Setup device
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)
        
        print(f"🎯 MultimodalEmotionDetector initializing on {self.device}")
        
        # Store weights
        self.facial_weight = facial_weight
        self.voice_weight = voice_weight
        
        # Initialize detectors
        self.facial_detector = None
        self.voice_detector = None
        
        self._init_facial_detector()
        self._init_voice_detector()
        
        print("✅ Multimodal detector ready!")
    
    def _init_facial_detector(self):
        """Initialize facial emotion detector from Hugging Face."""
        try:
            from facial_emotion_detector import FacialEmotionDetector
            self.facial_detector = FacialEmotionDetector(
                device=str(self.device)
            )
            print("  ✅ Facial detector loaded from Hugging Face (72.72% accuracy)")
        except Exception as e:
            print(f"  ⚠️ Facial detector failed: {e}")
            self.facial_detector = None
    
    def _init_voice_detector(self):
        """Initialize voice emotion detector from Hugging Face."""
        try:
            from voice_emotion_detector import VoiceEmotionDetector
            self.voice_detector = VoiceEmotionDetector(
                device=str(self.device)
            )
            print("  ✅ Voice detector loaded from Hugging Face (73.37% accuracy)")
        except Exception as e:
            print(f"  ⚠️ Voice detector failed: {e}")
            self.voice_detector = None
    
    def _normalize_facial_emotions(self, emotions: Dict[str, float]) -> Dict[str, float]:
        """Normalize facial emotions to unified format."""
        unified = {e: 0.0 for e in UNIFIED_EMOTIONS}
        
        for emotion, prob in emotions.items():
            unified_emotion = EMOTION_MAPPING.get(emotion, emotion)
            if unified_emotion in unified:
                unified[unified_emotion] = prob
        
        return unified
    
    def _normalize_voice_emotions(self, emotions: Dict[str, float]) -> Dict[str, float]:
        """Normalize voice emotions to unified format."""
        unified = {e: 0.0 for e in UNIFIED_EMOTIONS}
        
        for emotion, prob in emotions.items():
            unified_emotion = EMOTION_MAPPING.get(emotion, emotion)
            if unified_emotion in unified:
                unified[unified_emotion] = prob
        
        return unified
    
    def detect_facial_emotion(self, frame) -> Optional[Dict]:
        """
        Detect emotion from video frame.
        
        Args:
            frame: BGR image as numpy array
            
        Returns:
            Dict with emotions or None if detection failed
        """
        if self.facial_detector is None:
            return None
        
        try:
            results = self.facial_detector.detect_emotions(frame)
            
            if not results:
                return {
                    'emotions': {e: 0.0 for e in FACIAL_EMOTIONS},
                    'dominant_emotion': 'neutral',
                    'confidence': 0.0,
                    'face_detected': False
                }
            
            result = results[0]
            emotions = result['emotions']
            dominant = max(emotions, key=emotions.get)
            
            return {
                'emotions': emotions,
                'dominant_emotion': dominant,
                'confidence': emotions[dominant],
                'face_detected': True,
                'face_box': result['box']
            }
        except Exception as e:
            print(f"Facial detection error: {e}")
            return None
    
    def detect_voice_emotion(self, audio, sample_rate: int = 16000) -> Optional[Dict]:
        """
        Detect emotion from audio.
        
        Args:
            audio: Audio waveform as numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            Dict with emotions or None if detection failed
        """
        if self.voice_detector is None:
            return None
        
        try:
            result = self.voice_detector.detect_emotions(audio, sample_rate)
            result['voice_detected'] = True
            return result
        except Exception as e:
            print(f"Voice detection error: {e}")
            return None
    
    def fuse_emotions(
        self,
        facial_result: Optional[Dict],
        voice_result: Optional[Dict],
        method: str = "weighted_average"
    ) -> Dict[str, float]:
        """
        Fuse facial and voice emotions.
        
        Args:
            facial_result: Result from facial detection
            voice_result: Result from voice detection
            method: Fusion method ('weighted_average', 'max', 'confidence_weighted')
            
        Returns:
            Fused emotion probabilities
        """
        fused = {e: 0.0 for e in UNIFIED_EMOTIONS}
        
        has_facial = facial_result is not None and facial_result.get('face_detected', False)
        has_voice = voice_result is not None and voice_result.get('voice_detected', False)
        
        if not has_facial and not has_voice:
            fused['neutral'] = 1.0
            return fused
        
        # Normalize emotions
        facial_unified = self._normalize_facial_emotions(
            facial_result['emotions']
        ) if has_facial else {e: 0.0 for e in UNIFIED_EMOTIONS}
        
        voice_unified = self._normalize_voice_emotions(
            voice_result['emotions']
        ) if has_voice else {e: 0.0 for e in UNIFIED_EMOTIONS}
        
        if method == "weighted_average":
            # Simple weighted average
            if has_facial and has_voice:
                for e in UNIFIED_EMOTIONS:
                    fused[e] = (
                        self.facial_weight * facial_unified[e] +
                        self.voice_weight * voice_unified[e]
                    )
            elif has_facial:
                fused = facial_unified
            else:
                fused = voice_unified
        
        elif method == "confidence_weighted":
            # Weight by detection confidence
            facial_conf = facial_result.get('confidence', 0.0) if has_facial else 0.0
            voice_conf = voice_result.get('confidence', 0.0) if has_voice else 0.0
            
            total_conf = facial_conf + voice_conf
            if total_conf > 0:
                f_weight = facial_conf / total_conf
                v_weight = voice_conf / total_conf
                
                for e in UNIFIED_EMOTIONS:
                    fused[e] = f_weight * facial_unified[e] + v_weight * voice_unified[e]
            else:
                fused['neutral'] = 1.0
        
        elif method == "max":
            # Take max probability across modalities
            for e in UNIFIED_EMOTIONS:
                fused[e] = max(facial_unified[e], voice_unified[e])
        
        # Normalize to sum to 1
        total = sum(fused.values())
        if total > 0:
            fused = {e: p / total for e, p in fused.items()}
        
        return fused
    
    def detect(
        self,
        frame=None,
        audio=None,
        sample_rate: int = 16000,
        fusion_method: str = "weighted_average"
    ) -> MultimodalResult:
        """
        Detect emotions from video frame and/or audio.
        
        Args:
            frame: BGR image as numpy array (optional)
            audio: Audio waveform as numpy array (optional)
            sample_rate: Sample rate of audio
            fusion_method: Method for fusing modalities
            
        Returns:
            MultimodalResult with all detection results
        """
        import time
        timestamp = time.time()
        
        # Detect from each modality
        facial_result = self.detect_facial_emotion(frame) if frame is not None else None
        voice_result = self.detect_voice_emotion(audio, sample_rate) if audio is not None else None
        
        # Fuse results
        fused = self.fuse_emotions(facial_result, voice_result, fusion_method)
        dominant = max(fused, key=fused.get)
        confidence = fused[dominant]
        
        return MultimodalResult(
            emotions=fused,
            dominant_emotion=dominant,
            confidence=confidence,
            facial_emotions=facial_result['emotions'] if facial_result else None,
            facial_dominant=facial_result.get('dominant_emotion') if facial_result else None,
            facial_confidence=facial_result.get('confidence', 0.0) if facial_result else 0.0,
            face_detected=facial_result.get('face_detected', False) if facial_result else False,
            voice_emotions=voice_result.get('emotions') if voice_result else None,
            voice_dominant=voice_result.get('dominant_emotion') if voice_result else None,
            voice_confidence=voice_result.get('confidence', 0.0) if voice_result else 0.0,
            voice_detected=voice_result.get('voice_detected', False) if voice_result else False,
            timestamp=timestamp,
            fusion_method=fusion_method
        )
    
    def calculate_interview_confidence(self, result: MultimodalResult) -> Tuple[float, str]:
        """
        Calculate interview confidence score from multimodal result.
        
        Uses weighted combination of emotions:
        - Positive: happy, neutral, surprise
        - Negative: anger, fear, sad, disgust
        
        Args:
            result: MultimodalResult from detection
            
        Returns:
            Tuple of (confidence_score 0-100, confidence_level string)
        """
        weights = {
            'happy': 0.85,
            'neutral': 0.75,
            'surprise': 0.50,
            'sad': -0.60,
            'fear': -0.70,
            'anger': -0.50,
            'disgust': -0.40
        }
        
        # Calculate weighted score
        raw_score = 0.5  # Base score
        for emotion, prob in result.emotions.items():
            if emotion in weights:
                raw_score += weights[emotion] * prob * 0.5
        
        # Clamp to 0-1
        score = max(0.0, min(1.0, raw_score))
        
        # Determine level
        if score >= 0.80:
            level = "Excellent"
        elif score >= 0.65:
            level = "Confident"
        elif score >= 0.50:
            level = "Moderate"
        elif score >= 0.35:
            level = "Nervous"
        elif score >= 0.20:
            level = "Anxious"
        else:
            level = "Very Anxious"
        
        return score * 100, level


# Convenience function
def create_multimodal_detector(**kwargs) -> MultimodalEmotionDetector:
    """Create and return a multimodal emotion detector."""
    return MultimodalEmotionDetector(**kwargs)
