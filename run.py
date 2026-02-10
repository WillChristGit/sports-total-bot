#!/usr/bin/env python3
"""
SportsTotalBot Runner

Simple entry point that works with the package structure.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Now run the bot
if __name__ == '__main__':
    from src.bot import main
    sys.exit(main())
