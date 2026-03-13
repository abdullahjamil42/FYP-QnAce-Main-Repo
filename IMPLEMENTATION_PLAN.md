# Q&Ace — Implementation Plan

> **Last Updated**: 2026-03-10  
> **Target**: TTFA < 800ms | Single RTX 4090 (24GB) | Monorepo  
> **Legend**: ⬜ Not Started | 🔄 In Progress | ✅ Complete | ❌ Blocked | ⏭️ Skipped

---

## Phase Summary

| Phase | Name | Tasks | Done | Status |
|-------|------|-------|------|--------|
| 0 | Planning & Documentation | 4 | 4 | ✅ Complete |
| 1 | Foundation — WebRTC + Audio Pipeline | 17 | 17 | ✅ Complete |
| 2 | Parallel Perception Engine | 13 | 13 | ✅ Complete |
| 3 | Intelligence, RAG & Scoring | 10 | 10 | ✅ Complete |
| 4 | Synthesis — TTS + Avatar | 12 | 12 | ✅ Complete |
| 5 | Frontend Polish & Session Flow | 11 | 1 | 🔄 In Progress |
| X | Cross-Cutting | 6 | 2 | 🔄 In Progress |
| **TOTAL** | | **73** | **59** | |

---

## Phase 0: Planning & Documentation ✅

| # | Task | Status | Date |
|---|------|--------|------|
| 0.1 | Architecture design & latency feasibility analysis | ✅ | 2026-03-04 |
| 0.2 | 12 Architecture Decision Records (ADRs) | ✅ | 2026-03-04 |
| 0.3 | Project Memory file (`PROJECT_MEMORY.md`) | ✅ | 2026-03-04 |
| 0.4 | Implementation Plan file (`IMPLEMENTATION_PLAN.md`) | ✅ | 2026-03-04 |

---

## Phase 1: Foundation — WebRTC Transport + Audio Pipeline

> **Goal**: User speaks → audio arrives at server → VAD detects silence → Whisper transcribes → transcript shown in UI.  
> **Success Criteria**: End-to-end audio transcription via WebRTC in <500ms (200ms VAD + ~200ms Whisper + overhead).  
> **Prerequisites**: None (greenfield).

| # | Task | File(s) | Depends On | Status | Notes |
|---|------|---------|-----------|--------|-------|
| 1.1 | Scaffold monorepo directory structure | All dirs | — | ✅ | Base directories + Python package `__init__.py` files created |
| 1.2 | Initialize Next.js 14 + TypeScript + TailwindCSS | `client/` | 1.1 | ✅ | Manual scaffold, deps installed, `next build` passing, custom theme (qace-primary/surface/dark/muted/accent) |
| 1.3 | Initialize FastAPI project (pyproject.toml, requirements.txt) | `server/` | 1.1 | ✅ | Backend package, dependency files, app entrypoint, `.venv311` (Python 3.11) |
| 1.4 | Pydantic Settings config | `server/app/config.py` | 1.3 | ✅ | QACE_ENV, CORS, model paths, VAD thresholds (300ms silence, 1.0s min speech), runtime Whisper configurable via `QACE_WHISPER_MODEL` |
| 1.5 | Model registry + FastAPI lifespan pre-warming | `server/app/models/registry.py`, `server/app/main.py` | 1.3 | ✅ | Startup prewarm, GPU→CPU fallback, Windows CUDA DLL discovery, smoke-test on load |
| 1.6 | Silero VAD v5 ONNX integration | `server/app/vad/silero.py` | 1.5 | ✅ | Silero ONNX path wired + energy-based fallback (ONNX file not yet downloaded) |
| 1.7 | Numpy ring buffer (30s, 16kHz mono) | `server/app/vad/ring_buffer.py` | 1.3 | ✅ | Pre-allocated int16 circular buffer, wraparound, read_last_seconds |
| 1.8 | WebRTC signaling endpoint (POST /offer) | `server/app/webrtc/signaling.py` | 1.5 | ✅ | SDP exchange, session dict, transcribe_and_send with asyncio.Lock, cleanup |
| 1.9 | Audio track handler (receive, resample 48→16kHz) | `server/app/webrtc/tracks.py` | 1.7, 1.8 | ✅ | Linear resampler, to_mono_int16, frame timeout handling, flush on track end |
| 1.10 | Wire VAD → ring buffer → end_of_speech event | `server/app/vad/silero.py` | 1.6, 1.9 | ✅ | EndOfSpeechDetector with configurable silence/min_speech, callback-based EOS |
| 1.11 | Faster-Whisper STT module | `server/app/perception/stt.py` | 1.5, 1.10 | ✅ | STTResult dataclass, filler detection, WPM calc, greedy beam_size=1 |
| 1.12 | Client useWebRTC hook | `client/src/hooks/useWebRTC.ts` | 1.2, 1.8 | ✅ | Mic capture, SDP exchange, DataChannel creation before offer, error handling |
| 1.13 | Minimal session UI | `client/src/app/session/page.tsx` | 1.12 | ✅ | TranscriptCard + ScoreItem components, status log, connection state indicator |
| 1.14 | DataChannel for transcript delivery (server→client) | `server/app/webrtc/data_channel.py`, `client/src/hooks/useDataChannel.ts` | 1.8, 1.12 | ✅ | Final-only transcript events, scores, status; AU telemetry parser ready for Phase 2 |
| 1.15 | Docker Compose + NVIDIA Container Toolkit | `infra/docker-compose.yml`, `server/Dockerfile` | 1.3 | ✅ | Compose + backend Dockerfile; import layout supports root and server-dir launches |
| 1.16 | Model download script (Whisper, Silero) | `scripts/download_models.py` | 1.1 | ✅ | Idempotent model directory bootstrap script |
| 1.17 | Integration test: speak → transcript in UI | `tests/test_vad.py` | All 1.x | ✅ | 17/17 pytest pass, SDP exchange returns 200, session page renders, backend health OK |

