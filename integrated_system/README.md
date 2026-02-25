# Q&ACE Integrated Multimodal Emotion Detection System

A comprehensive interview preparation system that combines **facial**, **voice**, and **text (BERT)** analysis for robust confidence scoring and feedback.

## 🎯 Overview

This integrated system combines three state-of-the-art models:

| Modality | Model | Accuracy | Purpose |
|----------|-------|----------|---------|
| **Facial** | EfficientNet-B2 | 72.72% | Emotion detection from video |
| **Voice** | Wav2Vec2 + Attention | 73.37% | Emotion detection from audio |
| **Text** | Fine-tuned BERT | - | Answer quality evaluation |

## 🚀 Quick Start

### 1. Start the Unified API

```bash
cd /Users/aziqrauf/codes/FYP/integrated_system
python api/main.py
```

The API will be available at: **http://localhost:8001**

### 2. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze/facial` | POST | Analyze facial emotions from image |
| `/analyze/voice` | POST | Analyze voice emotions from audio |
| `/analyze/text` | POST | Analyze answer quality with BERT |
| `/analyze/multimodal` | POST | Combined analysis of all modalities |

### 3. API Documentation

Visit **http://localhost:8001/docs** for interactive Swagger documentation.

## 📡 API Usage Examples

### Health Check
```bash
curl http://localhost:8001/health
```

### Text Analysis
```bash
curl -X POST http://localhost:8001/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your interview answer here..."}'
```

### Multimodal Analysis
```bash
curl -X POST http://localhost:8001/analyze/multimodal \
  -F "image=<base64_image>" \
  -F "audio=@recording.wav" \
  -F "text=Your answer text"
```

## 🔧 Configuration

The API uses the following model sources:
- Facial: `abdullahjamil42/QnAce-Face-Model` (Hugging Face Hub)
- Voice: `abdullahjamil42/QnAce-Voice-Model` (Hugging Face Hub)
- BERT: `BERT_Model/` (Local)

Models are automatically downloaded and cached on first use.

## 📊 Response Format

### Multimodal Response
```json
{
  "success": true,
  "overall_confidence": 75.5,
  "overall_emotion": "neutral",
  "confidence_score": 75.5,
  "clarity_score": 80.0,
  "engagement_score": 65.0,
  "recommendations": [
    "💡 Great neutral expression! Try adding a slight smile.",
    "✅ Good vocal tone! You sound confident."
  ],
  "facial": { ... },
  "voice": { ... },
  "text": { ... }
}
```

## 📂 Project Structure

```
Q&ACE/
├── integrated_system/          # 🆕 Multimodal integration
│   ├── multimodal_detector.py  # Combined facial + voice detection
│   ├── interview_analyzer.py   # Real-time analysis system
│   ├── report_generator.py     # Visual & text reports
│   ├── voice_emotion_detector.py
│   ├── hf_facial_emotion_detector.py  # HF-based facial detector
│   ├── facial_emotion_detector.py     # Wrapper for HF detector
│   ├── requirements.txt
│   └── README.md
│
├── BERT_Model/                  # Local BERT model
└── other_modules/               # Other project components
    ├── QnAce_Voice-Model.json
    └── ...
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd integrated_system
pip install -r requirements.txt
```

### 2. Run Real-time Analysis

```bash
python interview_analyzer.py
```

### Controls:
- `SPACE` - Start/Stop recording
- `R` - Reset session
- `S` - Save session & generate report
- `Q` - Quit

## 🔧 Usage

### Basic Multimodal Detection

```python
from multimodal_detector import MultimodalEmotionDetector
import cv2

# Initialize detector
detector = MultimodalEmotionDetector(
    facial_weight=0.5,
    voice_weight=0.5
)

# Detect from video frame
frame = cv2.imread("face.jpg")
result = detector.detect(frame=frame)

print(f"Emotion: {result.dominant_emotion}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Face detected: {result.face_detected}")
```

### With Audio

