"""
Coaching Engine for Q&ACE - Orchestrates the complete coaching pipeline.

This module combines:
- BERT classification (existing)
- Sentence-BERT similarity (new)
- Deterministic diagnosis (new)
- Template-based recommendations (new)
- GenAI phrasing with Gemini (new)

All coaching logic is explainable and reproducible.
"""

import os
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict

# Handle both package and direct import contexts
try:
    # When imported as integrated_system.coaching_engine (local dev or with /app in PYTHONPATH)
    from integrated_system.sentence_bert_service import get_sbert_service, SentenceBertService
    from integrated_system.reference_embeddings import get_reference_cache, ReferenceEmbeddingCache
    from integrated_system.diagnosis_engine import get_diagnosis_engine, DiagnosisEngine, Diagnosis
    from integrated_system.recommendation_templates import get_recommendation_templates, RecommendationTemplates, Recommendation
    from integrated_system.genai_service import get_genai_service, GenAIService
    from integrated_system.bert_score_service import get_bert_score_service, BertScoreService
    from integrated_system.star_analyzer import get_star_analyzer, STARAnalyzer, analyze_star
except ImportError:
    # When imported directly (with /app/integrated_system in PYTHONPATH)
    from sentence_bert_service import get_sbert_service, SentenceBertService
    from reference_embeddings import get_reference_cache, ReferenceEmbeddingCache
    from diagnosis_engine import get_diagnosis_engine, DiagnosisEngine, Diagnosis
    from recommendation_templates import get_recommendation_templates, RecommendationTemplates, Recommendation
    from genai_service import get_genai_service, GenAIService
    from bert_score_service import get_bert_score_service, BertScoreService
    from star_analyzer import get_star_analyzer, STARAnalyzer, analyze_star