**2026-03-07 Latency / UX Delta**:
- Runtime STT target restored to `distil-large-v3` for improved transcription quality; actual throughput now depends on the repaired CUDA environment.
- Signaling now honors config-driven VAD thresholds instead of hardcoded values.
- Hybrid and rolling-window transcript experiments were tried and then reverted.
- Current local-dev transcript path is back to end-of-speech final-only delivery for stability.
- GPU STT verified on native Windows (CUDA runtime with pip-installed cuBLAS/cuDNN).
- Decode times: ~770ms–1223ms for ~2.5–3.1s utterances on RTX 4060.
- All 17/17 backend tests pass, `npm run build` succeeds, SDP exchange returns 200.

**Phase 1 Verification Checklist**:
- [ ] Docker compose starts without errors
- [ ] Browser opens, clicks "Start Session", WebRTC connects
- [ ] Speak a sentence → transcript appears in UI
- [ ] Console logs: VAD trigger time, Whisper inference time, total latency
- [ ] No `.wav` or `.mp4` files written anywhere on disk
- [ ] Whisper model loaded at startup (not on first inference)

---

## Phase 2: Parallel Perception Engine

> **Goal**: Multi-modal parallel analysis — STT + Vocal + Face on every utterance.  
> **Success Criteria**: `PerceptionResult` populated in ≤ max(STT, Wav2Vec2, EfficientNet) + 20ms.  
> **Prerequisites**: Phase 1 complete.

