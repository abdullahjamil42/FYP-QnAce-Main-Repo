"""
Q&ACE Integrated Multimodal Emotion Detection System.

This package combines facial and voice emotion detection for
comprehensive interview analysis.
"""

# Version
__version__ = "1.0.0"

# Expose main classes
try:
    from .multimodal_detector import MultimodalEmotionDetector, MultimodalResult
    from .voice_emotion_detector import VoiceEmotionDetector
    from .interview_analyzer import MultimodalInterviewAnalyzer
    from .report_generator import generate_reports, generate_multimodal_report
except ImportError:
    # Allow importing individual modules
    pass

__all__ = [
    'MultimodalEmotionDetector',
    'MultimodalResult',
    'VoiceEmotionDetector',
    'MultimodalInterviewAnalyzer',
    'generate_reports',
    'generate_multimodal_report',
]
