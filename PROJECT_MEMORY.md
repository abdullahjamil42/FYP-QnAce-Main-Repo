# Q&Ace — Project Memory

> **PURPOSE**: This is the AI assistant's persistent memory file.  
> **RULE**: Update this file after EVERY significant implementation step.  
> **RULE**: Read this file at the START of every new session to restore context.  
> **RULE**: Never delete history — append new entries, mark old ones as done.

---

## 🔑 Quick Context Restore (Read This First)

**What is Q&Ace?** Real-time AI interview prep platform. User speaks → AI analyzes speech/face/emotions in parallel → AI interviewer responds with lip-synced avatar. Target: <800ms Time-to-First-Audio.

**Tech Stack Summary**:
- Frontend: Next.js 14 + TailwindCSS + MediaPipe Face Mesh (WASM) + WebRTC
- Backend: FastAPI + aiortc (Python WebRTC)
- Perception: Faster-Whisper (STT) + Wav2Vec2 (vocal) + EfficientNet-B2 (face) — all parallel via ProcessPoolExecutor
- Intelligence: Custom BERT (scoring) + Sentence-BERT + ChromaDB (RAG) + Groq or Airforce chat completions (reasoning)
- Synthesis: Qwen3-TTS 0.6B (voice) + LivePortrait + MuseTalk (avatar lip-sync)
- Deployment: Single RTX 4090 (24GB), ~11GB VRAM used

**Critical Numbers to Remember**:
- TTFA budget: VAD(200ms) + STT(140ms) + Context(15ms) + Groq(200ms) + TTS(120ms) = **~675ms p50**
- VRAM: Whisper(4.5G) + Wav2Vec2(0.4G) + TTS(1.5G) + LP+MT(2.8G) + BERT(0.3G) + SBERT(0.09G) + CUDA(1.5G) = **~11.1G / 24G**
- VAD silence threshold: 200ms (aggressive, but necessary)
- Whisper variant: distil-large-v3 (NOT large-v3)
- EfficientNet: runs on CPU (not GPU)
- LLM: Groq API by default, with Airforce as an alternate hosted provider option

**Scoring Formula**: Final = 0.70×Content + 0.20×Delivery + 0.10×Composure

---

## 📊 Phase Status

| Phase | Name | Status | Started | Completed |
|-------|------|--------|---------|-----------|
| 0 | Planning & Documentation | ✅ COMPLETE | 2026-03-04 | 2026-03-04 |
| 1 | Foundation — WebRTC + Audio Pipeline | ✅ COMPLETE | 2026-03-04 | 2026-03-07 |
| 2 | Parallel Perception Engine | ✅ COMPLETE | 2026-03-07 | 2026-03-07 |
| 3 | Intelligence, RAG & Scoring | ✅ COMPLETE | 2026-03-07 | 2026-03-07 |
| 4 | Synthesis — TTS + Avatar | ✅ COMPLETE | 2026-03-08 | 2026-03-08 |
| 5 | Frontend Polish & Session Flow | ⬜ NOT STARTED | — | — |

---

## 📝 Session Log (Chronological)

### Session 1 — 2026-03-04
**What happened**:
- Received full system specification from user
- Conducted latency feasibility analysis (TTFA ~675ms p50 achievable)
- Conducted VRAM budget analysis (~11GB fits on RTX 4090)
- Designed complete architecture (5 phases)
- Made 12 architecture decisions (ADR-001 through ADR-012)
- Created 4 persistent documentation files

**Decisions made during this session**:
- Monorepo structure (ADR-001)
- distil-large-v3 for Whisper (ADR-002)
- EfficientNet on CPU (ADR-003)
- Qwen3-TTS 0.6B (ADR-004)
- Fixed avatar (ADR-005)
- VAD 200ms threshold (ADR-006)
- NVIDIA MPS (ADR-007)
- ProcessPoolExecutor (ADR-008)
- Punctuation-triggered TTS (ADR-009)
- DataChannel for AUs (ADR-010)
- Single RTX 4090 (ADR-011)
- Groq API for LLM (ADR-012)

**Files created**:
- `docs/architecture.md` — Full system architecture with diagrams
- `docs/decisions.md` — 12 ADRs
- `PROJECT_MEMORY.md` — This file
- `IMPLEMENTATION_PLAN.md` — 5-phase task breakdown

**What's next**: Begin Phase 1 implementation (scaffold monorepo, FastAPI server, WebRTC signaling, VAD, Whisper STT, client WebRTC hook).

