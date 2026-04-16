# Conversational Realism Features — Design Spec

**Date:** 2026-04-17
**Scope:** Three features that make the AI interviewer feel more human: intelligent answer completion detection, spoken acknowledgments between questions, and backchannel listening sounds during candidate speech.

**Target codebase:** `FYP-QnAce-Main-Repo/server/`

---

## Features Overview

| # | Feature | Summary |
|---|---------|---------|
| 1 | Dynamic Answer Completion Detection | Replaces the 0.5s polling silence monitor with a multi-signal completeness scoring pipeline |
| 3 | Interviewer Acknowledgment Phrases | Short spoken phrases between answer completion and the next question |
| 4 | Backchannel Audio | Occasional "mhm", "right" sounds while the candidate speaks |

**Pipeline order:** completion detection → acknowledgment → next question TTS
**Feature 4** runs on an independent parallel async task.

---

## Architecture: New & Modified Files

### New files

| File | Responsibility |
|------|---------------|
| `server/app/intelligence/completeness.py` | Orchestrates three scoring signals (semantic, prosodic, coverage) into a composite completeness score |
| `server/app/intelligence/coverage.py` | Question sub-classification (behavioral/technical/situational) and structural coverage heuristic |
| `server/app/synthesis/backchannel.py` | `BackchannelTrack` (silence-emitting WebRTC audio track) and `BackchannelManager` (trigger logic, phrase pool, state) |

### Modified files

| File | Changes |
|------|---------|
| `server/app/intelligence/llm.py` | Add non-streaming `call_llm()` function |
| `server/app/perception/vocal.py` | Add `analyze_finality()` function |
| `server/app/webrtc/signaling.py` | Replace `_answer_phase_monitor()`, add new session state fields, acknowledgment logic in transition, backchannel track setup, VAD callback additions |
| `server/app/webrtc/data_channel.py` | Add `send_answer_complete()` helper |
| `client/src/hooks/useWebRTC.ts` | Handle second incoming audio track (backchannel) |

---

## Feature 1: Dynamic Answer Completion Detection

### Session State Additions

Added to the session dict at construction (signaling.py ~line 284), reset at start of each question in `_start_question_flow()`:

```python
# Completion detection
"current_answer_transcript": "",        # accumulates Whisper chunks for current question
"silence_since_last_speech": None,      # float, updated by VAD
"last_completeness_score": 0.0,         # latest composite score
"last_completeness_signals": {},        # {semantic, prosodic, coverage}
"answer_prompted_at": None,             # float, set when question is asked
"answer_prompted_spoken": False,        # whether 12s encouragement was spoken
"current_question_subtype": "unknown",  # behavioral/technical/situational
```

### `llm.py` — `call_llm()`

```python
async def call_llm(
    messages: list[dict],
    provider_config: LLMProviderConfig,
    temperature: float = 0.3,
    max_tokens: int = 256,
    timeout_s: float = 3.0,
) -> str | None
```

- Reuses the same provider routing as `stream_llm()` (Groq, Airforce, Local) but makes a non-streaming request (`stream=False`)
- Wrapped in `asyncio.wait_for(coro, timeout=timeout_s)`
- On timeout or any exception: logs warning, returns `None`
- No retry logic — callers supply their own fallback values

### `vocal.py` — `analyze_finality()`

```python
def analyze_finality(audio: np.ndarray, sample_rate: int = 16000) -> tuple[float, float]
```

Returns `(pitch_slope, energy_drop)`.

**Pitch slope:**
- Takes the last 1.5s of the audio array (full array if shorter)
- Reuses existing autocorrelation pitch estimation per-frame (30ms frame, 10ms hop)
- Collects pitch estimates into a contour, discarding unvoiced frames
- `numpy.polyfit(x, pitch_contour, 1)` — slope coefficient is `pitch_slope`
- If fewer than 3 voiced frames: returns `pitch_slope = 0.0` (neutral)

**Energy drop:**
- Splits 1.5s segment into last 0.5s (tail) and preceding 1.0s (body)
- `energy_drop = rms_tail / max(rms_body, 1e-10)`
- If segment shorter than 0.5s: returns `energy_drop = 1.0` (neutral)

### `intelligence/coverage.py`

**Sub-classification — `classify_question_subtype()`:**

```python
async def classify_question_subtype(
    question_text: str,
    question_type: str,       # "dsa" or "role_specific"
    provider_config: LLMProviderConfig,
) -> str  # "behavioral" | "technical" | "situational"
```

- `"dsa"` questions → always `"technical"`, no LLM call
- `"role_specific"` questions → `call_llm()` with a short classification prompt, 3s timeout, fallback `"behavioral"`
- Called once per question at the start of `_start_question_flow()`, stored in `session["current_question_subtype"]`

