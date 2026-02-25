# Railway-optimized Dockerfile for Q&ACE Backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install BASE requirements (cached)
COPY integrated_system/requirements-base.txt requirements-base.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=100 -r requirements-base.txt

# Copy and install APP requirements
COPY integrated_system/requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=100 -r requirements.txt

# Copy application code
COPY integrated_system/ /app/integrated_system/
COPY BERT_Model/ /app/BERT_Model/

# Copy Interview Dataset for reference embeddings
COPY Interview_Dataset.csv /app/Interview_Dataset.csv

# Set environment variables
ENV PYTHONPATH=/app:/app/integrated_system
ENV PORT=8001

# Expose port (Railway will set PORT automatically)
EXPOSE $PORT

# Run the application
CMD ["sh", "-c", "cd integrated_system && python api/main.py"]