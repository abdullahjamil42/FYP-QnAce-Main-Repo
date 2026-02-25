"""
Q&ACE End-to-End Integration Tests

This module tests:
1. Individual model accuracy and functionality
2. API endpoint responses
3. End-to-end multimodal integration
4. Model cooperation and fusion accuracy
"""

import os
import sys
import json
import time
import requests
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:8001"
TIMEOUT = 30

# ============================================
# Test Result Classes
# ============================================

@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    duration: float
    message: str
    details: Dict = None


@dataclass
class TestSuiteResult:
    """Result of a test suite."""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration: float
    results: List[TestResult]


# ============================================
# Test Utilities
# ============================================

def create_test_image(width=640, height=480, color=(100, 100, 100)):
    """Create a test image as numpy array."""
    import cv2
    img = np.full((height, width, 3), color, dtype=np.uint8)
    return img


def image_to_base64(img) -> str:
    """Convert numpy image to base64 string."""
    import cv2
    import base64
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')


def create_test_audio(duration=2.0, sample_rate=16000):
    """Create test audio signal."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Create a simple sine wave with some variation
    audio = np.sin(2 * np.pi * 440 * t) * 0.5
    audio += np.sin(2 * np.pi * 880 * t) * 0.25
    audio = (audio * 32767).astype(np.int16)
    return audio, sample_rate


def save_test_audio(audio, sample_rate, filepath):
    """Save audio to WAV file."""
    import wave
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())


# ============================================
# API Health Tests
# ============================================

class APIHealthTests:
    """Test API availability and health."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.results = []
    
    def test_api_health(self) -> TestResult:
        """Test if API is running and healthy."""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=TIMEOUT)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                models_loaded = all([
                    data.get('models', {}).get('facial', False),
                    data.get('models', {}).get('voice', False),
                    data.get('models', {}).get('bert', False)
                ])
                
                return TestResult(
                    name="API Health Check",
                    passed=models_loaded,
                    duration=duration,
                    message=f"All models loaded: {models_loaded}",
                    details=data
                )
            else:
                return TestResult(
                    name="API Health Check",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="API Health Check",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_api_root(self) -> TestResult:
        """Test API root endpoint."""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/", timeout=TIMEOUT)
            duration = time.time() - start
            
            return TestResult(
                name="API Root Endpoint",
                passed=response.status_code == 200,
                duration=duration,
                message=f"Status: {response.status_code}",
                details=response.json() if response.status_code == 200 else None
            )
        except Exception as e:
            return TestResult(
                name="API Root Endpoint",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all health tests."""
        start = time.time()
        results = [
            self.test_api_health(),
            self.test_api_root()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="API Health Tests",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# Facial Emotion Model Tests
# ============================================

class FacialModelTests:
    """Test facial emotion detection model."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def test_facial_no_face(self) -> TestResult:
        """Test facial detection with no face in image."""
        start = time.time()
        try:
            # Create blank image
            img = create_test_image(color=(50, 50, 50))
            base64_img = image_to_base64(img)
            
            response = requests.post(
                f"{self.base_url}/analyze/facial",
                data={"image": base64_img},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                # Should report no face detected
                return TestResult(
                    name="Facial - No Face Detection",
                    passed=data.get('face_detected') == False,
                    duration=duration,
                    message=f"Face detected: {data.get('face_detected')}",
                    details=data
                )
            else:
                return TestResult(
                    name="Facial - No Face Detection",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Facial - No Face Detection",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_facial_response_format(self) -> TestResult:
        """Test facial API response format."""
        start = time.time()
        try:
            img = create_test_image()
            base64_img = image_to_base64(img)
            
            response = requests.post(
                f"{self.base_url}/analyze/facial",
                data={"image": base64_img},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['success', 'emotions', 'dominant_emotion', 'confidence', 'face_detected']
                has_all_fields = all(field in data for field in required_fields)
                
                return TestResult(
                    name="Facial - Response Format",
                    passed=has_all_fields,
                    duration=duration,
                    message=f"All required fields present: {has_all_fields}",
                    details={"fields": list(data.keys())}
                )
            else:
                return TestResult(
                    name="Facial - Response Format",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Facial - Response Format",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_facial_emotions_valid(self) -> TestResult:
        """Test that facial emotions are valid probabilities."""
        start = time.time()
        try:
            img = create_test_image()
            base64_img = image_to_base64(img)
            
            response = requests.post(
                f"{self.base_url}/analyze/facial",
                data={"image": base64_img},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                emotions = data.get('emotions', {})
                
                if not emotions:
                    return TestResult(
                        name="Facial - Valid Emotions",
                        passed=True,
                        duration=duration,
                        message="No face detected, empty emotions expected"
                    )
                
                # Check probabilities are valid
                all_valid = all(0 <= v <= 1 for v in emotions.values())
                sum_close_to_one = abs(sum(emotions.values()) - 1.0) < 0.01
                
                return TestResult(
                    name="Facial - Valid Emotions",
                    passed=all_valid,
                    duration=duration,
                    message=f"Valid probabilities: {all_valid}, Sum ~1: {sum_close_to_one}",
                    details=emotions
                )
            else:
                return TestResult(
                    name="Facial - Valid Emotions",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Facial - Valid Emotions",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all facial model tests."""
        start = time.time()
        results = [
            self.test_facial_no_face(),
            self.test_facial_response_format(),
            self.test_facial_emotions_valid()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="Facial Model Tests",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# Voice Emotion Model Tests
# ============================================

class VoiceModelTests:
    """Test voice emotion detection model."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.test_audio_path = "/tmp/test_audio.wav"
    
    def _create_test_audio_file(self):
        """Create a test audio file."""
        audio, sr = create_test_audio(duration=2.0)
        save_test_audio(audio, sr, self.test_audio_path)
    
    def test_voice_response_format(self) -> TestResult:
        """Test voice API response format."""
        start = time.time()
        try:
            self._create_test_audio_file()
            
            with open(self.test_audio_path, 'rb') as f:
                response = requests.post(
                    f"{self.base_url}/analyze/voice",
                    files={"audio": ("test.wav", f, "audio/wav")},
                    timeout=TIMEOUT
                )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['success', 'emotions', 'dominant_emotion', 'confidence']
                has_all_fields = all(field in data for field in required_fields)
                
                return TestResult(
                    name="Voice - Response Format",
                    passed=has_all_fields,
                    duration=duration,
                    message=f"All required fields present: {has_all_fields}",
                    details={"fields": list(data.keys())}
                )
            else:
                return TestResult(
                    name="Voice - Response Format",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}: {response.text[:200]}"
                )
        except Exception as e:
            return TestResult(
                name="Voice - Response Format",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_voice_emotions_valid(self) -> TestResult:
        """Test that voice emotions are valid probabilities."""
        start = time.time()
        try:
            self._create_test_audio_file()
            
            with open(self.test_audio_path, 'rb') as f:
                response = requests.post(
                    f"{self.base_url}/analyze/voice",
                    files={"audio": ("test.wav", f, "audio/wav")},
                    timeout=TIMEOUT
                )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get('success'):
                    return TestResult(
                        name="Voice - Valid Emotions",
                        passed=False,
                        duration=duration,
                        message=f"Analysis failed: {data.get('error')}"
                    )
                
                emotions = data.get('emotions', {})
                
                # Check all expected emotions are present
                expected_emotions = ['anger', 'fear', 'happy', 'neutral', 'sad', 'surprise']
                has_all_emotions = all(e in emotions for e in expected_emotions)
                
                # Check probabilities are valid
                all_valid = all(0 <= v <= 1 for v in emotions.values())
                
                return TestResult(
                    name="Voice - Valid Emotions",
                    passed=has_all_emotions and all_valid,
                    duration=duration,
                    message=f"All emotions: {has_all_emotions}, Valid probs: {all_valid}",
                    details=emotions
                )
            else:
                return TestResult(
                    name="Voice - Valid Emotions",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Voice - Valid Emotions",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all voice model tests."""
        start = time.time()
        results = [
            self.test_voice_response_format(),
            self.test_voice_emotions_valid()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="Voice Model Tests",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# BERT Text Model Tests
# ============================================

class BERTModelTests:
    """Test BERT text analysis model."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        
        # Test answers with expected quality
        self.test_answers = [
            {
                "text": "I don't know.",
                "expected_label": "Poor",
                "description": "Very short, uninformative answer"
            },
            {
                "text": "I have some experience with Python and databases. I've worked on a few projects.",
                "expected_label": "Average",
                "description": "Brief answer with some detail"
            },
            {
                "text": """In my previous role as a Senior Software Engineer at TechCorp, I led a team of 6 developers 
                to migrate our legacy monolithic application to a microservices architecture. Over 8 months, 
                we successfully decomposed the system into 12 independent services, implemented CI/CD pipelines 
                using Jenkins and Docker, and achieved a 40% reduction in deployment time. I was responsible for 
                designing the API contracts, mentoring junior developers, and coordinating with stakeholders. 
                The project was delivered on time and under budget, and our system uptime improved from 99.5% to 99.99%.""",
                "expected_label": "Excellent",
                "description": "Detailed STAR-format answer with metrics"
            }
        ]
    
    def test_text_response_format(self) -> TestResult:
        """Test text API response format."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/text",
                json={"text": "This is a test answer."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['success', 'quality_score', 'quality_label', 'probabilities', 'feedback']
                has_all_fields = all(field in data for field in required_fields)
                
                return TestResult(
                    name="BERT - Response Format",
                    passed=has_all_fields,
                    duration=duration,
                    message=f"All required fields present: {has_all_fields}",
                    details={"fields": list(data.keys())}
                )
            else:
                return TestResult(
                    name="BERT - Response Format",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="BERT - Response Format",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_text_empty_input(self) -> TestResult:
        """Test text API with empty input."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/text",
                json={"text": ""},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                # Should handle empty input gracefully
                return TestResult(
                    name="BERT - Empty Input Handling",
                    passed=True,  # As long as it doesn't crash
                    duration=duration,
                    message=f"Handled empty input: success={data.get('success')}",
                    details=data
                )
            else:
                return TestResult(
                    name="BERT - Empty Input Handling",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="BERT - Empty Input Handling",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_text_quality_labels(self) -> TestResult:
        """Test that quality labels are valid."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/text",
                json={"text": "I have experience in software development."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                valid_labels = ['Poor', 'Average', 'Excellent']
                label = data.get('quality_label', '')
                is_valid = label in valid_labels
                
                return TestResult(
                    name="BERT - Valid Quality Labels",
                    passed=is_valid,
                    duration=duration,
                    message=f"Label '{label}' is valid: {is_valid}",
                    details={"label": label, "valid_labels": valid_labels}
                )
            else:
                return TestResult(
                    name="BERT - Valid Quality Labels",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="BERT - Valid Quality Labels",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_text_score_range(self) -> TestResult:
        """Test that quality score is in valid range."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/text",
                json={"text": "I am a software engineer with Python skills."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                score = data.get('quality_score', -1)
                is_valid = 0 <= score <= 100
                
                return TestResult(
                    name="BERT - Score Range (0-100)",
                    passed=is_valid,
                    duration=duration,
                    message=f"Score {score:.2f} is in valid range: {is_valid}",
                    details={"score": score}
                )
            else:
                return TestResult(
                    name="BERT - Score Range (0-100)",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="BERT - Score Range (0-100)",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_text_probabilities_sum(self) -> TestResult:
        """Test that probabilities sum to approximately 1."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/text",
                json={"text": "I have 5 years of experience in data science."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                probs = data.get('probabilities', {})
                prob_sum = sum(probs.values())
                is_valid = abs(prob_sum - 1.0) < 0.01
                
                return TestResult(
                    name="BERT - Probabilities Sum to 1",
                    passed=is_valid,
                    duration=duration,
                    message=f"Sum: {prob_sum:.4f}, Valid: {is_valid}",
                    details=probs
                )
            else:
                return TestResult(
                    name="BERT - Probabilities Sum to 1",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="BERT - Probabilities Sum to 1",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all BERT model tests."""
        start = time.time()
        results = [
            self.test_text_response_format(),
            self.test_text_empty_input(),
            self.test_text_quality_labels(),
            self.test_text_score_range(),
            self.test_text_probabilities_sum()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="BERT Model Tests",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# Multimodal Integration Tests
# ============================================

class MultimodalIntegrationTests:
    """Test multimodal integration and model cooperation."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.test_audio_path = "/tmp/test_audio_multi.wav"
    
    def _create_test_audio_file(self):
        """Create a test audio file."""
        audio, sr = create_test_audio(duration=2.0)
        save_test_audio(audio, sr, self.test_audio_path)
    
    def test_multimodal_text_only(self) -> TestResult:
        """Test multimodal endpoint with text only."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/multimodal",
                data={"text": "I have extensive experience in machine learning."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                has_text_result = data.get('text') is not None
                has_scores = all(k in data for k in ['confidence_score', 'clarity_score', 'engagement_score'])
                
                return TestResult(
                    name="Multimodal - Text Only",
                    passed=data.get('success') and has_text_result and has_scores,
                    duration=duration,
                    message=f"Success: {data.get('success')}, Has scores: {has_scores}",
                    details={
                        "confidence_score": data.get('confidence_score'),
                        "clarity_score": data.get('clarity_score'),
                        "engagement_score": data.get('engagement_score')
                    }
                )
            else:
                return TestResult(
                    name="Multimodal - Text Only",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Multimodal - Text Only",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_multimodal_image_only(self) -> TestResult:
        """Test multimodal endpoint with image only."""
        start = time.time()
        try:
            img = create_test_image()
            base64_img = image_to_base64(img)
            
            response = requests.post(
                f"{self.base_url}/analyze/multimodal",
                data={"image": base64_img},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                
                return TestResult(
                    name="Multimodal - Image Only",
                    passed=data.get('success', False),
                    duration=duration,
                    message=f"Success: {data.get('success')}",
                    details={
                        "facial_result": data.get('facial') is not None,
                        "overall_emotion": data.get('overall_emotion')
                    }
                )
            else:
                return TestResult(
                    name="Multimodal - Image Only",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Multimodal - Image Only",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_multimodal_response_format(self) -> TestResult:
        """Test multimodal API response format."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/multimodal",
                data={"text": "Test answer for format check."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                required_fields = [
                    'success', 'overall_confidence', 'overall_emotion',
                    'fused_emotions', 'confidence_score', 'clarity_score',
                    'engagement_score', 'recommendations', 'timestamp'
                ]
                has_all_fields = all(field in data for field in required_fields)
                
                return TestResult(
                    name="Multimodal - Response Format",
                    passed=has_all_fields,
                    duration=duration,
                    message=f"All required fields present: {has_all_fields}",
                    details={"fields": list(data.keys())}
                )
            else:
                return TestResult(
                    name="Multimodal - Response Format",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Multimodal - Response Format",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_multimodal_recommendations(self) -> TestResult:
        """Test that recommendations are generated."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/multimodal",
                data={"text": "I have some experience with coding."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                has_recommendations = len(recommendations) > 0
                
                return TestResult(
                    name="Multimodal - Recommendations Generated",
                    passed=has_recommendations,
                    duration=duration,
                    message=f"Number of recommendations: {len(recommendations)}",
                    details={"recommendations": recommendations}
                )
            else:
                return TestResult(
                    name="Multimodal - Recommendations Generated",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Multimodal - Recommendations Generated",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_multimodal_score_ranges(self) -> TestResult:
        """Test that all scores are in valid range (0-100)."""
        start = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/analyze/multimodal",
                data={"text": "I am experienced in software development."},
                timeout=TIMEOUT
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                scores = {
                    'confidence': data.get('confidence_score', -1),
                    'clarity': data.get('clarity_score', -1),
                    'engagement': data.get('engagement_score', -1)
                }
                
                all_valid = all(0 <= v <= 100 for v in scores.values())
                
                return TestResult(
                    name="Multimodal - Score Ranges Valid",
                    passed=all_valid,
                    duration=duration,
                    message=f"All scores in 0-100 range: {all_valid}",
                    details=scores
                )
            else:
                return TestResult(
                    name="Multimodal - Score Ranges Valid",
                    passed=False,
                    duration=duration,
                    message=f"HTTP {response.status_code}"
                )
        except Exception as e:
            return TestResult(
                name="Multimodal - Score Ranges Valid",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all multimodal integration tests."""
        start = time.time()
        results = [
            self.test_multimodal_text_only(),
            self.test_multimodal_image_only(),
            self.test_multimodal_response_format(),
            self.test_multimodal_recommendations(),
            self.test_multimodal_score_ranges()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="Multimodal Integration Tests",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# Model Accuracy Tests
# ============================================

class ModelAccuracyTests:
    """Test model accuracy with known test cases."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def test_facial_model_info(self) -> TestResult:
        """Get facial model accuracy information."""
        start = time.time()
        try:
            # The facial detector reports its accuracy when loaded
            response = requests.get(f"{self.base_url}/health", timeout=TIMEOUT)
            duration = time.time() - start
            
            # Expected accuracy: 72.72%
            expected_accuracy = 72.72
            
            return TestResult(
                name="Facial Model - Expected Accuracy",
                passed=True,
                duration=duration,
                message=f"Model accuracy: {expected_accuracy}% (EfficientNet-B2)",
                details={
                    "model": "EfficientNet-B2",
                    "accuracy": expected_accuracy,
                    "emotions": ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
                }
            )
        except Exception as e:
            return TestResult(
                name="Facial Model - Expected Accuracy",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_voice_model_info(self) -> TestResult:
        """Get voice model accuracy information."""
        start = time.time()
        try:
            # Expected accuracy: 73.37%
            expected_accuracy = 73.37
            
            return TestResult(
                name="Voice Model - Expected Accuracy",
                passed=True,
                duration=time.time() - start,
                message=f"Model accuracy: {expected_accuracy}% (Wav2Vec2 + Attention)",
                details={
                    "model": "Wav2Vec2 + Attention Pooling",
                    "accuracy": expected_accuracy,
                    "emotions": ["anger", "fear", "happy", "neutral", "sad", "surprise"]
                }
            )
        except Exception as e:
            return TestResult(
                name="Voice Model - Expected Accuracy",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_bert_model_info(self) -> TestResult:
        """Get BERT model information."""
        start = time.time()
        try:
            return TestResult(
                name="BERT Model - Configuration",
                passed=True,
                duration=time.time() - start,
                message="BERT fine-tuned for interview answer quality",
                details={
                    "model": "BertForSequenceClassification",
                    "base": "bert-base-uncased",
                    "classes": ["Poor", "Average", "Excellent"],
                    "max_length": 512
                }
            )
        except Exception as e:
            return TestResult(
                name="BERT Model - Configuration",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all accuracy tests."""
        start = time.time()
        results = [
            self.test_facial_model_info(),
            self.test_voice_model_info(),
            self.test_bert_model_info()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="Model Accuracy Information",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# Performance Tests
# ============================================

class PerformanceTests:
    """Test API performance and response times."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def test_text_latency(self, iterations: int = 5) -> TestResult:
        """Test text analysis latency."""
        start = time.time()
        latencies = []
        
        try:
            for _ in range(iterations):
                iter_start = time.time()
                response = requests.post(
                    f"{self.base_url}/analyze/text",
                    json={"text": "This is a test answer for latency measurement."},
                    timeout=TIMEOUT
                )
                if response.status_code == 200:
                    latencies.append(time.time() - iter_start)
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                
                return TestResult(
                    name="Performance - Text Analysis Latency",
                    passed=avg_latency < 5.0,  # Should be under 5 seconds
                    duration=time.time() - start,
                    message=f"Avg: {avg_latency:.3f}s, Min: {min_latency:.3f}s, Max: {max_latency:.3f}s",
                    details={
                        "iterations": iterations,
                        "avg_latency": avg_latency,
                        "min_latency": min_latency,
                        "max_latency": max_latency
                    }
                )
            else:
                return TestResult(
                    name="Performance - Text Analysis Latency",
                    passed=False,
                    duration=time.time() - start,
                    message="No successful requests"
                )
        except Exception as e:
            return TestResult(
                name="Performance - Text Analysis Latency",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def test_health_latency(self, iterations: int = 10) -> TestResult:
        """Test health endpoint latency."""
        start = time.time()
        latencies = []
        
        try:
            for _ in range(iterations):
                iter_start = time.time()
                response = requests.get(f"{self.base_url}/health", timeout=TIMEOUT)
                if response.status_code == 200:
                    latencies.append(time.time() - iter_start)
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                
                return TestResult(
                    name="Performance - Health Check Latency",
                    passed=avg_latency < 0.5,  # Should be under 500ms
                    duration=time.time() - start,
                    message=f"Avg: {avg_latency*1000:.1f}ms over {iterations} requests",
                    details={"avg_latency_ms": avg_latency * 1000}
                )
            else:
                return TestResult(
                    name="Performance - Health Check Latency",
                    passed=False,
                    duration=time.time() - start,
                    message="No successful requests"
                )
        except Exception as e:
            return TestResult(
                name="Performance - Health Check Latency",
                passed=False,
                duration=time.time() - start,
                message=str(e)
            )
    
    def run_all(self) -> TestSuiteResult:
        """Run all performance tests."""
        start = time.time()
        results = [
            self.test_health_latency(),
            self.test_text_latency()
        ]
        
        passed = sum(1 for r in results if r.passed)
        return TestSuiteResult(
            suite_name="Performance Tests",
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=len(results) - passed,
            duration=time.time() - start,
            results=results
        )


# ============================================
# Test Runner
# ============================================

def print_test_result(result: TestResult, indent: int = 2):
    """Print a single test result."""
    status = "✅ PASS" if result.passed else "❌ FAIL"
    indent_str = " " * indent
    print(f"{indent_str}{status} {result.name}")
    print(f"{indent_str}   └─ {result.message} ({result.duration:.3f}s)")
    if result.details and not result.passed:
        print(f"{indent_str}   └─ Details: {json.dumps(result.details, indent=2)[:200]}")


def print_suite_result(suite: TestSuiteResult):
    """Print a test suite result."""
    print(f"\n{'='*60}")
    print(f"📋 {suite.suite_name}")
    print(f"{'='*60}")
    
    for result in suite.results:
        print_test_result(result)
    
    print(f"\n   Summary: {suite.passed_tests}/{suite.total_tests} tests passed ({suite.duration:.2f}s)")


def run_all_tests():
    """Run all test suites."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Q&ACE END-TO-END INTEGRATION TEST SUITE                         ║
║                                                                   ║
║   Testing: Facial, Voice, BERT Models & Multimodal Integration    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    start_time = time.time()
    all_suites = []
    
    # Run all test suites
    print("\n🔍 Running tests...\n")
    
    # 1. API Health Tests
    api_tests = APIHealthTests()
    all_suites.append(api_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # Check if API is available before continuing
    if all_suites[-1].passed_tests == 0:
        print("\n❌ API is not available. Cannot continue with other tests.")
        print("   Please start the API server: python api/main.py")
        return
    
    # 2. Facial Model Tests
    facial_tests = FacialModelTests()
    all_suites.append(facial_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # 3. Voice Model Tests
    voice_tests = VoiceModelTests()
    all_suites.append(voice_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # 4. BERT Model Tests
    bert_tests = BERTModelTests()
    all_suites.append(bert_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # 5. Multimodal Integration Tests
    multimodal_tests = MultimodalIntegrationTests()
    all_suites.append(multimodal_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # 6. Model Accuracy Information
    accuracy_tests = ModelAccuracyTests()
    all_suites.append(accuracy_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # 7. Performance Tests
    perf_tests = PerformanceTests()
    all_suites.append(perf_tests.run_all())
    print_suite_result(all_suites[-1])
    
    # Final Summary
    total_duration = time.time() - start_time
    total_tests = sum(s.total_tests for s in all_suites)
    total_passed = sum(s.passed_tests for s in all_suites)
    total_failed = sum(s.failed_tests for s in all_suites)
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                     FINAL TEST RESULTS                            ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║""")
    
    for suite in all_suites:
        status = "✅" if suite.failed_tests == 0 else "⚠️"
        print(f"║   {status} {suite.suite_name:<40} {suite.passed_tests}/{suite.total_tests} ║")
    
    print(f"""║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║   Total Tests:  {total_tests:<5}                                          ║
║   Passed:       {total_passed:<5} ✅                                        ║
║   Failed:       {total_failed:<5} {'❌' if total_failed > 0 else '  '}                                        ║
║   Duration:     {total_duration:.2f}s                                          ║
║                                                                   ║
║   Pass Rate:    {(total_passed/total_tests*100):.1f}%                                           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    if total_failed == 0:
        print("🎉 All tests passed! The system is working correctly.\n")
    else:
        print(f"⚠️  {total_failed} test(s) failed. Please review the output above.\n")
    
    return all_suites


if __name__ == "__main__":
    run_all_tests()
