# Q&ACE - AI-Powered Interview Preparation Platform

<div align="center">

![Q&ACE Logo](https://img.shields.io/badge/Q%26ACE-Interview%20Prep-00d9ff?style=for-the-badge)

**Master your interviews with AI-powered feedback on content, voice, and facial expressions**

[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0-red?style=flat-square&logo=pytorch)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)

</div>

## 🎯 Overview

Q&ACE is a comprehensive interview preparation platform that uses multimodal AI to analyze:

- **📝 Text Analysis** - BERT-based model for answer quality assessment (89.93% accuracy)
- **🎤 Voice Analysis** - Wav2Vec2 model for speech emotion detection (73.37% accuracy)
- **😊 Facial Analysis** - EfficientNet-B2 for facial emotion recognition (72.72% accuracy)

## 🏗️ Project Structure

```
FYP/
├── Frontend/           # Next.js 14 web application
├── BERT_Model/         # Text analysis API
├── QnAce_Voice-Model/  # Voice emotion detection
├── interview_emotion_detection/  # Facial emotion training
├── integrated_system/  # Multimodal integration API
└── outputs/            # Generated reports
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- pip or conda

### Frontend Setup

```bash
cd Frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Backend Setup

```bash
# Install Python dependencies
cd integrated_system
pip install -r requirements.txt

# Start the API server
uvicorn api.main:app --reload --port 8000
```

## 🧠 Models

### BERT Text Model
- Architecture: BERT-base fine-tuned
- Accuracy: 89.93%
- Task: Interview answer quality assessment

### Voice Emotion Model
- Architecture: Wav2Vec2
- Accuracy: 73.37%
- Emotions: Angry, Fear, Happy, Neutral, Sad, Surprise

### Facial Emotion Model
- Architecture: EfficientNet-B2
- Accuracy: 72.72%
- Emotions: Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral

## 📱 Features

- ✅ Practice interviews with AI feedback
- ✅ Real-time emotion analysis
- ✅ Comprehensive performance reports
- ✅ Progress tracking dashboard
- ✅ Multiple interview types (Technical, Behavioral, etc.)
- ✅ Personalized improvement suggestions

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Python 3.11 |
| ML Models | PyTorch, Transformers, timm |
| Face Detection | MTCNN, OpenCV |
| Audio Processing | librosa, soundfile |

## 📊 API Endpoints

```
POST /api/analyze/text      - Analyze text response
POST /api/analyze/voice     - Analyze voice recording
POST /api/analyze/facial    - Analyze facial expressions
POST /api/analyze/multimodal - Combined analysis
GET  /api/health            - Health check
```

## 🧪 Testing

```bash
# Frontend tests
cd Frontend
npm test

# Backend tests
cd integrated_system
python -m pytest tests/
```

## 📄 License

This project is part of a Final Year Project (FYP).

## 👤 Author

Aziq Rauf

---

<div align="center">
Made with ❤️ for better interview preparation
</div>