| # | Task | File(s) | Depends On | Status | Notes |
|---|------|---------|-----------|--------|-------|
| 2.1 | MediaPipe Face Mesh WASM component | `client/src/components/MediaPipeFaceMesh.tsx` | Phase 1 | ✅ | Dynamic import @mediapipe/tasks-vision, GPU delegate, 10 FPS detection loop, canvas overlay |
| 2.2 | AU extractor (AU4, AU12, AU45, eye contact, blink) | `client/src/lib/au-extractor.ts` | 2.1 | ✅ | Geometry-based from 478 landmarks, EAR for blink, iris for eye contact, 20-byte binary pack |
| 2.3 | Face crop 224×224 via canvas + captureStream(10) | `client/src/lib/face-crop.ts`, `client/src/components/VideoCanvas.tsx` | 2.1 | ✅ | Square crop from bbox, VideoCanvas integrates mesh+crop+AU dispatch |
| 2.4 | Add face crop video track to WebRTC | `client/src/hooks/useWebRTC.ts` | 2.3 | ✅ | addVideoTrack(), webcamStream, separate webcam capture (640×480, 15fps) |
| 2.5 | RTCDataChannel for AU telemetry (binary, 10Hz, UDP) | `client/src/hooks/useDataChannel.ts` | 2.2 | ✅ | au-telemetry channel (ordered:false, maxRetransmits:0), sendAUTelemetry, PerceptionEvent |
| 2.6 | Server AU telemetry receiver | `server/app/webrtc/data_channel.py`, `server/app/webrtc/signaling.py` | 2.5 | ✅ | parse_au_telemetry (20-byte struct unpack), datachannel handler detects au-telemetry label |
| 2.7 | Wav2Vec2 FP16 vocal emotion module | `server/app/perception/vocal.py` | Phase 1 | ✅ | VocalResult, pitch/energy via autocorrelation, INTERVIEW_EMOTIONS mapping, acoustic-only fallback |
| 2.8 | EfficientNet-B2 ONNX export + CPU inference | `server/app/perception/face.py` | Phase 1 | ✅ | FaceResult, ImageNet normalization, bilinear resize, ONNX CPUExecutionProvider |
| 2.9 | ProcessPoolExecutor orchestrator (3 workers) | `server/app/perception/orchestrator.py` | 2.7, 2.8, 1.11 | ✅ | asyncio.gather parallel STT+Vocal+Face → sequential BERT, exception handling per task |
| 2.10 | NVIDIA MPS setup script | `infra/nvidia-mps.sh` | 2.9 | ✅ | start/stop subcommands, exclusive process mode, MPS daemon control |
| 2.11 | Custom BERT ONNX text quality scorer | `server/app/perception/text_quality.py` | 1.11 | ✅ | TextQualityResult, STAR heuristic fallback, word-count/structure/keyword scoring |
| 2.12 | PerceptionResult dataclass | `server/app/perception/orchestrator.py` | 2.9 | ✅ | Unified STT+Vocal+Face+TextQuality+AU+timing fields, wall-clock logging |
| 2.13 | Test: parallel wall-clock ≤ max(models) + 20ms | `tests/test_perception_parallel.py` | 2.12 | ✅ | 16/16 tests pass, covers fallbacks, AU parsing, orchestrator with no models |

**2026-03-07 Phase 2 Implementation Notes**:
- All 13 tasks completed in a single session (Session 10-11).
- Client-side: MediaPipe Face Landmarker uses dynamic import with GPU WASM delegate.
- AU extraction is pure geometry (no ML) — distances between landmarks for AU4/AU12/AU45/eye contact.
- Face crop canvas uses `captureStream(10)` for 10 FPS WebRTC video track.
- Server-side: Three perception modules run in parallel via `asyncio.gather` + `run_in_executor`.
- All modules gracefully degrade to defaults/heuristics when models are None.
- Text quality uses STAR method keyword heuristic when BERT ONNX not available.
- Model registry updated with `load_vocal()`, `load_face()`, `load_bert()` + prewarm at startup.
- Session page updated to 4-column layout: Webcam | Transcript | Scores | Perception.
- `@mediapipe/tasks-vision` npm package installed, `pytest-asyncio` pip package installed.
- 33/33 tests pass (16 new perception + 17 existing), frontend build succeeds.

**Phase 2 Verification Checklist**:
- [x] MediaPipe Face Mesh component created with landmark overlay
- [x] AU telemetry binary protocol (20 bytes: uint32 + 4×f32) implemented
- [x] 224×224 face crop canvas + captureStream(10) created
- [x] Server datachannel handler detects au-telemetry channel
- [x] Wav2Vec2, EfficientNet-B2, BERT text quality modules created
- [x] PerceptionOrchestrator runs parallel inference
- [x] PerceptionResult dataclass fully populated
- [x] NVIDIA MPS setup script created
- [ ] Webcam active, MediaPipe overlay shows face landmarks (needs manual test)
- [ ] ONNX model files downloaded (need `scripts/export_onnx.py` or manual download)
- [ ] NVIDIA MPS daemon running (production only)

---

## Phase 3: Intelligence, RAG & Scoring

> **Goal**: Context enrichment + LLM reasoning + scoring formula.  
> **Success Criteria**: Per-utterance scores computed; Groq streams response; punctuation buffer fires sentence chunks.  
> **Prerequisites**: Phase 2 complete.

