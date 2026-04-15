import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File

from ..intelligence.cv import extract_text, parse_cv_structured, generate_seed_bank

logger = logging.getLogger("qace.cv_routes")

cv_router = APIRouter()

# In-memory storage per user request constraint 2
# Format: { "cv_session_id": { "parsed_cv": {}, "seed_bank": [] } }
_cv_store: Dict[str, Dict[str, Any]] = {}

def get_cv_session(cv_session_id: str) -> Optional[Dict[str, Any]]:
    return _cv_store.get(cv_session_id)

@cv_router.post("/upload")
async def upload_cv(file: UploadFile = File(...)):
    if not file.filename:
        return {"error": "No filename"}
        
    try:
        content = await file.read()
        raw_text = extract_text(content, file.filename)
        
        # Fake settings object to pass to parser
        class DummySettings:
            interviewer_generator_model = "" 
        
        parsed_cv = await parse_cv_structured(raw_text, DummySettings())
        seed_bank = await generate_seed_bank(parsed_cv, "technical", DummySettings())
        
        cv_session_id = str(uuid.uuid4())
        _cv_store[cv_session_id] = {
            "parsed_cv": parsed_cv,
            "seed_bank": seed_bank
        }
        
        return {
            "cv_session_id": cv_session_id,
            "parsed_cv": parsed_cv
        }
    except Exception as e:
        logger.error(f"Error handling CV upload: {e}")
        return {"error": str(e)}
