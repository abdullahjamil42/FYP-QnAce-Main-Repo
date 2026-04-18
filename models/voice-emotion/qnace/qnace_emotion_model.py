import torch
import torch.nn as nn
import numpy as np
import librosa
import json
import os
from transformers import Wav2Vec2Model

class AttentionPooling(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1)
        )
    
    def forward(self, x):
        weights = self.attention(x)
        weights = torch.softmax(weights, dim=1)
        pooled = torch.sum(x * weights, dim=1)
        return pooled

class EmotionModel(nn.Module):
    def __init__(self, num_classes=6, dropout=0.3):
        super().__init__()
        self.wav2vec2 = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")
        hidden_size = 768
        self.attention_pool = AttentionPooling(hidden_size)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 512),
            nn.LayerNorm(512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        outputs = self.wav2vec2(x).last_hidden_state
        pooled = self.attention_pool(outputs)
        logits = self.classifier(pooled)
        return logits

    def preprocess_audio(self, audio_path, sample_rate=16000, max_length=8.0):
        """Preprocess audio file for inference"""
        waveform, sr = librosa.load(audio_path, sr=sample_rate)
        max_samples = int(max_length * sample_rate)
        
        if len(waveform) > max_samples:
            waveform = waveform[:max_samples]
        else:
            waveform = np.pad(waveform, (0, max_samples - len(waveform)))
        
        return torch.FloatTensor(waveform).unsqueeze(0)
    
    def predict_emotion(self, audio_path, emotions=None):
        """Predict emotion from audio file"""
        if emotions is None:
            emotions = ['anger', 'fear', 'happy', 'neutral', 'sad', 'surprise']
            
        self.eval()
        audio_tensor = self.preprocess_audio(audio_path)
        
        with torch.no_grad():
            logits = self(audio_tensor)
            probabilities = torch.softmax(logits, dim=-1)
            prediction = torch.argmax(logits, dim=-1)
            emotion = emotions[prediction.item()]
            confidence = probabilities.max().item()
        
        return emotion, confidence

def load_qnace_emotion_model(model_path="QnAce_Voice-Model.pth"):
    """Load the QnAce emotion recognition model"""
    
    # Load checkpoint
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    # Get emotions and config
    emotions = checkpoint.get('emotions', ['anger', 'fear', 'happy', 'neutral', 'sad', 'surprise'])
    config = checkpoint.get('config', {})
    
    # Create model
    model = EmotionModel(
        num_classes=len(emotions), 
        dropout=config.get('dropout', 0.3)
    )
    
    # Load weights
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    return model, emotions, config