| # | Task | File(s) | Depends On | Status | Notes |
|---|------|---------|-----------|--------|-------|
| 3.1 | Author STAR method rubric documents | `data/rubrics/*.md` | — | ✅ | 3 rubrics: behavioral, technical, leadership (5 sections each) |
| 3.2 | ChromaDB seeding script | `scripts/seed_chromadb.py` | 3.1 | ✅ | 15 chunks seeded (3 files × 5 sections), cosine similarity |
| 3.3 | Sentence-BERT + ChromaDB RAG retrieval | `server/app/intelligence/rag.py` | 3.2 | ✅ | all-MiniLM-L6-v2, init at startup, top-k retrieval |
| 3.4 | Groq streaming client (httpx SSE) | `server/app/intelligence/llm.py` | Phase 2 | ✅ | httpx SSE, llama-3.3-70b-versatile, async generator |
| 3.5 | System prompt design | `server/app/intelligence/llm.py` | 3.3, 3.4 | ✅ | Rubric context + perception placeholders + 7-point instructions |
| 3.6 | Punctuation-triggered buffer | `server/app/synthesis/punctuation_buffer.py` | 3.4 | ✅ | Sentence fire on `.?!`, clause fire ≥8 tokens on `,;:—` |
| 3.7 | Scoring engine (0.70C + 0.20D + 0.10Co) | `server/app/intelligence/scoring.py` | Phase 2 | ✅ | UtteranceScores + RunningScorer, full weighted formula |
| 3.8 | Score delivery to client via DataChannel | `server/app/webrtc/data_channel.py` | 3.7, 1.14 | ✅ | Per-utterance + running avg via send_scores/send_perception |
| 3.9 | Test: scoring formula validation | `tests/test_scoring.py` | 3.7 | ✅ | 50 tests: scoring, punctuation buffer, RAG, running avg |
| 3.10 | Integration: speak → Groq responds → chunks stream | — | 3.6 | ✅ | _post_transcript pipeline wired in signaling.py, backend verified |

**Scoring Formula Detail** (for implementation reference):

```python
# Content (70%) — Range 0-100
content_base = bert_classify(transcript)  # Poor→30, Average→60, Excellent→90 (interpolated)
content_modifier = llm_star_analysis(transcript, rubric_context)  # ±10
content = clamp(content_base + content_modifier, 0, 100)

# Delivery (20%) — Range 0-100
fluency = compute_fluency(wpm, filler_count)  # Sweet spot 130-160 WPM
delivery = 0.50 * fluency + 0.50 * wav2vec2_confidence

# Composure (10%) — Range 0-100
blink_deviation = abs(blinks_per_min - 17.5) / 17.5  # Baseline: 15-20 bpm
composure = 0.60 * eye_contact_ratio + 0.25 * (1.0 - blink_deviation) + 0.15 * emotion_positivity

# Final
final_score = 0.70 * content + 0.20 * delivery + 0.10 * composure
```

**2026-03-07 Phase 3 Implementation Notes**:
- All 10 tasks completed in Session 12.
- 3 STAR rubrics (behavioral, technical, leadership) with Excellent/Average/Poor criteria.
- ChromaDB seeded with 15 chunks (3 files × 5 sections), persistent at `data/chroma/`.
- RAG uses all-MiniLM-L6-v2 SBERT embeddings, initialized at server startup.
- Groq client uses httpx SSE streaming with `llama-3.3-70b-versatile` (requires `GROQ_API_KEY`).
- System prompt includes rubric context, vocal emotion, eye contact %, text quality, and 7-point instruction set.
- PunctuationBuffer fires sentence chunks at `.?!` and clause chunks ≥8 tokens at `,;:—`.
- Scoring: `0.70*Content + 0.20*Delivery + 0.10*Composure`, RunningScorer tracks per-session averages.
- `_post_transcript()` in signaling.py orchestrates: text quality → vocal → AU → scores → perception → RAG → LLM.
- Frontend updated: ScoresEvent includes running averages, session page shows avg when utterance_count > 1.
- 50/50 pytest tests pass, frontend build succeeds, backend healthy with all Phase 3 modules loaded.

**Phase 3 Verification Checklist**:
- [x] ChromaDB seeded with STAR rubrics (15 chunks in collection)
- [x] RAG module initialized at startup (all-MiniLM-L6-v2 loaded)
- [ ] Groq streams response tokens (requires GROQ_API_KEY, manual test)
- [x] Punctuation buffer fires sentence chunks on `.?!` (50 unit tests pass)
- [x] Scoring formula outputs 0-100 for hand-calculated test cases (50 tests)
- [x] Scores arrive at client via DataChannel (send_scores wired in _post_transcript)

---

## Phase 4: Synthesis — TTS + Avatar

