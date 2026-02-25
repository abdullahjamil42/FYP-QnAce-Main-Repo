#!/usr/bin/env python3
"""
Test script to verify Hugging Face facial emotion detector integration.
"""

import sys
from pathlib import Path
import numpy as np
import cv2

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_hf_facial_detector():
    """Test the Hugging Face facial emotion detector."""
    print("🧪 Testing Hugging Face Facial Emotion Detector...")
    
    try:
        from hf_facial_emotion_detector import HuggingFaceEmotionDetector
        
        print("📦 Creating detector...")
        detector = HuggingFaceEmotionDetector()
        
        print("🖼️ Testing with dummy image...")
        # Create a dummy image (simulate a face)
        dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Add a simple rectangle to simulate a face
        cv2.rectangle(dummy_image, (200, 100), (400, 300), (150, 150, 150), -1)
        cv2.circle(dummy_image, (250, 180), 10, (0, 0, 0), -1)  # Left eye
        cv2.circle(dummy_image, (350, 180), 10, (0, 0, 0), -1)  # Right eye
        cv2.ellipse(dummy_image, (300, 220), (30, 15), 0, 0, 180, (0, 0, 0), 2)  # Mouth
        
        results = detector.detect_emotions(dummy_image)
        
        if results:
            print(f"✅ Detection successful! Found {len(results)} face(s)")
            for i, result in enumerate(results):
                emotions = result['emotions']
                dominant = max(emotions, key=emotions.get)
                confidence = emotions[dominant]
                
                print(f"Face {i+1}:")
                print(f"  Dominant emotion: {dominant}")
                print(f"  Confidence: {confidence:.3f}")
                print(f"  All emotions: {emotions}")
        else:
            print("⚠️ No faces detected (expected with dummy image)")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_facial_emotion_wrapper():
    """Test the facial emotion detector wrapper."""
    print("\n🧪 Testing Facial Emotion Detector Wrapper...")
    
    try:
        from facial_emotion_detector import FacialEmotionDetector
        
        print("📦 Creating wrapped detector...")
        detector = FacialEmotionDetector()
        
        print("🖼️ Testing detect_emotions_from_frame...")
        # Create a dummy image
        dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = detector.detect_emotions_from_frame(dummy_image)
        
        print(f"✅ Wrapper test successful!")
        print(f"  Face detected: {result['face_detected']}")
        print(f"  Dominant emotion: {result['dominant_emotion']}")
        print(f"  Confidence: {result['confidence']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Wrapper test failed: {e}")
        return False

def test_multimodal_integration():
    """Test the multimodal detector integration."""
    print("\n🧪 Testing Multimodal Detector Integration...")
    
    try:
        from multimodal_detector import MultimodalEmotionDetector
        
        print("📦 Creating multimodal detector...")
        detector = MultimodalEmotionDetector()
        
        if detector.facial_detector is not None:
            print("✅ Facial detector loaded successfully in multimodal system!")
        else:
            print("❌ Facial detector failed to load in multimodal system!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Multimodal integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Q&ACE Hugging Face Integration Test")
    print("=" * 50)
    
    # Run tests
    test1 = test_hf_facial_detector()
    test2 = test_facial_emotion_wrapper()
    test3 = test_multimodal_integration()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"✅ HF Facial Detector: {'PASS' if test1 else 'FAIL'}")
    print(f"✅ Facial Wrapper: {'PASS' if test2 else 'FAIL'}")
    print(f"✅ Multimodal Integration: {'PASS' if test3 else 'FAIL'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 All tests passed! Integration successful!")
        print("🔗 Model source: https://huggingface.co/abdullahjamil42/QnAce-Face-Model")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)