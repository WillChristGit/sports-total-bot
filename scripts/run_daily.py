#!/usr/bin/env python3
"""
Scheduled daily runner for SportsTotalBot

This script is designed to be run via cron at specific times
to check for new betting opportunities.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import main, load_config, setup_logging
from storage.database import Database
from output.formatter import OutputFormatter
import yaml


def scheduled_run():
    """Run the scheduled analysis"""
    logger = setup_logging()

    # Load config
    config = load_config('config/config.yaml')

    # Get run times from config
    run_times = config.get('schedule', {}).get('run_times', ['09:00', '12:00', '17:00'])
    current_time = datetime.now().strftime('%H:%M')

    if current_time not in run_times:
        logger.info(f"Current time {current_time} not in scheduled run times {run_times}")
        return

    logger.info(f"Starting scheduled run at {current_time}")

    # First, update any completed game results
    db = Database(config.get('database', {}).get('path', 'data/sportstotalbot.db'))
    updated = db.update_results_for_completed_games()
    logger.info(f"Updated {len(updated)} game results")

    if updated:
        stats = db.get_performance_stats()
        formatter = OutputFormatter()
        logger.info(f"\n{formatter.format_performance_report(stats)}")

    # Run the main analysis
    sys.argv = ['main.py']  # Reset sys.argv
    exit_code = main()

    if exit_code == 0:
        logger.info("Scheduled run completed successfully")
    else:
        logger.error(f"Scheduled run failed with exit code {exit_code}")

    return exit_code


if __name__ == '__main__':
    sys.exit(scheduled_run() or 0)
