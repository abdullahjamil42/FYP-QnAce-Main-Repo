# Q&Ace — Architecture Decision Records (ADR)

> **Last Updated**: 2026-03-04  
> **Convention**: Each ADR is numbered sequentially. Status = Accepted | Superseded | Deprecated.  
> **Rule**: Never delete an ADR. If a decision changes, mark the old one Superseded and create a new one.

---

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| 001 | Monorepo over Polyrepo | Accepted | 2026-03-04 |
| 002 | distil-large-v3 over large-v3 for Whisper | Accepted | 2026-03-04 |
| 003 | EfficientNet-B2 on CPU (ONNX) not GPU | Accepted | 2026-03-04 |
| 004 | Qwen3-TTS 0.6B over 1.7B | Accepted | 2026-03-04 |
| 005 | Fixed avatar (single interviewer persona) | Accepted | 2026-03-04 |
| 006 | Silero VAD silence threshold = 200ms | Accepted | 2026-03-04 |
| 007 | NVIDIA MPS for GPU concurrency | Accepted | 2026-03-04 |
| 008 | ProcessPoolExecutor over asyncio for inference | Accepted | 2026-03-04 |
| 009 | Punctuation-triggered TTS streaming | Accepted | 2026-03-04 |
| 010 | RTCDataChannel for AU telemetry (not WebSocket) | Accepted | 2026-03-04 |
| 011 | Single RTX 4090 deployment | Accepted | 2026-03-04 |
| 012 | Groq API for LLM (not local) | Accepted | 2026-03-04 |

---

## ADR-001: Monorepo over Polyrepo

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: We need a structure for frontend (Next.js), backend (FastAPI), model weights, infrastructure configs, and documentation.

**Decision**: Single monorepo (`Qace_Official/`) with `/client`, `/server`, `/models`, `/data`, `/scripts`, `/infra`, `/tests`, `/docs` directories.

**Rationale**:
- Simpler CI/CD for a single-team project
- Shared scripts (download_models, export_onnx) live alongside the code they serve
- Docker Compose orchestrates from one repo
- No cross-repo version sync headaches
- Atomic commits across frontend + backend changes

**Consequences**:
- Model weights (multi-GB) are gitignored; downloaded via `scripts/download_models.py`
- Git history may grow large — use shallow clones for CI

---

## ADR-002: distil-large-v3 over large-v3 for Whisper

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Faster-Whisper `large-v3` takes ~280ms for a 7.5s utterance on RTX 4090 (FP16, beam=1). This consumes 35% of our 800ms TTFA budget.

**Decision**: Use `distil-large-v3` which halves inference time to ~140ms.

**Rationale**:
- Saves ~140ms — the single largest latency improvement available
- WER penalty is ~5% (negligible for interview transcription of conversational English)
- Same VRAM footprint (~4.5GB FP16)
- Greedy decoding (beam=1) adds another 30-50% speedup

**Tradeoff**: Slightly lower accuracy on:
- Heavily accented speech
- Domain-specific terminology
- Low-quality microphone input

**Escape hatch**: If transcription quality is unacceptable, swap to `large-v3` and accept 800ms p50 becoming ~815ms (marginal). Or use Whisper-turbo as an alternative.

---

## ADR-003: EfficientNet-B2 on CPU (ONNX) instead of GPU

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: EfficientNet-B2 (`abdullahjamil42/QnAce-Face-Model`) is 9M params. Running it on GPU would compete with Whisper and Wav2Vec2 for CUDA cores and scheduling.

**Decision**: Export to ONNX, run via `onnxruntime` CPUExecutionProvider.

**Rationale**:
- Inference takes <5ms on CPU — negligible vs. other components
- Eliminates GPU contention entirely for this model
- ONNX CPU has no CUDA context overhead (saves ~500MB VRAM from not needing a CUDA context)
- Model is small enough that CPU inference is I/O-bound to cache, not compute-bound

**Consequences**:
- CPU must have spare cores (not a concern on modern server CPUs with 8+ cores)
- Must export model to ONNX via `scripts/export_onnx.py` before deployment

---

## ADR-004: Qwen3-TTS 0.6B over 1.7B

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Qwen3-TTS comes in 0.6B and 1.7B parameter variants. Both support dual-track streaming.

**Decision**: Use 0.6B.

**Rationale**:
- **VRAM**: 1.5GB vs 4GB — saves 2.5GB, keeping total VRAM at ~11GB (within 24GB card with ample headroom)
- **Latency**: First-chunk ~120ms vs ~200ms — saves 80ms on critical path
- **Quality**: Speech quality is sufficient for a professional interviewer voice in English
- Dual-track streaming supported on both variants

**Tradeoff**:
- 1.7B has richer prosody, more natural pausing, better emotional inflection
- 1.7B handles unusual names/terms more reliably

