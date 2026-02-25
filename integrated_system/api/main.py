"""
Q&ACE Unified API - Combines Facial, Voice, Text (BERT), and Speech-to-Text Analysis

This is the single API endpoint that the Frontend connects to.
It orchestrates all ML models for comprehensive interview analysis.

Endpoints:
- POST /analyze/facial     - Analyze facial emotions from image
- POST /analyze/voice      - Analyze voice emotions from audio
- POST /analyze/text       - Analyze answer quality with BERT
- POST /analyze/speech     - Transcribe speech to text (Whisper) + BERT analysis
- POST /analyze/multimodal - Analyze all modalities together
- GET  /health             - Health check
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import base64
import io
import tempfile
from dotenv import load_dotenv

# Root directory for the project (contains .env, BERT_Model, etc.)
ROOT_DIR = Path(__file__).parent.parent.parent

# Ensure integrated_system is in path
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Load environment variables from .env file
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Loaded environment variables from {env_path}")
else:
    # Fallback to current directory for Docker/Railway
    load_dotenv()
    print("ℹ️ No .env file found at root, using default load_dotenv()")

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import math

# Coaching Pipeline Imports - handle different execution contexts
try:
    # When running from project root (local dev)
    from integrated_system.coaching_engine import (
        get_coaching_engine, 
        initialize_coaching_engine,
        CoachingResult
    )
except ImportError:
    # When running from inside integrated_system (Docker)
    try:
        from coaching_engine import (
            get_coaching_engine, 
            initialize_coaching_engine,
            CoachingResult
        )
    except ImportError:
        # Fallback: disable coaching
        print("⚠️ Coaching engine not available - coaching features disabled")
        get_coaching_engine = None
        initialize_coaching_engine = None
        CoachingResult = None

# ============================================
# FastAPI App Setup
# ============================================

def sanitize_floats(obj):
    """Recursively convert NaN/Inf to 0.0 in dicts, lists, and values."""
    if isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_floats(i) for i in obj]
    
    # Try direct numeric check
    if isinstance(obj, (float, int)):
        if not math.isfinite(obj):
            print(f"⚠️ [SANITIZE] Found non-finite float: {obj} -> 0.0", flush=True)
            return 0.0
        return obj
    
    # Handle numpy/torch types
    try:
        if hasattr(obj, 'item') and callable(obj.item):
            fval = float(obj.item())
        else:
            # Maybe it's a string like "NaN"
            fval = float(obj)
            
        if not math.isfinite(fval):
            print(f"⚠️ [SANITIZE] Found non-finite numeric: {obj} -> 0.0", flush=True)
            return 0.0
        return fval
    except (TypeError, ValueError, AttributeError):
        return obj

app = FastAPI(
    title="Q&ACE Unified API",
    description="Multimodal Interview Analysis API - Facial, Voice, and Text",
    version="1.0.0",
)

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# App Events
# ============================================

@app.on_event("startup")
async def startup_event():
    """Quick startup - load models on demand."""
    print("\n🚀 Server started! HF models will load on first request.")
    
    try:
        # Only load local BERT (fast)
        print("Loading local BERT model...")
        get_bert_model()
        print("✅ BERT ready. HF models load on demand.")
    except Exception as e:
        print(f"⚠️ BERT error: {e}")
    
    # Initialize coaching engine (loads Sentence-BERT and reference embeddings)
    try:
        print("🔄 Initializing Coaching Engine...")
        # Path to the Interview Dataset for reference answers
        dataset_path = str(ROOT_DIR / ".." / "Interview_Dataset.csv")
        import os
        if not os.path.exists(dataset_path):
            # Try alternative paths
            alt_paths = [
                str(ROOT_DIR / "Interview_Dataset.csv"),
                "c:/22i-2451/Q&Ace/Interview_Dataset.csv"
            ]
            for alt in alt_paths:
                if os.path.exists(alt):
                    dataset_path = alt
                    break
        
        if os.path.exists(dataset_path):
            if initialize_coaching_engine:
                initialize_coaching_engine(dataset_path=dataset_path)
                print("✅ Coaching Engine ready.")
            else:
                print("⚠️ Coaching Engine initialization function not available.")
        else:
            print(f"⚠️ Dataset not found, coaching will have limited reference comparison")
            if initialize_coaching_engine:
                initialize_coaching_engine()
            else:
                print("⚠️ Coaching Engine initialization function not available.")
    except Exception as e:
        print(f"⚠️ Coaching Engine initialization error: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("🔄 Shutting down gracefully...")

# ============================================
# Global Model Instances
# ============================================

# Device setup
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
elif torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
else:
    DEVICE = torch.device("cpu")

# Model instances (lazy loaded)
facial_detector = None
voice_detector = None
bert_model = None
bert_tokenizer = None
speech_to_text = None


def get_facial_detector():
    """Lazy load facial detector."""
    global facial_detector
    if facial_detector is None:
        try:
            from facial_emotion_detector import FacialEmotionDetector
            facial_detector = FacialEmotionDetector(device=str(DEVICE))
            print("✅ Facial detector loaded")
        except Exception as e:
            print(f"❌ Facial detector failed: {e}")
    return facial_detector


def get_voice_detector():
    """Lazy load voice detector."""
    global voice_detector
    if voice_detector is None:
        try:
            from voice_emotion_detector import VoiceEmotionDetector
            model_path = ROOT_DIR / "QnAce_Voice-Model" / "QnAce_Voice-Model.pth"
            voice_detector = VoiceEmotionDetector(
                model_path=str(model_path),
                device=str(DEVICE)
            )
            print("✅ Voice detector loaded")
        except Exception as e:
            print(f"❌ Voice detector failed: {e}")
    return voice_detector


def get_bert_model():
    """Lazy load BERT model."""
    global bert_model, bert_tokenizer
    if bert_model is None:
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            model_dir = ROOT_DIR / "BERT_Model"
            
            bert_model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
            bert_model.to(DEVICE)
            bert_model.eval()
            
            # Try local tokenizer, fallback to base
            try:
                bert_tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
            except:
                bert_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
            
            print("✅ BERT model loaded")
        except Exception as e:
            print(f"❌ BERT model failed: {e}")
    return bert_model, bert_tokenizer


def get_speech_to_text():
    """Lazy load Whisper speech-to-text model."""
    global speech_to_text
    if speech_to_text is None:
        try:
            from speech_to_text import SpeechToText
            speech_to_text = SpeechToText(model_size="base", device="cpu")
            print("✅ Whisper speech-to-text loaded")
        except Exception as e:
            print(f"❌ Whisper failed: {e}")
    return speech_to_text


# ============================================
# Request/Response Models
# ============================================

class TextAnalysisRequest(BaseModel):
    text: str
    question: Optional[str] = None


class FacialAnalysisResponse(BaseModel):
    success: bool
    emotions: Dict[str, float]
    dominant_emotion: str
    confidence: float
    face_detected: bool
    error: Optional[str] = None


class VoiceAnalysisResponse(BaseModel):
    success: bool
    emotions: Dict[str, float]
    dominant_emotion: str
    confidence: float
    error: Optional[str] = None


class TextAnalysisResponse(BaseModel):
    success: bool
    quality_score: float  # 0-100
    quality_label: str    # "Poor", "Average", "Excellent"
    probabilities: Dict[str, float]
    feedback: str
    # NEW: Short explanation for why the model chose this classification
    reason: Optional[str] = None  # e.g., "Lacks specific examples"
    error: Optional[str] = None


class SpeechToTextResponse(BaseModel):
    success: bool
    transcription: str
    language: Optional[str] = None
    segments: Optional[List[Dict]] = None
    # BERT analysis of the transcribed text
    text_analysis: Optional[TextAnalysisResponse] = None
    # NEW: Count of filler words detected (um, uh, like, you know, etc.)
    filler_word_count: int = 0
    filler_words: Optional[List[str]] = None  # List of detected filler words
    # NEW: Speech rate classification
    speech_rate: Optional[str] = None  # "slow", "normal", "fast"
    error: Optional[str] = None


# ============================================
# Coaching Response Models (NEW)
# ============================================

class CoachingTip(BaseModel):
    """A single coaching tip with context."""
    what_went_well: str
    what_to_improve: str
    reason: str  # Explainability - why this recommendation


class CoachingDiagnosis(BaseModel):
    """Diagnosis for a single modality."""
    issue: str
    description: str
    reason: str
    severity: str  # 'low', 'medium', 'high'


class CoachingResponse(BaseModel):
    """Complete coaching analysis response."""
    success: bool
    
    # Sentence-BERT Similarity Scores
    sbert_similarities: Dict[str, float]  # poor, average, excellent
    closest_tier: str  # Which reference the answer is most similar to
    excellent_gap: float  # Gap between user answer and excellent
    
    # Combined Text Score (BERT + SBERT)
    combined_text_score: float  # 0-100
    bert_component: float
    sbert_component: float
    
    # Diagnoses (deterministic)
    content_diagnosis: CoachingDiagnosis
    voice_diagnosis: CoachingDiagnosis
    facial_diagnosis: CoachingDiagnosis
    
    # Recommendations (template-based)
    content_tip: CoachingTip
    voice_tip: CoachingTip
    facial_tip: CoachingTip
    
    # Human-readable interpretation
    quality_interpretation: str  # Single verdict label
    quality_description: str  # User-friendly explanation
    progress_position: float  # 0-100 position on Poor→Excellent scale
    improvement_tips: Optional[List[str]] = None  # GenAI-powered or fallback tips
    
    # Optional GenAI-rephrased feedback
    generated_feedback: Optional[str] = None
    
    # NEW: BERTScore (Semantic Accuracy)
    bert_score_f1: float = 0.0  # 0-1 scale, display as percentage
    bert_score_precision: float = 0.0
    bert_score_recall: float = 0.0
    
    # NEW: LLM Judge
    llm_judge_score: int = 5  # 1-10 scale
    llm_judge_rationale: str = ""  # Explanation for the score
    llm_actionable_tips: Optional[List[str]] = None  # Specific improvement tips
    
    # NEW: STAR Structure Breakdown
    star_breakdown: Optional[Dict[str, float]] = None  # {situation, task, action, result}
    content_relevance: int = 3  # 1-5 rubric
    coherence_score: int = 3  # 1-5 rubric
    
    timestamp: str
    error: Optional[str] = None


class MultimodalAnalysisResponse(BaseModel):
    success: bool
    
    # Overall scores
    overall_confidence: float
    overall_emotion: str
    
    # Individual results
    facial: Optional[FacialAnalysisResponse] = None
    voice: Optional[VoiceAnalysisResponse] = None
    text: Optional[TextAnalysisResponse] = None
    
    # Fused emotions
    fused_emotions: Dict[str, float]
    
    # Interview metrics
    confidence_score: float  # 0-100
    clarity_score: float     # 0-100
    engagement_score: float  # 0-100
    
    # Recommendations (legacy string list)
    recommendations: List[str]
    
    # NEW: Structured coaching data
    coaching: Optional[CoachingResponse] = None
    
    timestamp: str
    error: Optional[str] = None


# ============================================
# Utility Functions
# ============================================

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode base64 image to numpy array."""
    import cv2
    
    # Remove data URL prefix if present
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    
    img_bytes = base64.b64decode(base64_string)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img