**Coverage scoring — `compute_coverage_score()`:**

```python
def compute_coverage_score(transcript: str, question_subtype: str) -> float
```

Structural checks via regex/keyword matching (no LLM call):

| Subtype | Elements expected | Detection |
|---------|------------------|-----------|
| behavioral | (1) past-tense narrative, (2) action taken, (3) outcome/result | Past-tense verbs, first-person action phrases ("I did", "I led"), result keywords ("resulted in", "improved", "reduced") |
| technical | (1) mechanism explanation, (2) tradeoff/reasoning | Technical verbs ("works by", "uses", "implements"), tradeoff markers ("however", "tradeoff", "alternatively", "because") |
| situational | (1) decision stated, (2) rationale given | Decision language ("I would", "my approach"), reasoning markers ("because", "since", "in order to") |

`coverage_score = elements_found / elements_expected`, capped at 1.0. Unknown subtype defaults to 0.5.

### `intelligence/completeness.py`

**Main function:**

```python
async def evaluate_completeness(
    full_transcript: str,
    question_text: str,
    question_subtype: str,
    audio_tail: np.ndarray,
    sample_rate: int,
    provider_config: LLMProviderConfig,
) -> CompletenessResult
```

**`CompletenessResult`:**

```python
@dataclass
class CompletenessResult:
    score: float          # weighted composite 0.0-1.0
    semantic: float       # Signal A (weight 0.50)
    prosodic: float       # Signal B (weight 0.30)
    coverage: float       # Signal C (weight 0.20)
    should_advance: bool  # score >= 0.70
```

**Signal A — Semantic completeness (weight 0.50):**
- Calls `call_llm()` with the prompt:
  - System: "You are evaluating interview answers. Return only valid JSON."
  - User: "Question asked: {question_text}\nAnswer so far: {full_transcript}\n\nDoes this answer feel complete — like the speaker has reached a natural conclusion — or does it feel mid-thought and unfinished?\n\nReturn JSON: { \"complete\": true/false, \"score\": 0.0-1.0, \"reason\": \"...\" }\nScore 1.0 = clearly finished, 0.0 = clearly mid-sentence."
- Timeout: 3s. Fallback: `semantic_score = 0.5`
- JSON parsing: `json.loads()` with regex fallback for `"score": <float>`

**Signal B — Prosodic finality (weight 0.30):**
- Calls `vocal.analyze_finality(audio_tail, sample_rate)` → `(pitch_slope, energy_drop)`
- Threshold logic:
  - `1.0` if pitch_slope < -0.3 AND energy_drop < 0.6
  - `0.6` if pitch_slope < -0.1 OR energy_drop < 0.6
  - `0.2` otherwise

**Signal C — Coverage (weight 0.20):**
- Calls `coverage.compute_coverage_score(full_transcript, question_subtype)`

**Combination:**
```
score = (semantic * 0.50) + (prosodic * 0.30) + (coverage * 0.20)
should_advance = score >= 0.70
```

**Execution:** Signal A (LLM) runs concurrently with Signals B+C (pure computation) via `asyncio.gather()`.

### Replacing `_answer_phase_monitor()` in signaling.py

The 0.5s polling loop is removed. Completeness evaluation is triggered reactively:

1. **On new Whisper transcript chunk:** append to `current_answer_transcript`, call `evaluate_completeness()`, then `_check_advance()`
2. **On VAD speech end:** update `silence_since_last_speech` timestamp

**`_check_advance()` conditions (all must be true):**
- `last_completeness_score >= 0.70`
- `silence_duration >= 1.5s` (computed from `silence_since_last_speech`)
- VAD is not currently detecting speech

**On advance:** emit WebSocket event via data channel:
```json
{"type": "answer_complete", "completeness_score": 0.82,
 "signals": {"semantic": 0.9, "prosodic": 0.8, "coverage": 0.6}}
```

Then proceed to acknowledgment → next question TTS.

### Fallback Timer — `_answer_fallback_timer()`

A new async task started when the question is asked:

- **At 12 seconds** of total silence (no speech detected since question asked): TTS speaks a random encouragement from `["Take your time, I'm listening.", "No rush, whenever you're ready."]`. Sets `answer_prompted_spoken = True` (fires once only).
- **At 20 seconds:** marks as skipped, logs as anomaly. `completeness_score = 0.0`, all signals 0.0. Advances to next question.
- Cancelled if any speech is detected or a normal advance happens first.

### `data_channel.py` — `send_answer_complete()`

