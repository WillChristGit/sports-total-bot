"""
NCAA Basketball Season Utilities

Handles NCAA-specific season calculations and dates.
"""

from datetime import datetime


def get_current_ncaa_season() -> str:
    """
    Get the current NCAA basketball season string.

    NCAA season runs from November through March/April.
    The season straddles two calendar years.

    Examples:
        - March 2026 -> "2025-26"
        - November 2025 -> "2025-26"
        - October 2025 -> "2024-25" (pre-season)
        - April 2026 -> "2025-26"

    Returns:
        Season string in format "YYYY-YY" (e.g., "2025-26")
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # NCAA season is Nov-Mar
    if current_month >= 11:
        # November or December = current season starting
        season_start = current_year
    elif current_month <= 3:
        # January-March = current season ongoing
        season_start = current_year - 1
    else:
        # April-October = between seasons, return next season
        season_start = current_year - 1

    season_end = season_start + 1
    return f"{season_start}-{str(season_end)[-2:]}"


def get_ncaa_season_start_year() -> int:
    """
    Get the starting year of the current NCAA season.

    Returns:
        Integer year (e.g., 2025 for 2025-26 season)
    """
    now = datetime.now()
    current_month = now.month

    if current_month >= 11:
        return now.year
    else:
        return now.year - 1


def is_ncaa_season_active() -> bool:
    """
    Check if NCAA basketball season is currently active.

    Season is considered active from November 1 through April 15
    (includes tournament time).

    Returns:
        True if season is active, False otherwise
    """
    now = datetime.now()
    return 11 <= now.month <= 12 or now.month <= 4


def get_tournament_start_date(year: int) -> datetime:
    """
    Get the approximate start date of NCAA tournament for a given year.

    Args:
        year: The year the tournament concludes (e.g., 2026 for 2025-26 season)

    Returns:
        datetime object for tournament start
    """
    # Tournament typically starts third Thursday of March
    return datetime(year, 3, 14)


def is_tournament_time() -> bool:
    """
    Check if it's currently NCAA tournament time.

    Returns:
        True if in March/April during tournament period
    """
    now = datetime.now()
    # Tournament runs roughly mid-March to early April
    return (now.month == 3 and now.day >= 14) or (now.month == 4 and now.day <= 7)


if __name__ == "__main__":
    # Test the functions
    print(f"Current NCAA Season: {get_current_ncaa_season()}")
    print(f"Season Start Year: {get_ncaa_season_start_year()}")
    print(f"Is Season Active: {is_ncaa_season_active()}")
    print(f"Is Tournament Time: {is_tournament_time()}")
