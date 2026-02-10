#!/bin/bash
# SportsTotalBot Runner

cd "$(dirname "$0")"
source venv/bin/activate
python -c "import sys; sys.path.insert(0, '.'); from src.bot import main; main()" "$@"
