#!/bin/bash
# SportsTotalBot Tracker - View performance

cd "$(dirname "$0")"
source venv/bin/activate
python scripts/tracker.py "$@"
