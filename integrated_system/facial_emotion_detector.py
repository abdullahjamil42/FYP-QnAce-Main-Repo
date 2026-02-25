"""
Facial Emotion Detector Wrapper for Q&ACE Integration.

This module wraps the Hugging Face emotion detector for unified interface.
"""

import torch
from hf_facial_emotion_detector import HuggingFaceEmotionDetector, EMOTION_LABELS

# Re-export for convenience
__all__ = ['FacialEmotionDetector', 'EMOTION_LABELS']


class FacialEmotionDetector(HuggingFaceEmotionDetector):
    """
    Facial emotion detector wrapper for unified interface.
    
    Inherits from the existing EmotionDetector but provides
    consistent interface with VoiceEmotionDetector.
    
    Accuracy: 72.72% (EfficientNet-B2)
    Emotions: angry, disgust, fear, happy, sad, surprise, neutral
    
    Note: FER2013-trained models have known "angry" bias, especially for
    resting faces. This class includes intelligent bias correction.
    """
    
    def __init__(self, **kwargs):
        """Initialize facial emotion detector."""
        super().__init__(**kwargs)
        self.emotions = EMOTION_LABELS
    
    def _correct_fer_bias(self, emotions: dict) -> dict:
        """
        Correct for known FER2013 biases, particularly the "angry" bias.
        
        FER2013 models often misclassify neutral/resting faces as angry
        because the training data had more expressive angry faces.
        
        Strategy:
        - If angry is dominant but confidence is low (<40%), redistribute to neutral
        - If angry and neutral are both high, boost neutral confidence
        - Preserve clear anger signals (>60% confidence)
        
        Args:
            emotions: Dict of emotion probabilities
            
        Returns:
            Corrected emotion probabilities
        """
        corrected = emotions.copy()
        
        angry_prob = emotions.get('angry', 0)
        neutral_prob = emotions.get('neutral', 0)
        
        # Case 1: Low confidence angry detection - likely a neutral/resting face
        if angry_prob > 0 and angry_prob < 0.40:
            # Transfer most of angry probability to neutral
            transfer = angry_prob * 0.7
            corrected['angry'] = angry_prob - transfer
            corrected['neutral'] = neutral_prob + transfer
        
        # Case 2: Ambiguous angry/neutral - boost neutral slightly
        elif angry_prob >= 0.40 and angry_prob < 0.60:
            if neutral_prob > 0.10:
                # It's ambiguous, slightly favor neutral for resting faces
                transfer = angry_prob * 0.3
                corrected['angry'] = angry_prob - transfer
                corrected['neutral'] = neutral_prob + transfer
        
        # Case 3: High confidence angry (>60%) - likely genuine, keep it
        # No correction needed
        
        # Normalize probabilities to sum to 1
        total = sum(corrected.values())
        if total > 0:
            corrected = {k: v / total for k, v in corrected.items()}
        
        return corrected
    
    def detect_emotions_from_frame(self, frame, assume_face_if_not_detected=True):
        """
        Detect emotions from a video frame.
        
        Args:
            frame: BGR image as numpy array
            assume_face_if_not_detected: If True and no face is detected,
                assume the center of the frame contains a face (common in webcam usage)
            
        Returns:
            Dict with 'emotions', 'dominant_emotion', 'confidence', 'face_detected'
        """
        results = self.detect_emotions(frame)
        
        if not results and assume_face_if_not_detected:
            # No face detected by MTCNN/Haar, but assume center region is a face
            # This is common in webcam scenarios where the user is centered
            h, w = frame.shape[:2]
            
            # Take center region (assume face is in middle 60% of frame)
            margin_x = int(w * 0.2)
            margin_y = int(h * 0.15)
            center_region = frame[margin_y:h-margin_y, margin_x:w-margin_x]
            
            # Try to analyze the center region directly
            try:
                import cv2
                from PIL import Image
                
                # Resize and preprocess
                if len(center_region.shape) == 3:
                    rgb_region = cv2.cvtColor(center_region, cv2.COLOR_BGR2RGB)
                else:
                    rgb_region = cv2.cvtColor(center_region, cv2.COLOR_GRAY2RGB)
                
                pil_img = Image.fromarray(rgb_region)
                tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    outputs = self.model(tensor)
                    probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
                
                emotions = {e: float(probs[i]) for i, e in enumerate(self.emotions)}
                # Apply FER2013 bias correction
                emotions = self._correct_fer_bias(emotions)
                dominant = max(emotions, key=emotions.get)
                
                return {
                    'emotions': emotions,
                    'dominant_emotion': dominant,
                    'confidence': emotions[dominant],
                    'face_detected': True,  # Assumed face
                    'face_box': (margin_x, margin_y, w - 2*margin_x, h - 2*margin_y)
                }
            except Exception as e:
                print(f"Center region analysis failed: {e}")
        
        if not results:
            return {
                'emotions': {e: 0.0 for e in self.emotions},
                'dominant_emotion': 'neutral',
                'confidence': 0.0,
                'face_detected': False,
                'face_box': None
            }
        
        # Get first face result
        result = results[0]
        emotions = result['emotions']
        # Apply FER2013 bias correction
        emotions = self._correct_fer_bias(emotions)
        dominant = max(emotions, key=emotions.get)
        
        return {
            'emotions': emotions,
            'dominant_emotion': dominant,
            'confidence': emotions[dominant],
            'face_detected': True,
            'face_box': result['box']
        }
