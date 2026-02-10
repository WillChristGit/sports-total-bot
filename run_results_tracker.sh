#!/bin/bash
# Run the results tracker for SportsTotalBot

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the tracker with provided arguments
python3 src/results/tracker.py "$@"