@dataclass
class CoachingResult:
    """Complete coaching analysis result."""
    
    # Similarity scores
    sbert_similarities: Dict[str, float]
    closest_tier: str
    excellent_gap: float
    
    # Combined score
    combined_text_score: float
    bert_component: float
    sbert_component: float
    
    # Diagnosis
    content_diagnosis: Dict[str, str]
    voice_diagnosis: Dict[str, str]
    facial_diagnosis: Dict[str, str]
    
    # Recommendations
    content_tip: Dict[str, str]
    voice_tip: Dict[str, str]
    facial_tip: Dict[str, str]
    
    # Human-readable interpretation
    quality_interpretation: str = "On the Right Track"  # Single verdict
    quality_description: str = ""  # User-friendly explanation
    progress_position: float = 50.0  # 0-100 position on Poor→Excellent scale
    improvement_tips: Optional[List[str]] = None  # GenAI-powered tips
    
    # Optional GenAI feedback
    generated_feedback: Optional[str] = None
    
    # NEW: BERTScore (semantic similarity)
    bert_score_f1: float = 0.0  # 0-1 scale, display as percentage
    bert_score_precision: float = 0.0
    bert_score_recall: float = 0.0
    
    # NEW: LLM Judge
    llm_judge_score: int = 5  # 1-10 scale
    llm_judge_rationale: str = ""  # Explanation
    llm_actionable_tips: Optional[List[str]] = None  # Specific tips from LLM
    
    # NEW: STAR Structure Breakdown
    star_breakdown: Optional[Dict[str, float]] = None  # {situation, task, action, result}
    content_relevance: int = 3  # 1-5 rubric
    coherence_score: int = 3  # 1-5 rubric
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CoachingEngine:
    """
    Main coaching engine that orchestrates all coaching components.
    
    Flow:
    1. Compute Sentence-BERT similarity to reference answers
    2. Combine BERT + SBERT for text score
    3. Run deterministic diagnosis
    4. Generate template recommendations
    5. (Optional) Rephrase with GenAI
    """
    
    def __init__(
        self,
        dataset_path: str = None,
        cache_dir: str = None,
        enable_genai: bool = True
    ):
        """
        Initialize the coaching engine.
        
        Args:
            dataset_path: Path to Interview_Dataset.csv
            cache_dir: Directory for embedding cache
            enable_genai: Whether to enable GenAI-enhanced recommendations
        """
        self.sbert_service: Optional[SentenceBertService] = None
        self.reference_cache: Optional[ReferenceEmbeddingCache] = None
        self.diagnosis_engine: DiagnosisEngine = get_diagnosis_engine()
        self.recommendation_templates: RecommendationTemplates = get_recommendation_templates()
        self.genai_service: Optional[GenAIService] = None
        
        self._dataset_path = dataset_path
        self._cache_dir = cache_dir
        self._enable_genai = enable_genai
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize all coaching components.
        
        This should be called at startup to preload models and cache.
        
        Returns:
            True if initialization successful
        """
        try:
            print("🚀 Initializing Coaching Engine...", flush=True)
            
            # Initialize Sentence-BERT service
            self.sbert_service = get_sbert_service()
            
            # Initialize reference cache
            if self._dataset_path:
                self.reference_cache = get_reference_cache(
                    self._dataset_path,
                    self._cache_dir
                )
            else:
                # Try to find dataset automatically
                possible_paths = [
                    os.path.join(os.path.dirname(__file__), "..", "..", "Interview_Dataset.csv"),
                    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Interview_Dataset.csv"),
                    "Interview_Dataset.csv",
                    "c:/22i-2451/Q&Ace/Interview_Dataset.csv"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        print(f"   Found dataset at: {path}", flush=True)
                        self.reference_cache = get_reference_cache(path, self._cache_dir)
                        break
                else:
                    print("⚠️ Dataset not found, reference comparison will be limited", flush=True)
            
            # Load or compute embeddings
            if self.reference_cache:
                self.reference_cache.load_or_compute(self.sbert_service)
            
            # Initialize GenAI service if enabled
            if self._enable_genai:
                try:
                    self.genai_service = get_genai_service()
                    if self.genai_service.is_initialized:
                        print(f"✅ GenAI service initialized (Provider: {self.genai_service.active_provider})", flush=True)
                    else:
                        print("⚠️ GenAI service not available (check API keys/tokens)", flush=True)
                except Exception as e:
                    print(f"⚠️ GenAI initialization failed: {e}", flush=True)
            
            self._initialized = True
            print("✅ Coaching Engine initialized successfully", flush=True)
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Coaching Engine: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False
    
    def compute_combined_text_score(
        self,
        bert_label: str,
        bert_confidence: float,
        bert_probs: Dict[str, float],
        sbert_similarities: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute combined text score using BERT + Sentence-BERT.
        
        Formula: TextScore = 0.7 × BERT_class_score + 0.3 × SBERT_similarity_excellent
        If BERT confidence < 0.6, weights become 0.5/0.5
        
        Args:
            bert_label: BERT classification label
            bert_confidence: BERT confidence score
            bert_probs: BERT probability distribution
            sbert_similarities: Sentence-BERT similarity scores
            
        Returns:
            Dictionary with score components
        """
        # BERT class score (0-100)
        # Weight based on classification
        if bert_label == 'Excellent':
            bert_class_score = 70 + bert_probs.get('Excellent', 0) * 30
        elif bert_label == 'Average':
            bert_class_score = 40 + bert_probs.get('Excellent', 0) * 20 + bert_probs.get('Average', 0) * 10
        else:  # Poor
            bert_class_score = bert_probs.get('Average', 0) * 30 + bert_probs.get('Excellent', 0) * 10
        
        # SBERT similarity to excellent (0-100)
        sbert_score = sbert_similarities.get('excellent', 0.5) * 100
        
        # Adjust weights based on BERT confidence
        if bert_confidence < 0.6:
            bert_weight = 0.5
            sbert_weight = 0.5
        else:
            bert_weight = 0.7
            sbert_weight = 0.3
        
        combined_score = (bert_weight * bert_class_score) + (sbert_weight * sbert_score)
        combined_score = min(100, max(0, combined_score))
        
        return {
            'combined_score': combined_score,
            'bert_component': bert_class_score,
            'sbert_component': sbert_score,
            'bert_weight': bert_weight,
            'sbert_weight': sbert_weight
        }
    
    def compute_interpretation(
        self,
        sbert_similarities: Dict[str, float],
        closest_tier: str
    ) -> Dict[str, Any]:
        """
        Compute human-readable interpretation of SBERT similarity scores.
        
        Args:
            sbert_similarities: Dictionary with poor/average/excellent similarity scores
            closest_tier: Which reference tier the answer is closest to
            
        Returns:
            Dictionary with:
            - quality_interpretation: Single verdict label
            - quality_description: User-friendly explanation
            - progress_position: 0-100 position on Poor→Excellent scale
        """
        excellent_sim = sbert_similarities.get('excellent', 0.5)
        average_sim = sbert_similarities.get('average', 0.5)
        poor_sim = sbert_similarities.get('poor', 0.3)
        
        # Interpretation scale based on similarity to excellent
        if excellent_sim >= 0.80:
            interpretation = "Very Close to Excellent"
            description = "Your answer closely matches top-quality responses. Just minor refinements needed."
        elif excellent_sim >= 0.65:
            interpretation = "Strong, Needs Refinement"
            description = "Good foundation with clear structure. Add more specific examples to elevate it further."
        elif excellent_sim >= 0.50:
            interpretation = "On the Right Track"
            description = "You're covering the basics well. Work on adding depth and concrete examples."
        elif excellent_sim >= 0.35:
            interpretation = "Basic but Incomplete"
            description = "Your answer exists but needs more substance and structured reasoning."
        else:
            interpretation = "Needs Restructuring"
            description = "Consider reorganizing your response using the STAR method for better structure."
        
        # Calculate progress position (0-100)
        # Map: poor → 0-33, average → 33-66, excellent → 66-100
        if closest_tier == 'excellent':
            # Position in excellent zone (66-100)
            progress_position = 66 + (excellent_sim - 0.5) * 68  # Scale 0.5-1.0 to 66-100
        elif closest_tier == 'average':
            # Position in average zone (33-66)
            progress_position = 33 + (average_sim - 0.3) * 47  # Scale 0.3-1.0 to 33-66
        else:
            # Position in poor zone (0-33)
            progress_position = poor_sim * 33  # Scale 0-1.0 to 0-33
        
        progress_position = max(0, min(100, progress_position))
        
        return {
            'quality_interpretation': interpretation,
            'quality_description': description,
            'progress_position': round(progress_position, 1)
        }
    
    def analyze(
        self,
        answer_text: str,
        question_text: str,
        bert_label: str,
        bert_confidence: float,
        bert_probs: Dict[str, float],
        voice_emotion: str = 'neutral',
        voice_confidence: float = 0.5,
        filler_count: int = 0,
        speech_rate: str = 'normal',
        facial_emotion: str = 'neutral',
        facial_confidence: float = 0.5,
        engagement_score: float = 60.0,
        face_detected: bool = True
    ) -> CoachingResult:
        """
        Run complete coaching analysis.
        
        Args:
            answer_text: User's answer text
            question_text: The interview question
            bert_label: BERT classification result
            bert_confidence: BERT confidence score
            bert_probs: BERT probability distribution
            voice_emotion: Detected voice emotion
            voice_confidence: Voice emotion confidence
            filler_count: Number of filler words
            speech_rate: Speech rate classification
            facial_emotion: Detected facial emotion
            facial_confidence: Facial emotion confidence
            engagement_score: Calculated engagement score
            face_detected: Whether face was detected
            
        Returns:
            CoachingResult with all analysis and recommendations
        """
        # ========================================
        # Step 1: Compute Sentence-BERT Similarity
        # ========================================
        sbert_similarities = None
        closest_tier = 'average'
        excellent_gap = 0.0
        
        # Generic answer archetypes for fallback when no cache match
        GENERIC_POOR = "I don't know. I guess I would try my best."
        GENERIC_AVERAGE = "I would approach this task by breaking it down into steps, working with my team, and making sure to meet deadlines."
        GENERIC_EXCELLENT = "I would use the STAR method to structure my approach. First, I'd analyze the situation to understand the context and constraints. Then, identify the specific task and deliverables. For action, I'd create a detailed plan with milestones, delegate appropriately, and maintain clear communication with stakeholders. Finally, I'd measure results against KPIs and document lessons learned for continuous improvement."
        
        if self.reference_cache and self.reference_cache.is_loaded:
            # Try to get cached embeddings first (exact question match)
            cached_embs = self.reference_cache.get_embeddings(question_text)
            
            if cached_embs:
                # Use precomputed embeddings
                result = self.sbert_service.compare_with_cached_embeddings(
                    answer_text,
                    cached_embs.get('poor'),
                    cached_embs.get('average'),
                    cached_embs.get('excellent')
                )
                sbert_similarities = {k: v for k, v in result.items() if k in ['poor', 'average', 'excellent']}
                closest_tier = result.get('closest_tier', 'average')
                excellent_gap = result.get('excellent_gap', 0.0)
            else:
                # Try semantic search for similar question (lower threshold for better matching)
                similar_key = self.reference_cache.find_similar_question(
                    question_text, 
                    self.sbert_service,
                    threshold=0.5  # Lowered from 0.7 for better matching
                )
                
                if similar_key:
                    cached_embs = self.reference_cache._embeddings.get(similar_key)
                    if cached_embs:
                        result = self.sbert_service.compare_with_cached_embeddings(
                            answer_text,
                            cached_embs.get('poor'),
                            cached_embs.get('average'),
                            cached_embs.get('excellent')
                        )
                        sbert_similarities = {k: v for k, v in result.items() if k in ['poor', 'average', 'excellent']}
                        closest_tier = result.get('closest_tier', 'average')
                        excellent_gap = result.get('excellent_gap', 0.0)
        
        # Fallback: Use generic answer archetypes if no cache match found
        if sbert_similarities is None and self.sbert_service:
            result = self.sbert_service.compare_to_references(
                answer_text,
                GENERIC_POOR,
                GENERIC_AVERAGE,
                GENERIC_EXCELLENT
            )
            sbert_similarities = {k: v for k, v in result.items() if k in ['poor', 'average', 'excellent']}
            closest_tier = result.get('closest_tier', 'average')
            excellent_gap = result.get('excellent_gap', 0.0)
        
        # Final fallback if SBERT service unavailable
        if sbert_similarities is None:
            sbert_similarities = {'poor': 0.3, 'average': 0.5, 'excellent': 0.5}
        
        # ========================================
        # Step 2: Compute Combined Text Score
        # ========================================
        score_result = self.compute_combined_text_score(
            bert_label, bert_confidence, bert_probs, sbert_similarities
        )
        
        # ========================================
        # Step 3: Run Deterministic Diagnosis
        # ========================================
        content_diag = self.diagnosis_engine.diagnose_content(
            bert_label=bert_label,
            bert_confidence=bert_confidence,
            bert_probs=bert_probs,
            sbert_similarities=sbert_similarities,
            answer_text=answer_text,
            question_text=question_text
        )
        
        voice_diag = self.diagnosis_engine.diagnose_voice(
            dominant_emotion=voice_emotion,
            confidence=voice_confidence,
            filler_count=filler_count,
            speech_rate=speech_rate
        )
        
        facial_diag = self.diagnosis_engine.diagnose_facial(
            dominant_emotion=facial_emotion,
            confidence=facial_confidence,
            engagement_score=engagement_score,
            face_detected=face_detected
        )
        
        # ========================================
        # Step 4: Generate Recommendations
        # ========================================
        recommendations = self.recommendation_templates.get_all_recommendations(
            content_issue=content_diag.issue,
            content_reason=content_diag.reason,
            voice_issue=voice_diag.issue,
            voice_reason=voice_diag.reason,
            facial_issue=facial_diag.issue,
            facial_reason=facial_diag.reason
        )
        
        tips = self.recommendation_templates.format_as_tips(recommendations)
        
        # ========================================
        # Step 5: Enhance with GenAI (if available)
        # ========================================
        generated_feedback = None
        
        if self.genai_service and self.genai_service.is_initialized:
            try:
                # Enhance content recommendation
                content_context = {
                    'score': score_result['combined_score'],
                    'transcript': answer_text,
                    'question': question_text,
                    'issue': content_diag.issue
                }
                enhanced_content = self.genai_service.enhance_recommendation(
                    'content',
                    tips['content_tip']['what_went_well'],
                    tips['content_tip']['what_to_improve'],
                    content_context
                )
                tips['content_tip']['what_went_well'] = enhanced_content['what_went_well']
                tips['content_tip']['what_to_improve'] = enhanced_content['what_to_improve']
                
                # Enhance voice recommendation
                voice_context = {
                    'score': voice_confidence * 100,
                    'transcript': answer_text,
                    'question': question_text,
                    'issue': voice_diag.issue
                }
                enhanced_voice = self.genai_service.enhance_recommendation(
                    'voice',
                    tips['voice_tip']['what_went_well'],
                    tips['voice_tip']['what_to_improve'],
                    voice_context
                )
                tips['voice_tip']['what_went_well'] = enhanced_voice['what_went_well']
                tips['voice_tip']['what_to_improve'] = enhanced_voice['what_to_improve']
                
                # Enhance facial recommendation
                facial_context = {
                    'score': engagement_score,
                    'transcript': answer_text,
                    'question': question_text,
                    'issue': facial_diag.issue
                }
                enhanced_facial = self.genai_service.enhance_recommendation(
                    'facial',
                    tips['facial_tip']['what_went_well'],
                    tips['facial_tip']['what_to_improve'],
                    facial_context
                )
                tips['facial_tip']['what_went_well'] = enhanced_facial['what_went_well']
                tips['facial_tip']['what_to_improve'] = enhanced_facial['what_to_improve']
                
                # Generate overall summary
                generated_feedback = self.genai_service.generate_coaching_summary(
                    scores={
                        'content': score_result['combined_score'],
                        'voice': voice_confidence * 100,
                        'facial': engagement_score
                    },
                    question=question_text,
                    transcript=answer_text
                )
                
                # Generate improvement tips (GenAI-powered)
                improvement_tips = self.genai_service.generate_improvement_tips(
                    question=question_text,
                    answer=answer_text,
                    similarity_to_excellent=sbert_similarities.get('excellent', 0.5),
                    closest_tier=closest_tier
                )
                
            except Exception as e:
                print(f"⚠️ GenAI enhancement failed, using templates: {e}", flush=True)
                improvement_tips = None
        
        # ========================================
        # Step 6: Compute BERTScore (Semantic Accuracy)
        # ========================================
        bert_score_result = {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
        try:
            bert_score_service = get_bert_score_service()
            # Get reference answer for comparison
            reference_answer = None
            if self.reference_cache and self.reference_cache.is_loaded:
                cached_refs = self.reference_cache.get_references(question_text)
                if cached_refs:
                    reference_answer = cached_refs.get('excellent', '')
            
            if reference_answer:
                bert_score_result = bert_score_service.compute_score(
                    answer_text, 
                    reference_answer
                )
            else:
                # Use generic excellent answer
                bert_score_result = bert_score_service.compute_score(
                    answer_text,
                    GENERIC_EXCELLENT
                )
        except Exception as e:
            print(f"⚠️ BERTScore computation failed: {e}", flush=True)
        
        # ========================================
        # Step 7: STAR Structure Analysis
        # ========================================
        star_result = {
            'star_breakdown': {'situation': 0, 'task': 0, 'action': 0, 'result': 0},
            'content_relevance': 3,
            'coherence_score': 3
        }
        try:
            star_analyzer = get_star_analyzer()
            star_analysis = star_analyzer.analyze(answer_text, question_text)
            star_result = {
                'star_breakdown': {
                    'situation': star_analysis.situation,
                    'task': star_analysis.task,
                    'action': star_analysis.action,
                    'result': star_analysis.result
                },
                'content_relevance': star_analysis.content_relevance,
                'coherence_score': star_analysis.coherence_score
            }
        except Exception as e:
            print(f"⚠️ STAR analysis failed: {e}", flush=True)
        
        # ========================================
        # Step 8: LLM Judge Evaluation
        # ========================================
        llm_judge_result = {
            'score': 5,
            'rationale': '',
            'actionable_tips': []
        }
        if self.genai_service and self.genai_service.is_initialized:
            try:
                reference_answer = None
                if self.reference_cache and self.reference_cache.is_loaded:
                    cached_refs = self.reference_cache.get_references(question_text)
                    if cached_refs:
                        reference_answer = cached_refs.get('excellent', '')
                
                llm_judge_result = self.genai_service.judge_answer_quality(
                    question=question_text,
                    answer=answer_text,
                    reference_answer=reference_answer
                )
            except Exception as e:
                print(f"⚠️ LLM Judge evaluation failed: {e}", flush=True)
        
        # ========================================
        # Step 9: Compute Interpretation
        # ========================================
        interpretation = self.compute_interpretation(sbert_similarities, closest_tier)
        
        # Fallback improvement tips if GenAI unavailable
        if improvement_tips is None:
            excellent_sim = sbert_similarities.get('excellent', 0.5)
            improvement_tips = []
            if excellent_sim < 0.65:
                improvement_tips.append("Add a concrete example from your experience")
            if excellent_sim < 0.55:
                improvement_tips.append("Explain your reasoning more clearly")
            if excellent_sim < 0.45:
                improvement_tips.append("Discuss the impact or results of your actions")
        
        # ========================================
        # Step 10: Create Result
        # ========================================
        return CoachingResult(
            sbert_similarities=sbert_similarities,
            closest_tier=closest_tier,
            excellent_gap=excellent_gap,
            combined_text_score=score_result['combined_score'],
            bert_component=score_result['bert_component'],
            sbert_component=score_result['sbert_component'],
            content_diagnosis={
                'issue': content_diag.issue,
                'description': content_diag.issue_description,
                'reason': content_diag.reason,
                'severity': content_diag.severity
            },
            voice_diagnosis={
                'issue': voice_diag.issue,
                'description': voice_diag.issue_description,
                'reason': voice_diag.reason,
                'severity': voice_diag.severity
            },
            facial_diagnosis={
                'issue': facial_diag.issue,
                'description': facial_diag.issue_description,
                'reason': facial_diag.reason,
                'severity': facial_diag.severity
            },
            content_tip=tips['content_tip'],
            voice_tip=tips['voice_tip'],
            facial_tip=tips['facial_tip'],
            quality_interpretation=interpretation['quality_interpretation'],
            quality_description=interpretation['quality_description'],
            progress_position=interpretation['progress_position'],
            improvement_tips=improvement_tips,
            generated_feedback=generated_feedback,
            # NEW: BERTScore
            bert_score_f1=bert_score_result.get('f1', 0.0),
            bert_score_precision=bert_score_result.get('precision', 0.0),
            bert_score_recall=bert_score_result.get('recall', 0.0),
            # NEW: LLM Judge
            llm_judge_score=llm_judge_result.get('score', 5),
            llm_judge_rationale=llm_judge_result.get('rationale', ''),
            llm_actionable_tips=llm_judge_result.get('actionable_tips', []),
            # NEW: STAR Breakdown
            star_breakdown=star_result.get('star_breakdown'),
            content_relevance=star_result.get('content_relevance', 3),
            coherence_score=star_result.get('coherence_score', 3)
        )


# Global singleton instance
_coaching_engine: Optional[CoachingEngine] = None


def get_coaching_engine(
    dataset_path: str = None,
    cache_dir: str = None
) -> CoachingEngine:
    """
    Get the global coaching engine instance.
    
    Args:
        dataset_path: Path to Interview_Dataset.csv
        cache_dir: Directory for embedding cache
        
    Returns:
        CoachingEngine instance
    """
    global _coaching_engine
    if _coaching_engine is None:
        _coaching_engine = CoachingEngine(dataset_path, cache_dir)
    return _coaching_engine


def initialize_coaching_engine(
    dataset_path: str = None,
    cache_dir: str = None
) -> bool:
    """
    Initialize the coaching engine.
    
    Should be called at application startup.
    
    Returns:
        True if initialization successful
    """
    engine = get_coaching_engine(dataset_path, cache_dir)
    return engine.initialize()
