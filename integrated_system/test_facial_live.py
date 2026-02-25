#!/usr/bin/env python3
"""
Live Facial Emotion Detection Tester
=====================================
This tool lets you test the facial emotion model in real-time
to verify it correctly detects different expressions.

Usage:
    python test_facial_live.py

Controls:
    - Press 'q' to quit
    - Press 's' to save current frame analysis
    - Press 'r' to reset statistics
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from facial_emotion_detector import FacialEmotionDetector

def create_emotion_bar(emotion: str, probability: float, width: int = 200) -> np.ndarray:
    """Create a colored bar for emotion probability."""
    bar_height = 25
    bar = np.zeros((bar_height, width, 3), dtype=np.uint8)
    
    # Color mapping for emotions
    colors = {
        'happy': (0, 255, 0),      # Green
        'neutral': (255, 200, 0),  # Cyan
        'surprise': (0, 255, 255), # Yellow
        'sad': (255, 0, 100),      # Purple
        'fear': (0, 165, 255),     # Orange
        'angry': (0, 0, 255),      # Red
        'disgust': (255, 0, 255),  # Magenta
    }
    
    color = colors.get(emotion.lower(), (128, 128, 128))
    filled_width = int(width * probability)
    
    # Draw filled portion
    cv2.rectangle(bar, (0, 0), (filled_width, bar_height), color, -1)
    # Draw border
    cv2.rectangle(bar, (0, 0), (width-1, bar_height-1), (255, 255, 255), 1)
    
    return bar


def get_score_interpretation(score: float) -> tuple:
    """Get interpretation and color for interview score."""
    if score >= 80:
        return "Excellent", (0, 255, 0)
    elif score >= 70:
        return "Good", (0, 200, 0)
    elif score >= 60:
        return "Average", (0, 255, 255)
    elif score >= 50:
        return "Below Average", (0, 165, 255)
    else:
        return "Poor", (0, 0, 255)


def calculate_interview_score(emotions: dict, confidence: float) -> float:
    """Calculate interview score using the same logic as the app."""
    # Same scoring as in the frontend
    emotion_scores = {
        'happy': 88,
        'neutral': 75,
        'surprise': 60,
        'angry': 60,  # Resting face adjustment
        'sad': 40,
        'fear': 35,
        'disgust': 35,
    }
    
    weighted_score = 0
    total_weight = 0
    
    for emotion, prob in emotions.items():
        if emotion in emotion_scores and prob > 0.01:
            weighted_score += emotion_scores[emotion] * prob
            total_weight += prob
    
    base_score = weighted_score / total_weight if total_weight > 0 else 55
    
    # Confidence bonus
    if confidence > 0.7:
        base_score += 5
    elif confidence < 0.4:
        base_score -= 8
    
    # Happy + neutral bonus
    ideal_mix = emotions.get('happy', 0) + emotions.get('neutral', 0)
    if ideal_mix > 0.6 and confidence > 0.5:
        base_score += 8
    
    return min(95, max(25, base_score))


def main():
    print("=" * 60)
    print("   FACIAL EMOTION MODEL TESTER")
    print("=" * 60)
    print("\nLoading model...")
    
    # Initialize detector
    detector = FacialEmotionDetector()
    print(f"✅ Model loaded!")
    print(f"   Device: {detector.device}")
    print("\nControls:")
    print("  q - Quit")
    print("  s - Save current analysis")
    print("  r - Reset statistics")
    print("-" * 60)
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open webcam")
        return
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Statistics tracking
    stats = {
        'frames_analyzed': 0,
        'faces_detected': 0,
        'emotion_counts': {},
        'avg_confidence': 0,
        'confidence_sum': 0,
    }
    
    print("\n🎥 Webcam started. Look at the camera and try different expressions!")
    print("   Try: 😊 Happy, 😐 Neutral, 😲 Surprised, 😢 Sad, 😨 Fearful, 😠 Angry\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        display = frame.copy()
        
        # Analyze frame
        result = detector.detect_emotions_from_frame(frame)
        stats['frames_analyzed'] += 1
        
        # Create info panel on the right
        panel_width = 350
        panel = np.zeros((frame.shape[0], panel_width, 3), dtype=np.uint8)
        panel[:] = (30, 30, 30)  # Dark gray background
        
        y_offset = 30
        
        # Title
        cv2.putText(panel, "EMOTION ANALYSIS", (10, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_offset += 40
        
        if result['face_detected']:
            stats['faces_detected'] += 1
            stats['confidence_sum'] += result['confidence']
            stats['avg_confidence'] = stats['confidence_sum'] / stats['faces_detected']
            
            # Track emotion counts
            dominant = result['dominant_emotion']
            stats['emotion_counts'][dominant] = stats['emotion_counts'].get(dominant, 0) + 1
            
            # Draw face rectangle on frame
            if 'face_box' in result:
                x, y, w, h = result['face_box']
                cv2.rectangle(display, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Dominant emotion with emoji
            emoji_map = {
                'happy': '😊', 'neutral': '😐', 'surprise': '😲',
                'sad': '😢', 'fear': '😨', 'angry': '😠', 'disgust': '🤢'
            }
            
            cv2.putText(panel, f"Dominant: {dominant.upper()}", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y_offset += 30
            
            cv2.putText(panel, f"Confidence: {result['confidence']*100:.1f}%", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += 35
            
            # Emotion bars
            cv2.putText(panel, "Emotion Probabilities:", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            y_offset += 25
            
            emotions = result['emotions']
            sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
            
            for emotion, prob in sorted_emotions:
                # Emotion name and percentage
                text = f"{emotion}: {prob*100:.1f}%"
                cv2.putText(panel, text, (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                
                # Draw bar
                bar = create_emotion_bar(emotion, prob, 150)
                panel[y_offset+5:y_offset+5+bar.shape[0], 180:180+bar.shape[1]] = bar
                y_offset += 30
            
            y_offset += 20
            
            # Interview Score
            interview_score = calculate_interview_score(emotions, result['confidence'])
            interpretation, color = get_score_interpretation(interview_score)
            
            cv2.putText(panel, "INTERVIEW SCORE:", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 35
            
            cv2.putText(panel, f"{interview_score:.0f}%", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
            cv2.putText(panel, interpretation, (100, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_offset += 50
            
            # Expected score guide
            cv2.putText(panel, "Expected Scores:", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            y_offset += 22
            guides = [
                ("Happy/Smile", "80-90%", (0, 255, 0)),
                ("Neutral/Calm", "70-80%", (0, 200, 200)),
                ("Surprise", "55-65%", (0, 255, 255)),
                ("Sad/Fear", "35-50%", (0, 0, 255)),
            ]
            for label, score_range, guide_color in guides:
                cv2.putText(panel, f"  {label}: {score_range}", (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, guide_color, 1)
                y_offset += 18
            
        else:
            cv2.putText(panel, "No face detected", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 30
            cv2.putText(panel, "Please look at the camera", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Statistics section at bottom
        y_offset = frame.shape[0] - 100
        cv2.line(panel, (10, y_offset), (panel_width-10, y_offset), (100, 100, 100), 1)
        y_offset += 20
        
        cv2.putText(panel, "SESSION STATS:", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        y_offset += 22
        
        detection_rate = (stats['faces_detected'] / max(1, stats['frames_analyzed'])) * 100
        cv2.putText(panel, f"Face Detection: {detection_rate:.0f}%", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y_offset += 18
        
        cv2.putText(panel, f"Avg Confidence: {stats['avg_confidence']*100:.1f}%", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        y_offset += 18
        
        # Most common emotion
        if stats['emotion_counts']:
            most_common = max(stats['emotion_counts'], key=stats['emotion_counts'].get)
            cv2.putText(panel, f"Most Common: {most_common}", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        
        # Combine frame and panel
        combined = np.hstack([display, panel])
        
        # Add instructions at top
        cv2.putText(combined, "Press 'q' to quit | 's' to save | 'r' to reset stats", 
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        cv2.imshow('Facial Emotion Tester', combined)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"emotion_test_{timestamp}.png"
            cv2.imwrite(filename, combined)
            print(f"✅ Saved: {filename}")
            if result['face_detected']:
                print(f"   Emotion: {result['dominant_emotion']} ({result['confidence']*100:.1f}%)")
                print(f"   Interview Score: {calculate_interview_score(result['emotions'], result['confidence']):.0f}%")
        elif key == ord('r'):
            # Reset stats
            stats = {
                'frames_analyzed': 0,
                'faces_detected': 0,
                'emotion_counts': {},
                'avg_confidence': 0,
                'confidence_sum': 0,
            }
            print("🔄 Statistics reset")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Print final stats
    print("\n" + "=" * 60)
    print("FINAL SESSION STATISTICS")
    print("=" * 60)
    print(f"Frames Analyzed: {stats['frames_analyzed']}")
    print(f"Faces Detected: {stats['faces_detected']} ({(stats['faces_detected']/max(1,stats['frames_analyzed'])*100):.1f}%)")
    print(f"Average Confidence: {stats['avg_confidence']*100:.1f}%")
    print("\nEmotion Distribution:")
    total_detections = sum(stats['emotion_counts'].values())
    for emotion, count in sorted(stats['emotion_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / max(1, total_detections)) * 100
        print(f"  {emotion}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
