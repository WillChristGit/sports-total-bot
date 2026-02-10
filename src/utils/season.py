# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CRITICAL: NEVER HARDCODE SEASON VALUES ANYWHERE IN THE CODEBASE!
# ALWAYS use get_current_nba_season() or get_season_start_year()
# Bad picks on Feb 3, 2026 (1-5 record) were caused by hardcoded seasons
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""
NBA Season Utilities
IMPORTANT: Season must ALWAYS be calculated dynamically - NEVER hardcode!
"""
from datetime import datetime


def get_current_nba_season() -> str:
    """
    Calculate the current NBA season string dynamically.
    
    NBA seasons span two calendar years (e.g., 2025-26).
    - If current month >= October (10), we are in a new season starting this year
    - Otherwise, we are in the season that started last year
    
    Returns:
        str: Season string in format "YYYY-YY" (e.g., "2025-26")
    
    Example:
        - February 2026 -> "2025-26" (season started Oct 2025)
        - November 2025 -> "2025-26" (season just started)
        - August 2025 -> "2024-25" (last season, before new one starts)
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # NBA season starts in October
    if current_month >= 10:
        # New season starting this year
        season_start = current_year
    else:
        # Still in season that started last year
        season_start = current_year - 1
    
    season_end = season_start + 1
    return f"{season_start}-{str(season_end)[-2:]}"


def get_season_start_year() -> int:
    """Get just the starting year of the current NBA season."""
    now = datetime.now()
    if now.month >= 10:
        return now.year
    return now.year - 1


if __name__ == "__main__":
    print(f"Current NBA Season: {get_current_nba_season()}")
