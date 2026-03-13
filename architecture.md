# Q&Ace — System Architecture

> **Last Updated**: 2026-03-04  
> **Status**: Pre-Implementation (Planning Complete)  
> **Author**: Lead Systems Architect / Senior Multimodal AI Engineer

---

## 1. Mission Statement

Q&Ace is an ultra-low latency, real-time AI interview preparation platform.  
**Non-negotiable target**: Time-to-First-Audio (TTFA) < 800 milliseconds.  
**Design philosophy**: Treat like a high-frequency trading engine — every millisecond counts, disk I/O is forbidden during live sessions, parallel processing is mandatory.

---

## 2. High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Browser)                               │
│  Next.js 14 (App Router) + TailwindCSS                                  │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ MediaPipe Face    │  │ Face Crop    │  │ WebRTC PeerConnection     │ │
│  │ Mesh (WASM)       │──│ 224×224      │──│  → Audio Track (mic)      │ │
│  │                   │  │ <canvas>     │  │  → Video Track (face crop)│ │
│  │ Extracts:         │  │ captureStream│  │  → DataChannel (AU telem.)│ │
│  │  AU4 (brow lower) │  │ @ 10 FPS    │  │  ← Avatar Video Track     │ │
│  │  AU12 (lip corner)│  └──────────────┘  │  ← TTS Audio Track        │ │
│  │  AU45 (blink)     │                    │  ← DataChannel (scores)   │ │
│  │  Eye Contact Ratio│                    └───────────────────────────┘ │
│  │  Blink Rate       │                                                  │
│  └──────────────────┘                                                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ WebRTC (UDP: audio, video, data)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     GATEWAY (FastAPI + aiortc)                           │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────────────────────────────────┐ │
│  │ Signaling         │  │ Session Manager                              │ │
│  │ POST /offer       │  │  - Per-connection state dict                 │ │
│  │ ICE negotiation   │  │  - Ring buffers (numpy, in-memory)           │ │
│  │ SDP exchange      │  │  - Model inference dispatch                  │ │
│  └──────────────────┘  └──────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────┐   end_of_speech    ┌─────────────────────────────┐   │
│  │ Silero VAD   │───────────────────▶│ PERCEPTION ORCHESTRATOR     │   │
│  │ v5 (ONNX)    │   event            │ ProcessPoolExecutor         │   │
│  │ CPU, 200ms   │                    │ (3 workers, MPS-enabled)    │   │
│  │ silence thr. │                    │                             │   │
│  └──────────────┘                    │ ┌─────────┐ ┌─────────┐    │   │
│        ▲                             │ │ Faster  │ │ Wav2Vec2│    │   │
│        │ 32ms chunks                 │ │ Whisper │ │ FP16    │    │   │
│  ┌─────┴────────┐                    │ │ distil  │ │ GPU/MPS │    │   │
│  │ Ring Buffer   │                    │ │ large-v3│ │ ~60ms   │    │   │
│  │ numpy int16   │                    │ │ FP16,GPU│ │         │    │   │
│  │ 30s @ 16kHz   │                    │ │ beam=1  │ │         │    │   │
│  │ zero-copy     │                    │ │ ~140ms  │ │         │    │   │
│  └──────────────┘                    │ └────┬────┘ └────┬────┘    │   │
│                                      │      │          │          │   │
│                                      │ ┌────┴──────────┴────┐     │   │
│                                      │ │ EfficientNet-B2     │     │   │
│                                      │ │ ONNX, CPU, <5ms     │     │   │
│                                      │ │ (abdullahjamil42/    │     │   │
│                                      │ │  QnAce-Face-Model)   │     │   │
│                                      │ └────────┬────────────┘     │   │
│                                      └──────────┼──────────────────┘   │
│                                                 ▼                      │
│                                    ┌──────────────────────┐            │
│                                    │ PerceptionResult     │            │
│                                    │  .transcript         │            │
│                                    │  .word_timestamps    │            │
│                                    │  .wpm                │            │
│                                    │  .filler_words       │            │
│                                    │  .vocal_confidence   │            │
│                                    │  .pitch_contour      │            │
│                                    │  .facial_emotion     │            │
│                                    │  .au_telemetry       │            │
│                                    └──────────┬───────────┘            │
│                                               ▼                        │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ INTELLIGENCE LAYER                                                 ││
│  │                                                                    ││
│  │  ┌──────────────┐   ┌────────────────┐   ┌─────────────────────┐  ││
│  │  │ Custom BERT   │   │ Sentence-BERT  │   │ Groq API            │  ││
│  │  │ ONNX, FP16    │   │ all-MiniLM-L6  │   │ Llama 3.3 70B       │  ││
│  │  │ Baseline score│   │ + ChromaDB     │   │ SSE streaming       │  ││
│  │  │ Poor/Avg/Exc  │   │ RAG top-3      │   │ ~394 TPS output     │  ││
│  │  │ ~4ms          │   │ ~15ms total    │   │ ~200ms TTFT         │  ││
│  │  └──────┬───────┘   └──────┬─────────┘   └──────┬──────────────┘  ││
│  │         │                  │                     │                  ││
│  │         ▼                  ▼                     ▼                  ││
│  │  ┌─────────────────────────────────────────────────────────────┐   ││
│  │  │ SCORING ENGINE                                              │   ││
│  │  │ Final = (0.70 × Content) + (0.20 × Delivery) + (0.10 × Co) │   ││
│  │  └─────────────────────────────────────────────────────────────┘   ││
│  └────────────────────────────────────────────────────────────────────┘│
│                                               │                        │
│                              LLM token stream │                        │
│                                               ▼                        │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │ SYNTHESIS PIPELINE                                                 ││
│  │                                                                    ││
│  │  ┌──────────────────┐  ┌────────────────┐  ┌───────────────────┐  ││
│  │  │ Punctuation      │  │ Qwen3-TTS      │  │ LivePortrait      │  ││
│  │  │ Buffer           │──│ 0.6B BF16      │──│ + MuseTalk        │  ││
│  │  │                  │  │ Dual-track      │  │                   │  ││
│  │  │ Fires on: . ? !  │  │ streaming       │  │ Pre-computed src  │  ││
│  │  │ Also: , ; — if   │  │ ~120ms 1st chunk│  │ features (fixed   │  ││
│  │  │ clause > 8 tokens│  │ In-memory only  │  │ avatar)           │  ││
│  │  └──────────────────┘  └────────────────┘  │ ~25ms/frame       │  ││
│  │                                            │ = 40 FPS           │  ││
│  │                                            └───────────────────┘  ││
│  └───────────────────────────────┬────────────────────────────────────┘│
│                                  │                                     │
│                   WebRTC Audio + Video Tracks (return path)            │
│                                  │                                     │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   ▼
                           Back to Client Browser
