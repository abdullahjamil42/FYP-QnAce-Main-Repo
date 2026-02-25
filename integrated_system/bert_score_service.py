"""
BERTScore Service for Q&ACE

Calculates semantic similarity using BERTScore (based on contextual embeddings)
for more accurate answer evaluation than surface-level matching.

BERTScore leverages BERT/RoBERTa/DeBERTa models to compute token-level similarity
and produces Precision, Recall, and F1 scores.
"""

import os
import logging
from typing import Dict, Optional, Tuple
import torch

logger = logging.getLogger(__name__)

# Lazy import to avoid loading heavy dependencies at startup
_bert_score_module = None
_scorer = None


def _get_bert_score():
    """Lazy load bert_score module."""
    global _bert_score_module
    if _bert_score_module is None:
        try:
            import bert_score
            _bert_score_module = bert_score
            logger.info("✅ bert_score library loaded successfully")
        except ImportError:
            logger.error("❌ bert_score not installed. Run: pip install bert-score")
            raise ImportError("bert_score library required. Install via: pip install bert-score")
    return _bert_score_module


class BertScoreService:
    """
    Service for computing BERTScore between candidate and reference answers.
    
    BERTScore uses contextual embeddings to compute similarity, making it
    more robust to paraphrasing and synonym usage than exact matching.
    """
    
    # Model options (smaller to larger):
    # - "roberta-large" (default, good balance)
    # - "microsoft/deberta-xlarge-mnli" (highest accuracy, larger)
    # - "distilbert-base-uncased" (fastest, lower accuracy)
    DEFAULT_MODEL = "roberta-large"
    
    def __init__(self, model_type: Optional[str] = None):
        """
        Initialize BERTScore service.
        
        Args:
            model_type: BERT model to use. Defaults to roberta-large.
        """
        self.model_type = model_type or os.getenv("BERTSCORE_MODEL", self.DEFAULT_MODEL)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialized = False
        self._cache: Dict[Tuple[str, str], Dict[str, float]] = {}
        
        logger.info(f"BertScoreService configured with model: {self.model_type}, device: {self.device}")
    
    def _ensure_initialized(self):
        """Ensure the scorer is loaded (lazy initialization)."""
        if not self._initialized:
            _get_bert_score()  # This will raise if not installed
            self._initialized = True
            logger.info(f"✅ BertScoreService initialized with {self.model_type}")
    
    def compute_score(
        self, 
        candidate: str, 
        reference: str,
        use_cache: bool = True
    ) -> Dict[str, float]:
        """
        Compute BERTScore between candidate answer and reference answer.
        
        Args:
            candidate: The user's answer
            reference: The reference (ideal) answer
            use_cache: Whether to use cached results for repeated queries
            
        Returns:
            Dictionary with 'precision', 'recall', 'f1' scores (0-1 scale)
        """
        self._ensure_initialized()
        
        # Check cache
        cache_key = (candidate.strip().lower(), reference.strip().lower())
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Handle edge cases
        if not candidate or not candidate.strip():
            result = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
            return result
        
        if not reference or not reference.strip():
            # No reference to compare against
            result = {"precision": 0.5, "recall": 0.5, "f1": 0.5}
            return result
        
        try:
            bert_score = _get_bert_score()
            
            # Compute BERTScore
            P, R, F1 = bert_score.score(
                cands=[candidate],
                refs=[reference],
                lang="en",
                model_type=self.model_type,
                device=self.device,
                verbose=False
            )
            
            result = {
                "precision": float(P[0]),
                "recall": float(R[0]),
                "f1": float(F1[0])
            }
            
            # Cache the result
            if use_cache:
                self._cache[cache_key] = result
            
            logger.debug(f"BERTScore computed: P={result['precision']:.3f}, R={result['recall']:.3f}, F1={result['f1']:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"BERTScore computation failed: {e}")
            # Return neutral scores on error
            return {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    
    def compute_f1(self, candidate: str, reference: str) -> float:
        """
        Convenience method to get just the F1 score.
        
        Args:
            candidate: The user's answer
            reference: The reference answer
            
        Returns:
            F1 score between 0 and 1
        """
        result = self.compute_score(candidate, reference)
        return result["f1"]
    
    def compute_batch(
        self, 
        candidates: list, 
        references: list
    ) -> list:
        """
        Compute BERTScore for multiple candidate-reference pairs.
        
        Args:
            candidates: List of candidate answers
            references: List of reference answers (same length as candidates)
            
        Returns:
            List of score dictionaries
        """
        self._ensure_initialized()
        
        if len(candidates) != len(references):
            raise ValueError("candidates and references must have same length")
        
        if not candidates:
            return []
        
        try:
            bert_score = _get_bert_score()
            
            P, R, F1 = bert_score.score(
                cands=candidates,
                refs=references,
                lang="en",
                model_type=self.model_type,
                device=self.device,
                verbose=False
            )
            
            results = []
            for i in range(len(candidates)):
                results.append({
                    "precision": float(P[i]),
                    "recall": float(R[i]),
                    "f1": float(F1[i])
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Batch BERTScore computation failed: {e}")
            return [{"precision": 0.5, "recall": 0.5, "f1": 0.5} for _ in candidates]
    
    def interpret_f1(self, f1_score: float) -> Dict[str, str]:
        """
        Provide human-readable interpretation of F1 score.
        
        Args:
            f1_score: F1 score between 0 and 1
            
        Returns:
            Dictionary with 'label' and 'description'
        """
        if f1_score >= 0.90:
            return {
                "label": "Excellent",
                "description": "Your answer closely matches the ideal response in meaning and depth."
            }
        elif f1_score >= 0.80:
            return {
                "label": "Very Good",
                "description": "Strong semantic alignment with minor gaps in detail or phrasing."
            }
        elif f1_score >= 0.70:
            return {
                "label": "Good",
                "description": "Solid response with room for more specific examples or depth."
            }
        elif f1_score >= 0.60:
            return {
                "label": "Fair",
                "description": "Covers the basics but missing key details or structure."
            }
        elif f1_score >= 0.50:
            return {
                "label": "Needs Improvement",
                "description": "Significant gaps in content or relevance to the question."
            }
        else:
            return {
                "label": "Poor",
                "description": "Answer does not adequately address the question requirements."
            }
    
    def clear_cache(self):
        """Clear the score cache."""
        self._cache.clear()
        logger.debug("BERTScore cache cleared")


# ============================================
# Global Singleton Pattern
# ============================================

_bert_score_service: Optional[BertScoreService] = None


def get_bert_score_service() -> BertScoreService:
    """Get or create the global BertScoreService instance."""
    global _bert_score_service
    if _bert_score_service is None:
        _bert_score_service = BertScoreService()
    return _bert_score_service


def initialize_bert_score_service(model_type: Optional[str] = None) -> BertScoreService:
    """Initialize the global BertScoreService with custom settings."""
    global _bert_score_service
    _bert_score_service = BertScoreService(model_type=model_type)
    return _bert_score_service