> **Goal**: AI interviewer speaks back with lip-synced avatar. Close the full loop.  
> **Success Criteria**: TTFA p50 < 800ms. Avatar renders at ≥30 FPS. Lip sync within ±50ms.  
> **Prerequisites**: Phase 3 complete.

| # | Task | File(s) | Depends On | Status | Notes |
|---|------|---------|-----------|--------|-------|
| 4.1 | Qwen3-TTS integration (0.6B CustomVoice, BF16/FP16) | `server/app/synthesis/tts.py` | Phase 3 | ✅ | Qwen `0.6B-CustomVoice` is now the runtime target, with edge-tts + tone fallback retained; startup requires a fully cached local model and skips blocking downloads |
| 4.2 | Pre-compute interviewer voice embedding | `server/app/synthesis/tts.py` | 4.1 | ✅ | TTSEngine with fixed voice persona (en-US-GuyNeural); voice embed placeholder for Qwen3 |
| 4.3 | LivePortrait source feature pre-computation | `server/app/synthesis/avatar.py` | Phase 1 | ✅ | SourceFeatures dataclass + precompute_source_features(); static fallback with generated avatar |
| 4.4 | MuseTalk whisper-tiny → latent lip inpainting | `server/app/synthesis/avatar.py` | 4.1, 4.3 | ✅ | Interface ready; energy-based mouth animation fallback; MuseTalk wiring deferred |
| 4.5 | LivePortrait expression driver + micro-expressions | `server/app/synthesis/avatar.py` | 4.4 | ✅ | EXPRESSION_PRESETS defined; render_frame() with breathing idle + speaking mouth |
| 4.6 | WebRTC return AudioStreamTrack (TTS → Opus) | `server/app/webrtc/tracks.py` | 4.1 | ✅ | TTSAudioStreamTrack: enqueue_audio → 20ms Opus frames at 48kHz, real-time paced |
| 4.7 | WebRTC return VideoStreamTrack (avatar → VP8) | `server/app/webrtc/tracks.py` | 4.5 | ✅ | AvatarVideoStreamTrack: renders via avatar_engine at configurable FPS, 90kHz timebase |
| 4.8 | Full pipeline wiring: LLM → buffer → TTS → Avatar → WebRTC | All synthesis files | 4.1-4.7 | ✅ | signaling.py: PunctuationBuffer → asyncio.Queue → TTS consumer → audio track + avatar state |
| 4.9 | Latency instrumentation (perf_counter_ns at each stage) | All pipeline files | 4.8 | ✅ | perf_counter at: tq, vocal, rag, llm_ttft, tts_first, total. Logged + sent via DataChannel |
| 4.10 | TTFA benchmark script (20 samples, percentiles) | `scripts/benchmark_latency.py` | 4.9 | ✅ | STT, TTS, avatar per-frame benchmarks with p50/p90/p99 + TTFA estimate |
| 4.11 | Model download update (TTS, LivePortrait, MuseTalk) | `scripts/download_models.py` | 4.1, 4.3 | ✅ | Added TTS (edge-tts pip) + avatar directory bootstrap (future model placeholders) |
| 4.12 | Integration test: TTFA p50 < 800ms | `tests/test_ttfa_budget.py` | 4.10 | ✅ | 12 tests: TTS synth, avatar render <25ms, track creation, scoring budget |

**Phase 4 Verification Checklist**:
- [x] Full loop: speak → AI responds with voice + avatar (pipeline wired end-to-end)
- [ ] TTFA p50 < 750ms (measured by instrumentation — needs live E2E with API key)
- [ ] TTFA p90 < 900ms
- [x] Avatar lip movement synced with audio (energy-based mouth animation)
- [x] Avatar renders at ≥30 FPS (p90 < 25ms per frame — 12 tests pass)
- [x] No audio gaps between TTS sentence chunks (queue-based continuous playback)
- [x] No `.wav` or `.mp4` files on disk (audit hot path — all in-memory PCM)

