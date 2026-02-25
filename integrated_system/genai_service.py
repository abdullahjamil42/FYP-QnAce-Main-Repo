import os
import logging
import json
import requests
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

# Try to import Google's generative AI library
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed. Gemini features limited.")


class GenAIService:
    """
    Unified service for generating personalized coaching recommendations.
    Supports Hugging Face Inference API (primary) and Google Gemini (backup).
    """
    
    def __init__(
        self, 
        hf_token: Optional[str] = None,
        gemini_key: Optional[str] = None,
        prefer_hf: bool = True
    ):
        """
        Initialize the GenAI service.
        """
        self.hf_token = hf_token or os.getenv('HF_API_TOKEN')
        self.gemini_key = gemini_key or os.getenv('GOOGLE_API_KEY')
        self.prefer_hf = prefer_hf
        
        self.hf_model_id = "meta-llama/Meta-Llama-3-8B-Instruct"
        # Correct OpenAI-compatible endpoint for HuggingFace router
        self.hf_api_url = "https://router.huggingface.co/v1/chat/completions"
        
        self.gemini_model = None
        self.is_initialized = False
        self.active_provider = None

        # Try to initialize HF first if preferred
        if self.prefer_hf and self.hf_token:
            if self._test_hf_connectivity():
                self.is_initialized = True
                self.active_provider = "huggingface"
                logger.info(f"✅ GenAI status: Active (Provider: Hugging Face, Model: {self.hf_model_id})")
        
        # Fallback or primary Gemini check
        if not self.is_initialized and GEMINI_AVAILABLE and self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                # Try a list of models to avoid 404
                for m in ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro']:
                    try:
                        self.gemini_model = genai.GenerativeModel(m)
                        self.gemini_model.generate_content("ping", generation_config={'max_output_tokens': 5})
                        self.is_initialized = True
                        self.active_provider = "gemini"
                        logger.info(f"✅ GenAI status: Active (Provider: Gemini, Model: {m})")
                        break
                    except: continue
            except Exception as e:
                logger.warning(f"Gemini initialization failed: {e}")

        if not self.is_initialized:
            logger.warning("⚠️ No GenAI provider initialized. Falling back to templates.")

    def _test_hf_connectivity(self) -> bool:
        """Test if HF API is reachable with the token."""
        try:
            headers = {
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/json"
            }
            # Use OpenAI-compatible chat format
            payload = {
                "model": self.hf_model_id,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }
            response = requests.post(
                self.hf_api_url, 
                headers=headers, 
                json=payload,
                timeout=15
            )
            logger.info(f"HF connectivity test: Status {response.status_code}")
            if response.status_code == 200:
                logger.info("✅ HF connectivity test successful")
                return True
            elif response.status_code == 503:
                logger.info("⏳ HF model is loading (Stat 503)")
                return True  # Model exists, just loading
            else:
                logger.warning(f"HF connectivity test failed: {response.status_code} - {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"HF connectivity test error: {e}")
            return False

    def _call_hf_api(self, prompt: str, max_tokens: int = 250) -> Optional[str]:
        """Call Hugging Face Inference API using OpenAI-compatible format."""
        if not self.hf_token:
            return None
            
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.hf_model_id,
            "messages": [
                {"role": "system", "content": "You are an expert interview coach."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.hf_api_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                # OpenAI format: choices[0].message.content
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0].get('message', {}).get('content', '').strip()
                return None
            elif response.status_code == 503:
                logger.warning("HF Model is currently loading...")
                return None
            else:
                logger.error(f"HF API Error {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"HF API request failed: {e}")
            return None

    def enhance_recommendation(
        self,
        category: str,
        template_well: str,
        template_improve: str,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate personalized feedback using active provider."""
        if not self.is_initialized:
            return {'what_went_well': template_well, 'what_to_improve': template_improve}
            
        prompt = self._build_prompt(category, template_well, template_improve, context)
        
        result_text = None
        if self.active_provider == "huggingface":
            # Wrap for Llama-3 instruction format
            hf_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are an expert interview coach.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            result_text = self._call_hf_api(hf_prompt)
        elif self.active_provider == "gemini" and self.gemini_model:
            try:
                resp = self.gemini_model.generate_content(prompt)
                result_text = resp.text
            except: pass
            
        if not result_text:
            return {'what_went_well': template_well, 'what_to_improve': template_improve}
            
        parsed = self._parse_dual_output(result_text)
        return parsed if parsed else {'what_went_well': template_well, 'what_to_improve': template_improve}

    def generate_coaching_summary(
        self,
        scores: Dict[str, float],
        question: str,
        transcript: str
    ) -> Optional[str]:
        """Generate overall performance summary."""
        if not self.is_initialized:
            return None
            
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        prompt = f"""Provide a 2-sentence interview coaching summary.
Question: {question}
Transcript: {transcript[:400]}
Scores: Content={scores.get('content',0):.0f}, Voice={scores.get('voice',0):.0f}, Facial={scores.get('facial',0):.0f}
Constraint: Be encouraging, highlight one strength and one improvement area. No introduction, just the summary."""

        if self.active_provider == "huggingface":
            hf_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            return self._call_hf_api(hf_prompt, max_tokens=100)
        elif self.active_provider == "gemini" and self.gemini_model:
            try:
                return self.gemini_model.generate_content(prompt).text.strip()
            except: return None
        return None

    def _build_prompt(self, cat: str, well: str, imp: str, ctx: Dict[str, Any]) -> str:
        return f"""Personalize this interview feedback:
Category: {cat}
Issue: {ctx.get('issue', '')}
Question: {ctx.get('question', '')}
Transcript: {ctx.get('transcript', '')[:300]}
Template Well: {well}
Template Improve: {imp}
Output format exactly:
WELL: [personalized version]
IMPROVE: [personalized version]"""

    def _parse_dual_output(self, text: str) -> Optional[Dict[str, str]]:
        try:
            lines = text.strip().split('\n')
            well, imp = None, None
            for l in lines:
                if l.upper().startswith('WELL:'): well = l.split(':', 1)[1].strip()
                if l.upper().startswith('IMPROVE:'): imp = l.split(':', 1)[1].strip()
            if well and imp: return {'what_went_well': well, 'what_to_improve': imp}
            return None
        except: return None

    def generate_improvement_tips(
        self,
        question: str,
        answer: str,
        similarity_to_excellent: float,
        closest_tier: str
    ) -> Optional[List[str]]:
        """
        Generate 2-3 actionable improvement tips using GenAI.
        
        Args:
            question: The interview question
            answer: The user's answer
            similarity_to_excellent: Similarity score to excellent reference (0-1)
            closest_tier: Which quality tier the answer is closest to
            
        Returns:
            List of 2-3 improvement tips, or None if GenAI unavailable
        """
        if not self.is_initialized:
            return None
        
        gap_description = ""
        if similarity_to_excellent >= 0.65:
            gap_description = "The answer is strong but could be more polished."
        elif similarity_to_excellent >= 0.50:
            gap_description = "The answer covers basics but lacks depth and specific examples."
        elif similarity_to_excellent >= 0.35:
            gap_description = "The answer is superficial and needs more structure and detail."
        else:
            gap_description = "The answer needs significant restructuring and more content."
        
        prompt = f"""Analyze this interview answer and provide exactly 2-3 specific, actionable improvement tips.

Question: {question}
Answer: {answer[:500]}
Analysis: {gap_description} Currently closest to a {closest_tier}-quality answer.

Provide tips in this exact format (2-3 tips only):
TIP1: [specific actionable suggestion]
TIP2: [specific actionable suggestion]
TIP3: [specific actionable suggestion]

Focus on: structure, examples, clarity, and impact. Be specific to this answer."""

        result_text = None
        if self.active_provider == "huggingface":
            result_text = self._call_hf_api(prompt, max_tokens=200)
        elif self.active_provider == "gemini" and self.gemini_model:
            try:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={'max_output_tokens': 200, 'temperature': 0.7}
                )
                result_text = response.text
            except Exception as e:
                logger.warning(f"Gemini tips generation failed: {e}")
                return None
        
        if result_text:
            return self._parse_tips(result_text)
        return None
    
    def _parse_tips(self, text: str) -> Optional[List[str]]:
        """Parse TIP1/TIP2/TIP3 format into list of tips."""
        try:
            tips = []
            for line in text.strip().split('\n'):
                line = line.strip()
                for prefix in ['TIP1:', 'TIP2:', 'TIP3:', '1.', '2.', '3.', '-', '•']:
                    if line.upper().startswith(prefix.upper()):
                        tip = line.split(':', 1)[-1].strip() if ':' in line else line[len(prefix):].strip()
                        if tip and len(tip) > 10:
                            tips.append(tip)
                        break
            return tips[:3] if tips else None
        except:
            return None
    
    def judge_answer_quality(
        self,
        question: str,
        answer: str,
        reference_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM as a judge to evaluate answer quality with detailed rationale.
        
        Args:
            question: The interview question
            answer: The user's answer
            reference_answer: Optional ideal answer for comparison
            
        Returns:
            Dictionary with score, rationale, and tips
        """
        if not self.is_initialized:
            return self._fallback_judgment(answer)
        
        prompt = self._build_judge_prompt(question, answer, reference_answer)
        
        result_text = None
        if self.active_provider == "huggingface":
            result_text = self._call_hf_api(prompt, max_tokens=400)
        elif self.active_provider == "gemini" and self.gemini_model:
            try:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={'max_output_tokens': 400, 'temperature': 0.3}
                )
                result_text = response.text
            except Exception as e:
                logger.warning(f"Gemini judge call failed: {e}")
                return self._fallback_judgment(answer)
        
        if result_text:
            parsed = self._parse_judge_response(result_text)
            if parsed:
                return parsed
        
        return self._fallback_judgment(answer)
    
    def _build_judge_prompt(self, question: str, answer: str, reference: Optional[str]) -> str:
        """Build the LLM judge prompt."""
        reference_section = f"\nReference Answer:\n{reference[:500]}\n" if reference else ""
        
        return f"""You are an expert interview coach evaluating a candidate's answer.

Interview Question: {question}

Candidate's Answer:
{answer[:800]}
{reference_section}
Evaluate on a 1-10 scale based on: relevance, STAR method usage, specific examples, professional communication.

Respond in this EXACT format:
SCORE: [1-10]
RATIONALE: [2-3 sentence explanation]
TIP1: [First improvement suggestion]
TIP2: [Second improvement suggestion]
TIP3: [Third improvement suggestion]"""

    def _parse_judge_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM judge response."""
        try:
            lines = text.strip().split('\n')
            score = 5
            rationale = ""
            tips = []
            
            for line in lines:
                line = line.strip()
                if line.upper().startswith('SCORE:'):
                    import re
                    match = re.search(r'\d+', line.split(':', 1)[1])
                    if match:
                        score = min(10, max(1, int(match.group())))
                elif line.upper().startswith('RATIONALE:'):
                    rationale = line.split(':', 1)[1].strip()
                elif line.upper().startswith('TIP'):
                    tip_content = line.split(':', 1)[-1].strip()
                    if tip_content and len(tip_content) > 10:
                        tips.append(tip_content)
            
            return {
                "score": score,
                "rationale": rationale or "Your answer shows effort but could be more structured.",
                "actionable_tips": tips[:3] if tips else [
                    "Use the STAR method to structure your response",
                    "Include specific metrics and outcomes",
                    "Practice delivering with confidence"
                ]
            }
        except Exception as e:
            logger.warning(f"Failed to parse judge response: {e}")
            return None
    
    def _fallback_judgment(self, answer: str) -> Dict[str, Any]:
        """Provide fallback judgment when LLM is unavailable."""
        word_count = len(answer.split()) if answer else 0
        
        if word_count < 30:
            score, rationale = 3, "Your answer is too brief. Professional responses require more detail."
        elif word_count < 80:
            score, rationale = 5, "Covers basics but needs more specific examples and structure."
        elif word_count < 150:
            score, rationale = 7, "Good detail. Consider adding measurable outcomes."
        else:
            score, rationale = 8, "Well-developed response. Focus on impact of achievements."
        
        return {
            "score": score,
            "rationale": rationale,
            "actionable_tips": [
                "Structure using STAR method (Situation, Task, Action, Result)",
                "Include quantifiable metrics (percentages, time saved)",
                "Use 'I' statements to show personal contributions"
            ]
        }

# Global instance switch
_genai_service: Optional[GenAIService] = None

def get_gemini_service() -> GenAIService:
    """Compatibility alias for get_genai_service."""
    return get_genai_service()

def get_genai_service() -> GenAIService:
    global _genai_service
    if _genai_service is None:
        _genai_service = GenAIService()
    return _genai_service

def initialize_genai_service(hf_token=None, gemini_key=None) -> GenAIService:
    global _genai_service
    _genai_service = GenAIService(hf_token, gemini_key)
    return _genai_service
