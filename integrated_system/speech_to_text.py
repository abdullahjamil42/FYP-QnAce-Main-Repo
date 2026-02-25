"""
Speech-to-Text Module using OpenAI Whisper.

This module provides local speech-to-text transcription using Whisper,
which is then used to send the transcribed text to the BERT model
for answer quality analysis.

No API key required - runs completely locally!
"""

import os
from pathlib import Path
from typing import Optional, Dict, Tuple
import numpy as np

import torch

# Try to import whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Whisper not installed. Run: pip install openai-whisper")

# Try to import librosa for audio processing
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


class SpeechToText:
    """
    Speech-to-Text transcription using OpenAI Whisper.
    
    Supports multiple model sizes:
    - tiny: Fastest, ~1GB VRAM, good accuracy
    - base: Fast, ~1GB VRAM, better accuracy (recommended)
    - small: Medium speed, ~2GB VRAM, great accuracy
    - medium: Slower, ~5GB VRAM, best accuracy for FYP
    - large: Slowest, ~10GB VRAM, highest accuracy
    """
    
    SUPPORTED_MODELS = ['tiny', 'base', 'small', 'medium', 'large']
    
    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        language: str = "en"
    ):
        """
        Initialize Whisper speech-to-text.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            device: Device for inference ('cuda', 'mps', 'cpu', or None for auto)
            language: Language code for transcription (default: 'en' for English)
        """
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "Whisper not installed. Install with: pip install openai-whisper"
            )
        
        # Validate model size
        if model_size not in self.SUPPORTED_MODELS:
            print(f"⚠️ Unknown model size '{model_size}', using 'base'")
            model_size = "base"
        
        # Setup device
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "cpu"  # Whisper has issues with MPS, use CPU
            else:
                self.device = "cpu"
        else:
            self.device = device
        
        self.model_size = model_size
        self.language = language
        self.model = None
        
        print(f"🎤 Loading Whisper '{model_size}' model on {self.device}...")
        self._load_model()
        print(f"✅ Whisper model loaded successfully!")
    
    def _load_model(self):
        """Load the Whisper model."""
        try:
            self.model = whisper.load_model(self.model_size, device=self.device)
        except Exception as e:
            print(f"❌ Failed to load Whisper model: {e}")
            raise
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            language: Override language for this transcription
            
        Returns:
            Dict with 'text', 'language', 'segments' (with timestamps)
        """
        if self.model is None:
            raise RuntimeError("Whisper model not loaded")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        lang = language or self.language
        
        try:
            result = self.model.transcribe(
                audio_path,
                language=lang,
                task="transcribe",
                verbose=False
            )
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', lang),
                'segments': result.get('segments', []),
                'success': True
            }
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return {
                'text': '',
                'language': lang,
                'segments': [],
                'success': False,
                'error': str(e)
            }
    
    def transcribe_audio_array(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio from numpy array.
        
        Args:
            audio: Audio waveform as numpy array
            sample_rate: Sample rate of the audio (default: 16000)
            language: Override language for this transcription
            
        Returns:
            Dict with 'text', 'language', 'segments'
        """
        if self.model is None:
            raise RuntimeError("Whisper model not loaded")
        
        lang = language or self.language
        
        try:
            # Whisper expects float32 audio at 16kHz
            if sample_rate != 16000:
                if LIBROSA_AVAILABLE:
                    audio = librosa.resample(
                        audio.astype(np.float32),
                        orig_sr=sample_rate,
                        target_sr=16000
                    )
                else:
                    print("⚠️ librosa not available for resampling, results may vary")
            
            # Ensure float32
            audio = audio.astype(np.float32)
            
            # Normalize if needed
            if np.abs(audio).max() > 1.0:
                audio = audio / np.abs(audio).max()
            
            result = self.model.transcribe(
                audio,
                language=lang,
                task="transcribe",
                verbose=False
            )
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', lang),
                'segments': result.get('segments', []),
                'success': True
            }
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return {
                'text': '',
                'language': lang,
                'segments': [],
                'success': False,
                'error': str(e)
            }
    
    def get_text(self, audio_path: str) -> str:
        """
        Simple method to get just the transcribed text.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text string
        """
        result = self.transcribe(audio_path)
        return result.get('text', '')


