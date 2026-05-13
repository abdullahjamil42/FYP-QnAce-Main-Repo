# ─── Q&Ace Backend ───
FROM python:3.11-slim

# System deps for aiortc (libavcodec etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libavcodec-dev libavformat-dev libavutil-dev libswresample-dev \
    libopus-dev libvpx-dev pkg-config gcc wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Silero VAD ONNX (~2 MB) at build time so it's always available
RUN mkdir -p models/silero-vad && \
    wget -q -O models/silero-vad/silero_vad.onnx \
    https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx

# ── Download perception models from Hugging Face Hub ──
# Face model (abdullahjamil42/QnAce-Face-Model, ~65 MB)
RUN huggingface-cli download abdullahjamil42/QnAce-Face-Model \
    --local-dir models/face-emotion/qnace \
    --local-dir-use-symlinks False

# Voice emotion model (abdullahjamil42/QnAce-Voice-Model, ~363 MB)
RUN huggingface-cli download abdullahjamil42/QnAce-Voice-Model \
    --local-dir models/voice-emotion/qnace \
    --local-dir-use-symlinks False

# BERT text-quality ONNX (abdullahjamil42/QnAce-Text-Quality, ~418 MB)
# Uncomment after running: huggingface-cli upload abdullahjamil42/QnAce-Text-Quality models/text-quality/ .
# RUN huggingface-cli download abdullahjamil42/QnAce-Text-Quality \
#     --local-dir models/text-quality \
#     --local-dir-use-symlinks False

# Copy server code
COPY . .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