# ============================================
# Filler Word Detection & Speech Rate Classification
# ============================================

# Common filler words to detect
FILLER_WORDS = [
    "um", "uh", "like", "you know", "so", "basically", "actually", 
    "literally", "honestly", "i mean", "kind of", "sort of", 
    "i guess", "right", "well"
]

def detect_filler_words(text: str) -> tuple[int, list]:
    """
    Detect filler words in transcribed text.
    
    Returns:
        tuple: (count, list of detected filler words with positions)
    """
    text_lower = text.lower()
    detected = []
    count = 0
    
    for filler in FILLER_WORDS:
        occurrences = text_lower.count(filler)
        if occurrences > 0:
            count += occurrences
            detected.extend([filler] * occurrences)
    
    return count, detected


def classify_speech_rate(duration_seconds: float, word_count: int) -> str:
    """
    Classify speech rate based on words per minute.
    
    Normal speaking rate: 125-150 WPM
    - < 100 WPM = slow
    - 100-180 WPM = normal
    - > 180 WPM = fast
    """
    if duration_seconds <= 0 or word_count <= 0:
        return "unknown"
    
    wpm = (word_count / duration_seconds) * 60
    
    if wpm < 100:
        return "slow"
    elif wpm > 180:
        return "fast"
    else:
        return "normal"


