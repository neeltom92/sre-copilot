#!/bin/bash
#
# SRE Copilot - Start Script
# Starts both the Python backend and React frontend
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SRE Copilot - Starting Services                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copy from env.example:${NC}"
    echo "  cp env.example .env"
    echo "  # Then edit .env with your API keys"
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
fi

# Start backend
echo -e "${GREEN}Starting Python backend on port 8000...${NC}"
python server.py &
BACKEND_PID=$!

# Wait for backend to be ready
echo -e "${BLUE}Waiting for backend to start...${NC}"
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start!${NC}"
    exit 1
fi

# Start frontend
echo -e "${GREEN}Starting React frontend on port 3000...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
sleep 2

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SRE Copilot - Ready!                            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"
echo "║  Frontend:  http://localhost:3000                            ║"
echo "║  Backend:   http://localhost:8000                            ║"
echo "║                                                              ║"
echo "║  Press Ctrl+C to stop all services                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Wait for either process to exit
wait
