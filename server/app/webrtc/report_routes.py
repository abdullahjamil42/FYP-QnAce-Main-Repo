import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Body

from ..config import get_settings
from ..intelligence.llm import LLMProviderConfig, resolve_provider_config, stream_llm

logger = logging.getLogger("qace.report")
report_router = APIRouter()

@report_router.post("/{session_id}/coaching")
async def get_coaching_report(session_id: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    settings = get_settings()
    provider = resolve_provider_config(settings)
    if not provider:
        return {"error": "LLM Provider not configured"}

    transcripts = payload.get("transcripts", [])
    scores = payload.get("scores", {})
    stress_level = payload.get("stress_level", "none")
    mode = payload.get("mode", "software_engineer")

    # Construct prompt
    system_prompt = (
        "You are an expert technical interview coach. Given the transcripts and scores of a candidate's interview, "
        "provide structured coaching feedback in JSON format. Schema: "
        '{"general_tip": str, "stress_tip": str, "cv_tip": str}'
    )

    t_str = "\n".join([f"Candidate [{t.get('inference_ms', 0)}ms]: {t.get('text', '')}" for t in transcripts[-10:]])
    prompt_text = (
        f"Mode: {mode}\nStress Level: {stress_level}\n"
        f"Final Score: {scores.get('final', 0)}\n\n"
        f"Recent Transcripts:\n{t_str}\n\n"
        "Generate short, actionable coaching tips."
    )

    try:
        model = getattr(settings, "interviewer_generator_model", provider.model)
        cfg = LLMProviderConfig(provider=provider.provider, api_key=provider.api_key, model=model)
        
        tokens = []
        async for token in stream_llm(
            prompt_text,
            system_prompt,
            cfg,
            temperature=0.3,
            max_tokens=300,
        ):
            tokens.append(token)
            
        full_text = "".join(tokens).strip()
        if full_text.startswith("```json"):
            full_text = full_text.replace("```json", "").replace("```", "").strip()
        elif full_text.startswith("```"):
            full_text = full_text.replace("```", "").strip()
            
        return json.loads(full_text)
    except Exception as e:
        logger.error(f"Coaching Generate Error: {e}")
        return {
            "general_tip": "Focus on the STAR method to structure your answers.",
            "stress_tip": "When interrupted, stay calm and get straight to the bottom line." if stress_level != "none" else "",
            "cv_tip": "Make sure you can dive deep into the specific metrics you listed." 
        }
