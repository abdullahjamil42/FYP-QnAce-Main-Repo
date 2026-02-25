"""
Reference Embeddings Cache for Q&ACE Coaching Pipeline.

This module manages precomputed embeddings for reference answers.
Reference answers come from Interview_Dataset.csv with Poor/Average/Excellent tiers.

Embeddings are cached to disk to avoid recomputation on restart.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple


class ReferenceEmbeddingCache:
    """
    Cache for precomputed reference answer embeddings.
    
    Structure:
    - For each unique question, stores:
        - Reference texts (Poor, Average, Excellent)
        - Precomputed embeddings for each
    
    Cache is persisted to disk as:
    - reference_embeddings.npz (numpy arrays)
    - reference_texts.json (text data and metadata)
    """
    
    def __init__(
        self, 
        dataset_path: str,
        cache_dir: str = None
    ):
        """
        Initialize the reference embedding cache.
        
        Args:
            dataset_path: Path to Interview_Dataset.csv
            cache_dir: Directory to store cache files (default: ./embeddings_cache)
        """
        self.dataset_path = dataset_path
        
        if cache_dir is None:
            # Default to a cache directory next to the dataset
            cache_dir = os.path.join(
                os.path.dirname(dataset_path) or ".",
                "embeddings_cache"
            )
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self._embeddings: Dict[str, Dict[str, np.ndarray]] = {}
        self._references: Dict[str, Dict[str, str]] = {}
        self._question_index: Dict[str, str] = {}  # normalized_question -> question_key
        
        self._loaded = False
        
    def _normalize_question(self, question: str) -> str:
        """Normalize question text for consistent lookup."""
        return question.strip().lower()
    
    def _question_key(self, question: str) -> str:
        """Generate a unique key for a question."""
        normalized = self._normalize_question(question)
        # Use first 100 chars + hash for uniqueness
        short = normalized[:100]
        hash_suffix = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"{short}_{hash_suffix}"
    
    def load_or_compute(self, sbert_service) -> int:
        """
        Load embeddings from cache or compute them.
        
        Args:
            sbert_service: SentenceBertService instance for computing embeddings
            
        Returns:
            Number of questions with cached embeddings
        """
        cache_embeddings_path = self.cache_dir / "reference_embeddings.npz"
        cache_texts_path = self.cache_dir / "reference_texts.json"
        
        # Check if cache exists and is valid
        if cache_embeddings_path.exists() and cache_texts_path.exists():
            try:
                print("📂 Loading cached reference embeddings...", flush=True)
                
                # Load texts
                with open(cache_texts_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self._references = cache_data.get('references', {})
                    self._question_index = cache_data.get('index', {})
                
                # Load embeddings
                npz_data = np.load(cache_embeddings_path, allow_pickle=True)
                for key in npz_data.files:
                    # Each key is question_key, value is dict with poor/avg/excellent embeddings
                    self._embeddings[key] = npz_data[key].item()
                
                self._loaded = True
                print(f"✅ Loaded {len(self._references)} cached reference embeddings", flush=True)
                return len(self._references)
                
            except Exception as e:
                print(f"⚠️ Cache corrupted, recomputing: {e}", flush=True)
        
        # Compute embeddings from dataset
        return self._compute_all(sbert_service)
    
    def _compute_all(self, sbert_service) -> int:
        """
        Compute embeddings for all reference answers in the dataset.
        
        Args:
            sbert_service: SentenceBertService instance
            
        Returns:
            Number of questions processed
        """
        print(f"🔄 Computing reference embeddings from {self.dataset_path}...", flush=True)
        
        # Load dataset
        df = pd.read_csv(self.dataset_path)
        print(f"   Loaded {len(df)} rows from dataset", flush=True)
        
        # Group by question
        questions = df['question'].unique()
        print(f"   Found {len(questions)} unique questions", flush=True)
        
        processed = 0
        skipped = 0
        
        for i, question in enumerate(questions):
            if i % 100 == 0:
                print(f"   Processing question {i+1}/{len(questions)}...", flush=True)
            
            q_data = df[df['question'] == question]
            
            # Get reference answers for each tier
            refs = {}
            for label, tier_name in [(0, 'poor'), (1, 'average'), (2, 'excellent')]:
                tier_data = q_data[q_data['label'] == label]
                if len(tier_data) > 0:
                    # Take the first answer for this tier
                    refs[tier_name] = tier_data['answer'].iloc[0]
                else:
                    refs[tier_name] = ""
            
            # Skip if we don't have at least excellent reference
            if not refs.get('excellent'):
                skipped += 1
                continue
            
            # Generate key and store references
            q_key = self._question_key(question)
            self._references[q_key] = refs
            self._question_index[self._normalize_question(question)] = q_key
            
            # Compute embeddings
            texts_to_encode = [
                refs.get('poor', ''),
                refs.get('average', ''),
                refs.get('excellent', '')
            ]
            
            # Filter out empty texts
            valid_texts = [t for t in texts_to_encode if t]
            if not valid_texts:
                skipped += 1
                continue
                
            try:
                embeddings = sbert_service.encode(texts_to_encode)
                self._embeddings[q_key] = {
                    'poor': embeddings[0],
                    'average': embeddings[1],
                    'excellent': embeddings[2]
                }
                processed += 1
            except Exception as e:
                print(f"⚠️ Failed to encode question {i}: {e}", flush=True)
                skipped += 1
        
        print(f"✅ Computed embeddings for {processed} questions ({skipped} skipped)", flush=True)
        
        # Save cache
        self._save_cache()
        self._loaded = True
        
        return processed
    
    def _save_cache(self):
        """Save embeddings and texts to disk."""
        print("💾 Saving reference embeddings cache...", flush=True)
        
        # Save texts and index
        cache_data = {
            'references': self._references,
            'index': self._question_index
        }
        with open(self.cache_dir / "reference_texts.json", 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
        
        # Save embeddings
        np.savez_compressed(
            self.cache_dir / "reference_embeddings.npz",
            **{k: v for k, v in self._embeddings.items()}
        )
        
        print(f"✅ Cache saved to {self.cache_dir}", flush=True)
    
    def get_references(self, question: str) -> Optional[Dict[str, str]]:
        """
        Get reference texts for a question.
        
        Args:
            question: The interview question text
            
        Returns:
            Dictionary with poor/average/excellent reference texts, or None if not found
        """
        if not self._loaded:
            print("⚠️ Reference cache not loaded!", flush=True)
            return None
        
        normalized = self._normalize_question(question)
        q_key = self._question_index.get(normalized)
        
        if q_key:
            return self._references.get(q_key)
        
        # Try fuzzy match by key generation
        q_key = self._question_key(question)
        return self._references.get(q_key)
    
    def get_embeddings(self, question: str) -> Optional[Dict[str, np.ndarray]]:
        """
        Get precomputed embeddings for a question.
        
        Args:
            question: The interview question text
            
        Returns:
            Dictionary with poor/average/excellent embeddings, or None if not found
        """
        if not self._loaded:
            print("⚠️ Reference cache not loaded!", flush=True)
            return None
        
        normalized = self._normalize_question(question)
        q_key = self._question_index.get(normalized)
        
        if q_key:
            return self._embeddings.get(q_key)
        
        # Try fuzzy match by key generation
        q_key = self._question_key(question)
        return self._embeddings.get(q_key)
    
    def find_similar_question(self, question: str, sbert_service, threshold: float = 0.8) -> Optional[str]:
        """
        Find a similar question in the cache using semantic similarity.
        
        Args:
            question: The question to find
            sbert_service: SentenceBertService instance
            threshold: Minimum similarity threshold
            
        Returns:
            The matching question key, or None if no match above threshold
        """
        if not self._loaded or not self._references:
            return None
        
        # Encode the query question
        query_emb = sbert_service.encode([question])[0]
        
        best_match = None
        best_score = 0
        
        # Compare against all stored questions
        for normalized_q, q_key in self._question_index.items():
            # Get the excellent embedding as representative
            embs = self._embeddings.get(q_key)
            if embs is None:
                continue
            
            # Use excellent embedding as representative of the question
            excellent_emb = embs.get('excellent')
            if excellent_emb is None:
                continue
            
            # Compute similarity
            similarity = np.dot(query_emb, excellent_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(excellent_emb)
            )
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = q_key
        
        return best_match
    
    @property
    def is_loaded(self) -> bool:
        """Check if cache is loaded."""
        return self._loaded
    
    @property
    def question_count(self) -> int:
        """Get number of cached questions."""
        return len(self._references)


# Global singleton instance
_reference_cache: Optional[ReferenceEmbeddingCache] = None


def get_reference_cache(
    dataset_path: str = None,
    cache_dir: str = None
) -> ReferenceEmbeddingCache:
    """
    Get the global reference embedding cache instance.
    
    Args:
        dataset_path: Path to Interview_Dataset.csv
        cache_dir: Optional cache directory
        
    Returns:
        ReferenceEmbeddingCache instance
    """
    global _reference_cache
    
    if _reference_cache is None:
        if dataset_path is None:
            # Default path
            dataset_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "..", "..", "Interview_Dataset.csv"
            )
        _reference_cache = ReferenceEmbeddingCache(dataset_path, cache_dir)
    
    return _reference_cache