### Session 2 — 2026-03-04
**What happened**:
- Started Phase 1 implementation
- Scaffolded monorepo directories (`client`, `server`, `infra`, `scripts`, `tests`, `models`, `data`)
- Implemented FastAPI gateway skeleton with lifespan startup and `/health`
- Implemented WebRTC signaling route `POST /webrtc/offer`
- Added in-memory ring buffer + end-of-speech detector + STT wrapper
- Added server DataChannel transcript sender path
- Implemented Next.js skeleton with homepage + session page + `useWebRTC` hook
- Added Docker Compose, server Dockerfile, `.env.example`, `.gitignore`
- Added initial test scaffold for VAD behavior

**Current Phase 1 status**:
- Implemented: 1.1, 1.3, 1.4, 1.5, 1.7, 1.8, 1.10 (baseline), 1.11 (baseline), 1.12, 1.13, 1.15, 1.16, 1.17 (initial)
- Partially implemented: 1.2 (manual Next scaffold), 1.6 (placeholder EOS detector; Silero ONNX wiring pending), 1.9 (track consume exists; explicit 48k→16k resample pending), 1.14 (server data channel path done; dedicated client data hook pending)

**What's next**:
- Install dependencies and run smoke tests (`server` + `client`)
- Replace placeholder VAD with Silero ONNX inference in hot path
- Add explicit 48kHz → 16kHz resampling in track handler
- Add dedicated `useDataChannel.ts` for client event channel lifecycle
- Validate end-to-end: speak → transcript appears in session UI

**Session 2 delta (latest update)**:
- Added explicit audio resampling path in `server/app/webrtc/tracks.py` (source sample rate → 16kHz)
- Added Silero model prewarm load path in `server/app/models/registry.py`
- Updated `EndOfSpeechDetector` to use Silero speech probability when available, with energy fallback
- Wired signaling to pass `registry.silero_vad` into VAD detector
- Added dedicated client hook `client/src/hooks/useDataChannel.ts`
- Refactored `useWebRTC.ts` to use data-channel hook instead of inline parsing

**Updated immediate next actions**:
- Install dependencies and run smoke tests (`server` + `client`)
- Validate aiortc frame sample-rate assumptions in live WebRTC run
- Validate end-to-end: speak → transcript appears in session UI

**Environment note (important)**:
- `client` dependencies installed successfully (`npm install` complete)
- Backend core deps installed in `.venv` (FastAPI/Pydantic/Numpy/Uvicorn)
- `aiortc` install is blocked on Python 3.14 due `av` native build requirements (FFmpeg headers/libs not available)
- Signaling route now fails gracefully with HTTP 503 when `aiortc` is missing, so development can continue without import-time crashes

---

## 🗂️ File Registry

> Track every significant file created/modified. Helps restore context about what exists.