def generate_bert_reason(quality_label: str, text: str) -> str:
    """
    Generate a short explanation for why BERT classified the answer.
    Analyzes text characteristics to provide meaningful reason.
    """
    word_count = len(text.split())
    
    # Simple heuristics for reason generation
    if quality_label == "Poor":
        if word_count < 20:
            return "Answer is too brief - needs more detail"
        else:
            return "Lacks specific examples and structured response"
    elif quality_label == "Average":
        if word_count < 50:
            return "Good start, but could use more depth"
        else:
            return "Decent structure, needs more specific examples"
    else:  # Excellent
        return "Well-structured with specific, relevant details"


def calculate_facial_score(facial_result: dict) -> float:
    """
    Calculate facial analysis score (0-100) optimized for interview performance.
    
    Professional interview expressions:
    - Neutral (professional, attentive) = Excellent (90-100)
    - Happy (confident, positive) = Excellent (90-100)  
    - Surprise (engaged, interested) = Good (75-85)
    - Sad/Fear (nervous) = Needs work (40-60)
    - Angry/Disgust (negative) = Poor (30-50)
    
    IMPORTANT: Includes "resting face correction" - many people with neutral/professional
    expressions are misclassified as "angry" by FER2013-trained models due to dataset bias.
    If angry is high but neutral+happy+surprise are also significant, it's likely a resting face.
    """
    if not facial_result or not facial_result.get('face_detected'):
        return 50.0  # Default if no face
    
    emotions = facial_result.get('emotions', {})
    confidence = facial_result.get('confidence', 0.5)
    
    # Get probabilities
    angry_prob = emotions.get('angry', 0)
    neutral_prob = emotions.get('neutral', 0)
    happy_prob = emotions.get('happy', 0)
    surprise_prob = emotions.get('surprise', 0)
    sad_prob = emotions.get('sad', 0)
    fear_prob = emotions.get('fear', 0)
    disgust_prob = emotions.get('disgust', 0)
    
    # ========== RESTING FACE CORRECTION ==========
    # FER2013 models often misclassify neutral/professional faces as "angry"
    
    positive_sum = neutral_prob + happy_prob + surprise_prob
    corrected_emotions = emotions.copy()
    
    if angry_prob > 0.35 and angry_prob < 0.70 and positive_sum > 0.15:
        # This is likely a resting face being misclassified
        correction_factor = min(0.6, positive_sum)
        angry_transfer = angry_prob * correction_factor
        
        corrected_emotions['neutral'] = neutral_prob + angry_transfer * 0.8
        corrected_emotions['happy'] = happy_prob + angry_transfer * 0.2
        corrected_emotions['angry'] = angry_prob * (1 - correction_factor)
        
        print(f"🔄 Resting face correction: angry {angry_prob:.1%} -> {corrected_emotions['angry']:.1%}")
    
    emotions = corrected_emotions
    
    # ========== REALISTIC EMOTION SCORING v2.0 ==========
    # Interview-appropriate scores - NOT inflated
    # Scale: 25-95 (never give 100% or below 20%)
    emotion_scores = {
        'happy': 85,      # Positive, confident - good
        'neutral': 70,    # Professional but not engaging - average
        'surprise': 55,   # Can seem unprepared - below average
        'sad': 35,        # Nervous, uncomfortable - poor
        'fear': 30,       # Very nervous - poor
        'angry': 40,      # Defensive/hostile - poor
        'disgust': 30,    # Very negative - poor
    }
    
    # Calculate weighted score
    weighted_score = 0
    total_weight = 0
    
    for emotion, prob in emotions.items():
        if emotion in emotion_scores and prob > 0.01:
            weighted_score += emotion_scores[emotion] * prob
            total_weight += prob
    
    base_score = weighted_score / total_weight if total_weight > 0 else 50
    
    # ========== PENALTIES AND BONUSES ==========
    
    # PENALTY: Low confidence = uncertain detection
    if confidence < 0.4:
        base_score -= 10
    elif confidence < 0.6:
        base_score -= 5
    
    # BONUS: High happy + neutral mix = ideal interview demeanor
    ideal_mix = happy_prob * 0.5 + neutral_prob * 0.5
    if ideal_mix > 0.5 and confidence > 0.5:
        base_score += 8
    
    if not math.isfinite(base_score):
        base_score = 50.0
        
    # Cap the score between 20 and 95
    final_score = max(20, min(95, base_score))
    
    return round(final_score, 1)


