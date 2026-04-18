import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.intelligence.coverage import compute_coverage_score, classify_question_subtype

def test_compute_coverage_score_behavioral():
    # Transcript with CAR (Context/Action/Result)
    transcript = "In my previous role, I led a team to develop a new feature. I decided to use a microservices approach. As a result, we improved performance by 40%."
    score = compute_coverage_score(transcript, "behavioral")
    assert score == 1.0

    # Partial
    transcript_partial = "I did some coding."
    score_partial = compute_coverage_score(transcript_partial, "behavioral")
    assert 0.0 < score_partial < 1.0

    # Empty
    assert compute_coverage_score("", "behavioral") == 0.0

def test_compute_coverage_score_technical():
    # Transcript with mechanism + tradeoff
    transcript = "It works by using a load balancer. However, the tradeoff is increased latency."
    score = compute_coverage_score(transcript, "technical")
    assert score == 1.0

    # Mechanism only
    transcript_partial = "It uses an algorithm."
    score_partial = compute_coverage_score(transcript_partial, "technical")
    assert score_partial == 0.5

def test_compute_coverage_score_situational():
    # Decision + Rationale
    transcript = "I would prioritize the urgent bugs because stability is key."
    score = compute_coverage_score(transcript, "situational")
    assert score == 1.0

@pytest.mark.asyncio
async def test_classify_question_subtype():
    mock_config = AsyncMock()
    
    # DSA should be technical always
    assert await classify_question_subtype("Some DSA text", "dsa", mock_config) == "technical"

    # Mock call_llm for role_specific
    with patch("app.intelligence.llm.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Technical"
        res = await classify_question_subtype("How does JVM work?", "role_specific", mock_config)
        assert res == "technical"

        mock_call.return_value = "behavioral"
        res = await classify_question_subtype("Tell me about a time...", "role_specific", mock_config)
        assert res == "behavioral"

        # Fallback
        mock_call.return_value = None
        res = await classify_question_subtype("Whatever", "role_specific", mock_config)
        assert res == "behavioral"
