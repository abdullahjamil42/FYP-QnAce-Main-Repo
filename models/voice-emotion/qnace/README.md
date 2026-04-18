# QnAce Voice Emotion Recognition Model

## Model Description
This is a voice emotion recognition model based on Wav2Vec2 that can classify 6 emotions in speech audio.

**Emotions:** anger, fear, happy, neutral, sad, surprise

## Usage

```python
import torch
from qnace_emotion_model import load_qnace_emotion_model

# Load the model
model, emotions, config = load_qnace_emotion_model("pytorch_model.bin")

# Predict emotion from audio file
emotion, confidence = model.predict_emotion("path/to/audio.wav", emotions)
print(f"Detected emotion: {emotion} (confidence: {confidence:.3f})")
```

## Model Performance
- **Validation Accuracy**: 73.60%
- **Test Accuracy**: 73.37%

## Requirements
```
torch>=1.9.0
transformers>=4.20.0
librosa>=0.8.0
numpy>=1.21.0
```

## Model Details
- **Base Model**: facebook/wav2vec2-base
- **Architecture**: Wav2Vec2 + Attention Pooling + Multi-layer Classifier
- **Input**: 16kHz audio, max 8 seconds
- **Output**: Emotion classification with confidence scores