class SpeechAnalyzer:
    """
    Combined Speech-to-Text and BERT Text Analysis.
    
    This class:
    1. Transcribes user's spoken answer using Whisper
    2. Sends the transcribed text to BERT for quality analysis
    3. Returns both transcription and quality scores
    """
    
    def __init__(
        self,
        whisper_model: str = "base",
        bert_api_url: str = "http://localhost:8001",
        device: Optional[str] = None
    ):
        """
        Initialize speech analyzer.
        
        Args:
            whisper_model: Whisper model size
            bert_api_url: URL of the BERT API endpoint
            device: Device for Whisper inference
        """
        self.stt = SpeechToText(model_size=whisper_model, device=device)
        self.bert_api_url = bert_api_url.rstrip('/')
        
        print(f"🔗 BERT API configured at: {self.bert_api_url}")
    
    def analyze_audio(
        self,
        audio_path: str,
        question: Optional[str] = None
    ) -> Dict:
        """
        Analyze spoken answer: transcribe and evaluate quality.
        
        Args:
            audio_path: Path to audio file with user's answer
            question: Optional question for context
            
        Returns:
            Dict with transcription and BERT analysis results
        """
        import requests
        
        # Step 1: Transcribe audio to text
        print("📝 Transcribing audio...")
        transcription = self.stt.transcribe(audio_path)
        
        if not transcription.get('success') or not transcription.get('text'):
            return {
                'success': False,
                'transcription': transcription,
                'text_analysis': None,
                'error': 'Transcription failed or empty'
            }
        
        text = transcription['text']
        print(f"✅ Transcribed: \"{text[:100]}{'...' if len(text) > 100 else ''}\"")
        
        # Step 2: Send to BERT for analysis
        print("🧠 Analyzing text quality with BERT...")
        try:
            # Prepare text (optionally include question for context)
            analysis_text = text
            if question:
                analysis_text = f"Question: {question}\nAnswer: {text}"
            
            response = requests.post(
                f"{self.bert_api_url}/api/analyze/text",
                json={"text": analysis_text},
                timeout=30
            )
            
            if response.status_code == 200:
                bert_result = response.json()
                print(f"✅ BERT Analysis complete: {bert_result.get('quality_label', 'N/A')}")
            else:
                bert_result = {
                    'success': False,
                    'error': f"BERT API returned {response.status_code}"
                }
        except requests.exceptions.ConnectionError:
            bert_result = {
                'success': False,
                'error': 'Could not connect to BERT API. Is the server running?'
            }
        except Exception as e:
            bert_result = {
                'success': False,
                'error': str(e)
            }
        
        return {
            'success': True,
            'transcription': {
                'text': text,
                'language': transcription.get('language'),
                'segments': transcription.get('segments', [])
            },
            'text_analysis': bert_result
        }
    
    def analyze_audio_array(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        question: Optional[str] = None
    ) -> Dict:
        """
        Analyze spoken answer from audio array.
        
        Args:
            audio: Audio waveform as numpy array
            sample_rate: Sample rate of audio
            question: Optional question for context
            
        Returns:
            Dict with transcription and BERT analysis results
        """
        import requests
        
        # Step 1: Transcribe
        print("📝 Transcribing audio...")
        transcription = self.stt.transcribe_audio_array(audio, sample_rate)
        
        if not transcription.get('success') or not transcription.get('text'):
            return {
                'success': False,
                'transcription': transcription,
                'text_analysis': None,
                'error': 'Transcription failed or empty'
            }
        
        text = transcription['text']
        print(f"✅ Transcribed: \"{text[:100]}{'...' if len(text) > 100 else ''}\"")
        
        # Step 2: Send to BERT
        print("🧠 Analyzing text quality with BERT...")
        try:
            analysis_text = text
            if question:
                analysis_text = f"Question: {question}\nAnswer: {text}"
            
            response = requests.post(
                f"{self.bert_api_url}/api/analyze/text",
                json={"text": analysis_text},
                timeout=30
            )
            
            if response.status_code == 200:
                bert_result = response.json()
            else:
                bert_result = {'success': False, 'error': f"API error {response.status_code}"}
        except Exception as e:
            bert_result = {'success': False, 'error': str(e)}
        
        return {
            'success': True,
            'transcription': {
                'text': text,
                'language': transcription.get('language'),
                'segments': transcription.get('segments', [])
            },
            'text_analysis': bert_result
        }


# Convenience function
def transcribe_and_analyze(
    audio_path: str,
    question: Optional[str] = None,
    whisper_model: str = "base",
    bert_api_url: str = "http://localhost:8001"
) -> Dict:
    """
    One-shot function to transcribe audio and analyze with BERT.
    
    Args:
        audio_path: Path to audio file
        question: Optional interview question
        whisper_model: Whisper model size
        bert_api_url: BERT API endpoint
        
    Returns:
        Analysis results
    """
    analyzer = SpeechAnalyzer(
        whisper_model=whisper_model,
        bert_api_url=bert_api_url
    )
    return analyzer.analyze_audio(audio_path, question)


if __name__ == "__main__":
    # Quick test
    print("=" * 60)
    print("Speech-to-Text Test (Whisper)")
    print("=" * 60)
    
    # Test initialization
    try:
        stt = SpeechToText(model_size="base")
        print("\n✅ Whisper loaded successfully!")
        
        # Test with a sample file if exists
        test_files = [
            "test_audio.wav",
            "sample.wav",
            "../test_audio.wav"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\n📁 Testing with: {test_file}")
                result = stt.transcribe(test_file)
                print(f"📝 Text: {result.get('text', 'No text')}")
                break
        else:
            print("\n📌 No test audio file found. To test:")
            print("   1. Record or download a .wav file")
            print("   2. Run: python speech_to_text.py")
            
    except ImportError as e:
        print(f"\n❌ {e}")
        print("Install Whisper with: pip install openai-whisper")
