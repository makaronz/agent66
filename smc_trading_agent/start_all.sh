#!/bin/bash

# Start All Services for SMC Trading Agent
# This script starts:
# 1. TypeScript Backend (Express) on port 3001
# 2. Python Trading Agent on port 8000
# 3. React Frontend (Vite) on port 5173

set -e

echo "🚀 Starting SMC Trading Agent - All Services"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down all services...${NC}"
    kill $TS_BACKEND_PID $PYTHON_AGENT_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start TypeScript Backend
echo -e "${GREEN}📡 Starting TypeScript Backend (port 3001)...${NC}"
cd "$(dirname "$0")"
npm start > logs/ts-backend.log 2>&1 &
TS_BACKEND_PID=$!
echo "   PID: $TS_BACKEND_PID"
sleep 3

# Check if backend started
if ! kill -0 $TS_BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ TypeScript Backend failed to start${NC}"
    cat logs/ts-backend.log
    exit 1
fi

# Start Python Trading Agent
echo -e "${GREEN}🐍 Starting Python Trading Agent (port 8000)...${NC}"
python3 start_paper_trading.py > logs/python-agent.log 2>&1 &
PYTHON_AGENT_PID=$!
echo "   PID: $PYTHON_AGENT_PID"
sleep 3

# Check if Python agent started
if ! kill -0 $PYTHON_AGENT_PID 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Python Agent may have issues (check logs/python-agent.log)${NC}"
fi

# Start React Frontend
echo -e "${GREEN}⚛️  Starting React Frontend (port 5173)...${NC}"
npm run client:dev > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"
sleep 3

# Check if frontend started
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Frontend failed to start${NC}"
    cat logs/frontend.log
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo "📊 Services:"
echo "   • TypeScript Backend:  http://localhost:3001"
echo "   • Python Trading Agent: http://localhost:8000"
echo "   • React Frontend:      http://localhost:5173"
echo ""
echo "📝 Logs:"
echo "   • Backend:  tail -f logs/ts-backend.log"
echo "   • Python:   tail -f logs/python-agent.log"
echo "   • Frontend: tail -f logs/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all processes
wait

