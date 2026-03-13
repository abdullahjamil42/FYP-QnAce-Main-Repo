#!/bin/bash
# Q&Ace — NVIDIA MPS (Multi-Process Service) setup.
# Enables concurrent GPU kernel execution from multiple processes
# (Whisper + Wav2Vec2 via ProcessPoolExecutor).
#
# Must be run BEFORE starting the Q&Ace server.
# Requires: Volta+ GPU (RTX 4090 = Ada Lovelace ✓).
#
# Usage:
#   sudo bash infra/nvidia-mps.sh start
#   sudo bash infra/nvidia-mps.sh stop

set -euo pipefail

ACTION="${1:-start}"

export CUDA_VISIBLE_DEVICES=0

case "$ACTION" in
  start)
    echo "Starting NVIDIA MPS daemon …"
    nvidia-smi -i 0 -c EXCLUSIVE_PROCESS
    nvidia-cuda-mps-control -d
    echo "MPS daemon started ✓"
    echo "Verify: echo get_server_list | nvidia-cuda-mps-control"
    ;;
  stop)
    echo "Stopping NVIDIA MPS daemon …"
    echo quit | nvidia-cuda-mps-control
    nvidia-smi -i 0 -c DEFAULT
    echo "MPS daemon stopped ✓"
    ;;
  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;
esac