```

---

## 3. Component Inventory

### 3.1 Client-Side (Frontend)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Next.js 14 (App Router) + TailwindCSS | UI shell, routing, styling |
| Vision | MediaPipe Face Mesh (WASM backend) | Extract AU4, AU12, AU45; eye contact; blink rate |
| Face Crop | HTML5 `<canvas>` (224×224) + `captureStream()` | Isolate face for server-side classification |
| Transport | WebRTC (`RTCPeerConnection`) | Bidirectional audio/video/data streaming |
| Data Sync | `RTCDataChannel` (unordered, unreliable) | AU telemetry at 10Hz, synced with media |

### 3.2 Gateway & Routing (Backend Entry)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Server | FastAPI + uvicorn | HTTP endpoints, async event loop |
| WebRTC | aiortc | Python-native WebRTC (SDP, ICE, media tracks) |
| VAD | Silero VAD v5 (ONNX, CPU) | Detect speech end, trigger inference pipeline |
| Buffering | Numpy ring buffer (30s, 16kHz mono) | In-memory audio accumulation, zero disk I/O |

### 3.3 Parallel Perception Engine

| Component | Technology | Precision | Runs On | VRAM | Latency (p50) |
|-----------|-----------|-----------|---------|------|----------------|
| STT | Faster-Whisper distil-large-v3 | FP16 (CTranslate2) | GPU | ~4.5GB | 140ms |
| Vocal Emotion | Wav2Vec2 | FP16 | GPU (MPS) | ~0.4GB | 60ms |
| Face Emotion | EfficientNet-B2 (QnAce-Face-Model) | ONNX FP16 | CPU | 0 | 5ms |
| Text Quality | Custom Fine-Tuned BERT | ONNX FP16 | GPU | ~0.3GB | 4ms |
| **Orchestration** | ProcessPoolExecutor (3 workers) | — | — | — | max(STT,Vocal,Face) |

### 3.4 Intelligence & Reasoning Core

| Component | Technology | Purpose | Latency (p50) |
|-----------|-----------|---------|----------------|
| RAG Embed | Sentence-BERT (all-MiniLM-L6-v2) | Embed transcript for retrieval | 8ms |
| RAG Store | ChromaDB (in-memory) | STAR rubric passage retrieval | 3ms |
| LLM | Llama 3.3 70B on Groq (API) | STAR analysis + follow-up generation | 200ms TTFT |
| Scoring | Custom weighted formula | 0.70C + 0.20D + 0.10Co aggregation | <1ms |

### 3.5 Synthesis & Avatar Pipeline

| Component | Technology | Purpose | Latency (p50) |
|-----------|-----------|---------|----------------|
| Sentence Buffer | Custom punctuation detector | Fire TTS on `.?!` boundaries | <1ms |
| TTS | Qwen3-TTS 0.6B (BF16, dual-track) | Streaming speech synthesis | 120ms first chunk |
| Avatar | LivePortrait + MuseTalk (FP16) | Latent lip-sync + micro-expressions | 25ms/frame |

---

## 4. VRAM Budget (Single RTX 4090 — 24GB)

| Model | Precision | VRAM | Notes |
|-------|-----------|------|-------|
| Faster-Whisper distil-large-v3 | FP16 | ~4.5GB | CTranslate2 engine |
| Wav2Vec2 | FP16 | ~0.4GB | 95M params |
| EfficientNet-B2 | ONNX | 0GB (CPU) | 9M params, CPU inference |
| Custom BERT | ONNX FP16 | ~0.3GB | 110M params |
| all-MiniLM-L6-v2 | FP16 | ~0.09GB | 22M params |
| Qwen3-TTS 0.6B | BF16 | ~1.5GB | + KV cache + codec |
| LivePortrait (all modules) | FP16 | ~1.0GB | ~130M params total |
| MuseTalk 1.5 | FP16 | ~1.8GB | UNet + VAE + whisper-tiny |
| CUDA context overhead | — | ~1.5GB | Per-process runtime |
| **TOTAL** | | **~11.1GB** | **12.9GB headroom** |

---

## 5. Critical Path — TTFA Budget

```
Event                              Component                        Duration    Cumulative
─────────────────────────────────────────────────────────────────────────────────────────
User stops speaking                                                              0ms
  │
  ├─ Silence confirmed             Silero VAD (200ms threshold)      200ms       200ms
  │
  ├─ Audio transcribed             Faster-Whisper (FP16, beam=1)     140ms       340ms
  │  (parallel: Wav2Vec2 60ms,     ProcessPoolExecutor
  │   EfficientNet 5ms)
  │
  ├─ Context enriched              BERT(4ms) + SBERT(8ms) +          15ms        355ms
  │                                ChromaDB(3ms)
  │
  ├─ LLM starts generating         Groq TTFT + first clause          200ms       555ms
  │                                (~8-12 tokens buffered)
  │
  ├─ First audio chunk ready       Qwen3-TTS (dual-track stream)     120ms       675ms
  │
  └─ CLIENT PLAYS AUDIO            ═════════════  TTFA  ═══════════          ~675ms ✅
                                                                      (target: <800ms)
  │
  └─ First video frame             LivePortrait + MuseTalk            +25ms      ~700ms
                                   (TTFV — not on audio critical path)