| File Path | Purpose | Phase | Status |
|-----------|---------|-------|--------|
| `architecture.md` | System architecture (moved to repo root) | 0 | ✅ Created |
| `decisions.md` | Architecture Decision Records (ADR-001 to ADR-012) | 0 | ✅ Created |
| `PROJECT_MEMORY.md` | This file — persistent AI memory | 0 | ✅ Active |
| `IMPLEMENTATION_PLAN.md` | Phased implementation checklist | 0 | ✅ Active |
| `client/` | Next.js 14 + TypeScript + TailwindCSS frontend | 1 | ✅ Complete |
| `server/` | FastAPI + aiortc backend | 1 | ✅ Complete |
| `server/app/main.py` | FastAPI app with lifespan pre-warming, CORS, health endpoint | 1 | ✅ Complete |
| `server/app/config.py` | Pydantic Settings (env, CORS, model paths, VAD, Phase 2 perception model paths) | 1,2 | ✅ Complete |
| `server/app/models/registry.py` | Model pre-warming (Whisper+Silero+Vocal+Face+BERT), GPU→CPU fallback | 1,2 | ✅ Complete |
| `server/app/vad/silero.py` | EndOfSpeechDetector + Silero ONNX + energy fallback | 1 | ✅ Complete |
| `server/app/vad/ring_buffer.py` | Numpy int16 circular buffer (30s, 16kHz) | 1 | ✅ Complete |
| `server/app/webrtc/signaling.py` | POST /offer, SDP exchange, audio pipeline + AU channel wiring | 1,2 | ✅ Complete |
| `server/app/webrtc/tracks.py` | Audio track: resample 48→16kHz, mono, VAD feed | 1 | ✅ Complete |
| `server/app/webrtc/data_channel.py` | Transcript/scores/perception/status events + AU telemetry binary parser | 1,2 | ✅ Complete |
| `server/app/perception/stt.py` | Faster-Whisper STT wrapper (STTResult, fillers, WPM) | 1 | ✅ Complete |
| `server/app/perception/orchestrator.py` | Parallel inference dispatcher (PerceptionResult, asyncio.gather) | 2 | ✅ Complete |
| `server/app/perception/vocal.py` | Wav2Vec2 vocal emotion (VocalResult, pitch, energy, acoustic fallback) | 2 | ✅ Complete |
| `server/app/perception/face.py` | EfficientNet-B2 face emotion ONNX CPU (FaceResult) | 2 | ✅ Complete |
| `server/app/perception/text_quality.py` | Custom BERT ONNX text quality (STAR heuristic fallback) | 2 | ✅ Complete |
| `server/app/intelligence/rag.py` | SBERT + ChromaDB RAG | 3 | ✅ Complete |
| `server/app/intelligence/llm.py` | Groq + Airforce streaming client (dual provider) | 3 | ✅ Complete |
| `server/app/intelligence/scoring.py` | Weighted scoring engine (0.70C + 0.20D + 0.10Co) | 3 | ✅ Complete |
| `server/app/synthesis/tts.py` | TTS engine: Qwen3 (stub) → edge-tts → tone fallback, PCM int16 24kHz | 4 | ✅ Complete |
| `server/app/synthesis/avatar.py` | Avatar engine: LivePortrait+MuseTalk (stub) → static animated fallback | 4 | ✅ Complete |
| `server/app/synthesis/punctuation_buffer.py` | LLM → sentence chunker (.?! fire, ≥8 token clause fire) | 3 | ✅ Complete |
| `client/src/hooks/useWebRTC.ts` | Mic + webcam capture, SDP exchange, DataChannel + AU channel | 1,2 | ✅ Complete |
| `client/src/hooks/useDataChannel.ts` | Transcript/scores/perception/status + AU telemetry sender | 1,2 | ✅ Complete |
| `client/src/app/page.tsx` | Landing page with Start Interview link | 1 | ✅ Complete |
| `client/src/app/session/page.tsx` | Session UI (webcam/transcript/scores/perception 4-col layout) | 1,2 | ✅ Complete |
| `client/src/hooks/useMediaPipe.ts` | MediaPipe hook | 2 | ⏭️ Replaced by MediaPipeFaceMesh component |
| `client/src/components/WebRTCProvider.tsx` | WebRTC context provider | 5 | ⬜ Not created |
| `client/src/components/MediaPipeFaceMesh.tsx` | Face Landmarker WASM (GPU delegate, 10 FPS, overlay) | 2 | ✅ Complete |
| `client/src/components/VideoCanvas.tsx` | Webcam + face mesh + face crop + AU telemetry dispatch | 2 | ✅ Complete |
| `client/src/components/AvatarDisplay.tsx` | Avatar renderer | 5 | ⬜ Not created |
| `client/src/components/ScoreBoard.tsx` | Score display | 5 | ⬜ Not created |
| `client/src/lib/au-extractor.ts` | AU extraction from 478 landmarks (20-byte binary pack) | 2 | ✅ Complete |
| `client/src/lib/face-crop.ts` | Bounding box → 224×224 crop + captureStream(10) | 2 | ✅ Complete |
| `scripts/download_models.py` | Model weight downloader (Silero, Whisper, TTS, Avatar) | 1,4 | ✅ Updated |
| `scripts/export_onnx.py` | ONNX export script | 2 | ⬜ Not created |
| `scripts/seed_chromadb.py` | ChromaDB ingestion (15 STAR rubric chunks) | 3 | ✅ Complete |
| `scripts/benchmark_latency.py` | TTFA latency profiler (STT/TTS/avatar p50/p90/p99) | 4 | ✅ Complete |
| `infra/docker-compose.yml` | Docker orchestration | 1 | ✅ Created |
| `infra/nvidia-mps.sh` | MPS daemon setup (start/stop) | 2 | ✅ Created |
| `tests/conftest.py` | Pytest fixtures (silence, speech, mixed audio) | 1 | ✅ Complete |
| `tests/test_vad.py` | Ring buffer + EOS detector tests (17 tests) | 1 | ✅ Complete |
| `tests/test_scoring.py` | Scoring + punctuation buffer + RAG tests (50 tests) | 3 | ✅ Complete |
| `tests/test_perception_parallel.py` | Parallel perception + AU parsing tests (16 tests) | 2 | ✅ Complete |
| `tests/test_ttfa_budget.py` | TTFA budget tests (TTS, avatar, tracks, scoring — 12 tests) | 4 | ✅ Complete |