```python
import librosa

# Load audio
audio, sr = librosa.load("speech.wav", sr=16000)

# Detect from both modalities
result = detector.detect(frame=frame, audio=audio, sample_rate=sr)

print(f"Fused Emotion: {result.dominant_emotion}")
print(f"Facial: {result.facial_dominant} ({result.facial_confidence:.2f})")
print(f"Voice: {result.voice_dominant} ({result.voice_confidence:.2f})")
```

### Interview Session Analysis

```python
from interview_analyzer import MultimodalInterviewAnalyzer

# Initialize analyzer
analyzer = MultimodalInterviewAnalyzer()

# Start session
session_id = analyzer.start_session()

# Analyze frames in loop
for frame in video_frames:
    analysis = analyzer.analyze_frame(frame, audio_segment)
    print(f"Confidence: {analysis.confidence_score:.1f}%")

# End session and get results
session_data = analyzer.end_session()

# Generate reports
from report_generator import generate_reports
generate_reports(session_data, "./outputs")
```

## 📊 Fusion Methods

The system supports multiple fusion strategies:

| Method | Description |
|--------|-------------|
| `weighted_average` | Fixed weights for each modality (default) |
| `confidence_weighted` | Dynamic weighting based on detection confidence |
| `max` | Take maximum probability across modalities |

```python
result = detector.detect(
    frame=frame,
    audio=audio,
    fusion_method="confidence_weighted"
)
```

## 📈 Confidence Scoring

Interview confidence is calculated from emotion probabilities:

| Emotion | Weight | Interpretation |
|---------|--------|----------------|
| Happy | +0.85 | Strong positive signal |
| Neutral | +0.75 | Professional composure |
| Surprise | +0.50 | Engagement indicator |
| Sad | -0.60 | Negative indicator |
| Fear | -0.70 | Anxiety signal |
| Anger | -0.50 | Frustration signal |
| Disgust | -0.40 | Mild negative |

### Confidence Levels

| Score | Level | Feedback |
|-------|-------|----------|
| 80%+ | Excellent | Outstanding interview presence |
| 65-80% | Confident | Strong professional composure |
| 50-65% | Moderate | Room for improvement |
| 35-50% | Nervous | Visible anxiety signs |
| 20-35% | Anxious | High stress indicators |
| <20% | Very Anxious | Needs significant practice |

## 📝 Generated Reports

### Visual Report (PNG)
- Confidence timeline with both modalities
- Segment analysis (beginning/middle/end)
- Emotion distribution pie chart
- Modality comparison
- Recommendations

### Text Report (TXT)
- Detailed statistics
- Modality coverage
- Emotion breakdown
- Session metadata

## 🔗 API Reference

### MultimodalEmotionDetector

```python
class MultimodalEmotionDetector:
    def __init__(
        facial_model_path: str = None,
        voice_model_path: str = None,
        device: str = None,
        facial_weight: float = 0.5,
        voice_weight: float = 0.5
    )
    
    def detect(
        frame: np.ndarray = None,
        audio: np.ndarray = None,
        sample_rate: int = 16000,
        fusion_method: str = "weighted_average"
    ) -> MultimodalResult
```

### MultimodalResult

```python
@dataclass
class MultimodalResult:
    emotions: Dict[str, float]      # Fused probabilities
    dominant_emotion: str           # Top emotion
    confidence: float               # Highest probability
    
    facial_emotions: Dict[str, float]
    facial_dominant: str
    facial_confidence: float
    face_detected: bool
    
    voice_emotions: Dict[str, float]
    voice_dominant: str
    voice_confidence: float
    voice_detected: bool
    
    timestamp: float
    fusion_method: str
```

## 🛠️ Troubleshooting

### "No face detected"
- Ensure good lighting
- Face the camera directly
- Check webcam permissions

### "Voice detection unavailable"
- Install `transformers`: `pip install transformers`
- Check microphone permissions
- Ensure audio device is working: `python -c "import sounddevice; print(sounddevice.query_devices())"`

### "Model not found"
- Models are automatically downloaded from Hugging Face Hub:
  - Facial: `abdullahjamil42/QnAce-Face-Model`
  - Voice: `abdullahjamil42/QnAce-Voice-Model`
- Ensure internet connection for first-time downloads

## 📄 License

Part of the Q&ACE Interview Preparation System.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request