**Escape hatch**: Upgrade to 1.7B later if quality feedback demands it and VRAM allows (still fits on 4090 with ~8.5GB headroom).

---

## ADR-005: Fixed avatar (single interviewer persona)

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: LivePortrait requires source face feature extraction (appearance, keypoints, rotation, translation, scale). This takes ~200ms per face and produces features `f_s`, `x_s`, `R_s`, `t_s`, `scale_s`.

**Decision**: Single fixed interviewer face image. Pre-compute all source features once at session start and cache in session state. Reuse for every frame during the live session.

**Rationale**:
- Eliminates 200ms per-frame penalty
- Consistent visual persona builds user trust during interview simulation
- Simplifies asset management (one face image, one voice embedding)
- Source features are ~10KB — trivial memory footprint

**Consequences**:
- Multi-avatar support (selectable or user-uploaded) deferred to future version
- Adding multi-avatar will require: avatar selection UI, per-avatar pre-computation cache, voice embedding mapping
- The architecture supports this extension: just compute multiple source feature sets at startup

---

## ADR-006: Silero VAD silence threshold = 200ms

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Default Silero VAD `min_silence_duration_ms` is 2000ms. This alone would consume 2.5× our entire 800ms TTFA budget before any inference begins.

**Decision**: Set `min_silence_duration_ms=200`.

**Rationale**:
- Saves 1800ms vs default — the single most impactful configuration change
- Silero v5 processes 32ms chunks in <0.2ms — detection accuracy is maintained at this threshold
- 200ms of silence is a natural micro-pause between sentences

**Tradeoff**: Will occasionally misfire on:
- Natural thinking pauses ("umm..." followed by 200ms silence mid-thought)
- Speakers with slower cadence or deliberate pauses

**Mitigations**:
1. Implement a 100ms "look-ahead" confirmation window (if speech resumes within 100ms, cancel the EOS event)
2. Allow user to interrupt the AI response (press-to-talk or voice interrupt)
3. If the extracted audio segment is < 0.5s, treat as noise and skip inference
4. Can tune up to 250ms if false-positive rate is > 10% in testing

---

## ADR-007: NVIDIA MPS for GPU concurrency

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Whisper (GPU) and Wav2Vec2 (GPU) need to run in parallel. Options:
- Same process, separate CUDA streams → time-slicing, not true parallelism
- Separate processes, no MPS → expensive CUDA context switches (~500MB overhead each)
- Separate processes, MPS enabled → true concurrent kernels, shared CUDA context

**Decision**: Enable NVIDIA Multi-Process Service (MPS). Run Whisper and Wav2Vec2 in separate `ProcessPoolExecutor` workers sharing the GPU via MPS.

**Rationale**:
- True concurrent kernel execution from different processes
- Wav2Vec2 (~60ms, smaller model) fits into Whisper's SM utilization gaps
- MPS shares a single CUDA context — avoids per-process ~500MB overhead
- Total parallel perception time ≈ max(Whisper, Wav2Vec2) ≈ 140ms, not sum ≈ 200ms

**Prerequisites**:
- Volta+ architecture (RTX 4090 = Ada Lovelace ✓)
- Must start `nvidia-cuda-mps-control` daemon before server launch (see `infra/nvidia-mps.sh`)
- MPS server process must run as same user as inference processes

**Consequences**:
- Added operational complexity (MPS daemon lifecycle management)
- MPS error isolation is weaker (one process crash can affect others sharing MPS)
- Must be disabled for debugging (MPS interferes with `cuda-gdb`)

---

## ADR-008: ProcessPoolExecutor over asyncio for inference

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Python's GIL prevents true parallelism in `asyncio` tasks. AI model inference is CPU/GPU-bound, not I/O-bound.

**Decision**: Use `concurrent.futures.ProcessPoolExecutor(max_workers=3)` for perception (STT, Vocal, Face). Models pre-loaded in each worker via pool `initializer` function.

**Rationale**:
- GIL bypass — each process has its own Python interpreter
- True parallel execution on CPU and GPU
- `concurrent.futures.wait(return_when=ALL_COMPLETED)` blocks only for the slowest model
- Clean API: submit/future/result pattern

**Implementation details**:
- Pool `initializer` loads the model once per worker process (not per inference call)
- Workers are long-lived (created at server startup, destroyed at shutdown)
- Audio data passed to workers via `multiprocessing.shared_memory` or numpy serialization

**Consequences**:
- Higher memory: ~3 Python processes × ~200MB base = ~600MB extra
- Model duplication in process memory (mitigated by MPS sharing GPU memory)
- Must handle worker crashes gracefully (pool auto-replaces dead workers)

---

