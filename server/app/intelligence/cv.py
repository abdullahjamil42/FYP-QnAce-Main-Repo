import json
import logging
import io
import re
from typing import Any, Dict, List, Optional
from .llm import LLMProviderConfig, resolve_provider_config, stream_llm

try:
    import fitz
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger("qace.cv")

def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from PDF, DOCX, or TXT formats."""
    text = ""
    lower_name = filename.lower()
    try:
        if lower_name.endswith(".pdf"):
            if fitz is None:
                logger.error("PyMuPDF (fitz) is not installed. Cannot parse PDF.")
                return "CV text could not be extracted (Missing PyMuPDF)."
            doc = fitz.open("pdf", file_bytes)
            for page in doc:
                text += page.get_text() + "\n"
        elif lower_name.endswith(".docx"):
            if docx is None:
                logger.error("python-docx is not installed. Cannot parse DOCX.")
                return "CV text could not be extracted (Missing python-docx)."
            doc = docx.Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            text = file_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error(f"Failed to extract text from {filename}: {e}")
    
    # Simple cleanup
    return re.sub(r"\s+", " ", text).strip()

async def parse_cv_structured(raw_text: str, settings: Any) -> dict:
    """Use LLM to extract structured CV data."""
    provider = resolve_provider_config(settings)
    if not provider:
        return {"name": "Candidate", "skills": [], "roles": [], "projects": []}
    
    system_prompt = (
        "You are an expert HR data extractor. Extract the candidate's CV information into structured JSON. "
        "Strictly return single valid JSON object only. No prose, no markdown formatting. "
        "Schema: {\"name\": str, \"skills\": [str], \"roles\": [str], \"projects\": [str], \"gaps\": [str]} "
        "roles and projects should be brief 1-sentence summaries. Gaps identifies missing years."
    )
    
    # Create fake stream collector logic
    payload = raw_text[:4000] # Limiting size for cost/time
    tokens = []
    
    try:
        model = getattr(settings, "interviewer_generator_model", provider.model)
        cfg = LLMProviderConfig(provider=provider.provider, api_key=provider.api_key, model=model)
        
        async for token in stream_llm(
            payload,
            system_prompt,
            cfg,
            temperature=0.1,
            max_tokens=400,
        ):
            tokens.append(token)
            
        full_text = "".join(tokens).strip()
        if full_text.startswith("```json"):
            full_text = full_text.replace("```json", "").replace("```", "").strip()
        elif full_text.startswith("```"):
            full_text = full_text.replace("```", "").strip()
            
        return json.loads(full_text)
    except Exception as e:
        logger.error(f"CV Parse Error: {e}")
        return {"error": str(e), "name": "Candidate"}

async def generate_seed_bank(parsed_cv: dict, interview_mode: str, settings: Any) -> list[dict]:
    """Generate a seed bank of interview questions based on the candidate's CV."""
    provider = resolve_provider_config(settings)
    if not provider:
        return []

    system_prompt = (
        "You are an expert technical interviewer. Create a seed bank of 5 tough probing questions tailored exactly "
        "to the candidate's CV. Output strict JSON only, an array of objects. Schema: "
        "[{\"question\": str, \"topic_area\": str, \"priority\": int (1-5), \"cv_anchor\": str}] "
        f"The interview mode is {interview_mode}."
    )
    cv_str = json.dumps(parsed_cv)
    
    tokens = []
    try:
        model = getattr(settings, "interviewer_generator_model", provider.model)
        cfg = LLMProviderConfig(provider=provider.provider, api_key=provider.api_key, model=model)
        
        async for token in stream_llm(
            cv_str,
            system_prompt,
            cfg,
            temperature=0.3,
            max_tokens=600,
        ):
            tokens.append(token)
            
        full_text = "".join(tokens).strip()
        if full_text.startswith("```json"):
            full_text = full_text.replace("```json", "").replace("```", "").strip()
        elif full_text.startswith("```"):
            full_text = full_text.replace("```", "").strip()
            
        data = json.loads(full_text)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.error(f"Generate Seed Bank Error: {e}")
        return []