New helper function alongside `send_question()`, `send_phase()`, etc:

```python
def send_answer_complete(channel, completeness_score: float, signals: dict):
    send_event(channel, {
        "type": "answer_complete",
        "completeness_score": completeness_score,
        "signals": signals,
    })
```

---

## Feature 3: Interviewer Acknowledgment Phrases

### Phrase Pools

Defined as a module-level constant in `signaling.py`:

```python
ACKNOWLEDGMENT_PHRASES = {
    "high": ["Great, thank you.", "Got it, appreciate that.",
             "That's helpful context.", "Good, makes sense.",
             "Okay, noted.", "Right, thank you."],
    "medium": ["Okay, thank you.", "Alright.", "Sure, okay.",
               "Got it.", "Mm, okay.", "Right."],
    "low": ["Okay.", "Alright, moving on.", "Sure."],
}
```

### Tone Selection

Based on `last_completeness_score`:
- `>= 0.75` → high
- `>= 0.45` → medium
- `< 0.45` → low

### Injection Point

Inside the modified `_transition_to_next()`:

1. Answer complete event fires, all scoring finished
2. Select tone based on completeness score, pick random phrase from pool
3. TTS speaks acknowledgment via `_speak_session_text()` (existing helper). Await full playback.
4. `await asyncio.sleep(0.4)` — 400ms pause
5. Send question text to frontend via `send_question()`
6. TTS speaks the next question

### Skip Conditions

- Do NOT speak acknowledgment on the very first question (`question_index == 0`)
- DO speak acknowledgment for skipped answers (20s timeout) — uses the "low" pool

---

## Feature 4: Backchannel Audio

### Session State Additions

```python
"last_backchannel_time": None,       # float, for 8s cooldown
"backchannel_active": False,         # prevents overlapping backchannels
"backchannel_track": None,           # BackchannelTrack instance
"backchannel_log": [],               # list of {timestamp, phrase, cut_short} dicts
```

`last_backchannel_time` and `backchannel_log` persist across questions. `backchannel_active` resets to `False` if a backchannel was mid-playback during question transition.

### `synthesis/backchannel.py`

**`BackchannelTrack` class:**

A WebRTC audio track dedicated to backchannel playback:

- Mirrors `TTSAudioStreamTrack` structure but `recv()` emits silence frames (960 zero samples at 48kHz = 20ms) when the queue is empty, instead of blocking
- `play(audio_pcm: np.ndarray)` — enqueues audio frames for playback
- `cancel()` — flushes the queue, immediately resumes emitting silence. Sets a flag so `BackchannelManager` knows playback was cut short.
- Frame format: 20ms of 48kHz PCM int16, matching the main TTS track

**`BackchannelManager` class:**

```python
class BackchannelManager:
    def __init__(self, session: dict, tts_engine, backchannel_track: BackchannelTrack):
        ...

    def on_speech_end(self):
        """Called when VAD fires on_speech_end (~200ms after silence onset).
           Schedules a delayed check for backchannel opportunity."""

    async def _delayed_backchannel_check(self):
        """Waits 0.6s after on_speech_end (total ~0.8s silence), then evaluates triggers."""
```

**Pause detection mechanism:** The VAD fires `on_speech_end` after ~200ms of silence. The manager records this timestamp and schedules `_delayed_backchannel_check()` via `asyncio.get_event_loop().call_later(0.6, ...)`. When the delayed check fires (~0.8s total silence), it verifies speech has not resumed (VAD not active) and the pause has not exceeded 2.5s. If speech resumes before the check fires, the pending check is cancelled.

**Phrase pool:**
```python
["Mhm.", "Right.", "Okay.", "I see.", "Sure.", "Mm."]
```

**Trigger conditions (all checked in `_delayed_backchannel_check()`):**

1. Speech has been absent for >= 0.8s and < 2.5s (computed from recorded speech-end timestamp)
2. `session["current_phase"] == "answering"`
3. `time.perf_counter() - session["answer_prompted_at"] >= 6.0` (not during opening breath)
4. `session["last_backchannel_time"] is None` or `>= 8.0s` ago
5. `random.random() < 0.35`
6. `session["backchannel_active"] is False`

