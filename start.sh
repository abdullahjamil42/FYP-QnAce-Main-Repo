#!/usr/bin/env bash
# Q&Ace Backend Startup Script
# Lets you choose between Groq cloud API or local MLX LLM before launching.

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$REPO_DIR/.env"
VENV_DIR="$REPO_DIR/.venv311"
LOCAL_LLM_SCRIPT="$REPO_DIR/../qace_local_llm_server.py"
LOCAL_LLM_PID=""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}Stopping frontend (PID $FRONTEND_PID)...${NC}"
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi

    if [ -n "$LOCAL_LLM_PID" ] && kill -0 "$LOCAL_LLM_PID" 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}Stopping local LLM server (PID $LOCAL_LLM_PID)...${NC}"
        kill "$LOCAL_LLM_PID" 2>/dev/null || true
        wait "$LOCAL_LLM_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║           Q&Ace Backend               ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Check venv
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Virtual environment not found at $VENV_DIR${NC}"
    echo "Run: python3 -m venv .venv311 && .venv311/bin/pip install -r server/requirements.txt"
    exit 1
fi

PYTHON="$VENV_DIR/bin/python"

# Choose LLM provider
echo -e "${YELLOW}Select LLM provider:${NC}"
echo ""
echo "  1) ${GREEN}Groq Cloud API${NC}  (fast, requires GROQ_API_KEY)"
echo "  2) ${GREEN}Local MLX LLM${NC}   (runs on Apple Silicon, no API key needed)"
echo ""
read -rp "Enter choice [1/2]: " choice

case "$choice" in
    2|local)
        PROVIDER="local"
        echo ""
        echo -e "${CYAN}Local MLX LLM selected.${NC}"
        echo -e "${CYAN}Starts with evaluator adapter (auto-swaps to coach after interview).${NC}"

        # Update .env
        sed -i '' 's/^QACE_LLM_PROVIDER=.*/QACE_LLM_PROVIDER=local/' "$ENV_FILE"

        echo -e "${CYAN}Starting local LLM server with evaluator adapter...${NC}"

        if [ ! -f "$LOCAL_LLM_SCRIPT" ]; then
            echo -e "${RED}Local LLM server script not found at $LOCAL_LLM_SCRIPT${NC}"
            exit 1
        fi

        # Kill any leftover mlx_lm / wrapper processes on ports 8080/8081
        for p in $(lsof -ti :8080 2>/dev/null) $(lsof -ti :8081 2>/dev/null); do
            kill "$p" 2>/dev/null || true
        done
        sleep 1

        # Prepend global pyenv bin so mlx_lm.server is found without installing it
        # into the project venv (which would cause dependency conflicts).
        export PATH="/Users/aziqrauf/.pyenv/versions/3.11.9/bin:$PATH"

        # Start local LLM server in background (evaluator for live interview;
        # the backend /coaching/generate endpoint auto-swaps to coach when needed).
        "$PYTHON" "$LOCAL_LLM_SCRIPT" --adapter evaluator --port 8081 &
        LOCAL_LLM_PID=$!

        echo -e "${YELLOW}Waiting for local LLM server to be ready...${NC}"
        for i in $(seq 1 60); do
            if curl -s http://localhost:8081/health > /dev/null 2>&1; then
                echo -e "${GREEN}Local LLM server ready (took ${i}s).${NC}"
                break
            fi
            if ! kill -0 "$LOCAL_LLM_PID" 2>/dev/null; then
                echo -e "${RED}Local LLM server process died. Check output above.${NC}"
                exit 1
            fi
            sleep 1
        done

        if ! curl -s http://localhost:8081/health > /dev/null 2>&1; then
            echo -e "${RED}Local LLM server failed to start within 60s.${NC}"
            exit 1
        fi
        ;;
    *)
        PROVIDER="groq"
        echo ""
        echo -e "${CYAN}Groq Cloud API selected.${NC}"

        # Update .env
        sed -i '' 's/^QACE_LLM_PROVIDER=.*/QACE_LLM_PROVIDER=groq/' "$ENV_FILE"

        # Check API key
        GROQ_KEY=$(grep '^GROQ_API_KEY=' "$ENV_FILE" | cut -d'=' -f2-)
        if [ "$GROQ_KEY" = "your_groq_api_key_here" ] || [ -z "$GROQ_KEY" ]; then
            echo ""
            echo -e "${YELLOW}GROQ_API_KEY is not set in .env${NC}"
            read -rp "Enter your Groq API key (or press Enter to skip): " api_key
            if [ -n "$api_key" ]; then
                sed -i '' "s/^GROQ_API_KEY=.*/GROQ_API_KEY=$api_key/" "$ENV_FILE"
                echo -e "${GREEN}API key saved to .env${NC}"
            else
                echo -e "${YELLOW}Warning: LLM features will be unavailable without an API key.${NC}"
            fi
        fi
        ;;
esac

echo ""
echo -e "${CYAN}Starting Q&Ace frontend...${NC}"
echo -e "${GREEN}URL: http://localhost:3000${NC}"
echo ""

CLIENT_DIR="$REPO_DIR/client"
if [ ! -d "$CLIENT_DIR" ]; then
    echo -e "${RED}Client directory not found at $CLIENT_DIR${NC}"
    exit 1
fi

# Use npm if available; fall back to yarn.
if command -v npm >/dev/null 2>&1; then
    (cd "$CLIENT_DIR" && npm install && npm run dev) &
    FRONTEND_PID=$!
elif command -v yarn >/dev/null 2>&1; then
    (cd "$CLIENT_DIR" && yarn install && yarn dev) &
    FRONTEND_PID=$!
else
    echo -e "${RED}Neither npm nor yarn found. Install Node.js (includes npm) to run the frontend.${NC}"
    exit 1
fi

echo -e "${YELLOW}Waiting for frontend to be ready...${NC}"
for i in $(seq 1 60); do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo -e "${GREEN}Frontend ready (took ${i}s).${NC}"
        break
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${RED}Frontend process died. Check output above.${NC}"
        exit 1
    fi
    sleep 1
done

if ! curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo -e "${RED}Frontend failed to start within 60s.${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Starting Q&Ace backend (provider: $PROVIDER)...${NC}"
echo -e "${GREEN}Health: http://localhost:8000/health${NC}"
echo ""

cd "$REPO_DIR"
exec "$VENV_DIR/bin/uvicorn" server.app.main:app --reload --host 0.0.0.0 --port 8000
