"""
Deterministic Diagnosis Engine for Q&ACE Coaching Pipeline.

This module provides rule-based diagnosis of weaknesses in interview responses.
All logic is EXPLAINABLE and REPRODUCIBLE - no GenAI involvement here.

The diagnosis engine analyzes:
- Content quality (using BERT + Sentence-BERT)
- Voice delivery (using voice analysis metrics)
- Facial expressions (using facial emotion analysis)
"""

from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class Diagnosis:
    """Represents a diagnosis for a single modality."""
    issue: str
    issue_description: str
    reason: str
    severity: str  # 'low', 'medium', 'high'


class DiagnosisEngine:
    """
    Deterministic diagnosis engine for interview response analysis.
    
    All rules are explicit and explainable.
    No machine learning or generative AI is used for diagnosis.
    """
    
    # ========================================
    # Content Issue Categories
    # ========================================
    CONTENT_ISSUES = {
        'lacks_examples': 'Answer lacks specific examples',
        'poor_structure': 'Answer lacks clear structure (STAR method)',
        'missing_quantification': 'Answer lacks quantifiable metrics',
        'too_brief': 'Answer is too brief to be comprehensive',
        'low_relevance': 'Answer has low relevance to the question',
        'lacks_depth': 'Answer lacks technical depth',
        'off_topic': 'Answer deviates from the question topic',
        'excellent': 'Strong, well-structured response'
    }
    
    # ========================================
    # Voice Issue Categories
    # ========================================
    VOICE_ISSUES = {
        'too_many_fillers': 'Excessive filler words detected',
        'pace_too_fast': 'Speaking pace is too fast',
        'pace_too_slow': 'Speaking pace is too slow',
        'low_confidence_tone': 'Voice tone suggests low confidence',
        'monotone': 'Voice lacks variation (monotone)',
        'unclear_articulation': 'Speech clarity could be improved',
        'excellent': 'Clear, confident vocal delivery'
    }
    
    # ========================================
    # Facial Issue Categories
    # ========================================
    FACIAL_ISSUES = {
        'low_engagement': 'Facial expressions show low engagement',
        'anxiety_detected': 'Facial expressions suggest anxiety',
        'anger_detected': 'Facial expressions suggest tension',
        'no_eye_contact': 'Limited eye contact with camera',
        'flat_affect': 'Limited facial expressiveness',
        'excellent': 'Good facial engagement and expressions'
    }
    
    # ========================================
    # STAR Method Keywords
    # ========================================
    STAR_KEYWORDS = [
        'situation', 'task', 'action', 'result',
        'example', 'for instance', 'specifically',
        'challenge', 'problem', 'solution', 'outcome',
        'achieved', 'accomplished', 'delivered', 'led'
    ]
    
    # ========================================
    # Quantification Indicators
    # ========================================
    QUANTIFICATION_PATTERNS = [
        '%', 'percent', 'increased', 'decreased', 'reduced',
        'saved', 'generated', 'million', 'thousand',
        'team of', 'managed', 'within', 'budget',
        'doubled', 'tripled', 'improved by'
    ]
    
    def __init__(self):
        """Initialize the diagnosis engine."""
        pass
    
    def diagnose_content(
        self,
        bert_label: str,
        bert_confidence: float,
        bert_probs: Dict[str, float],
        sbert_similarities: Dict[str, float],
        answer_text: str,
        question_text: Optional[str] = None
    ) -> Diagnosis:
        """
        Diagnose content issues based on BERT and Sentence-BERT analysis.
        
        Args:
            bert_label: BERT classification ('Poor', 'Average', 'Excellent')
            bert_confidence: BERT confidence score (0-1)
            bert_probs: BERT probabilities for each class
            sbert_similarities: Sentence-BERT similarity scores
            answer_text: The user's answer text
            question_text: The interview question (optional)
            
        Returns:
            Diagnosis object with issue, description, reason, and severity
        """
        answer_lower = answer_text.lower()
        word_count = len(answer_text.split())
        
        # ========================================
        # Rule 1: Too Brief
        # ========================================
        if word_count < 30:
            return Diagnosis(
                issue='too_brief',
                issue_description=self.CONTENT_ISSUES['too_brief'],
                reason=f'Answer has only {word_count} words (recommended: 50+ words for behavioral questions)',
                severity='high'
            )
        
        # ========================================
        # Rule 2: BERT says Poor
        # ========================================
        if bert_label == 'Poor':
            # Check for quantification
            has_numbers = any(char.isdigit() for char in answer_text)
            has_quant_words = any(word in answer_lower for word in self.QUANTIFICATION_PATTERNS)
            
            if not has_numbers and not has_quant_words:
                return Diagnosis(
                    issue='missing_quantification',
                    issue_description=self.CONTENT_ISSUES['missing_quantification'],
                    reason=f'BERT classified as Poor ({bert_confidence*100:.0f}% confidence), no quantifiable metrics found',
                    severity='high'
                )
            
            # Check for STAR structure
            star_count = sum(1 for kw in self.STAR_KEYWORDS if kw in answer_lower)
            if star_count < 2:
                return Diagnosis(
                    issue='lacks_examples',
                    issue_description=self.CONTENT_ISSUES['lacks_examples'],
                    reason=f'BERT classified as Poor, limited STAR method indicators ({star_count} found)',
                    severity='high'
                )
            
            return Diagnosis(
                issue='lacks_depth',
                issue_description=self.CONTENT_ISSUES['lacks_depth'],
                reason=f'BERT classified as Poor ({bert_confidence*100:.0f}% confidence)',
                severity='high'
            )
        
        # ========================================
        # Rule 3: BERT says Average - Check SBERT Gap
        # ========================================
        if bert_label == 'Average':
            excellent_sim = sbert_similarities.get('excellent', 0)
            average_sim = sbert_similarities.get('average', 0)
            excellent_gap = excellent_sim - average_sim
            
            # Check STAR structure
            star_count = sum(1 for kw in self.STAR_KEYWORDS if kw in answer_lower)
            
            if excellent_gap > 0.1 and star_count < 3:
                return Diagnosis(
                    issue='poor_structure',
                    issue_description=self.CONTENT_ISSUES['poor_structure'],
                    reason=f'Similarity gap to Excellent ({excellent_gap:.2f}) suggests structural improvements needed',
                    severity='medium'
                )
            
            if star_count < 2:
                return Diagnosis(
                    issue='lacks_examples',
                    issue_description=self.CONTENT_ISSUES['lacks_examples'],
                    reason=f'BERT classified as Average, limited specific examples detected',
                    severity='medium'
                )
            
            # Check for quantification
            has_numbers = any(char.isdigit() for char in answer_text)
            if not has_numbers:
                return Diagnosis(
                    issue='missing_quantification',
                    issue_description=self.CONTENT_ISSUES['missing_quantification'],
                    reason='Answer is good but lacks quantifiable achievements',
                    severity='low'
                )
        
        # ========================================
        # Rule 4: Low Semantic Similarity
        # ========================================
        excellent_sim = sbert_similarities.get('excellent', 0)
        if excellent_sim < 0.5 and bert_label != 'Excellent':
            return Diagnosis(
                issue='low_relevance',
                issue_description=self.CONTENT_ISSUES['low_relevance'],
                reason=f'Low semantic similarity to excellent reference ({excellent_sim:.2f})',
                severity='medium'
            )
        
        # ========================================
        # Rule 5: Excellent
        # ========================================
        return Diagnosis(
            issue='excellent',
            issue_description=self.CONTENT_ISSUES['excellent'],
            reason=f'Well-structured response with clear examples',
            severity='low'
        )
    
    def diagnose_voice(
        self,
        dominant_emotion: str,
        confidence: float,
        filler_count: int = 0,
        speech_rate: Optional[str] = None,
        emotions: Optional[Dict[str, float]] = None
    ) -> Diagnosis:
        """
        Diagnose voice delivery issues.
        
        Args:
            dominant_emotion: Detected dominant voice emotion
            confidence: Voice emotion confidence (0-1)
            filler_count: Number of filler words detected
            speech_rate: Speech rate classification ('slow', 'normal', 'fast')
            emotions: Full emotion breakdown (optional)
            
        Returns:
            Diagnosis object
        """
        # ========================================
        # Rule 1: Too Many Fillers
        # ========================================
        if filler_count > 5:
            return Diagnosis(
                issue='too_many_fillers',
                issue_description=self.VOICE_ISSUES['too_many_fillers'],
                reason=f'{filler_count} filler words detected (um, uh, like, you know, etc.)',
                severity='high' if filler_count > 10 else 'medium'
            )
        
        # ========================================
        # Rule 2: Pace Issues
        # ========================================
        if speech_rate == 'fast':
            return Diagnosis(
                issue='pace_too_fast',
                issue_description=self.VOICE_ISSUES['pace_too_fast'],
                reason='Speech rate classified as too fast, may indicate nervousness',
                severity='medium'
            )
        
        if speech_rate == 'slow':
            return Diagnosis(
                issue='pace_too_slow',
                issue_description=self.VOICE_ISSUES['pace_too_slow'],
                reason='Speech rate classified as slow, may reduce engagement',
                severity='low'
            )
        
        # ========================================
        # Rule 3: Emotional Tone Issues
        # ========================================
        if dominant_emotion in ['fear', 'sad'] and confidence > 0.3:
            return Diagnosis(
                issue='low_confidence_tone',
                issue_description=self.VOICE_ISSUES['low_confidence_tone'],
                reason=f'Voice emotion detected as {dominant_emotion} ({confidence*100:.0f}% confidence)',
                severity='medium'
            )
        
        # ========================================
        # Rule 4: Moderate Filler Count
        # ========================================
        if filler_count > 2:
            return Diagnosis(
                issue='too_many_fillers',
                issue_description=self.VOICE_ISSUES['too_many_fillers'],
                reason=f'{filler_count} filler words detected - minor improvement opportunity',
                severity='low'
            )
        
        # ========================================
        # Rule 5: Excellent
        # ========================================
        return Diagnosis(
            issue='excellent',
            issue_description=self.VOICE_ISSUES['excellent'],
            reason='Clear vocal delivery with good pace and minimal fillers',
            severity='low'
        )
    
    def diagnose_facial(
        self,
        dominant_emotion: str,
        confidence: float,
        engagement_score: float,
        face_detected: bool = True,
        emotions: Optional[Dict[str, float]] = None
    ) -> Diagnosis:
        """
        Diagnose facial expression and non-verbal communication issues.
        
        Args:
            dominant_emotion: Detected dominant facial emotion
            confidence: Facial emotion confidence (0-1)
            engagement_score: Calculated engagement score (0-100)
            face_detected: Whether a face was detected
            emotions: Full emotion breakdown (optional)
            
        Returns:
            Diagnosis object
        """
        # ========================================
        # Rule 0: No Face Detected
        # ========================================
        if not face_detected:
            return Diagnosis(
                issue='no_eye_contact',
                issue_description=self.FACIAL_ISSUES['no_eye_contact'],
                reason='Face not consistently detected - ensure good lighting and camera position',
                severity='high'
            )
        
        # ========================================
        # Rule 1: Low Engagement
        # ========================================
        if engagement_score < 40:
            return Diagnosis(
                issue='low_engagement',
                issue_description=self.FACIAL_ISSUES['low_engagement'],
                reason=f'Engagement score is {engagement_score:.0f}% (threshold: 50%)',
                severity='high'
            )
        
        if engagement_score < 50:
            return Diagnosis(
                issue='low_engagement',
                issue_description=self.FACIAL_ISSUES['low_engagement'],
                reason=f'Engagement score is {engagement_score:.0f}% (threshold: 50%)',
                severity='medium'
            )
        
        # ========================================
        # Rule 2: Anxiety Detected
        # ========================================
        if dominant_emotion == 'fear' and confidence > 0.3:
            return Diagnosis(
                issue='anxiety_detected',
                issue_description=self.FACIAL_ISSUES['anxiety_detected'],
                reason=f'Fear/anxiety detected at {confidence*100:.0f}% confidence',
                severity='medium'
            )
        
        # ========================================
        # Rule 3: Tension/Anger Detected
        # ========================================
        if dominant_emotion in ['angry', 'anger'] and confidence > 0.3:
            return Diagnosis(
                issue='anger_detected',
                issue_description=self.FACIAL_ISSUES['anger_detected'],
                reason=f'Tension/anger detected at {confidence*100:.0f}% confidence - may appear as intensity',
                severity='medium'
            )
        
        # ========================================
        # Rule 4: Flat Affect
        # ========================================
        if dominant_emotion == 'neutral' and confidence > 0.7:
            return Diagnosis(
                issue='flat_affect',
                issue_description=self.FACIAL_ISSUES['flat_affect'],
                reason='Predominantly neutral expression - consider showing more enthusiasm',
                severity='low'
            )
        
        # ========================================
        # Rule 5: Excellent
        # ========================================
        return Diagnosis(
            issue='excellent',
            issue_description=self.FACIAL_ISSUES['excellent'],
            reason=f'Good facial engagement with appropriate expressions',
            severity='low'
        )
    
    def diagnose_all(
        self,
        content_data: Dict,
        voice_data: Dict,
        facial_data: Dict
    ) -> Dict[str, Diagnosis]:
        """
        Run all diagnoses and return combined results.
        
        Args:
            content_data: Dictionary with content analysis parameters
            voice_data: Dictionary with voice analysis parameters
            facial_data: Dictionary with facial analysis parameters
            
        Returns:
            Dictionary with 'content', 'voice', 'facial' diagnoses
        """
        return {
            'content': self.diagnose_content(**content_data),
            'voice': self.diagnose_voice(**voice_data),
            'facial': self.diagnose_facial(**facial_data)
        }


# Global singleton instance
_diagnosis_engine: Optional[DiagnosisEngine] = None


def get_diagnosis_engine() -> DiagnosisEngine:
    """Get the global diagnosis engine instance."""
    global _diagnosis_engine
    if _diagnosis_engine is None:
        _diagnosis_engine = DiagnosisEngine()
    return _diagnosis_engine