**Playback flow:**
1. Select random phrase from pool
2. Synthesize via `tts_engine` (same engine, normal synthesis)
3. Scale audio PCM by `0.85` for reduced volume
4. Set `session["backchannel_active"] = True`
5. Enqueue into `BackchannelTrack` — fire and continue (don't await completion)
6. On playback complete or `cancel()`: set `session["backchannel_active"] = False`, update `session["last_backchannel_time"]`, append to `session["backchannel_log"]`

**Speech resumption cutoff:**
- VAD `on_speech_start` event in signaling.py checks `session["backchannel_active"]`
- If true: calls `backchannel_track.cancel()` which flushes the queue and resumes silence frames
- Logs the backchannel as `cut_short: True`

### WebRTC Setup (signaling.py)

- `BackchannelTrack` is instantiated during session setup alongside the existing `TTSAudioStreamTrack`
- Added to the `RTCPeerConnection` as a second audio track
- `BackchannelManager` is instantiated with references to the session, TTS engine, and backchannel track
- A new callback is wired into the VAD chain to call `backchannel_manager.on_vad_pause()` on speech pauses

### Client-Side (useWebRTC.ts)

- The client receives a second audio track via `pc.ontrack`
- Currently the hook handles the first incoming audio track for TTS playback
- Needs to handle the second track: attach it to a second `<audio>` element or combine both tracks into a single `MediaStream`
- The browser mixes both audio tracks automatically when both are playing

---

## Integration Summary

### Pipeline Order (Features 1 → 3)

```
Candidate stops speaking
    │
    ▼
VAD fires on_speech_end → updates silence_since_last_speech
    │
    ▼
Whisper transcribes → appends to current_answer_transcript
    │
    ▼
evaluate_completeness() runs (Signals A+B+C in parallel)
    │
    ▼
_check_advance(): score >= 0.70 AND silence >= 1.5s AND no active speech?
    │                    │
    No                   Yes
    │                    │
    ▼                    ▼
  (wait for         send answer_complete event
   next chunk)          │
                        ▼
                   Select acknowledgment phrase (Feature 3)
                        │
                        ▼
                   TTS speaks acknowledgment, await playback
                        │
                        ▼
                   400ms pause
                        │
                        ▼
                   Send question to frontend + TTS speaks next question
```

### Feature 4 (Independent)

```
VAD detects speech pause (0.8s-2.5s)
    │
    ▼
BackchannelManager.on_vad_pause() checks 6 trigger conditions
    │                    │
    Fail                 Pass
    │                    │
    ▼                    ▼
  (nothing)         Synthesize + play at 85% volume
                        │
                    ┌────┴────┐
                    │         │
              Finishes    Speech resumes
              normally    → cancel() + silence
```

### LLM Timeout Behavior

All LLM calls use `call_llm()` with `timeout_s=3.0`:
- Feature 1 semantic scoring: fallback `semantic_score = 0.5`
- Question sub-classification: fallback `"behavioral"`

A slow API response never blocks the interview.

### Session State Reset Per Question

At the start of each question (`_start_question_flow()`), reset:
- `current_answer_transcript = ""`
- `silence_since_last_speech = None`
- `last_completeness_score = 0.0`
- `last_completeness_signals = {}`
- `answer_prompted_at = time.perf_counter()`
- `answer_prompted_spoken = False`
- `current_question_subtype` = result of `classify_question_subtype()`

Do NOT reset: `last_backchannel_time`, `backchannel_log`. Reset `backchannel_active = False` only if it was `True` (mid-playback during transition).

---

## Testing Strategy

### Unit Tests

| Test | What it validates |
|------|-------------------|
| `test_completeness.py` | `evaluate_completeness()` with mocked LLM responses. Verify weighted combination. Verify fallback when LLM times out (semantic defaults to 0.5). |
| `test_coverage.py` | `compute_coverage_score()` for each subtype with known transcripts. Verify element detection and capping at 1.0. `classify_question_subtype()` returns correct types for DSA vs role-specific. |
| `test_finality.py` | `analyze_finality()` with synthetic audio: falling pitch → negative slope, trailing silence → low energy_drop. Edge cases: very short audio, all-silence audio. |
| `test_backchannel.py` | `BackchannelTrack.recv()` returns silence when queue empty. `cancel()` flushes queue. `BackchannelManager` trigger conditions — test each condition independently. |
| `test_call_llm.py` | `call_llm()` returns parsed string on success, `None` on timeout. |

### Integration Tests

| Test | What it validates |
|------|-------------------|
| Advance logic | Feed a complete transcript + sufficient silence → verify `_check_advance()` fires. Feed incomplete transcript → verify it waits. |
| Fallback timer | Simulate 20s of no speech → verify skip + anomaly log. Simulate speech at 15s → verify timer cancellation. |
| Acknowledgment sequence | Verify TTS speaks phrase → 400ms pause → question sent → question spoken. Verify skip on first question. Verify low pool on timeout skip. |
| Backchannel cutoff | Play backchannel → simulate speech resumption → verify `cancel()` called and `cut_short` logged. |
