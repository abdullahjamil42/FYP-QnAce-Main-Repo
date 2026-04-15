"""
Q&Ace — Session Stages & Realism Engine

Encapsulates the state machines and timers for interview realism, including
the staged lifecycle, dynamic time management, silence monitoring, and
humanized response delays.
"""

from __future__ import annotations

import logging
import random
import time
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger("qace.session_stages")


class SessionStage(Enum):
    SMALL_TALK = 1
    INTRO = 2
    TECHNICAL = 3
    WRAP_UP = 4
    CLOSING = 5
    ENDED = 6


class SessionTimer:
    """Manages interview wall-clock duration and warnings."""

    def __init__(self, duration_minutes: int):
        self._target_duration_s = max(1, duration_minutes) * 60.0
        self._start_time: float | None = None
        self._warning_sent = False

    def start(self) -> None:
        if self._start_time is None:
            self._start_time = time.time()

    def elapsed_s(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def remaining_s(self) -> float:
        return max(0.0, self._target_duration_s - self.elapsed_s())

    def is_expired(self) -> bool:
        if self._start_time is None:
            return False
        return self.remaining_s() <= 0.0

    def should_warn(self) -> bool:
        """Returns True exactly once when 5 minutes or less remain."""
        if self._start_time is None or self._warning_sent:
            return False
        if self.remaining_s() <= 300.0:
            self._warning_sent = True
            return True
        return False


class QuestionBudget:
    """Tracks how many topics should be covered based on session duration."""

    def __init__(self, duration_minutes: int):
        # Rough average: 3.5 mins per full topic exchange (including probes/challenges)
        # Minimum 2 technical topics, max 10.
        target = int(max(0, duration_minutes - 5) / 3.5)
        self.topics_targeted = max(2, min(10, target))
        self.topics_completed = 0

    def complete_topic(self) -> None:
        self.topics_completed += 1

    def is_budget_exhausted(self) -> bool:
        return self.topics_completed >= self.topics_targeted


class SilenceMonitor:
    """Tracks candidate silence to trigger AI prompts."""

    def __init__(self):
        self._last_speech_ms: float | None = None
        self._active = False
        self._triggered_level = 0  # 0: none, 1: 8s, 2: 15s, 3: 25s

    def activate(self) -> None:
        """Called when AI finishes speaking its question."""
        self._last_speech_ms = time.perf_counter() * 1000.0
        self._active = True
        self._triggered_level = 0

    def deactivate(self) -> None:
        """Called when candidate starts speaking."""
        self._active = False
        self._triggered_level = 0

    def check_silence(self) -> int:
        """Returns the silence level triggered (0 if none or inactive)."""
        if not self._active or self._last_speech_ms is None:
            return 0
            
        silence_s = (time.perf_counter() * 1000.0 - self._last_speech_ms) / 1000.0
        
        if silence_s >= 25.0 and self._triggered_level < 3:
            self._triggered_level = 3
            return 3
        if silence_s >= 15.0 and self._triggered_level < 2:
            self._triggered_level = 2
            return 2
        if silence_s >= 8.0 and self._triggered_level < 1:
            self._triggered_level = 1
            return 1
            
        return 0


class AcknowledgmentPicker:
    """Provides varied acknowledgment phrases without repetition."""

    def __init__(self):
        self._phrases = [
            "Got it.",
            "Okay.",
            "Right, that makes sense.",
            "Interesting.",
            "Sure.",
            "Fair enough.",
            "Alright.",
            "Good to know.",
            "Noted.",
            "I hear you.",
            "Makes sense.",
            "Understood."
        ]
        self._last_idx = -1

    def pick(self) -> str:
        idx = self._last_idx
        while idx == self._last_idx:
            idx = random.randint(0, len(self._phrases) - 1)
        self._last_idx = idx
        return self._phrases[idx]


class ThinkingDelay:
    """Computes a simulated human response delay."""

    def __init__(self):
        self._turn_count = 0

    def get_delay_s(self, answer_word_count: int, stress_level: str = "none") -> float:
        self._turn_count += 1
        
        if stress_level == "brutal":
            delay_ms = random.uniform(200, 400)
        elif stress_level == "high":
            delay_ms = random.uniform(300, 700)
        else:
            # Base random delay between 800ms and 1500ms
            delay_ms = random.uniform(800, 1500)
            
            # Extroversion/introversion multiplier based on length
            if answer_word_count > 100:
                delay_ms += random.uniform(300, 800)  # longer answers take longer to digest
                
            if self._turn_count == 1:
                delay_ms += 500  # first real answer usually has a slightly longer beat
            
        # Cap at 2500ms so it doesn't feel broken
        return min(2500.0, delay_ms) / 1000.0