def calculate_confidence_score(facial_result: dict, voice_result: dict, text_result: dict) -> float:
    """
    Calculate overall interview confidence score (0-100).
    
    SCORING WEIGHTS v3.0 (January 2026):
    =====================================
    - Text (BERT):  35% - Answer content is most important for interview success
    - Voice:        35% - Vocal delivery conveys confidence and authenticity
    - Facial:       30% - Non-verbal cues complement overall impression
    
    Rationale: The NLP model assesses relevance and structure (not correctness),
    balanced by vocal and facial analysis. All three modalities contribute
    meaningfully to the overall interview performance assessment.
    
    Score Ranges:
    - Eyes closed + still face = LOW score (25-40%)
    - Nervous/fearful = LOW score (30-45%)
    - Neutral/professional = MEDIUM score (60-75%)
    - Happy/confident = HIGH score (75-90%)
    """
    scores = []
    weights = []
    
    # =====================================
    # FACIAL ANALYSIS (30% weight)
    # Non-verbal cues: eye contact, expressions, composure
    # =====================================
    if facial_result and facial_result.get('face_detected'):
        facial_score = calculate_facial_score(facial_result)
        scores.append(facial_score)
        weights.append(0.30)
    else:
        # No face detected = penalty but not severe
        scores.append(35)
        weights.append(0.30)
    
    # =====================================
    # VOICE ANALYSIS (35% weight)
    # Vocal delivery: tone, confidence, energy
    # =====================================
    if voice_result and voice_result.get('emotions'):
        voice_emotions = voice_result.get('emotions', {})
        
        # Voice emotion scoring - similar logic to facial
        emotion_scores = {
            'neutral': 75,   # Professional tone
            'happy': 88,     # Confident, enthusiastic
            'surprise': 60,  # Can indicate uncertainty
            'sad': 40,       # Low energy, nervous
            'fear': 35,      # Clearly nervous
            'angry': 45,     # Too aggressive
            'disgust': 35,   # Negative
        }
        
        weighted_score = 0
        total_weight = 0
        for emotion, prob in voice_emotions.items():
            if emotion in emotion_scores and prob > 0.01:
                weighted_score += emotion_scores[emotion] * prob
                total_weight += prob
        
        voice_score = weighted_score / total_weight if total_weight > 0 else 60
        
        # Confidence adjustment
        voice_confidence = voice_result.get('confidence', 0.5)
        if voice_confidence < 0.4:
            voice_score -= 10
        elif voice_confidence > 0.7:
            voice_score += 5
        
        if not math.isfinite(voice_score):
            voice_score = 60.0
            
        voice_score = min(95, max(25, voice_score))
        scores.append(voice_score)
        weights.append(0.35)
    else:
        # No voice analysis available
        scores.append(60)  # Neutral default
        weights.append(0.35)
    
    # =====================================
    # TEXT ANALYSIS (35% weight)
    # Answer quality: structure, relevance, depth
    # Using fine-tuned BERT model for semantic scoring
    # =====================================
    if text_result:
        # Use BERT score directly - model is trained for structure/relevance
        text_score = text_result.get('quality_score', 50)
        # Clamp to reasonable bounds
        text_score = min(95, max(20, text_score))
        scores.append(text_score)
        weights.append(0.35)
    else:
        # No text analysis - use neutral
        scores.append(55)
        weights.append(0.35)
    
    if not scores:
        return 50.0
    
    # Calculate weighted average
    total_weight = sum(weights)
    weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
    
    return round(min(100, max(0, weighted_score)), 1)


