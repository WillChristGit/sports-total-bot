#!/usr/bin/env python3
"""
SportsTotalBot Web Dashboard
=============================
Simple Flask backend for serving today's betting picks.

Features:
- /api/picks endpoint - returns today's real picks from data/picks/daily_picks_YYYYMMDD.json
- /api/health endpoint
- Auto-refresh picks every 60 seconds
- CORS enabled for cross-origin requests

Author: SportsTotalBot
Created: 2026-02-04
"""

import os
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# =============================================================================
# Configuration
# =============================================================================

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
PICKS_DIR = DATA_DIR / "picks"
DASHBOARD_DIR = APP_DIR / "dashboard"
REFRESH_INTERVAL = 60  # seconds

# Pick file pattern: daily_picks_YYYYMMDD.json
PICKS_FILE_PATTERN = "daily_picks_%Y%m%d.json"

# Results file
RESULTS_FILE = PICKS_DIR / "results_log.csv"

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__, static_folder=str(DASHBOARD_DIR), static_url_path="/")
CORS(app)  # Enable CORS for all routes

# Cache for today's picks to avoid excessive file reads
_today_picks_cache: Optional[List[Dict[str, Any]]] = None
_last_cache_update: Optional[datetime] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_today_date() -> datetime:
    """Get today's date in UTC."""
    return datetime.utcnow()


def get_picks_file_path(date: datetime) -> Path:
    """Get the path to the picks file for a specific date."""
    filename = date.strftime(PICKS_FILE_PATTERN)
    return PICKS_DIR / filename


def load_picks_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load picks from a JSON file.

    Args:
        file_path: Path to the picks JSON file

    Returns:
        List of pick dictionaries, or empty list if file not found or invalid
    """
    try:
        if not file_path.exists():
            return []

        with open(file_path, 'r') as f:
            picks = json.load(f)

        # Validate basic structure
        if not isinstance(picks, list):
            return []

        # Ensure each pick has required fields
        valid_picks = []
        for pick in picks:
            if isinstance(pick, dict) and pick.get('game_id'):
                valid_picks.append(pick)

        return valid_picks

    except (json.JSONDecodeError, IOError, ValueError) as e:
        app.logger.error(f"Error loading picks from {file_path}: {e}")
        return []


def get_most_recent_picks(use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Get the most recent picks with optional caching.
    Falls back to previous days if today's file doesn't exist.

    Args:
        use_cache: Whether to use cached data (refreshes every REFRESH_INTERVAL seconds)

    Returns:
        List of pick dictionaries from the most recent file
    """
    global _today_picks_cache, _last_cache_update

    now = datetime.utcnow()

    # Check if cache is valid
    if use_cache and _today_picks_cache is not None:
        if _last_cache_update and (now - _last_cache_update).total_seconds() < REFRESH_INTERVAL:
            return _today_picks_cache

    # Load fresh picks - try today, then yesterday, then recent days
    today = get_today_date()
    picks = []

    # Check up to 7 days back for most recent picks file
    for days_back in range(7):
        check_date = today - timedelta(days=days_back)
        file_path = get_picks_file_path(check_date)
        if file_path.exists():
            picks = load_picks_from_file(file_path)
            if picks:  # Found picks, stop looking
                break

    # Update cache
    _today_picks_cache = picks
    _last_cache_update = now

    return picks


def load_results_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load results from a CSV file.

    Args:
        file_path: Path to the results CSV file

    Returns:
        List of result dictionaries, or empty list if file not found or invalid
    """
    try:
        if not file_path.exists():
            return []

        results = []
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip comment lines
                if row.get('date', '').startswith('#'):
                    continue

                # Parse the result
                result = {
                    'date': row.get('date', ''),
                    'game': row.get('game', ''),
                    'pick': row.get('pick', ''),
                    'line': row.get('line', ''),
                    'projected': row.get('projected', ''),
                    'actual': row.get('actual', ''),
                    'result': row.get('result', ''),
                    'units_won': float(row.get('units_won', 0))
                }
                results.append(result)

        return results

    except (csv.Error, IOError, ValueError) as e:
        app.logger.error(f"Error loading results from {file_path}: {e}")
        return []


def calculate_results_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from results data.

    Args:
        results: List of result dictionaries

    Returns:
        Dictionary with calculated statistics
    """
    if not results:
        return {
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_units': 0.0,
            'roi_percentage': 0.0,
            'recent_results': []
        }

    wins = sum(1 for r in results if r['result'] == 'WIN')
    losses = sum(1 for r in results if r['result'] == 'LOSS')
    total_games = wins + losses
    total_units = sum(r['units_won'] for r in results)

    # Calculate ROI (assuming 1 unit per bet)
    total_invested = total_games
    roi_percentage = (total_units / total_invested * 100) if total_invested > 0 else 0.0

    # Calculate win rate
    win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

    return {
        'total_games': total_games,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 1),
        'total_units': round(total_units, 2),
        'roi_percentage': round(roi_percentage, 1),
        'recent_results': results[:10]  # Last 10 results
    }


