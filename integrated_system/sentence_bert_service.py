"""
Sentence-BERT Service for Q&ACE Coaching Pipeline.

This module provides semantic similarity scoring using Sentence-BERT.
IMPORTANT: This service is for SIMILARITY ONLY - not for text generation.

Model: all-MiniLM-L6-v2 (fast, lightweight, good quality)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class SentenceBertService:
    """
    Sentence-BERT service for semantic similarity calculations.
    
    Uses lazy loading to minimize startup time and memory usage.
    Only loads the model when first needed.
    """
    
    def __init__(self):
        self._model = None
        self._model_name = 'all-MiniLM-L6-v2'
        
    @property
    def model(self):
        """Lazy load the Sentence-BERT model."""
        if self._model is None:
            print(f"🔄 Loading Sentence-BERT model: {self._model_name}...", flush=True)
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                print(f"✅ Sentence-BERT loaded successfully", flush=True)
            except Exception as e:
                print(f"❌ Failed to load Sentence-BERT: {e}", flush=True)
                raise
        return self._model
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            numpy array of embeddings
        """
        return self.model.encode(texts, convert_to_numpy=True)
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score (0-1)
        """
        embeddings = self.encode([text1, text2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)
    
    def compare_to_references(
        self, 
        user_answer: str, 
        poor_ref: str, 
        avg_ref: str, 
        excellent_ref: str
    ) -> Dict[str, float]:
        """
        Compare user answer to all reference quality tiers.
        
        Args:
            user_answer: The user's answer text
            poor_ref: Poor quality reference answer
            avg_ref: Average quality reference answer
            excellent_ref: Excellent quality reference answer
            
        Returns:
            Dictionary with similarity scores for each tier:
            {
                'poor': float,
                'average': float,
                'excellent': float,
                'closest_tier': str,
                'excellent_gap': float
            }
        """
        # Encode all texts in one batch for efficiency
        all_texts = [user_answer, poor_ref, avg_ref, excellent_ref]
        embeddings = self.encode(all_texts)
        
        user_emb = embeddings[0]
        ref_embs = {
            'poor': embeddings[1],
            'average': embeddings[2],
            'excellent': embeddings[3]
        }
        
        # Compute similarities
        similarities = {}
        for tier, ref_emb in ref_embs.items():
            sim = np.dot(user_emb, ref_emb) / (
                np.linalg.norm(user_emb) * np.linalg.norm(ref_emb)
            )
            similarities[tier] = float(sim)
        
        # Determine closest tier
        closest_tier = max(similarities, key=similarities.get)
        
        # Calculate gap to excellent
        excellent_gap = similarities['excellent'] - max(
            similarities['poor'], 
            similarities['average']
        )
        
        return {
            **similarities,
            'closest_tier': closest_tier,
            'excellent_gap': excellent_gap
        }
    
    def compare_with_cached_embeddings(
        self,
        user_answer: str,
        poor_emb: np.ndarray,
        avg_emb: np.ndarray,
        excellent_emb: np.ndarray
    ) -> Dict[str, float]:
        """
        Compare user answer to precomputed reference embeddings.
        More efficient when reference embeddings are cached.
        
        Args:
            user_answer: The user's answer text
            poor_emb: Precomputed embedding for poor reference
            avg_emb: Precomputed embedding for average reference
            excellent_emb: Precomputed embedding for excellent reference
            
        Returns:
            Dictionary with similarity scores
        """
        user_emb = self.encode([user_answer])[0]
        
        def cosine_sim(a, b):
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        
        similarities = {
            'poor': cosine_sim(user_emb, poor_emb),
            'average': cosine_sim(user_emb, avg_emb),
            'excellent': cosine_sim(user_emb, excellent_emb)
        }
        
        closest_tier = max(similarities, key=similarities.get)
        excellent_gap = similarities['excellent'] - max(
            similarities['poor'],
            similarities['average']
        )
        
        return {
            **similarities,
            'closest_tier': closest_tier,
            'excellent_gap': excellent_gap
        }


# Global singleton instance (lazy loaded)
_sbert_service: Optional[SentenceBertService] = None


def get_sbert_service() -> SentenceBertService:
    """Get the global Sentence-BERT service instance."""
    global _sbert_service
    if _sbert_service is None:
        _sbert_service = SentenceBertService()
    return _sbert_service
