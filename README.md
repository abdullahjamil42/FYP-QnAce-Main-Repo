# QACE Final

Real-time AI interview preparation system with:
- Next.js frontend (WebRTC client)
- FastAPI backend (speech pipeline)
- STT + scoring + RAG + LLM + TTS

## 1. Prerequisites

- Windows 10/11
- Python 3.11
- Node.js 20+
- Git
- NVIDIA driver compatible with CUDA 12.4 (for GPU acceleration)

## 2. Clone

```powershell
git clone https://github.com/abdullahjamil42/FYP-QnAce-Main-Repo.git
cd FYP-QnAce-Main-Repo
```

## 3. Backend Setup

From repository root:

```powershell
python -m venv .venv311
.\.venv311\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r server\requirements.txt
```

Optional verification:

```powershell
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
```

## 4. Frontend Setup

```powershell
cd client
npm install
cd ..
```

## 5. Environment File

Create `.env` in repository root (do not commit secrets):

```env
QACE_ENV=development
QACE_HOST=0.0.0.0
QACE_PORT=8000
QACE_LOG_LEVEL=info

QACE_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

QACE_LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
QACE_GROQ_MODEL=llama-3.3-70b-versatile

QACE_MODEL_DIR=C:/path/to/FYP-QnAce-Main-Repo/models
QACE_WHISPER_MODEL=small.en
QACE_SILERO_ONNX=C:/path/to/FYP-QnAce-Main-Repo/models/silero-vad/silero_vad.onnx

QACE_VOCAL_MODEL=ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition
QACE_VOCAL_DEVICE=cpu

QACE_FACE_ONNX=C:/path/to/FYP-QnAce-Main-Repo/models/face-emotion/efficientnet_b2.onnx
QACE_BERT_ONNX=C:/path/to/FYP-QnAce-Main-Repo/models/text-quality/bert_quality.onnx
QACE_BERT_TOKENIZER=C:/path/to/FYP-QnAce-Main-Repo/models/text-quality

QACE_CHROMA_DIR=C:/path/to/FYP-QnAce-Main-Repo/data/chroma

QACE_TTS_BACKEND=chatterbox
QACE_VAD_SILENCE_MS=300
QACE_VAD_MIN_SPEECH_S=1.0
```

## 6. Run Backend

From repository root:

```powershell
.\.venv311\Scripts\Activate.ps1
uvicorn server.app.main:app --reload --host 0.0.0.0 --port 8000
```

Health endpoint:

- http://localhost:8000/health

## 7. Run Frontend

Open a second terminal:

```powershell
cd client
npm run dev
```

Frontend:

- http://localhost:3000

## 8. Tests

Backend tests:

```powershell
.\.venv311\Scripts\Activate.ps1
pytest -q
```

Frontend E2E (if configured):

```powershell
cd client
npx playwright test
```

## 9. Common Fixes

- If CUDA is not used, verify the active venv and torch CUDA build.
- If browser audio fails, allow microphone permissions and use localhost.
- If model loading fails, verify model paths in `.env`.
- If dependency conflicts appear, run `pip check` and reinstall from `server/requirements.txt`.