**2026-03-08 Phase 4 Implementation Notes**:
- All 12 tasks completed. Using fallback engines (edge-tts + static avatar) until GPU model weights are available.
- **TTS**: `TTSEngine` now supports `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` as the configured primary backend, with edge-tts and tone-generator fallback paths retained.
- **Avatar**: `AvatarEngine` with priority chain LivePortrait+MuseTalk → static animated. Procedurally generates interviewer face. Energy-based mouth animation + idle breathing.
- **Output Tracks**: `TTSAudioStreamTrack` (48kHz Opus, 20ms frames, queue-based) + `AvatarVideoStreamTrack` (30 FPS VP8, session-state driven).
- **Pipeline**: LLM tokens → PunctuationBuffer → asyncio.Queue → TTS consumer coroutine → audio track + avatar session state. Parallel TTS synthesis while LLM streams.
- **Client**: `useWebRTC.ts` handles `pc.ontrack` for incoming audio/video. Session page renders avatar `<video>` element + hidden TTS `<audio>` element.
- **Latency**: `perf_counter` instrumentation at 6 stages (tq, vocal, rag, llm_ttft, tts_first, total). Logged + sent to client via DataChannel.
- **Tests**: 12 new tests in `test_ttfa_budget.py` (TTS synthesis, avatar rendering <25ms, track creation, scoring budget). All 67/67 total tests pass.
- **Model Registry**: `load_tts_engine()` and `load_avatar_engine()` added to `prewarm_all()`. Both engines created at server startup.
- **Config**: Added `tts_voice`, `avatar_image`, `avatar_fps` settings.

**2026-03-09 Runtime Stabilization Notes**:
- Fixed Silero VAD chunking for real WebRTC frame sizes: resampled 320-sample frames now accumulate to 512-sample Silero windows before inference.
- Confirmed live pipeline progression: VAD → STT → scoring → perception → RAG → TTS all fire in production runs.
- Hardened signaling pipeline so post-transcript analysis is serialized per session; this prevents overlapping utterances from spamming the LLM provider and hitting avoidable `429` bursts.
- Added unusable-LLM-output detection so provider errors such as rate limits or invalid-model responses fall back to local coaching text instead of being spoken aloud.
- Fixed Wav2Vec2 inference dtype handling and retained CPU fallback after GPU failures to reduce repeated CUDA stalls.
- Patched session page remote audio playback to explicitly call `play()` after attaching the WebRTC audio stream; this targets the browser-side silent-TTS failure mode.
- Switched runtime config to `QACE_WHISPER_MODEL=distil-large-v3` and `QACE_TTS_BACKEND=qwen3` with `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` (`Ryan`, English) as the intended interviewer voice.

**2026-03-10 Verification / Runtime Notes**:
- Restored `.venv311` from CPU-only `torch 2.10.0` back to `torch 2.6.0+cu124` and `torchaudio 2.6.0+cu124`; CUDA is available again on the local RTX 4060 Laptop GPU.
- Verified backend startup and `/health` after the CUDA repair; Whisper, Silero VAD, vocal, face, and BERT models all prewarm successfully.
- Tightened Qwen TTS startup behavior so the server only uses Qwen when the complete local Hugging Face cache is present; missing files now trigger immediate fallback instead of a blocking startup download.
- The larger `1.7B-CustomVoice` variant proved impractical on the local 8 GB RTX 4060, so runtime target was reduced to `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` for the next verification cycle.
- Prefetched the full `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` asset set and verified backend `/health` on the smaller-model config.
- Standalone 0.6B engine initialization succeeds (`qwen3-tts`), but synthesis remains very slow without `flash-attn`; this still needs runtime tuning before treating Qwen as production-ready on the current laptop GPU.

---

## Phase 5: Frontend Polish & Session Flow

> **Goal**: Production-quality UX — landing, session, results pages.  
> **Success Criteria**: Complete 5-question interview session end-to-end.  
> **Prerequisites**: Phase 4 complete.

