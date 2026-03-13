"""
Q&Ace — Scoring Formula Tests.

Validates the weighted scoring formula:
  Final = 0.70 × Content + 0.20 × Delivery + 0.10 × Composure

Each sub-score is in [0, 100]. Tests use hand-calculated expected values.
"""

from __future__ import annotations

import pytest

from server.app.intelligence.scoring import (
    clamp,
    compute_fluency,
    compute_composure,
    compute_utterance_scores,
    RunningScorer,
    UtteranceScores,
)


def compute_final(content: float, delivery: float, composure: float) -> float:
    return 0.70 * content + 0.20 * delivery + 0.10 * composure


class TestScoringFormula:
    def test_perfect_score(self):
        """All perfect inputs → ~100."""
        content = 100.0
        delivery = 100.0
        composure = 100.0
        final = compute_final(content, delivery, composure)
        assert final == pytest.approx(100.0)

    def test_zero_score(self):
        """All zero inputs → 0."""
        assert compute_final(0, 0, 0) == 0.0

    def test_weighted_balance(self):
        """Content-heavy weighting: 70/0/0 should be 49."""
        final = compute_final(70, 0, 0)
        assert final == pytest.approx(49.0)

    def test_typical_candidate(self):
        """Realistic mid-range candidate."""
        content = 65.0    # average BERT + slight LLM boost
        delivery = 75.0   # decent WPM, few fillers
        composure = 80.0  # good eye contact
        final = compute_final(content, delivery, composure)
        # 0.70*65 + 0.20*75 + 0.10*80 = 45.5 + 15 + 8 = 68.5
        assert final == pytest.approx(68.5)

    def test_fluency_sweet_spot(self):
        score = compute_fluency(wpm=145, filler_count=0)
        assert score == 100.0

    def test_fluency_with_fillers(self):
        score = compute_fluency(wpm=145, filler_count=6, duration_s=60.0)
        # 100 - 6*5 = 70
        assert score == pytest.approx(70.0)

    def test_fluency_slow_speaker(self):
        score = compute_fluency(wpm=80, filler_count=0)
        assert score == pytest.approx(40.0)

    def test_fluency_fast_speaker(self):
        score = compute_fluency(wpm=170, filler_count=0)
        assert score == pytest.approx(80.0)

    def test_composure_perfect(self):
        score = compute_composure(
            eye_contact_ratio=1.0,
            blinks_per_min=17.5,
            emotion_positivity=1.0,
        )
        assert score == pytest.approx(100.0)

    def test_composure_low_eye_contact(self):
        score = compute_composure(
            eye_contact_ratio=0.3,
            blinks_per_min=17.5,
            emotion_positivity=0.5,
        )
        # 0.60*30 + 0.25*100 + 0.15*50 = 18 + 25 + 7.5 = 50.5
        assert score == pytest.approx(50.5)

    def test_composure_high_blink_rate(self):
        score = compute_composure(
            eye_contact_ratio=0.8,
            blinks_per_min=35.0,
            emotion_positivity=0.5,
        )
        blink_dev = abs(35.0 - 17.5) / 17.5  # 1.0
        expected = 0.60 * 80 + 0.25 * max(0, 1.0 - blink_dev) * 100 + 0.15 * 50
        assert score == pytest.approx(expected)

    def test_clamp_bounds(self):
        assert clamp(150.0) == 100.0
        assert clamp(-20.0) == 0.0
        assert clamp(50.0) == 50.0