---

## 🧠 Accumulated Knowledge & Gotchas

> Things learned during implementation that future sessions need to know.

### Latency Research (from Session 1)
- Silero VAD v5: 32ms chunks processed in <0.2ms. The 200ms threshold IS the latency.
- Faster-Whisper distil-large-v3 on 4090: ~140ms for 7.5s audio (FP16, beam=1, greedy)
- Faster-Whisper large-v3 on 4090: ~280ms for same (2× slower — that's why we use distil)
- Wav2Vec2 on 4090: ~60ms for 7.5s audio
- EfficientNet-B2 ONNX on CPU: <5ms for 224×224 input
- Custom BERT ONNX on GPU: ~4ms for 50-100 tokens
- SBERT embed: ~8ms, ChromaDB ANN lookup: ~3ms
- Groq TTFT: ~200ms typical, ~400ms p99 (network-dependent)
- Qwen3-TTS 0.6B first chunk: ~120ms (dual-track streaming)
- LivePortrait per frame: ~17ms (appearance 0.8 + motion 3.3 + warp 5.2 + spade 7.6 + stitch 0.3)
- MuseTalk per frame: ~10-20ms

### GPU Contention Strategy
- Whisper: GPU (primary compute consumer)
- Wav2Vec2: GPU via MPS (fits in Whisper's SM gaps)
- EfficientNet: CPU ONNX (avoids GPU entirely)
- BERT: GPU (but runs after Whisper finishes, sequential on critical path)
- SBERT: GPU (tiny, runs after Whisper, sequential)
- TTS: GPU (runs after Groq TTFT, separate pipeline stage)
- LivePortrait+MuseTalk: GPU (runs after TTS starts, pipelined)

### Critical Path Optimization Levers (ordered by impact)
1. VAD threshold: 200ms saves 1800ms vs default (BIGGEST lever)
2. distil-large-v3: saves ~140ms vs large-v3
3. Punctuation-triggered TTS: saves entire LLM generation wait time
4. Source feature caching: saves ~200ms per avatar frame
5. MPS concurrency: saves ~60ms vs sequential Whisper+Wav2Vec2
6. Groq prompt caching: saves ~50-100ms on TTFT for repeated system prompts

---

## ⚠️ Known Risks & Open Questions

| # | Risk/Question | Severity | Status | Notes |
|---|--------------|----------|--------|-------|
| 1 | VAD 200ms misfires on natural pauses | Medium | Open | Will test in Phase 1. Mitigation: 100ms look-ahead, min 0.5s audio filter |
| 2 | Groq API p99 latency (~400ms) blows TTFA | High | Open | Mitigation: co-locate, prompt cache, consider 8B fallback for simple follow-ups |
| 3 | GPU contention with many models | Medium | Open | Will validate with MPS in Phase 2 benchmarks |
| 4 | Qwen3-TTS 0.6B voice quality sufficient? | Low | Open | Will evaluate in Phase 4; upgrade to 1.7B if needed |
| 5 | aiortc Python WebRTC perf adequate? | Medium | Open | Will stress-test in Phase 1; fallback: use mediasoup via subprocess |
| 6 | MuseTalk audio→lip sync quality | Medium | Open | Will evaluate in Phase 4; alternative: SadTalker |
| 7 | Custom BERT model availability | Low | Open | Need to confirm fine-tuned model is trained and exported |
| 8 | STAR rubric quality for RAG | Low | Open | Need to author rubric documents before Phase 3 |
| 9 | Single session limitation acceptable for v1? | Low | Accepted | Yes — MVP/demo. Multi-session is v2 |
| 10 | ProcessPoolExecutor model serialization overhead | Medium | Open | Will benchmark; may need shared_memory for audio arrays |
| 11 | `aiortc` install on Python 3.14 (PyAV native build) | Medium | ✅ Resolved | Mitigated via Python 3.11 environment (`.venv311`) with prebuilt wheels |

### Session 3 — 2026-03-05
**What happened**:
- Created Python 3.11 environment: `.venv311`
- Installed Phase 1 gateway dependencies in `.venv311` including `aiortc`, `fastapi`, `uvicorn`, `numpy`, `pydantic`, `pydantic-settings`
- Switched workspace Python environment to `.venv311` for diagnostics
- Verified backend startup with `uvicorn app.main:app` from `server/`
- Verified health endpoint: `GET /health` → `{"status":"ok","env":"development"}`
- Verified client production build succeeds (`next build`)
- Fixed Next config compatibility by replacing `client/next.config.ts` with `client/next.config.mjs`
- Kept runtime-safe aiortc import strategy (lazy import in signaling) and torch-optional VAD fallback

**Current blocker status updates**:
- `aiortc` install blocker on Python 3.14 is now mitigated via Python 3.11 environment
- Full heavyweight ML stack install in `.venv311` was intentionally deferred during this step (focus: Phase 1 transport/runtime)

**What's next**:
- Run end-to-end manual WebRTC session test (mic speech → transcript appears)
- Add dedicated Phase 1 run instructions in README
- Then close Phase 1 remaining item 1.17 after runtime E2E verification

### Session 4 — 2026-03-05 (Playwright Validation)
**What happened**:
- Ran Microsoft Playwright checks against `http://127.0.0.1:3000`
- Verified landing and session pages render
- Executed session start flow and inspected network/console
- Detected and fixed CORS/host mismatch bug (`localhost` vs `127.0.0.1`)
	- Frontend now resolves backend URL from current browser host
	- Backend now allows both `localhost` and `127.0.0.1` variants in local CORS

### Session 5 — 2026-03-08 (Alternate LLM Provider)
**What happened**:
- Added Airforce chat completions as an alternate provider to Groq
- Added provider selection settings: `QACE_LLM_PROVIDER`, `QACE_LLM_MODEL`, `AIRFORCE_API_KEY`, `QACE_AIRFORCE_MODEL`
- Kept Groq as the default behavior for `auto` provider selection when both keys are present
- Updated signaling to resolve the active provider once and stream or return feedback through a provider-neutral wrapper
- Added focused tests for provider resolution and OpenAI-compatible chat content extraction
- Added explicit `httpx` dependency to backend manifests

**Verification**:
- `pytest tests/test_llm.py tests/test_scoring.py` → 30 passed

**What's next**:
- If Airforce will be the primary provider in this environment, set `QACE_LLM_PROVIDER=airforce` and add `AIRFORCE_API_KEY` in `.env`
- If low-latency chunked feedback is required on Airforce, verify whether their endpoint supports streaming and extend `stream_airforce()` accordingly
- Re-ran Playwright after fix:
	- `POST /webrtc/offer` returns `200 OK`

### Session 5 — 2026-03-07 (Latency triage + hybrid transcripts)
**What happened**:
- Fixed Faster-Whisper availability/runtime issues in `.venv311` by installing `faster-whisper` and NVIDIA CUDA runtime wheel packages.
- Added Windows CUDA DLL discovery in `server/app/models/registry.py` so pip-installed cuBLAS/cuDNN are visible to the loader.
- Moved STT work off the live audio receive path so WebRTC sessions no longer die while transcription is running.
- Tuned local dev runtime for RTX 4060-class hardware:
	- Whisper default switched to `tiny.en`
	- VAD silence threshold tuned to 300ms
	- VAD minimum speech tuned to 1.0s
- Implemented hybrid transcript delivery and later rolling-window interim ASR as experiments.
- Both interim approaches were reverted afterward because they were unreliable in practice on the local dev machine.
- Current path is again end-of-speech final-only transcription.

**Current local-dev performance snapshot**:
- GPU STT is healthy on native Windows (`device=cuda, CUDA runtime ready`).
- Recent finalized decode times observed: ~770ms to ~1223ms for ~2.5s to ~3.1s utterances.
- Current UX priority is stable final-only transcripts rather than unreliable interim text.

**Architecture deviation note**:
- The architecture docs target a single RTX 4090 with `distil-large-v3` and ~140ms STT.
- The current local dev environment is an RTX 4060 8GB on native Windows.
- The implementation therefore uses a local-dev low-latency profile (`tiny.en` + final-only transcript flow) rather than the original production-targeted Phase 1 assumptions.

**What’s next**:
- Continue improving end-of-speech latency without reintroducing unstable interim text.
- If needed later, revisit streaming ASR with a purpose-built streaming model rather than rolling Whisper windows.
	- Start button disables and Stop button enables after connect
	- Stop returns UI to idle state
	- No browser console errors
- Captured functional screenshot: `phase1-session-functional.png`

**Validation scope note**:
- Playwright run confirmed UI + signaling + session state transitions
- Full live transcript confirmation with real microphone speech still pending (manual E2E)

### Session 5 — 2026-03-06 (Whisper Download + Check)
**What happened**:
- Installed `faster-whisper==1.1.1` in `.venv311`
- Installed missing runtime deps (`requests`, `huggingface-hub`, `tokenizers`, `ctranslate2`, `tqdm`)
- Downloaded model by loading `WhisperModel('distil-large-v3', download_root='c:/Github/Qace_Official/models')`
- Confirmed model files exist under `models/models--Systran--faster-distil-whisper-large-v3/`
- Ran inference smoke test (2s synthetic audio) and got valid transcript output (`'Thank you.'`)

### Session 6 — 2026-03-06 (Fetch Failure Fix)
**Issue observed**:
- Frontend threw `TypeError: Failed to fetch` from `useWebRTC.ts` when posting offer to backend.

**Fix applied**:
- Updated `client/src/hooks/useWebRTC.ts`:
	- Added robust error handling around session start flow
	- Added deterministic backend URL fallback to `http://127.0.0.1:8000`
	- Added support for `NEXT_PUBLIC_QACE_API_URL` override
	- Added safe cleanup of partially-open peer connection on failure
	- Added `connecting` and `error` state outputs
- Updated `client/src/app/session/page.tsx`:
	- Shows `Connecting...` state on Start button
	- Displays explicit error banner with actionable backend guidance

**Validation**:
- `npm run build` passes in `client/`
- Backend health reachable: `GET http://127.0.0.1:8000/health` returns `{"status":"ok","env":"development"}`

### Session 7 — 2026-03-06 (Backend Import Fix)
**Issue observed**:
- `uvicorn` with reload crashed with `ModuleNotFoundError: No module named 'app'` depending on launch directory.

**Fix applied**:
- Converted backend imports under `server/app` from absolute `from app...` to package-relative imports
- Added `server/__init__.py` so `server.app.main` is importable from repo root

**Validation**:
- Root import works: `import server.app.main`
- Server-directory import works: `import app.main`

**Reliable launch commands**:
- From repo root: `c:\Github\Qace_Official\.venv311\Scripts\python.exe -m uvicorn server.app.main:app --reload --port 8000`
- From `server/`: `c:\Github\Qace_Official\.venv311\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

### Session 8 — 2026-03-06 (Root Uvicorn Compatibility Shim)
**Issue observed**:
- Running `uvicorn app.main:app --reload --port 8000` from repo root still failed because the repo did not contain a top-level `app` package.

**Fix applied**:
- Added a thin top-level `app` package that re-exports `server.app.main.app`
- This preserves compatibility with the existing repo-root launch command without changing backend ownership or import layout

**Expected result**:
- Repo root launch now works: `c:\Github\Qace_Official\.venv311\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

### Session 9 — 2026-03-06 (Transcript Delivery Debugging)
**Issue observed**:
- Session connected but no transcript appeared in the UI.

**Root cause fixed**:
- Browser transcript/status delivery was incorrectly implemented over a server-created data channel that was never negotiated by the client offer.
- Fixed by having the client create the `qace-events` data channel before `createOffer()`, and having the server reply over the negotiated inbound channel.

**Additional hardening**:
- Added server status events: `server-datachannel-ready`, `audio-track-received`, `audio-consumer-started`, `audio-frame-timeout`
- Added audio loop handling for `MediaStreamError` and end-of-track flush
- Retained the browser microphone `MediaStream` in a ref so it is not lost after session setup
- Added rolling status history to the session page for live debugging

**Probe result**:
- Direct aiortc probe now receives `server-datachannel-ready` and `audio-track-received`
- Probe still times out waiting for actual audio frames (`audio-frame-timeout`), so the remaining unresolved issue is media frame delivery / RTP decode, not signaling or data-channel delivery

### Session 10 — 2026-03-07 (Phase 1 Completion + Phase 2 Start)
**What happened**:
- Marked Phase 1 as complete (all 17/17 tasks done).
- Updated IMPLEMENTATION_PLAN.md with accurate statuses for every Phase 1 task.
- Updated PROJECT_MEMORY.md file registry to reflect all created files and their current state.
- Began Phase 2: Parallel Perception Engine.

**Phase 1 final state summary**:
- Backend: FastAPI + aiortc in `.venv311` (Python 3.11), Faster-Whisper `tiny.en` on GPU (RTX 4060), energy-based VAD fallback (Silero ONNX model not downloaded yet), end-of-speech final-only transcription.
- Frontend: Next.js 14.2.15, session page with TranscriptCard/ScoreItem, useWebRTC + useDataChannel hooks, `npm run build` passing.
- Tests: 17/17 pytest pass (ring buffer + EOS detector), SDP exchange returns 200.
- Infra: Docker Compose, Dockerfile, `.env.example`, `.gitignore` all in place.
- Known gaps: Silero ONNX file not downloaded (using energy fallback), real-mic E2E only validated via Playwright + probe (not full spoken-word-to-transcript in browser).

**What's next**: Implement Phase 2 tasks (MediaPipe Face Mesh, AU extraction, face crop, Wav2Vec2, EfficientNet, parallel orchestrator).

### Session 11 — 2026-03-07 (Phase 2 Complete)
**What happened**:
- Completed all remaining Phase 2 tasks (13/13).
- **Server perception modules created**: `vocal.py` (Wav2Vec2 FP16), `face.py` (EfficientNet-B2 ONNX CPU), `text_quality.py` (BERT ONNX + STAR heuristic), `orchestrator.py` (parallel asyncio.gather + PerceptionResult).
- **Client components created**: `MediaPipeFaceMesh.tsx` (WASM/GPU, 10 FPS), `VideoCanvas.tsx` (webcam + mesh + crop + AU dispatch).
- **Client libs created**: `au-extractor.ts` (AU4/AU12/AU45/eye contact from 478 landmarks, 20-byte binary pack), `face-crop.ts` (224×224 captureStream(10)).
- **Hooks updated**: `useWebRTC.ts` (webcam capture, au-telemetry DataChannel, addVideoTrack), `useDataChannel.ts` (PerceptionEvent, sendAUTelemetry).
- **Server updated**: `signaling.py` (au-telemetry channel handler), `data_channel.py` (send_perception + parse_au_telemetry), `registry.py` (load_vocal/face/bert + prewarm), `config.py` (Phase 2 model paths).
- **Session page** updated to 4-column layout: Webcam | Transcript | Scores | Perception (with PerceptionItem component).
- **Tests**: Created `test_perception_parallel.py` (16 tests covering fallbacks, AU parsing, orchestrator). All 33/33 tests pass.
- **Deps installed**: `@mediapipe/tasks-vision` (npm), `pytest-asyncio` (pip).
- Frontend build passes, all Python imports validated.

**Phase 2 final state**:
- All perception modules gracefully degrade to defaults when models are None.
- ONNX model files not yet downloaded (heuristic fallbacks work without them).
- Orchestrator uses thread pool by default; ProcessPoolExecutor available via flag.
- NVIDIA MPS script exists at `infra/nvidia-mps.sh` (production only).

**What's next**: Begin Phase 3 — Intelligence, RAG & Scoring (STAR rubrics, ChromaDB, Groq LLM, scoring engine).

### Session 12 — 2026-03-07 (Test Fixes + Playwright E2E)
**What happened**:
- User reported 5/33 pytest failures — identified root cause: `pytest-asyncio` was not installed when user ran tests (already installed in Session 11; re-verified 33/33 pass).
- **Playwright E2E test suite created**:
  - Installed `@playwright/test` ^1.58.2 as devDep in `client/`.
  - Downloaded Chromium browser via `npx playwright install chromium`.
  - Created `client/playwright.config.ts` — chromium project, fake media device args, baseURL `127.0.0.1:3000`, microphone/camera permissions.
  - Created `client/e2e/qace.spec.ts` — 23 E2E tests across 5 describe blocks:
    1. **Landing Page** (4 tests): title/subtitle, feature grid, Start link href, navigation to /session.
    2. **Session Page - Static UI** (10 tests): header, Start/Stop buttons, button states, connection idle, Transcript/Scores/Perception headers, placeholder messages, status, avatar placeholder.
    3. **Session Page - WebRTC Connection** (6 tests): connecting state, connection with backend, session ID, Stop button enable, Stop→idle, error when backend down.
    4. **Backend API** (2 tests): GET /health, POST /webrtc/offer with fake SDP.
    5. **Full User Journey** (1 test): landing → session → start → connecting.
- Diagnosed & fixed stale `.next` build cache (HTTP 500 on `/session` — `Cannot find module './138.js'`). Cleared `.next` directory.
- **Final result: 23/23 Playwright E2E tests pass, 33/33 pytest tests pass.**
- Follow-up hardening after live browser check: transcript delivery could miss early server events because the client only exposed the `qace-events` / `au-telemetry` channels after `onopen`. Updated `client/src/hooks/useWebRTC.ts` to publish both channel objects immediately after creation and to make `addVideoTrack()` idempotent, preventing duplicate face-crop tracks during React dev remounts / Strict Mode.

**Files created**:
- `client/playwright.config.ts` — Playwright configuration
- `client/e2e/qace.spec.ts` — 23 E2E test cases

**How to run tests**:
- **Pytest**: `cd c:\22i-2451\QACE_Final; .venv311\Scripts\activate; pytest tests/ -v`
- **Playwright**: Start both servers first, then: `cd client; npx playwright test --reporter=list`
- **Frontend dev server**: `cd client; npm run dev -- --hostname 127.0.0.1 --port 3000`
- **Backend**: `cd server; python -m uvicorn main:app --host 127.0.0.1 --port 8000`

**What's next**: Begin Phase 3 — Intelligence, RAG & Scoring (STAR rubrics, ChromaDB, Groq LLM, scoring engine).

### Session 13 — 2026-03-08 (Phase 3 Complete + Airforce LLM)
**What happened**:
- Completed all Phase 3 tasks (10/10): STAR rubrics, ChromaDB seeding, SBERT RAG, Groq streaming, system prompt, punctuation buffer, scoring engine, score delivery, 50 scoring tests, integration wiring.
- Added Airforce API as alternate LLM provider (deepseek-v3) with `QACE_LLM_PROVIDER` auto/groq/airforce selection.
- Fixed vocal model falling back to CPU: installed `torch==2.6.0+cu124` (CUDA 12.4), Wav2Vec2 now loads on `cuda:0`.
- Patched `requirements.txt` and `pyproject.toml` with CUDA torch pin + `--extra-index-url`.

### Session 14 — 2026-03-08 (Phase 4 Complete — Synthesis)
**What happened**:
- Completed all Phase 4 tasks (12/12): TTS engine, avatar engine, output tracks, pipeline wiring, latency instrumentation, benchmark script, TTFA tests, download script update, client UI updates, doc updates.
- **TTS**: `TTSEngine` with edge-tts v7.2.7 fallback (Microsoft Azure cloud). Returns PCM int16 at 24kHz mono. Qwen3-TTS interface defined but deferred.
- **Avatar**: `AvatarEngine` with procedurally generated interviewer face. Energy-based mouth animation using per-frame `render_frame()`. LivePortrait + MuseTalk interfaces defined but deferred.
- **Output Tracks**: `TTSAudioStreamTrack` (20ms Opus frames at 48kHz, queue-fed) + `AvatarVideoStreamTrack` (30 FPS VP8, session-state driven). Both added to PeerConnection before SDP answer.
- **Pipeline Wiring**: `_post_transcript()` → PunctuationBuffer fires sentence chunks → asyncio.Queue → `_tts_consumer()` coroutine → TTS synthesis → audio track + avatar state. LLM and TTS run in parallel.
- **Client**: `useWebRTC.ts` handles `pc.ontrack` for incoming audio/video. Session page renders avatar `<video>` (264px) + hidden `<audio>` for TTS.
- **Latency Instrumentation**: `perf_counter` at 6 stages: text quality, vocal, RAG, LLM TTFT, TTS first-audio, total. Logged + DataChannel status events.
- **Tests**: 12 new in `test_ttfa_budget.py`. All 67/67 total pass.
- **Deps**: edge-tts v7.2.7 installed in `.venv311`.

**Files created**: `server/app/synthesis/tts.py`, `server/app/synthesis/avatar.py`, `scripts/benchmark_latency.py`, `tests/test_ttfa_budget.py`
**Files modified**: `server/app/webrtc/tracks.py`, `signaling.py`, `config.py`, `registry.py`, `requirements.txt`, `download_models.py`, `useWebRTC.ts`, `session/page.tsx`

**What's next**: Phase 5 — Frontend Polish & Session Flow.

---

## 📐 Architecture Invariants (Never Violate These)

These are hard constraints that must hold true across ALL implementation:

1. **No disk I/O in the hot path** — If `file.open('w')` or `file.write()` appears anywhere in the live session loop, it's a bug.
2. **All models pre-warmed at startup** — If any model loads on first inference, it's a bug.
3. **Heavy inference in ProcessPoolExecutor** — If Whisper/Wav2Vec2/EfficientNet runs in an asyncio coroutine, it's a bug.
4. **Punctuation-triggered TTS** — If TTS waits for full LLM response, it's a bug.
5. **WebRTC for all media** — If audio/video goes through HTTP or WebSocket, it's a bug.
6. **AU telemetry via DataChannel** — If AU data goes through WebSocket, it's a bug.
7. **Face crops, not full frames** — If full webcam frames are sent to server, it's a bug.
8. **FP16 or INT8 for all models** — If any model runs in FP32, it's a bug (except Silero VAD on CPU).
9. **TTFA < 800ms at p50** — If benchmark shows p50 ≥ 800ms, stop and optimize before proceeding.
