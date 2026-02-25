#!/bin/bash

# ╔═══════════════════════════════════════════════════════════╗
# ║           Q&ACE - Full Stack Startup Script               ║
# ║                                                           ║
# ║   This script starts both Backend API and Frontend        ║
# ╚═══════════════════════════════════════════════════════════╝

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           Q&ACE Interview Preparation System              ║"
echo "║                                                           ║"
echo "║   Starting Full Stack Application...                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti :$port)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Killing existing process on port $port (PID: $pid)${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
    fi
}

# Check for required commands
echo -e "${BLUE}[1/4] Checking requirements...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All requirements met${NC}"
echo ""

# Kill any existing processes
echo -e "${BLUE}[2/4] Cleaning up existing processes...${NC}"
kill_port 8001
kill_port 3000
echo -e "${GREEN}✓ Ports cleared${NC}"
echo ""

# Start Backend API
echo -e "${BLUE}[3/4] Starting Backend API (Port 8001)...${NC}"
cd "$ROOT_DIR/integrated_system"

# Activate virtual environment if exists
if [ -d "$ROOT_DIR/.venv" ]; then
    source "$ROOT_DIR/.venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
fi

# Start API in background using uvicorn directly
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend API started (PID: $BACKEND_PID)${NC}"
echo ""

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
sleep 5

# Start Frontend
echo -e "${BLUE}[4/4] Starting Frontend (Port 3000)...${NC}"
cd "$ROOT_DIR/Frontend"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo ""

# Wait a moment for frontend to start
sleep 3

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    Q&ACE IS RUNNING!                      ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║                                                           ║"
echo "║   🌐 Frontend:    http://localhost:3000                   ║"
echo "║   🔧 Backend API: http://localhost:8001                   ║"
echo "║   📊 API Docs:    http://localhost:8001/docs              ║"
echo "║                                                           ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║   Press Ctrl+C to stop all services                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Trap Ctrl+C and cleanup
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down Q&ACE...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

trap cleanup INT

# Wait for both processes
wait