def generate_recommendations(facial_result: dict, voice_result: dict, text_result: dict) -> List[str]:
    """Generate personalized recommendations based on analysis."""
    recommendations = []
    
    # Facial recommendations
    if facial_result and facial_result.get('face_detected'):
        dominant = facial_result.get('dominant_emotion', '')
        if dominant in ['fear', 'sad']:
            recommendations.append("💡 Try to relax your facial expressions. Practice in front of a mirror to appear more confident.")
        elif dominant == 'angry':
            recommendations.append("💡 Soften your expressions. Take a deep breath before answering to appear more approachable.")
        elif dominant == 'neutral':
            recommendations.append("💡 Great neutral expression! Try adding a slight smile to appear more engaging.")
        elif dominant == 'happy':
            recommendations.append("✅ Excellent! Your positive expression conveys confidence and enthusiasm.")
    
    # Voice recommendations
    if voice_result and voice_result.get('emotions'):
        dominant = voice_result.get('dominant_emotion', '')
        if dominant in ['fear', 'sad']:
            recommendations.append("💡 Your voice indicates nervousness. Try speaking slightly slower and with more conviction.")
        elif dominant == 'anger':
            recommendations.append("💡 Your tone sounds intense. Try moderating your voice to sound more calm and professional.")
        elif dominant in ['happy', 'neutral']:
            recommendations.append("✅ Good vocal tone! You sound confident and professional.")
    
    # Text recommendations
    if text_result:
        quality = text_result.get('quality_label', '')
        if quality == 'Poor':
            recommendations.append("💡 Your answer could be more detailed. Use the STAR method (Situation, Task, Action, Result) for behavioral questions.")
        elif quality == 'Average':
            recommendations.append("💡 Good answer! Try adding more specific examples and quantifiable results to make it excellent.")
        elif quality == 'Excellent':
            recommendations.append("✅ Excellent answer! Well-structured with good detail and relevance.")
    
    if not recommendations:
        recommendations.append("💡 Keep practicing! Regular mock interviews will help you improve.")
    
    return recommendations


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Q&ACE Unified API",
        "version": "1.0.0",
        "endpoints": [
            "/analyze/facial",
            "/analyze/voice", 
            "/analyze/text",
            "/analyze/multimodal",
            "/health"
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "device": str(DEVICE),
        "models": {
            "facial": facial_detector is not None,
            "voice": voice_detector is not None,
            "bert": bert_model is not None,
            "whisper": speech_to_text is not None
        }
    }


@app.post("/analyze/facial", response_model=FacialAnalysisResponse)
async def analyze_facial(image: str = Form(...)):
    """
    Analyze facial emotions from base64 image.
    
    Args:
        image: Base64 encoded image string
    """
    try:
        detector = get_facial_detector()
        if detector is None:
            return FacialAnalysisResponse(
                success=False,
                emotions={},
                dominant_emotion="",
                confidence=0.0,
                face_detected=False,
                error="Facial detector not available"
            )
        
        # Decode image
        img = decode_base64_image(image)
        if img is None:
            return FacialAnalysisResponse(
                success=False,
                emotions={},
                dominant_emotion="",
                confidence=0.0,
                face_detected=False,
                error="Failed to decode image"
            )
        
        # Detect emotions (with fallback to center region if no face detected)
        result = detector.detect_emotions_from_frame(img, assume_face_if_not_detected=True)
        
        res_data = {
            "success": True,
            "emotions": result['emotions'],
            "dominant_emotion": result['dominant_emotion'],
            "confidence": result['confidence'],
            "face_detected": result['face_detected']
        }
        return FacialAnalysisResponse(**sanitize_floats(res_data))
        
    except Exception as e:
        return FacialAnalysisResponse(
            success=False,
            emotions={},
            dominant_emotion="",
            confidence=0.0,
            face_detected=False,
            error=str(e)
        )


@app.post("/analyze/voice", response_model=VoiceAnalysisResponse)
async def analyze_voice(audio: UploadFile = File(...)):
    """
    Analyze voice emotions from audio file.
    
    Args:
        audio: Audio file (WAV, MP3, WebM, etc.)
    """
    try:
        print(f"🎤 Voice analysis started. File: {audio.filename}, Content-Type: {audio.content_type}", flush=True)
        
        detector = get_voice_detector()
        if detector is None:
            print("❌ Voice detector not available!", flush=True)
            return VoiceAnalysisResponse(
                success=False,
                emotions={},
                dominant_emotion="",
                confidence=0.0,
                error="Voice detector not available"
            )
        
        # Read audio content
        content = await audio.read()
        print(f"📦 Read {len(content)} bytes of audio", flush=True)
        
        if len(content) < 1000:
            print("❌ Audio too short!", flush=True)
            return VoiceAnalysisResponse(
                success=False,
                emotions={},
                dominant_emotion="",
                confidence=0.0,
                error="Audio file too short"
            )
        
        # Determine file extension from content type
        ext = ".webm"
        if audio.content_type:
            if "wav" in audio.content_type:
                ext = ".wav"
            elif "mp3" in audio.content_type:
                ext = ".mp3"
            elif "ogg" in audio.content_type:
                ext = ".ogg"
        
        # Save original file
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            input_path = tmp.name
        
        try:
            import librosa
            import subprocess
            
            # If not wav, convert using ffmpeg
            if ext != ".wav":
                output_path = input_path.replace(ext, ".wav")
                print(f"🔄 Converting {ext} to WAV using ffmpeg...", flush=True)
                try:
                    result = subprocess.run(
                        ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_path],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode != 0:
                        print(f"⚠️ FFmpeg warning: {result.stderr[:200]}", flush=True)
                    audio_path = output_path
                except Exception as conv_err:
                    print(f"⚠️ FFmpeg conversion failed: {conv_err}, trying librosa directly", flush=True)
                    audio_path = input_path
            else:
                audio_path = input_path
            
            # Load with librosa
            print(f"📂 Loading audio from: {audio_path}", flush=True)
            audio_data, sr = librosa.load(audio_path, sr=16000)
            print(f"✅ Audio loaded: {len(audio_data)} samples, {sr}Hz, duration: {len(audio_data)/sr:.2f}s", flush=True)
            
            # Check if audio has actual content (not just silence)
            if len(audio_data) < 1600:  # Less than 0.1 seconds
                print("❌ Audio too short after loading", flush=True)
                return VoiceAnalysisResponse(
                    success=False,
                    emotions={},
                    dominant_emotion="",
                    confidence=0.0,
                    error="Audio too short"
                )
            
            # Detect emotions
            result = detector.detect_emotions(audio_data, sample_rate=sr)
            print(f"🎯 Voice emotions detected: {result['dominant_emotion']} ({result['confidence']*100:.1f}%)", flush=True)
            
            res_data = {
                "success": True,
                "emotions": result['emotions'],
                "dominant_emotion": result['dominant_emotion'],
                "confidence": result['confidence']
            }
            return VoiceAnalysisResponse(**sanitize_floats(res_data))
            
        finally:
            # Cleanup temp files
            try:
                os.unlink(input_path)
                if ext != ".wav":
                    output_file = input_path.replace(ext, ".wav")
                    if os.path.exists(output_file):
                        os.unlink(output_file)
            except:
                pass
        
    except Exception as e:
        print(f"❌ Voice analysis error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return VoiceAnalysisResponse(
            success=False,
            emotions={},
            dominant_emotion="",
            confidence=0.0,
            error=str(e)
        )