def filter_results_by_date(results: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    """
    Filter results to only include those within the last N days.

    Args:
        results: List of result dictionaries
        days: Number of days to look back

    Returns:
        Filtered list of results
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    filtered = []
    for result in results:
        try:
            result_date = datetime.strptime(result['date'], '%Y-%m-%d')
            if result_date >= cutoff_date:
                filtered.append(result)
        except (ValueError, TypeError):
            # Skip results with invalid dates
            continue

    return filtered


# =============================================================================
# API Routes
# =============================================================================

@app.route('/api/picks', methods=['GET'])
def api_picks():
    """
    Get today's betting picks.

    Query Parameters:
        refresh: Set to 'true' to bypass cache and force reload

    Returns:
        JSON response with today's picks
    """
    try:
        # Check if refresh is requested
        force_refresh = request.args.get('refresh', 'false').lower() == 'true'
        use_cache = not force_refresh

        picks = get_most_recent_picks(use_cache=use_cache)

        return jsonify({
            "success": True,
            "date": get_today_date().strftime('%Y-%m-%d'),
            "total_picks": len(picks),
            "picks": picks,
            "cached": use_cache and _last_cache_update is not None,
            "last_updated": _last_cache_update.isoformat() if _last_cache_update else None,
        })

    except Exception as e:
        app.logger.error(f"Error in /api/picks: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "picks": [],
            "total_picks": 0,
        }), 500


@app.route('/api/results', methods=['GET'])
def api_results():
    """
    Get results statistics and recent results.

    Query Parameters:
        days: Number of days to look back (default: 30, options: 7, 30)

    Returns:
        JSON response with results statistics and recent results
    """
    try:
        # Get days parameter (default: 30)
        days_str = request.args.get('days', '30')
        try:
            days = int(days_str)
            if days not in [7, 30]:
                days = 30
        except ValueError:
            days = 30

        # Load all results
        all_results = load_results_from_file(RESULTS_FILE)

        # Filter by date range
        filtered_results = filter_results_by_date(all_results, days)

        # Calculate statistics
        stats = calculate_results_stats(filtered_results)

        return jsonify({
            "success": True,
            "period_days": days,
            "stats": {
                "record": f"{stats['wins']}-{stats['losses']}",
                "wins": stats['wins'],
                "losses": stats['losses'],
                "total_games": stats['total_games'],
                "win_rate": stats['win_rate'],
                "total_units": stats['total_units'],
                "roi_percentage": stats['roi_percentage']
            },
            "recent_results": stats['recent_results']
        })

    except Exception as e:
        app.logger.error(f"Error in /api/results: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "stats": None,
            "recent_results": []
        }), 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({
        "success": True,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app": "SportsTotalBot Dashboard",
        "version": "1.0.0",
    })


# =============================================================================
# Static File Serving
# =============================================================================

@app.route('/')
def index():
    """Serve the main dashboard HTML file."""
    try:
        return send_from_directory(DASHBOARD_DIR, 'index.html')
    except FileNotFoundError:
        return jsonify({
            "success": False,
            "error": "Dashboard not found. Please create dashboard/index.html",
        }), 404


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the dashboard directory."""
    try:
        return send_from_directory(DASHBOARD_DIR, path)
    except FileNotFoundError:
        return jsonify({
            "success": False,
            "error": f"File not found: {path}",
        }), 404


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Not found",
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    app.logger.error(f"Internal error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error",
    }), 500


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    # Ensure directories exist
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SportsTotalBot Web Dashboard")
    print("=" * 60)
    print(f"Starting server on port 5001...")
    print(f"Data directory: {DATA_DIR}")
    print(f"Picks directory: {PICKS_DIR}")
    print(f"Dashboard directory: {DASHBOARD_DIR}")
    print(f"Refresh interval: {REFRESH_INTERVAL} seconds")
    print("")
    print("API Endpoints:")
    print("  GET /api/picks      - Today's picks")
    print("  GET /api/results    - Results statistics (7 or 30 days)")
    print("  GET /api/health     - Health check")
    print("")
    print("Open http://localhost:5001 in your browser")
    print("=" * 60)
    print("")

    # Run the Flask development server
    # For production, use gunicorn or uwsgi
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,  # Set to False in production
    )
