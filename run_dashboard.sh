#!/bin/bash
# SportsTotalBot Dashboard Launcher
# ================================
# This script starts the Flask web dashboard for SportsTotalBot
# It activates the venv, checks/install dependencies, and opens your browser

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}SportsTotalBot Web Dashboard${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created.${NC}"
    echo ""
    echo "Installing dependencies..."
    ./venv/bin/pip install -q --upgrade pip
    ./venv/bin/pip install -q -r requirements.txt
    echo -e "${GREEN}Dependencies installed.${NC}"
    echo ""
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}Flask not found. Installing dependencies...${NC}"
    pip install -q flask flask-cors
    echo -e "${GREEN}Flask installed.${NC}"
fi

# Check if dashboard.py exists
if [ ! -f "dashboard.py" ]; then
    echo -e "${RED}Error: dashboard.py not found!${NC}"
    exit 1
fi

# Check if dashboard directory exists
if [ ! -d "dashboard" ]; then
    echo -e "${YELLOW}Warning: dashboard/ directory not found. Creating...${NC}"
    mkdir -p dashboard
fi

echo -e "${GREEN}Starting Flask server...${NC}"
echo ""
echo -e "${BLUE}Dashboard URL:${NC}"
echo -e "  ${GREEN}http://localhost:5001${NC}"
echo ""

# Open browser after a short delay
(sleep 2 && open "http://localhost:5001") 2>/dev/null &

echo -e "${BLUE}API Endpoints:${NC}"
echo -e "  ${BLUE}GET /api/picks${NC}     - Today's picks"
echo -e "  ${BLUE}GET /api/history${NC}   - Historical performance"
echo -e "  ${BLUE}GET /api/stats${NC}     - Summary statistics"
echo -e "  ${BLUE}GET /api/health${NC}    - Health check"
echo ""
echo -e "Press ${YELLOW}Ctrl+C${NC} to stop the server"
echo -e "${BLUE}================================================${NC}"
echo ""

# Start the dashboard
python dashboard.py
