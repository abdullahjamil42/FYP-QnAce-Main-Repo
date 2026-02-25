"""
STAR Structure Analyzer for Q&ACE

Analyzes interview answers for STAR method compliance:
- Situation (20% ideal weight): Context and background
- Task (10% ideal weight): Specific responsibility or challenge
- Action (60% ideal weight): Concrete steps taken
- Result (10% ideal weight): Measurable outcomes

Also computes Content Relevance and Coherence scores.
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class STARAnalysis:
    """Result of STAR structure analysis."""
    # Individual component scores (0-100)
    situation: float
    task: float
    action: float
    result: float
    
    # Overall structure score (0-100)
    overall_score: float
    
    # Rubric scores (1-5)
    content_relevance: int
    coherence_score: int
    
    # Detected elements
    detected_elements: Dict[str, List[str]]
    
    # Feedback
    missing_components: List[str]
    strengths: List[str]


class STARAnalyzer:
    """
    Analyzes interview answers for STAR method structure.
    
    Uses keyword matching, sentence position heuristics, and
    pattern recognition to score each STAR component.
    """
    
    # Keywords and phrases for each STAR component
    SITUATION_KEYWORDS = [
        "when i was", "in my previous", "at my last", "while working",
        "during my time", "in my role as", "at company", "on the team",
        "context", "background", "situation", "scenario", "environment",
        "organization", "department", "project was", "we were facing",
        "the challenge was", "we had a problem", "there was an issue",
        "assigned to", "working on", "back in", "once", "i remember",
        "experience with", "faced with", "dealt with", "handled"
    ]
    
    TASK_KEYWORDS = [
        "my responsibility", "i was tasked", "i was assigned", "my role was",
        "i needed to", "i had to", "my job was", "i was responsible",
        "the goal was", "the objective", "we needed to", "the task was",
        "i was asked to", "my assignment", "the challenge", "the requirement",
        "duty", "mission", "purpose", "target", "deadline", "was required",
        "supposed to", "expected to", "aimed to", "intended to"
    ]
    
    ACTION_KEYWORDS = [
        "i implemented", "i developed", "i created", "i designed",
        "i led", "i managed", "i coordinated", "i analyzed",
        "i built", "i established", "i initiated", "i proposed",
        "i collaborated", "i worked with", "i conducted", "i executed",
        "first i", "then i", "next i", "finally i", "after that i",
        "my approach was", "i decided to", "i took the initiative",
        "i resolved", "i fixed", "i improved", "i optimized",
        "i solved", "i addressed", "i performed", "i organized",
        "i researched", "i programmed", "i coded", "i tested"
    ]
    
    RESULT_KEYWORDS = [
        "as a result", "consequently", "this led to", "the outcome",
        "we achieved", "i achieved", "the result was", "this resulted in",
        "increased by", "decreased by", "improved by", "reduced",
        "saved", "generated", "delivered", "accomplished", "succeeded",
        "percent", "%", "revenue", "efficiency", "productivity",
        "customer satisfaction", "time saved", "cost reduction",
        "on time", "under budget", "successfully", "exceeded",
        "feedback", "impact", "difference", "growth", "saved money",
        "resolved", "finished", "completed"
    ]
    
    # Quantification patterns (for Result detection)
    QUANT_PATTERNS = [
        r'\d+\s*%',                    # Percentages
        r'\$[\d,]+',                   # Dollar amounts
        r'\d+\s*(million|thousand|k)', # Large numbers
        r'\d+\s*(hours|days|weeks|months)', # Time durations
        r'\d+x',                       # Multipliers
        r'increased.*\d+',             # Increase with number
        r'reduced.*\d+',               # Reduction with number
        r'saved.*\d+',                 # Savings with number
    ]
    
    # Ideal STAR distribution
    IDEAL_WEIGHTS = {
        "situation": 0.20,
        "task": 0.10,
        "action": 0.60,
        "result": 0.10
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self.quant_regex = [re.compile(p, re.IGNORECASE) for p in self.QUANT_PATTERNS]
    
    def analyze(
        self, 
        answer_text: str, 
        question_text: Optional[str] = None
    ) -> STARAnalysis:
        """
        Analyze an answer for STAR structure compliance.
        
        Args:
            answer_text: The user's interview answer
            question_text: Optional question for relevance scoring
            
        Returns:
            STARAnalysis with detailed breakdown
        """
        if not answer_text or not answer_text.strip():
            return self._empty_analysis()
        
        answer_lower = answer_text.lower()
        sentences = self._split_sentences(answer_text)
        
        # Detect elements for each component
        detected = {
            "situation": self._detect_component(answer_lower, sentences, self.SITUATION_KEYWORDS, position_weight="start"),
            "task": self._detect_component(answer_lower, sentences, self.TASK_KEYWORDS, position_weight="start"),
            "action": self._detect_component(answer_lower, sentences, self.ACTION_KEYWORDS, position_weight="middle"),
            "result": self._detect_component(answer_lower, sentences, self.RESULT_KEYWORDS, position_weight="end"),
        }
        
        # Calculate scores for each component
        scores = {}
        for component, elements in detected.items():
            scores[component] = self._calculate_component_score(
                elements, 
                len(sentences),
                component,
                answer_text
            )
        
        # Check for quantification in results
        quant_count = self._count_quantification(answer_text)
        if quant_count > 0:
            # Boost result score if quantification present
            scores["result"] = min(100, scores["result"] + (quant_count * 15))
        
        # Calculate overall score (weighted by ideal distribution)
        overall = sum(
            scores[comp] * self.IDEAL_WEIGHTS[comp] 
            for comp in scores
        )
        
        # Calculate relevance and coherence
        content_relevance = self._calculate_relevance(answer_text, question_text)
        coherence = self._calculate_coherence(answer_text, sentences)
        
        # Identify missing components and strengths
        missing = [comp for comp, score in scores.items() if score < 30]
        strengths = [comp for comp, score in scores.items() if score >= 70]
        
        return STARAnalysis(
            situation=scores["situation"],
            task=scores["task"],
            action=scores["action"],
            result=scores["result"],
            overall_score=overall,
            content_relevance=content_relevance,
            coherence_score=coherence,
            detected_elements=detected,
            missing_components=missing,
            strengths=strengths
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _detect_component(
        self, 
        answer_lower: str, 
        sentences: List[str],
        keywords: List[str],
        position_weight: str = "any"
    ) -> List[tuple]:
        """
        Detect keywords/phrases for a STAR component using fuzzy regex matching.
        
        Args:
            answer_lower: Lowercase answer text
            sentences: List of sentences
            keywords: Keywords to look for
            position_weight: Where in the answer to weight ("start", "middle", "end", "any")
            
        Returns:
            List of (keyword, weight) tuples
        """
        detected = []
        
        for keyword in keywords:
            # Create a flexible pattern that allows for punctuation or filler words between words
            parts = keyword.split()
            if len(parts) > 1:
                # Allows for 1-3 non-word characters OR a short filler word between parts
                # e.g. "when i was" matches "when, i was" or "when uh i was"
                pattern = r'\b' + r'\b(?:[\s,.;]+|\s+\w{1,3}\s+)\b'.join(map(re.escape, parts)) + r'\b'
            else:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                
            match = re.search(pattern, answer_lower)
            
            if match:
                position = match.start()
                total_len = len(answer_lower)
                
                relative_pos = position / total_len if total_len > 0 else 0
                
                # Apply position weighting
                weight = 1.0
                if position_weight == "start" and relative_pos <= 0.33:
                    weight = 1.5
                elif position_weight == "middle" and 0.2 <= relative_pos <= 0.8:
                    weight = 1.3
                elif position_weight == "end" and relative_pos >= 0.5:
                    weight = 1.5
                
                detected.append((keyword, weight))
        
        return detected
    
    def _calculate_component_score(
        self, 
        elements: List[tuple], 
        sentence_count: int,
        component: str,
        answer_text: str = ""
    ) -> float:
        """
        Calculate score for a STAR component with word-level fallback.
        """
        base_score = 0.0
        
        if elements:
            # Phrase-based scoring (Primary)
            base_score = min(len(elements) * 20, 60)
            # Position weighting bonus
            position_bonus = sum(weight - 1.0 for _, weight in elements) * 10
            base_score += position_bonus
        else:
            # Fallback: Word-level intersection (if no phrases found)
            # Look for important keywords individually
            keywords = []
            if component == "situation":
                keywords = ["context", "background", "situation", "role", "company", "team"]
            elif component == "task":
                keywords = ["task", "responsibility", "goal", "objective", "challenge"]
            elif component == "action":
                keywords = ["implemented", "developed", "led", "managed", "created", "step", "decided"]
            elif component == "result":
                keywords = ["result", "achieved", "impact", "reduced", "improved", "success"]
            
            answer_words = set(answer_text.lower().split())
            matches = sum(1 for kw in keywords if kw in answer_words)
            if matches >= 2:
                base_score = 30  # Found individual words but no phrases
            elif matches >= 1:
                base_score = 15
        
        # Length appropriateness bonus
        length_bonus = 0
        word_count = len(answer_text.split())
        
        if component == "action":
            if word_count > 60: length_bonus = 30
            elif word_count > 30: length_bonus = 15
        elif word_count > 40:
            length_bonus = 15
        
        total = min(100, base_score + length_bonus)
        
        # Absolute minimum if text is substantial
        if word_count > 50 and total < 20:
            total = 20
            
        return round(total, 1)
    
    def _count_quantification(self, text: str) -> int:
        """Count quantifiable metrics in the text."""
        count = 0
        for pattern in self.quant_regex:
            matches = pattern.findall(text)
            count += len(matches)
        return count
    
    def _calculate_relevance(self, answer: str, question: Optional[str]) -> int:
        """
        Calculate content relevance score (1-5).
        
        Args:
            answer: The answer text
            question: The question being answered
            
        Returns:
            Score from 1-5
        """
        if not question:
            # Without question context, give neutral score
            return 3
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        # Extract key terms from question
        question_words = set(question_lower.split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "tell", "me", "about", "your", "you", "can", "describe", "give", "example"}
        key_terms = question_words - stop_words
        
        # Count how many key terms appear in answer
        matches = sum(1 for term in key_terms if term in answer_lower)
        match_ratio = matches / len(key_terms) if key_terms else 0
        
        # Also check answer length
        word_count = len(answer.split())
        
        if match_ratio >= 0.6 and word_count >= 80:
            return 5
        elif match_ratio >= 0.4 and word_count >= 50:
            return 4
        elif match_ratio >= 0.2 and word_count >= 30:
            return 3
        elif match_ratio > 0 or word_count >= 20:
            return 2
        else:
            return 1
    
    def _calculate_coherence(self, answer: str, sentences: List[str]) -> int:
        """
        Calculate coherence score (1-5) based on structure and flow.
        
        Args:
            answer: The answer text
            sentences: List of sentences
            
        Returns:
            Score from 1-5
        """
        if not sentences:
            return 1
        
        # Factors for coherence:
        # 1. Transition words
        transitions = [
            "first", "then", "next", "after", "finally", "as a result",
            "therefore", "consequently", "however", "additionally",
            "moreover", "furthermore", "in conclusion"
        ]
        transition_count = sum(1 for t in transitions if t in answer.lower())
        
        # 2. Sentence length consistency
        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        
        # 3. Paragraph structure (presence of multiple sentences)
        sentence_count = len(sentences)
        
        score = 2  # Base score
        
        if transition_count >= 3:
            score += 1
        if 10 <= avg_length <= 25:  # Good sentence length
            score += 1
        if sentence_count >= 4:
            score += 1
        
        return min(5, score)
    
    def _empty_analysis(self) -> STARAnalysis:
        """Return empty analysis for invalid input."""
        return STARAnalysis(
            situation=0,
            task=0,
            action=0,
            result=0,
            overall_score=0,
            content_relevance=1,
            coherence_score=1,
            detected_elements={
                "situation": [],
                "task": [],
                "action": [],
                "result": []
            },
            missing_components=["situation", "task", "action", "result"],
            strengths=[]
        )
    
    def get_improvement_suggestions(self, analysis: STARAnalysis) -> List[str]:
        """
        Generate specific improvement suggestions based on analysis.
        
        Args:
            analysis: The STAR analysis result
            
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        if analysis.situation < 50:
            suggestions.append(
                "Add more context about where and when this happened (e.g., 'At my previous company...')"
            )
        
        if analysis.task < 50:
            suggestions.append(
                "Clarify your specific responsibility or the challenge you were facing"
            )
        
        if analysis.action < 50:
            suggestions.append(
                "Describe the specific steps YOU took to address the situation using 'I' statements"
            )
        
        if analysis.result < 50:
            suggestions.append(
                "Include measurable outcomes (e.g., percentages, time saved, revenue impact)"
            )
        
        if analysis.coherence_score <= 2:
            suggestions.append(
                "Use transition words like 'First', 'Then', 'As a result' to improve flow"
            )
        
        if analysis.content_relevance <= 2:
            suggestions.append(
                "Make sure your answer directly addresses the specific question asked"
            )
        
        return suggestions


# ============================================
# Convenience Functions
# ============================================

_star_analyzer: Optional[STARAnalyzer] = None


def get_star_analyzer() -> STARAnalyzer:
    """Get or create the global STARAnalyzer instance."""
    global _star_analyzer
    if _star_analyzer is None:
        _star_analyzer = STARAnalyzer()
    return _star_analyzer


def analyze_star(answer_text: str, question_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to analyze STAR structure.
    
    Args:
        answer_text: The interview answer
        question_text: Optional question for context
        
    Returns:
        Dictionary with STAR breakdown and scores
    """
    analyzer = get_star_analyzer()
    analysis = analyzer.analyze(answer_text, question_text)
    
    return {
        "star_breakdown": {
            "situation": analysis.situation,
            "task": analysis.task,
            "action": analysis.action,
            "result": analysis.result
        },
        "overall_star_score": analysis.overall_score,
        "content_relevance": analysis.content_relevance,
        "coherence_score": analysis.coherence_score,
        "missing_components": analysis.missing_components,
        "strengths": analysis.strengths,
        "suggestions": analyzer.get_improvement_suggestions(analysis)
    }
