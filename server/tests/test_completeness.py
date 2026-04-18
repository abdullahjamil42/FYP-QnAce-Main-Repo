import pytest
from unittest.mock import AsyncMock, patch
import numpy as np
from app.intelligence.completeness import evaluate_completeness, CompletenessResult

@pytest.mark.asyncio
async def test_evaluate_completeness_success():
    mock_config = {}
    audio_tail = np.zeros(16000)
    
    # Mock Signal A (Semantic)
    # Mock Signal B (Prosodic) inside completeness.py's _evaluate_prosodic
    # Mock Signal C (Coverage) inside completeness.py's compute_coverage_score

    with patch("app.intelligence.completeness._evaluate_semantic", new_callable=AsyncMock) as mock_sem, \
         patch("app.intelligence.completeness._evaluate_prosodic") as mock_pros, \
         patch("app.intelligence.coverage.compute_coverage_score") as mock_cov:
        
        # Scenario: Clearly complete
        mock_sem.return_value = 0.9
        mock_pros.return_value = 1.0
        mock_cov.return_value = 1.0
        
        res = await evaluate_completeness("transcript", "question", "technical", audio_tail, 16000, mock_config)
        assert res.should_advance is True
        assert res.score >= 0.7
        
        # Scenario: Mid-thought
        mock_sem.return_value = 0.2
        mock_pros.return_value = 0.2
        mock_cov.return_value = 0.2
        
        res = await evaluate_completeness("transcript", "question", "technical", audio_tail, 16000, mock_config)
        assert res.should_advance is False
        assert res.score < 0.7

@pytest.mark.asyncio
async def test_evaluate_completeness_fallback():
    mock_config = {}
    audio_tail = np.zeros(16000)

    # If semantic LLM fails (returns 0.5 fallback)
    with patch("app.intelligence.completeness._evaluate_semantic", new_callable=AsyncMock) as mock_sem, \
         patch("app.intelligence.completeness._evaluate_prosodic") as mock_pros, \
         patch("app.intelligence.coverage.compute_coverage_score") as mock_cov:
        
        mock_sem.return_value = 0.5 # fallback
        mock_pros.return_value = 0.2
        mock_cov.return_value = 0.5
        
        # (0.5 * 0.5) + (0.2 * 0.3) + (0.5 * 0.2) = 0.25 + 0.06 + 0.10 = 0.41
        res = await evaluate_completeness("transcript", "question", "technical", audio_tail, 16000, mock_config)
        assert res.score == 0.41
        assert res.should_advance is False