```

---

## 6. Transport Protocol Matrix

| Channel | Protocol | Direction | Content | Reliability |
|---------|----------|-----------|---------|-------------|
| User mic audio | WebRTC MediaStreamTrack | Client → Server | 48kHz PCM (resampled to 16kHz server-side) | Reliable (media) |
| Face crop video | WebRTC MediaStreamTrack | Client → Server | 224×224 VP8 @ 10 FPS | Reliable (media) |
| AU telemetry | RTCDataChannel | Client → Server | Binary [AU4,AU12,AU45,eye,blink] @ 10Hz | Unreliable, unordered (UDP) |
| Transcript/Scores | RTCDataChannel | Server → Client | JSON messages | Reliable, ordered |
| Avatar video | WebRTC MediaStreamTrack | Server → Client | VP8 frames @ 30 FPS | Reliable (media) |
| TTS audio | WebRTC MediaStreamTrack | Server → Client | Opus @ 24kHz | Reliable (media) |
| Signaling | HTTP POST (REST) | Bidirectional | SDP offer/answer, ICE candidates | TCP (HTTPS) |

---

## 7. Data Flow Rules (Non-Negotiable)

1. **ZERO DISK I/O** during live sessions. All media data as `np.ndarray`, `torch.Tensor`, or `io.BytesIO`. No `.wav`, `.mp4`, `.jpg` files written.
2. **PRE-WARMED MODELS**: Every model loaded into VRAM/RAM via FastAPI `lifespan` at startup. No cold starts ever.
3. **GIL BYPASS**: Heavy inference runs in `ProcessPoolExecutor`, never `asyncio` coroutines. Each worker owns its model copy.
4. **NVIDIA MPS**: Daemon active for concurrent GPU kernel execution across Whisper and Wav2Vec2 processes.
5. **UDP-FIRST TELEMETRY**: AU data via `RTCDataChannel` (unreliable, unordered) — not WebSocket.
6. **PUNCTUATION-TRIGGERED STREAMING**: TTS fires on `.?!` boundaries during LLM streaming. Never waits for full response.
7. **SOURCE FEATURE CACHING**: LivePortrait face features computed once at session start, reused every frame.
8. **RING BUFFER ARCHITECTURE**: Audio stored in pre-allocated numpy circular buffer. No dynamic allocation during streaming.

---

## 8. Monorepo Directory Structure

```
Qace_Official/
├── client/                          # Next.js 14 (App Router) + TailwindCSS
│   ├── src/
│   │   ├── app/                     # Pages: /, /session, /results
│   │   │   ├── page.tsx             # Landing: role selector, interview type, difficulty
│   │   │   ├── session/
│   │   │   │   └── page.tsx         # Live session: avatar + webcam + transcript + scores
│   │   │   └── results/
│   │   │       └── page.tsx         # Post-session: breakdowns, graphs, recommendations
│   │   ├── components/
│   │   │   ├── WebRTCProvider.tsx    # RTCPeerConnection lifecycle context
│   │   │   ├── VideoCanvas.tsx      # Invisible <canvas> for face crop + captureStream()
│   │   │   ├── MediaPipeFaceMesh.tsx # WASM face mesh → AU extraction + 224×224 crops
│   │   │   ├── AvatarDisplay.tsx    # Renders incoming avatar video track
│   │   │   └── ScoreBoard.tsx       # Live + final scoring UI
│   │   ├── hooks/
│   │   │   ├── useWebRTC.ts         # Offer/answer + ICE + track management
│   │   │   ├── useMediaPipe.ts      # Face mesh lifecycle + rAF loop
│   │   │   └── useDataChannel.ts    # RTCDataChannel for AU telemetry (UDP semantics)
│   │   └── lib/
│   │       ├── au-extractor.ts      # AU4, AU12, AU45 from landmark geometry
│   │       └── face-crop.ts         # Bounding box → 224×224 canvas drawImage
│   ├── public/
│   │   └── mediapipe/               # @mediapipe/face_mesh WASM files
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── server/                          # FastAPI + aiortc
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan startup (model pre-warming)
│   │   ├── config.py                # Pydantic Settings: model paths, Groq key, thresholds
│   │   ├── webrtc/
│   │   │   ├── __init__.py
│   │   │   ├── signaling.py         # POST /offer → SDP answer, ICE candidates
│   │   │   ├── tracks.py            # Audio/Video StreamTrack handlers (in + out)
│   │   │   └── data_channel.py      # AU telemetry receiver + score/transcript sender
│   │   ├── vad/
│   │   │   ├── __init__.py
│   │   │   ├── silero.py            # Silero VAD v5 ONNX, min_silence=200ms
│   │   │   └── ring_buffer.py       # Numpy ring buffer (30s, 16kHz, mono, int16)
│   │   ├── perception/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py      # ProcessPoolExecutor dispatch → futures.wait()
│   │   │   ├── stt.py               # Faster-Whisper distil-large-v3 FP16 beam=1
│   │   │   ├── vocal.py             # Wav2Vec2 → pitch, confidence, WPM
│   │   │   ├── face.py              # EfficientNet-B2 ONNX (CPU) → emotion class
│   │   │   └── text_quality.py      # Custom BERT ONNX → Poor/Average/Excellent
│   │   ├── intelligence/
│   │   │   ├── __init__.py
│   │   │   ├── rag.py               # Sentence-BERT embed + ChromaDB top-k retrieve
│   │   │   ├── llm.py               # Groq streaming client (httpx SSE)
│   │   │   └── scoring.py           # Weighted formula: 0.70C + 0.20D + 0.10Co
│   │   ├── synthesis/
│   │   │   ├── __init__.py
│   │   │   ├── tts.py               # Qwen3-TTS 0.6B dual-track streaming
│   │   │   ├── avatar.py            # LivePortrait + MuseTalk pipeline
│   │   │   └── punctuation_buffer.py # LLM token → sentence chunk splitter
│   │   └── models/
│   │       ├── __init__.py
│   │       └── registry.py          # Pre-warm all models at startup, health checks
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── models/                          # Downloaded model weights (GITIGNORED)
│   ├── whisper-distil-large-v3/
│   ├── wav2vec2/
│   ├── efficientnet-b2/             # ONNX exported
│   ├── bert-scorer/                 # ONNX exported
│   ├── sentence-bert/
│   ├── qwen3-tts-0.6b/
│   ├── live-portrait/
│   ├── musetalk/
│   └── silero-vad/
│
├── data/
│   ├── chroma/                      # ChromaDB persistent store (loaded to RAM at startup)
│   └── rubrics/                     # STAR method rubric documents for RAG ingestion
│
├── scripts/
│   ├── download_models.py           # Downloads all model weights
│   ├── export_onnx.py               # EfficientNet + BERT → ONNX
│   ├── seed_chromadb.py             # Ingest STAR rubrics into ChromaDB
│   └── benchmark_latency.py         # End-to-end latency profiling
│
├── infra/
│   ├── docker-compose.yml           # Single service, GPU passthrough
│   ├── Dockerfile.client            # Next.js production build
│   └── nvidia-mps.sh               # Enable NVIDIA MPS daemon
│
├── tests/
│   ├── conftest.py
│   ├── test_vad.py
│   ├── test_perception_parallel.py
│   ├── test_scoring.py
│   └── test_ttfa_budget.py          # Asserts TTFA < 800ms
│
├── docs/
│   ├── architecture.md              # THIS FILE
│   └── decisions.md                 # Architecture Decision Records
│
├── PROJECT_MEMORY.md                # Persistent state tracker (updated after every step)
├── IMPLEMENTATION_PLAN.md           # Phased task checklist with status
├── .gitignore
├── .env.example
└── README.md
```

---

## 9. Scoring Formula

$$Score_{Final} = (0.70 \times Content) + (0.20 \times Delivery) + (0.10 \times Composure)$$

### Content (70%) — Range: 0-100
- **Base**: Custom BERT → Poor(30) / Average(60) / Excellent(90) with probability interpolation
- **Modifier**: Llama 3.3 STAR-method analysis → ±10 adjustment (clamped to [0, 100])

### Delivery (20%) — Range: 0-100
- `0.50 × fluency_score(WPM, filler_count)` — Sweet spot: 130-160 WPM, penalty outside 120-180
- `0.50 × wav2vec2_confidence` — Acoustic confidence from Wav2Vec2 emotion model

### Composure (10%) — Range: 0-100
- `0.60 × eye_contact_ratio` — MediaPipe gaze vector vs. camera normal
- `0.25 × inverse_blink_rate_deviation` — Deviation from 15-20 blinks/min baseline
- `0.15 × emotion_positivity` — EfficientNet-B2 classification mapped to positivity score

---

## 10. Key Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| TTFA (p50) | < 800ms | `scripts/benchmark_latency.py` over 20 utterances |
| TTFA (p90) | < 1000ms | Same benchmark |
| Avatar FPS | ≥ 30 FPS | LivePortrait+MuseTalk per-frame timer |
| Audio-lip sync | ±50ms | Visual inspection |
| STT latency | < 150ms | Whisper inference timer |
| Model cold start | 0ms | All pre-warmed at startup |
| Disk writes (live) | 0 | Audit: no file.open('w') in hot path |
| VRAM utilization | < 18GB | `nvidia-smi` during session |