class TestUtteranceScores:
    def test_default_scores(self):
        """Default params produce a sensible mid-range score."""
        scores = compute_utterance_scores()
        assert 0 <= scores.content <= 100
        assert 0 <= scores.delivery <= 100
        assert 0 <= scores.composure <= 100
        assert 0 <= scores.final <= 100

    def test_excellent_response(self):
        """High-quality response with good delivery."""
        scores = compute_utterance_scores(
            text_quality_score=90.0,
            wpm=145.0,
            filler_count=0,
            duration_s=60.0,
            vocal_confidence=0.8,
            eye_contact_ratio=0.9,
            blinks_per_min=17.5,
            emotion_positivity=0.8,
        )
        assert scores.content == pytest.approx(90.0)
        assert scores.final >= 75.0

    def test_poor_response(self):
        """Poor response should score low."""
        scores = compute_utterance_scores(
            text_quality_score=30.0,
            wpm=80.0,
            filler_count=10,
            duration_s=30.0,
            vocal_confidence=0.1,
            eye_contact_ratio=0.2,
            blinks_per_min=35.0,
            emotion_positivity=0.2,
        )
        assert scores.final < 40.0


class TestRunningScorer:
    def test_empty(self):
        scorer = RunningScorer()
        assert scorer.count == 0
        assert scorer.latest is None
        avg = scorer.average
        assert avg.final == 0.0

    def test_single_utterance(self):
        scorer = RunningScorer()
        scores = UtteranceScores(content=70, delivery=60, composure=80, final=68.5)
        scorer.add(scores)
        assert scorer.count == 1
        assert scorer.latest is scores
        assert scorer.average.final == 68.5

    def test_running_average(self):
        scorer = RunningScorer()
        scorer.add(UtteranceScores(content=80, delivery=70, composure=90, final=79))
        scorer.add(UtteranceScores(content=60, delivery=50, composure=70, final=59))
        assert scorer.count == 2
        avg = scorer.average
        assert avg.content == pytest.approx(70.0)
        assert avg.delivery == pytest.approx(60.0)
        assert avg.composure == pytest.approx(80.0)
        assert avg.final == pytest.approx(69.0)

    def test_to_dict(self):
        scorer = RunningScorer()
        scorer.add(UtteranceScores(content=80, delivery=70, composure=90, final=79))
        d = scorer.to_dict()
        assert d["content"] == 80
        assert d["final"] == 79
        assert d["avg_final"] == 79
        assert d["utterance_count"] == 1


class TestPunctuationBuffer:
    def test_sentence_fire(self):
        from server.app.synthesis.punctuation_buffer import PunctuationBuffer

        chunks: list[str] = []
        buf = PunctuationBuffer(on_chunk=chunks.append)
        for token in ["Hello ", "world", "."]:
            buf.feed(token)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world."

    def test_clause_fire_above_threshold(self):
        from server.app.synthesis.punctuation_buffer import PunctuationBuffer

        chunks: list[str] = []
        buf = PunctuationBuffer(on_chunk=chunks.append, min_clause_tokens=3)
        for token in ["One ", "two ", "three", ","]:
            buf.feed(token)
        assert len(chunks) == 1

    def test_clause_no_fire_below_threshold(self):
        from server.app.synthesis.punctuation_buffer import PunctuationBuffer

        chunks: list[str] = []
        buf = PunctuationBuffer(on_chunk=chunks.append, min_clause_tokens=10)
        for token in ["Hello", ","]:
            buf.feed(token)
        # Should NOT fire — only 2 tokens, below threshold of 10
        assert len(chunks) == 0
        buf.flush()
        assert len(chunks) == 1

    def test_flush(self):
        from server.app.synthesis.punctuation_buffer import PunctuationBuffer

        chunks: list[str] = []
        buf = PunctuationBuffer(on_chunk=chunks.append)
        for token in ["Hello ", "world"]:
            buf.feed(token)
        # No punctuation yet — nothing fired
        assert len(chunks) == 0
        buf.flush()
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_multiple_sentences(self):
        from server.app.synthesis.punctuation_buffer import PunctuationBuffer

        chunks: list[str] = []
        buf = PunctuationBuffer(on_chunk=chunks.append)
        for token in ["First.", " Second", ".", " Third", "!"]:
            buf.feed(token)
        assert len(chunks) == 3


class TestRAGModule:
    def test_retrieve_without_init(self):
        """Retrieve should return empty when not initialised."""
        from server.app.intelligence.rag import retrieve
        result = retrieve("test transcript")
        assert result.passages == []
        assert result.retrieval_ms == 0.0