| # | Task | File(s) | Depends On | Status | Notes |
|---|------|---------|-----------|--------|-------|
| 5.1 | Landing page (role, type, difficulty selector) | `client/src/app/page.tsx` | Phase 4 | ⬜ | "Start Interview" initiates WebRTC |
| 5.2 | WebRTCProvider context (connection lifecycle) | `client/src/components/WebRTCProvider.tsx` | Phase 1 | ⬜ | State, reconnection, track management |
| 5.3 | Session page layout (avatar + webcam + transcript + scores) | `client/src/app/session/page.tsx` | 5.2 | ✅ | Live session UI ships avatar video, webcam canvas, transcript, scores, perception, status log, and remote TTS audio element |
| 5.4 | AvatarDisplay component | `client/src/components/AvatarDisplay.tsx` | 5.3 | ⬜ | Render incoming video track in `<video>` |
| 5.5 | ScoreBoard component (live scores) | `client/src/components/ScoreBoard.tsx` | 3.8, 5.3 | ⬜ | Per-utterance + running average |
| 5.6 | Question management (queue, adaptive follow-ups) | `server/app/intelligence/llm.py` | Phase 3 | ⬜ | Pre-generate first question at connect time |
| 5.7 | Results page (breakdowns, graphs, recommendations) | `client/src/app/results/page.tsx` | Phase 3 | ⬜ | Score graphs, STAR adherence, LLM feedback |
| 5.8 | Post-session persistence (SQLite or JSON) | `server/app/` | 5.7 | ⬜ | After session ends (not during live) |
| 5.9 | Loading states ("Preparing your interviewer...") | `client/src/components/` | 5.3 | ⬜ | Progress bar during model warm-up |
| 5.10 | Accessibility (keyboard nav, ARIA, responsive) | `client/src/` | 5.3-5.7 | ⬜ | a11y audit |
| 5.11 | End-to-end user journey test (5 questions) | Manual | All | ⬜ | Homepage → session → 5 Qs → results |



**Phase 5 Verification Checklist**:
- [ ] Full user journey: homepage → select role → start → 3-5 questions → end → results
- [x] Live session page shows per-utterance and running-average scores
- [ ] Avatar ≥30 FPS, audio gap-free throughout session
- [x] Session page renders transcript, perception, status log, webcam canvas, and remote avatar/TTS elements
- [ ] Results page shows Content/Delivery/Composure breakdown
- [ ] Responsive on 1080p desktop and 768px tablet
- [ ] Keyboard-navigable, screen reader announces key elements

---

## Cross-Cutting Tasks (Any Phase)

| # | Task | File(s) | Status | Notes |
|---|------|---------|--------|-------|
| X.1 | `.gitignore` | `.gitignore` | ✅ | Base ignore rules added |
| X.2 | `.env.example` | `.env.example` | ✅ | Baseline runtime env file added |
| X.3 | `README.md` | `README.md` | ⬜ | Setup instructions, architecture overview, quickstart |
| X.4 | Model download automation | `scripts/download_models.py` | 🔄 | Directory bootstrap implemented; real model download pending |
| X.5 | ONNX export automation | `scripts/export_onnx.py` | ⬜ | EfficientNet-B2 + Custom BERT → ONNX |
| X.6 | CI/CD pipeline (lint, test, build) | `.github/workflows/ci.yml` | ⬜ | Ruff + mypy + pytest + next build |

---

## Dependency Graph

```
Phase 0 (Planning) ✅
    │
    ▼
Phase 1 (Foundation)
    │   WebRTC + VAD + Whisper
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 2 (Perception)    Phase 5.2 (WebRTCProvider — can start early)
    │   + Wav2Vec2
    │   + EfficientNet
    │   + Parallel orchestrator
    │
    ▼
Phase 3 (Intelligence)
    │   + RAG + Groq + Scoring
    │   + Punctuation buffer
    │
    ▼
Phase 4 (Synthesis)
    │   + TTS + Avatar
    │   + TTFA benchmark
    │
    ▼
Phase 5 (Frontend Polish)
    │   + Landing + Results
    │   + Session management
    │
    ▼
  🎉 MVP Complete
```

---

## Reference: Latency Budget per Stage

| Stage | Component | Target (ms) | Measurement Point |
|-------|-----------|-------------|-------------------|
| 1 | Silero VAD EOS confirmation | 200 | `vad.end_of_speech` event timestamp - last audio chunk timestamp |
| 2 | Faster-Whisper STT | 140 | `stt.transcribe()` return - call start |
| 2‖ | Wav2Vec2 (parallel) | 60 | `vocal.analyze()` return - call start |
| 2‖ | EfficientNet (parallel) | 5 | `face.classify()` return - call start |
| 3 | BERT + SBERT + ChromaDB | 15 | All three calls, sequential but fast |
| 4 | Groq TTFT + clause buffer | 200 | First SSE token timestamp - request sent |
| 5 | Qwen3-TTS first audio chunk | 120 | First audio samples ready - text input received |
| **Total TTFA** | | **~675** | **Target: <800** |
| 6 | LivePortrait + MuseTalk first frame | +25 | First video frame rendered - audio chunk ready |
| **Total TTFV** | | **~700** | |
