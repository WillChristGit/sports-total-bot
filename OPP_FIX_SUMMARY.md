# NBA Stats Cache - OPP_PTS Fix Summary

## Problem
The `avg_points_allowed` (OPP) field was returning 0 for all teams because the NBA.com `leaguedashteamstats` endpoint with `MeasureType=Base` doesn't include opponent points allowed (`OPP_PTS`).

## Root Cause
- The `Base` MeasureType returns offensive stats (PTS, FGA, FTA, etc.) but NOT defensive stats
- The `OPP_PTS` column is only available when using `MeasureType=Opponent`
- The code was trying to access `OPP_PTS` from Base stats, which doesn't exist

## Solution Implemented

### 1. Added New Method: `_fetch_opponent_stats()`
A new private method that fetches opponent/defensive stats using `MeasureType=Opponent`.

**Location:** `/Volumes/LegbaSSD/bots/SportsTotalBot/src/data/nba_stats_cache.py` (lines 203-253)

```python
def _fetch_opponent_stats(self, team_id: int, season: str) -> Optional[dict]:
    """
    Fetch opponent stats (defensive stats) for a team using MeasureType=Opponent.
    This returns stats that opponents accumulate against this team, including points allowed.
    """
    url = "https://stats.nba.com/stats/leaguedashteamstats"
    params = {
        "LeagueID": "00",
        "Season": season,
        "SeasonType": "Regular Season",
        "MeasureType": "Opponent",  # CRITICAL: This returns opponent stats against this team
        "PerMode": "PerGame",
        # ... other params
    }
    # ... fetch and return opponent stats dict with OPP_PTS
```

### 2. Modified `get_team_stats()` Method
Updated to fetch and merge opponent stats with base stats.

**Location:** `/Volumes/LegbaSSD/bots/SportsTotalBot/src/data/nba_stats_cache.py` (lines 315-324)

```python
# CRITICAL FIX: Fetch opponent stats separately to get OPP_PTS
# The Base MeasureType doesn't include opponent points allowed
opponent_stats = self._fetch_opponent_stats(team_id, season)
if opponent_stats:
    # Merge opponent stats into team_dict
    # The Opponent MeasureType returns columns prefixed with OPP_
    # OPP_PTS = average points opponents score against this team (points allowed)
    team_dict.update({
        'OPP_PTS': opponent_stats.get('OPP_PTS', 0),  # Points allowed per game
    })
```

### 3. Enhanced HTTP Headers
Updated session headers to better match NBA.com's expected request format to avoid 500 errors.

**Location:** `/Volumes/LegbaSSD/bots/SportsTotalBot/src/data/nba_stats_cache.py` (lines 28-34)

```python
self.session = requests.Session()
self.session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.nba.com/stats/',
    'Origin': 'https://www.nba.com',
    # ... additional headers
})
```

## NBA API Data Structure

### Base MeasureType Returns:
- PTS (points scored by team)
- FGA, FTA, OREB, TOV
- OFF_RATING (offensive rating)
- Plus-Minus
- No OPP_PTS or DEF_RATING

### Opponent MeasureType Returns:
- OPP_PTS (points opponents score against this team = points allowed)
- OPP_FGM, OPP_FGA, OPP_FG_PCT
- OPP_OREB, OPP_DREB, OPP_REB
- OPP_AST, OPP_TOV, OPP_STL, OPP_BLK
- All opponent stats prefixed with `OPP_`

## Verification Results

### Test Script Output
```
======================================================================
Testing NBA Stats Cache - OPP_PTS Fix
======================================================================

Fetching team stats to verify avg_points_allowed is no longer 0...

Testing Boston Celtics... ✓ PASS
  - Points Scored: 116.0
  - Points Allowed: 108.9
  - Off Rating: 117.1
  - Def Rating: 110.0

Testing Los Angeles Lakers... ✓ PASS
  - Points Scored: 116.3
  - Points Allowed: 116.2
  - Off Rating: 115.4
  - Def Rating: 115.3

Testing Golden State Warriors... ✓ PASS
  - Points Scored: 116.2
  - Points Allowed: 114.0
  - Off Rating: 112.6
  - Def Rating: 110.5

Testing Phoenix Suns... ✓ PASS
  - Points Scored: 114.1
  - Points Allowed: 111.6
  - Off Rating: 112.6
  - Def Rating: 110.1

======================================================================
Summary
======================================================================
Successful: 4/4
Failed: 0/4

✓ All tests passed! OPP_PTS fix is working correctly.
```

## Impact

### Before Fix
- All teams had `avg_points_allowed: 0`
- Defensive ratings were calculated using fallback logic
- Projections and EV calculations were inaccurate

### After Fix
- Teams now have accurate `avg_points_allowed` values (e.g., Celtics: 108.9, Lakers: 116.2)
- Defensive ratings are calculated from actual opponent data
- Projections and EV calculations should be more accurate

## Files Modified
1. `/Volumes/LegbaSSD/bots/SportsTotalBot/src/data/nba_stats_cache.py`
   - Added `_fetch_opponent_stats()` method
   - Modified `get_team_stats()` to call opponent stats fetcher
   - Enhanced HTTP headers for better API compatibility

## Test Scripts Created (for verification)
1. `/Volumes/LegbaSSD/bots/SportsTotalBot/test_opp_fix.py` - Tests 4 teams
2. `/Volumes/LegbaSSD/bots/SportsTotalBot/test_all_teams.py` - Tests all 30 teams
3. `/Volumes/LegbaSSD/bots/SportsTotalBot/debug_opponent.py` - Debug API response structure

## Notes
- The fix uses cached data when API returns errors (rate limiting, 500 errors)
- Cache files are stored in `data/cache/*.json`
- The Opponent MeasureType provides comprehensive defensive statistics
- No existing functionality was broken by this change