@app.post("/analyze/text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """
    Analyze answer quality using BERT model.
    
    Args:
        request: Text analysis request with answer text
    """
    try:
        model, tokenizer = get_bert_model()
        if model is None or tokenizer is None:
            return TextAnalysisResponse(
                success=False,
                quality_score=0.0,
                quality_label="",
                probabilities={},
                feedback="",
                error="BERT model not available"
            )
        
        text = request.text.strip()
        if not text:
            return TextAnalysisResponse(
                success=False,
                quality_score=0.0,
                quality_label="",
                probabilities={},
                feedback="",
                error="Empty text provided"
            )
        
        # Tokenize
        enc = tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        enc = {k: v.to(DEVICE) for k, v in enc.items()}
        
        # Inference
        with torch.no_grad():
            outputs = model(**enc)
            logits = outputs.logits.detach().cpu().numpy()[0]
            probs = np.exp(logits) / np.sum(np.exp(logits))
        
        # Map labels
        labels = {0: "Poor", 1: "Average", 2: "Excellent"}
        predicted_idx = int(np.argmax(probs))
        quality_label = labels[predicted_idx]
        
        # Calculate quality score (0-100)
        # Weight: Poor=0-33, Average=34-66, Excellent=67-100
        quality_score = (probs[0] * 16.5 + probs[1] * 50 + probs[2] * 83.5)
        
        # Generate feedback
        if quality_label == "Poor":
            feedback = "Your answer lacks depth and specificity. Try to include concrete examples and structure your response using the STAR method."
        elif quality_label == "Average":
            feedback = "Good foundation! To improve, add more specific details, quantifiable achievements, and connect your answer directly to the role requirements."
        else:
            feedback = "Excellent response! Well-structured with relevant details and clear communication. Keep up this level of preparation."
        
        # Generate reason for classification
        reason = generate_bert_reason(quality_label, text)
        
        res_data = {
            "success": True,
            "quality_score": float(quality_score),
            "quality_label": quality_label,
            "probabilities": {labels[i]: float(probs[i]) for i in range(3)},
            "feedback": feedback,
            "reason": reason
        }
        return TextAnalysisResponse(**sanitize_floats(res_data))
        
    except Exception as e:
        return TextAnalysisResponse(
            success=False,
            quality_score=0.0,
            quality_label="",
            probabilities={},
            feedback="",
            error=str(e)
        )


@app.post("/analyze/speech", response_model=SpeechToTextResponse)
async def analyze_speech(
    audio: UploadFile = File(...),
    question: Optional[str] = Form(None),
    analyze_text: bool = Form(True)
):
    """
    Transcribe speech to text using Whisper and optionally analyze with BERT.
    
    This endpoint:
    1. Receives an audio file with the user's spoken answer
    2. Transcribes it to text using Whisper (local, no API key needed)
    3. Optionally sends the transcription to BERT for quality analysis
    
    Args:
        audio: Audio file (WAV, MP3, WEBM, etc.)
        question: Optional interview question for context
        analyze_text: Whether to also analyze transcription with BERT (default: True)
    """
    try:
        stt = get_speech_to_text()
        if stt is None:
            return SpeechToTextResponse(
                success=False,
                transcription="",
                error="Speech-to-text model not available. Install with: pip install openai-whisper"
            )
        
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Transcribe audio
            print(f"📝 Transcribing audio file: {audio.filename}")
            result = stt.transcribe(tmp_path)
            
            if not result.get('success') or not result.get('text'):
                return SpeechToTextResponse(
                    success=False,
                    transcription="",
                    error=result.get('error', 'Transcription failed')
                )
            
            transcription = result['text']
            print(f"✅ Transcribed: \"{transcription[:100]}{'...' if len(transcription) > 100 else ''}\"")
            
            # Optionally analyze with BERT
            text_analysis_result = None
            if analyze_text and transcription.strip():
                model, tokenizer = get_bert_model()
                if model is not None and tokenizer is not None:
                    # Prepare text (include question for context if provided)
                    analysis_text = transcription
                    if question:
                        analysis_text = f"Question: {question}\nAnswer: {transcription}"
                    
                    # Tokenize and analyze
                    enc = tokenizer(
                        analysis_text,
                        padding=True,
                        truncation=True,
                        max_length=512,
                        return_tensors="pt"
                    )
                    enc = {k: v.to(DEVICE) for k, v in enc.items()}
                    
                    with torch.no_grad():
                        outputs = model(**enc)
                        logits = outputs.logits.detach().cpu().numpy()[0]
                        probs = np.exp(logits) / np.sum(np.exp(logits))
                    
                    labels = {0: "Poor", 1: "Average", 2: "Excellent"}
                    predicted_idx = int(np.argmax(probs))
                    quality_label = labels[predicted_idx]
                    quality_score = (probs[0] * 16.5 + probs[1] * 50 + probs[2] * 83.5)
                    
                    # Generate feedback
                    if quality_label == "Poor":
                        feedback = "Your answer lacks depth. Try using the STAR method with specific examples."
                    elif quality_label == "Average":
                        feedback = "Good start! Add more specific details and quantifiable achievements."
                    else:
                        feedback = "Excellent! Well-structured response with clear communication."
                    
                    text_analysis_result = TextAnalysisResponse(
                        success=True,
                        quality_score=float(quality_score),
                        quality_label=quality_label,
                        probabilities={labels[i]: float(probs[i]) for i in range(3)},
                        feedback=feedback,
                        reason=generate_bert_reason(quality_label, transcription)
                    )
                    print(f"🧠 BERT Analysis: {quality_label} ({quality_score:.1f}%)")
            
            # Detect filler words
            filler_count, filler_list = detect_filler_words(transcription)
            if filler_count > 0:
                print(f"📝 Detected {filler_count} filler words: {filler_list}")
            
            # Estimate speech rate (using segment durations if available)
            speech_rate = "unknown"
            word_count = len(transcription.split())
            total_duration = result.get('duration', 0)
            if total_duration > 0:
                speech_rate = classify_speech_rate(total_duration, word_count)
                print(f"🎤 Speech rate: {speech_rate} ({word_count} words in {total_duration:.1f}s)")
            
            return SpeechToTextResponse(
                success=True,
                transcription=transcription,
                language=result.get('language', 'en'),
                segments=result.get('segments', []),
                text_analysis=text_analysis_result,
                filler_word_count=filler_count,
                filler_words=filler_list if filler_list else None,
                speech_rate=speech_rate
            )
            
        finally:
            os.unlink(tmp_path)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return SpeechToTextResponse(
            success=False,
            transcription="",
            error=str(e)
        )


@app.post("/analyze/multimodal", response_model=MultimodalAnalysisResponse)
async def analyze_multimodal(
    image: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    question: Optional[str] = Form(None)
):
    """
    Analyze all modalities together for comprehensive interview feedback.
    
    Args:
        image: Base64 encoded image (optional)
        audio: Audio file (optional)
        text: Answer text (optional)
        question: Interview question (optional)
    """
    try:
        facial_result = None
        voice_result = None
        text_result = None
        
        # Analyze facial
        if image:
            response = await analyze_facial(image=image)
            if response.success:
                facial_result = response.model_dump()
        
        # Analyze voice
        if audio:
            response = await analyze_voice(audio=audio)
            if response.success:
                voice_result = response.model_dump()
        
        # Analyze text
        if text:
            response = await analyze_text(TextAnalysisRequest(text=text, question=question))
            if response.success:
                text_result = response.model_dump()
        
        # Fuse emotions
        fused_emotions = {}
        emotion_sources = 0
        
        if facial_result and facial_result.get('face_detected'):
            for emotion, prob in facial_result.get('emotions', {}).items():
                fused_emotions[emotion] = fused_emotions.get(emotion, 0) + prob * 0.5
            emotion_sources += 1
        
        if voice_result:
            for emotion, prob in voice_result.get('emotions', {}).items():
                fused_emotions[emotion] = fused_emotions.get(emotion, 0) + prob * 0.5
            emotion_sources += 1
        
        # Normalize fused emotions
        if emotion_sources > 0:
            total = sum(fused_emotions.values())
            if total > 0:
                fused_emotions = {k: v/total for k, v in fused_emotions.items()}
        
        # Calculate scores
        confidence_score = calculate_confidence_score(facial_result or {}, voice_result or {}, text_result or {})
        
        # Clarity based on text quality
        clarity_score = text_result.get('quality_score', 50.0) if text_result else 50.0
        
        # Engagement based on emotion variety and positivity
        engagement_score = 50.0
        if fused_emotions:
            positive_emotions = sum(fused_emotions.get(e, 0) for e in ['happy', 'surprise'])
            engagement_score = min(100, 50 + positive_emotions * 50)
        
        # Get dominant emotion
        overall_emotion = "neutral"
        if fused_emotions:
            overall_emotion = max(fused_emotions, key=fused_emotions.get)
        
        # Generate recommendations
        recommendations = generate_recommendations(
            facial_result or {},
            voice_result or {},
            text_result or {}
        )
        
        # ============================================
        # NEW: Coaching Analysis
        # ============================================
        coaching_data = None
        try:
            coaching_engine = get_coaching_engine()
            if coaching_engine._initialized and text_result:
                # Extract data for coaching
                bert_label = text_result.get('quality_label', 'Average')
                bert_probs = text_result.get('probabilities', {'Poor': 0.33, 'Average': 0.34, 'Excellent': 0.33})
                bert_confidence = max(bert_probs.values()) if bert_probs else 0.5
                
                # Voice data
                voice_emotion = voice_result.get('dominant_emotion', 'neutral') if voice_result else 'neutral'
                voice_confidence = voice_result.get('confidence', 0.5) if voice_result else 0.5
                filler_count = 0  # Will be available from speech analysis
                speech_rate = 'normal'
                
                # Facial data
                facial_emotion = facial_result.get('dominant_emotion', 'neutral') if facial_result else 'neutral'
                facial_confidence = facial_result.get('confidence', 0.5) if facial_result else 0.5
                face_detected = facial_result.get('face_detected', True) if facial_result else True
                
                # Run coaching analysis
                coaching_result = coaching_engine.analyze(
                    answer_text=text or "",
                    question_text=question or "",
                    bert_label=bert_label,
                    bert_confidence=bert_confidence,
                    bert_probs=bert_probs,
                    voice_emotion=voice_emotion,
                    voice_confidence=voice_confidence,
                    filler_count=filler_count,
                    speech_rate=speech_rate,
                    facial_emotion=facial_emotion,
                    facial_confidence=facial_confidence,
                    engagement_score=engagement_score,
                    face_detected=face_detected
                )
                
                # Convert to response format
                coaching_data = {
                    "success": True,
                    "sbert_similarities": coaching_result.sbert_similarities,
                    "closest_tier": coaching_result.closest_tier,
                    "excellent_gap": coaching_result.excellent_gap,
                    "combined_text_score": coaching_result.combined_text_score,
                    "bert_component": coaching_result.bert_component,
                    "sbert_component": coaching_result.sbert_component,
                    "content_diagnosis": coaching_result.content_diagnosis,
                    "voice_diagnosis": coaching_result.voice_diagnosis,
                    "facial_diagnosis": coaching_result.facial_diagnosis,
                    "content_tip": coaching_result.content_tip,
                    "voice_tip": coaching_result.voice_tip,
                    "facial_tip": coaching_result.facial_tip,
                    "quality_interpretation": coaching_result.quality_interpretation,
                    "quality_description": coaching_result.quality_description,
                    "progress_position": coaching_result.progress_position,
                    "improvement_tips": coaching_result.improvement_tips,
                    "generated_feedback": coaching_result.generated_feedback,
                    # NEW: BERTScore (Semantic Accuracy)
                    "bert_score_f1": coaching_result.bert_score_f1,
                    "bert_score_precision": coaching_result.bert_score_precision,
                    "bert_score_recall": coaching_result.bert_score_recall,
                    # NEW: LLM Judge
                    "llm_judge_score": coaching_result.llm_judge_score,
                    "llm_judge_rationale": coaching_result.llm_judge_rationale,
                    "llm_actionable_tips": coaching_result.llm_actionable_tips,
                    # NEW: STAR Breakdown
                    "star_breakdown": coaching_result.star_breakdown,
                    "content_relevance": coaching_result.content_relevance,
                    "coherence_score": coaching_result.coherence_score,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"✅ [COACHING] Analysis complete. Closest tier: {coaching_result.closest_tier}", flush=True)
        except Exception as coaching_error:
            print(f"⚠️ [COACHING] Error: {coaching_error}", flush=True)
            import traceback
            traceback.print_exc()
        
        # Prepare Response
        response_data = {
            "success": True,
            "overall_confidence": confidence_score,
            "overall_emotion": overall_emotion,
            "facial": facial_result,
            "voice": voice_result,
            "text": text_result,
            "fused_emotions": fused_emotions,
            "confidence_score": confidence_score,
            "clarity_score": clarity_score,
            "engagement_score": engagement_score,
            "recommendations": recommendations,
            "coaching": coaching_data,  # NEW: Structured coaching
            "timestamp": datetime.now().isoformat()
        }
        
        # Sanitize all floats before returning to avoid JSON serialization errors
        print(f"🚀 [MULTIMODAL] Preparing response. Sanitizing floats...", flush=True)
        sanitized_data = sanitize_floats(response_data)
        
        print(f"✅ [MULTIMODAL] Sanitization complete. Returning response.", flush=True)
        
        from fastapi.encoders import jsonable_encoder
        return JSONResponse(content=jsonable_encoder(sanitized_data))
        
    except Exception as e:
        return MultimodalAnalysisResponse(
            success=False,
            overall_confidence=0.0,
            overall_emotion="",
            fused_emotions={},
            confidence_score=0.0,
            clarity_score=0.0,
            engagement_score=0.0,
            recommendations=[],
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )



# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           Q&ACE Unified API Server                        ║
    ║                                                           ║
    ║   Facial + Voice + Text Analysis                          ║
    ║   http://localhost:8001                                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )
