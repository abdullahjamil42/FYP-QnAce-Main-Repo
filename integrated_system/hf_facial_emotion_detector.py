"""
Hugging Face-based Facial Emotion Detector for Q&ACE Integration.

This module loads the facial emotion model directly from Hugging Face Hub
using safetensors and maintains the same interface as the original detector.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import requests
import tempfile

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import timm

# Try to import safetensors for model loading
try:
    from safetensors import safe_open
    SAFETENSORS_AVAILABLE = True
except ImportError:
    SAFETENSORS_AVAILABLE = False

# Try to import MTCNN for face detection
try:
    from facenet_pytorch import MTCNN
    MTCNN_AVAILABLE = True
except ImportError:
    MTCNN_AVAILABLE = False

# Emotion labels in FER2013 order
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
HF_MODEL_URL = "https://huggingface.co/abdullahjamil42/QnAce-Face-Model/resolve/main/model.safetensors"


class HuggingFaceEmotionDetector:
    """
    Facial emotion detector using model from Hugging Face Hub.
    
    Loads the EfficientNet-B2 model directly from HF using safetensors.
    Provides same interface as original EmotionDetector for compatibility.
    
    Accuracy: 72.72% (EfficientNet-B2)
    Emotions: angry, disgust, fear, happy, sad, surprise, neutral
    """
    
    def __init__(
        self,
        use_mtcnn: bool = True,
        device: Optional[str] = None,
        cache_model: bool = True,
    ):
        """
        Initialize the Hugging Face emotion detector.
        
        Args:
            use_mtcnn: Whether to use MTCNN for face detection
            device: Device to run inference on ('cuda', 'mps', 'cpu', or None for auto)
            cache_model: Whether to cache the downloaded model locally
        """
        if not SAFETENSORS_AVAILABLE:
            raise ImportError("safetensors required. Install: pip install safetensors")
        
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
        
        print(f"HuggingFaceEmotionDetector using device: {self.device}")
        
        # Model settings
        self.model_type = 'b2'
        self.image_size = 260
        self.emotions = EMOTION_LABELS
        self.cache_model = cache_model
        
        # Load model from HF
        self._load_model_from_hf()
        
        # Setup face detector
        self.use_mtcnn = use_mtcnn and MTCNN_AVAILABLE
        if self.use_mtcnn:
            # Force CPU for MTCNN - MPS has interpolation issues
            self.face_detector = MTCNN(
                keep_all=True,
                device="cpu"  # Always CPU for MTCNN due to MPS issues
            )
            print("Using MTCNN for face detection (CPU)")
        else:
            # Fallback to Haar cascade
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_detector = cv2.CascadeClassifier(cascade_path)
            print("Using Haar cascade for face detection")
        
        # Image transforms (use correct size for model)
        self.transform = transforms.Compose([
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    
    def _get_cache_path(self) -> Path:
        """Get the cache path for the model."""
        cache_dir = Path.home() / ".cache" / "qnace" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "facial_emotion_model.safetensors"
    
    def _download_model(self) -> str:
        """Download model from Hugging Face and return path."""
        print("Downloading facial emotion model from Hugging Face...")
        
        if self.cache_model:
            cache_path = self._get_cache_path()
            if cache_path.exists():
                print(f"Using cached model from: {cache_path}")
                return str(cache_path)
        
        try:
            response = requests.get(HF_MODEL_URL, timeout=120)
            response.raise_for_status()
            
            if self.cache_model:
                model_path = self._get_cache_path()
                with open(model_path, "wb") as f:
                    f.write(response.content)
                print(f"Model cached to: {model_path}")
                return str(model_path)
            else:
                # Use temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".safetensors")
                temp_file.write(response.content)
                temp_file.close()
                return temp_file.name
                
        except Exception as e:
            raise RuntimeError(f"Failed to download model from HF: {e}")
    
    def _load_model_from_hf(self):
        """Load model from Hugging Face Hub."""
        print("Loading facial emotion model from Hugging Face Hub...")
        
        # Download model
        model_path = self._download_model()
        
        # Create EfficientNet-B2 architecture
        self.model = timm.create_model('efficientnet_b2.ra_in1k', pretrained=False)
        in_features = self.model.classifier.in_features
        
        # Replace classifier to match our trained model
        self.model.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),  # 0.4 * 0.75
            nn.Linear(512, len(EMOTION_LABELS))
        )
        
        # Load weights from safetensors
        try:
            tensors = {}
            with safe_open(model_path, framework="pt", device="cpu") as f:
                for k in f.keys():
                    tensor_key = k
                    # Remove 'backbone.' prefix if present to match timm model structure
                    if tensor_key.startswith('backbone.'):
                        tensor_key = tensor_key[9:]  # Remove 'backbone.' prefix
                    tensors[tensor_key] = f.get_tensor(k)
            
            # Load with strict=False to handle potential mismatches
            missing_keys, unexpected_keys = self.model.load_state_dict(tensors, strict=False)
            
            if missing_keys:
                print(f"Warning: Missing keys in model: {len(missing_keys)} keys")
            if unexpected_keys:
                print(f"Warning: Unexpected keys in model: {len(unexpected_keys)} keys")
            
            print("✅ Model loaded successfully from Hugging Face!")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load model weights: {e}")
        
        # Clean up temporary file if not cached
        if not self.cache_model and not str(model_path).startswith(str(Path.home())):
            try:
                os.unlink(model_path)
            except:
                pass
        
        self.model = self.model.to(self.device)
        self.model.eval()
    
    def _detect_faces_mtcnn(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using MTCNN."""
        # MTCNN expects RGB
        if len(image.shape) == 2:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        try:
            boxes, probs = self.face_detector.detect(image_rgb)
            
            faces = []
            if boxes is not None:
                for box, prob in zip(boxes, probs):
                    if prob > 0.7:  # Confidence threshold
                        x1, y1, x2, y2 = box.astype(int)
                        # Convert to (x, y, w, h) format
                        faces.append((x1, y1, x2-x1, y2-y1))
            
            return faces
        except Exception as e:
            print(f"MTCNN detection failed: {e}")
            return []
    
    def _detect_faces_haar(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using Haar cascade."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        return [(x, y, w, h) for (x, y, w, h) in faces]
    
    def detect_emotions(self, image: np.ndarray) -> List[Dict]:
        """
        Detect emotions from an image.
        
        Args:
            image: Input image as numpy array (BGR format)
            
        Returns:
            List of dictionaries containing emotions for each detected face
        """
        results = []
        
        # Detect faces
        if self.use_mtcnn:
            faces = self._detect_faces_mtcnn(image)
        else:
            faces = self._detect_faces_haar(image)
        
        for face_box in faces:
            x, y, w, h = face_box
            
            # Extract face region
            face_img = image[y:y+h, x:x+w]
            
            if face_img.size == 0:
                continue
            
            # Convert to RGB PIL Image
            if len(face_img.shape) == 3:
                face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            else:
                face_rgb = cv2.cvtColor(face_img, cv2.COLOR_GRAY2RGB)
            
            pil_img = Image.fromarray(face_rgb)
            
            # Preprocess
            input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
            
            # Inference
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)[0].cpu().numpy()
            
            # Format results
            emotions = {emotion: float(prob) for emotion, prob in zip(self.emotions, probabilities)}
            
            results.append({
                'box': face_box,
                'emotions': emotions
            })
        
        return results


# Alias for compatibility with existing code
EmotionDetector = HuggingFaceEmotionDetector
FacialEmotionDetector = HuggingFaceEmotionDetector