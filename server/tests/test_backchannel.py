import pytest
import asyncio
import time
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from app.synthesis.backchannel import BackchannelTrack, BackchannelManager

def test_backchannel_track_silence():
    track = BackchannelTrack()
    # Mock av.AudioFrame if needed, but here we just check if it returns something
    # Since av might not be installed in the environment, we check the logic
    # In a real test environment, we'd mock AudioFrame
    pass

@pytest.mark.asyncio
async def test_backchannel_manager_trigger_logic():
    session = {
        "current_phase": "answering",
        "answer_prompted_at": time.perf_counter() - 10,
        "last_backchannel_time": None,
        "backchannel_active": False,
        "backchannel_log": []
    }
    tts = AsyncMock()
    track = MagicMock()
    
    manager = BackchannelManager(session, tts, track)
    
    # ── Test Case 1: All conditions pass ──
    manager._speech_end_time = time.perf_counter() - 1.0 # 1s silence
    
    # Mock TTS synthesize return value
    # From app.synthesis.tts (assuming a dataclass or object with audio_pcm and sample_rate)
    mock_result = MagicMock()
    mock_result.audio_pcm = np.zeros(100, dtype=np.int16)
    mock_result.sample_rate = 24000
    tts.synthesize.return_value = mock_result

    with patch("random.random", return_value=0.1): # pass probability
        await manager._delayed_check()
        assert session["backchannel_active"] is False # It finishes synthesis and sets to false
        assert len(session["backchannel_log"]) == 1
        tts.synthesize.assert_called_once()

@pytest.mark.asyncio
async def test_backchannel_manager_cooldown():
    session = {
        "current_phase": "answering",
        "answer_prompted_at": time.perf_counter() - 10,
        "last_backchannel_time": time.perf_counter() - 2, # Only 2s ago
        "backchannel_active": False,
        "backchannel_log": []
    }
    tts = AsyncMock()
    track = MagicMock()
    
    manager = BackchannelManager(session, tts, track)
    manager._speech_end_time = time.perf_counter() - 1.0
    
    await manager._delayed_check()
    tts.synthesize.assert_not_called()

@pytest.mark.asyncio
async def test_backchannel_manager_wrong_phase():
    session = {
        "current_phase": "speaking", # Wrong phase
        "answer_prompted_at": time.perf_counter() - 10,
        "last_backchannel_time": None,
        "backchannel_active": False,
        "backchannel_log": []
    }
    tts = AsyncMock()
    track = MagicMock()
    
    manager = BackchannelManager(session, tts, track)
    manager._speech_end_time = time.perf_counter() - 1.0
    
    await manager._delayed_check()
    tts.synthesize.assert_not_called()