## ADR-009: Punctuation-triggered TTS streaming

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Groq streams LLM tokens at ~394 TPS. Waiting for the full response before starting TTS would add 500-2000ms to TTFA.

**Decision**: Accumulate LLM tokens in a string buffer. Fire to Qwen3-TTS the instant a sentence-ending punctuation (`.`, `?`, `!`) is detected. Also support clause boundaries (`,`, `;`, `—`, `:`) if the clause exceeds 8 tokens.

**Rationale**:
- First TTS chunk fires after just ~8-15 tokens (~35ms of Groq output at 394 TPS)
- TTS begins synthesis while LLM is still generating remaining sentences
- Pipelining saves the full LLM generation time from the TTFA critical path
- Natural sentence boundaries produce better TTS prosody than arbitrary token counts

**Token accumulation rules**:
1. On `.`, `?`, `!` → immediately detach and send to TTS (regardless of length)
2. On `,`, `;`, `—`, `:` → if accumulated tokens > 8, detach and send
3. On stream end → flush remaining buffer to TTS
4. Never send < 3 tokens to TTS (would produce choppy audio)

**Consequences**:
- TTS prosody at sentence boundaries may be slightly less natural than full-paragraph synthesis
- Must handle edge cases: abbreviations ("Dr."), decimal numbers ("3.14"), URLs
- Clause-level splitting may occasionally break mid-phrase; the 8-token minimum mitigates this

---

## ADR-010: RTCDataChannel for AU telemetry (not WebSocket)

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: MediaPipe AU values update at 10Hz from the client. Need to arrive at the server synchronized with the audio/video media packets.

**Decision**: Use `RTCDataChannel` configured with `ordered: false, maxRetransmits: 0` (UDP-like semantics).

**Rationale**:
- Same transport layer as media streams → inherently synchronized timing
- No WebSocket TCP overhead (no head-of-line blocking, no TCP retransmission delay)
- Dropped packets are acceptable — AUs are high-frequency telemetry, latest value is sufficient
- Lower latency than WebSocket for small, frequent messages

**Binary protocol** (per message, 20 bytes):
```
[timestamp: uint32][AU4: float32][AU12: float32][AU45: float32][eye_contact: float32]
```

**Consequences**:
- Must handle occasional dropped telemetry packets gracefully (use last-known-good value)
- No guaranteed ordering — but at 10Hz, out-of-order delivery is rare and the timestamp resolves it
- Slightly more complex client code than WebSocket

---

## ADR-011: Single RTX 4090 deployment

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Total VRAM needed is ~11GB across all models. RTX 4090 has 24GB GDDR6X. A100 has 40/80GB HBM.

**Decision**: Target single RTX 4090 (24GB) for all local inference. Groq API handles the 70B LLM remotely.

**Rationale**:
- 13GB headroom for KV caches, batch fluctuations, and CUDA workspace
- A100 not required — significant cost savings ($1,600 vs $10,000+)
- All models fit simultaneously; no model swapping or offloading needed
- RTX 4090 Ada Lovelace has excellent FP16/INT8 throughput (82.6 TFLOPS FP16)

**Consequences**:
- Supports **single concurrent session** only (all VRAM/compute dedicated to one user)
- Multi-session would require:
  - Model sharing via batched inference, or
  - Multiple GPUs (e.g., 2× 4090), or
  - Lighter models with quality tradeoff
- Acceptable for MVP/v1; multi-session is a v2 concern

---

## ADR-012: Groq API for LLM (not local)

**Date**: 2026-03-04  
**Status**: Accepted

**Context**: Llama 3.3 70B requires ~35-40GB VRAM in FP16. Cannot fit alongside other models on a single RTX 4090 (24GB).

**Decision**: Use Groq's hosted LPU inference API.

**Rationale**:
- ~394 TPS output speed — faster than any local GPU for a 70B model
- TTFT ~200ms including network RTT (Groq's LPU processes prompts in hardware)
- Offloads the single largest model from local VRAM entirely (0GB local)
- Prompt caching: identical system prompts across turns get cached prefill (50% cost reduction, faster TTFT)
- Pay-per-token pricing (no idle GPU cost)

**Tradeoff**:
- **Network dependency**: introduces latency variance (p99 ~400ms TTFT)
- **Availability**: Groq outage = no LLM reasoning (no local fallback for 70B)
- **Cost**: Per-token API fees (but much cheaper than renting a dedicated A100)

**Mitigations**:
- Co-locate server near Groq's US data centers (< 20ms network RTT)
- Keep persistent HTTPS connection (avoid TLS handshake per request)
- For simple follow-ups, consider Groq's Llama 3.1 8B (~840 TPS, ~50% lower TTFT)
- Cache common system prompts to trigger Groq's prompt caching
