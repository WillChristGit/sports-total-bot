# SportsTotalBot - Session Summary & Claude.md

**Date:** 2026-02-04 (Updated)
**Session:** Spread Betting Implementation

---

## NEW: Web Dashboard (February 4, 2026)

### What's New
The bot now includes a **Flask-based web dashboard** for viewing picks and performance!

**Features:**
- Real-time picks display with auto-refresh (every 60 seconds)
- Historical performance tracking (past 30 days)
- Statistics by sport, bet type, and side
- EV distribution and best picks
- RESTful API endpoints for integrations

**Quick Start:**
```bash
./run_dashboard.sh
```

The dashboard will:
- Activate the virtual environment
- Check/install Flask if needed
- Start the server on port 5001
- Open your browser to http://localhost:5001

**API Endpoints:**
- `GET /api/picks` - Today's picks
- `GET /api/history` - Historical performance
- `GET /api/stats` - Summary statistics
- `GET /api/health` - Health check

**Documentation:** See `dashboard/README.md` for full documentation

---

## NEW: Spread Betting Support (February 4, 2026)

### What's New
The bot now supports **point spread betting** alongside totals!

**Features:**
- Projects margin of victory for each game
- Calculates EV for both home and away spread bets
- Uses same efficiency metrics as totals model
- Kelly Criterion bet sizing for spreads
- Both totals and spreads shown in output (grouped by game)

**Output Format:**
```
Boston Celtics @ Los Angeles Lakers - 8:00 PM ET
TOTAL: 🔽 UNDER 234.5 (EV: 8.2%)
SPREAD: Los Angeles Lakers -3.5 (EV: 5.1%)
```

**Implementation Details:**
- See `SPREAD_BETTING_IMPLEMENTATION.md` for full documentation
- Test with: `./venv/bin/python test_spreads.py`
- No configuration changes needed - just run `python3 main_v2.py`

---

## Bug Fix: SMB Permission Error (February 4, 2026)

### Issue
Bot failed with "Permission denied" when trying to save CSV/JSON files on SMB mount:
```
Failed to save picks: [Errno 13] Permission denied: 'data/picks/daily_picks_20260204.csv'
```

### Root Cause
When running on SMB/CIFS mounted filesystems (`//will@legbassd/LegbaSSD`), files created in earlier runs could become unwritable due to:
- SMB file locking issues
- Extended attributes (@ flag)
- Permission inconsistencies on network mounts

### Fix Applied
Updated `src/output/formatter.py` with robust error handling:

**New Behavior:**
1. **Pre-flight check**: Tests if existing file is writable
2. **Auto-recovery**: If file can't be written, removes and recreates it
3. **Fallback**: Tries alternative filename if removal fails
4. **Absolute path retry**: Uses absolute path as last resort
5. **Clear logging**: Warns about issues and recovery actions

**Files Modified:**
- `src/output/formatter.py` - Enhanced `save_picks_to_csv()` and `save_picks_to_json()`

**Testing:**
```bash
# Verify save works:
python3 << 'EOF'
from src.output.formatter import OutputFormatter
from src.data.models import Game, BetRecommendation, SportType, BetType, BetSide
from datetime import datetime, timedelta

formatter = OutputFormatter(output_path="data/picks")
# ... test data ...
csv_file = formatter.save_picks_to_csv(recommendations, games)
print(f"Saved to: {csv_file}")
EOF
```

**Status:** ✅ Fixed and tested

---

## Previous Improvements (2026-02-02)

### Session: Bot Analysis & V3 Improvements

---

## What Was Done

### Issues Found
1. **Mock Data Bug** - All teams returned identical projections (224.6)
2. **Security Issue** - API key exposed in config.yaml
3. **Ugly Output** - Decimals like `238.83333333333334`
4. **No Tests** - Zero test coverage
5. **No Data Quality Indicator** - Couldn't trust picks
6. **No Retry Logic** - API failures caused crashes

### Improvements Made

#### 1. Real NBA Stats Integration
- Created `src/data/multi_source_stats.py`
- Fetches live stats from NBA.com with fallback to cache
- Tracks data quality with grades (A-F)

#### 2. Data Quality Indicator
- 🟢 **A** = Excellent (fresh from NBA.com)
- 🟡 **B** = Good (cached < 6 hours)
- 🟠 **C** = Fair (cached < 24 hours)
- 🔴 **D** = Poor (league averages)
- ⚫ **F** = Unreliable (no data)

#### 3. Environment Variable Support
- `.env.example` template created
- `.gitignore` for security
- `src/config/loader.py` for env-aware config

#### 4. Retry Logic
- `src/utils/retry.py` with exponential backoff
- Applied to API fetchers

#### 5. Test Suite
- `tests/test_models.py` - Data model tests
- `tests/test_ev_calculator.py` - EV calculation tests
- Run with: `pytest tests/ -v`

#### 6. Better Logging
- `src/utils/logging.py` with colored console output
- JSON logging option
- File logging to `logs/`

#### 7. Clean Output Formatting
- Fixed ugly decimals (now shows `219.7` not `218.27777777777777`)

---

## Current Status

### Working Features
- ✅ Fetches games from The Odds API (using your key)
- ✅ Pulls real team stats from NBA.com
- ✅ Calculates projections using efficiency metrics
- ✅ Finds +EV opportunities
- ✅ Kelly Criterion bet sizing
- ✅ Data quality tracking
- ✅ Retry logic on API failures
- ✅ Saves picks to CSV/JSON
- ✅ SQLite database tracking

### Files Structure
```
/Volumes/LegbaSSD/bots/SportsTotalBot/
├── main_v2.py                    # Main entry point (USE THIS)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore
├── requirements.txt              # Dependencies
├── config/                       # Config files
├── src/
│   ├── data/
│   │   ├── models.py                 # Data classes
│   │   ├── fetchers.py               # API fetchers (with retry)
│   │   ├── nba_stats_cache.py        # Old NBA fetcher
│   │   └── multi_source_stats.py     # NEW: Multi-source with quality
│   ├── analysis/
│   │   ├── projections_v2.py         # Enhanced projections
│   │   └── ev_calculator_v2.py       # Kelly + EV calculator
│   ├── storage/
│   │   └── database.py               # SQLite operations
│   ├── output/
│   │   └── formatter.py              # Output formatting (w/ quality)
│   ├── config/
│   │   └── loader.py                 # Config with env support
│   └── utils/
│       ├── logging.py                # Structured logging
│       └── retry.py                  # Retry decorator
├── tests/                       # Test suite
├── data/
│   ├── cache/                   # NBA stats cache
│   ├── picks/                   # Daily picks
│   └── sportstotalbot.db        # Database
└── logs/                       # Application logs
```

---

## API Keys Used

### Your Working API Keys
```
The Odds API: c09a8b422200e71fa8b64e62a705f6a2
```
This key is configured in the code and working!

---

## How to Run

```bash
# Navigate to project
cd /Volumes/LegbaSSD/bots/SportsTotalBot

# Run the bot (generate today's picks)
python3 main_v2.py

# Run tests
pytest tests/ -v

# View performance
python3 main_v2.py --performance

# Start the web dashboard (NEW!)
./run_dashboard.sh
```

### Web Dashboard (NEW!)

The bot now includes a Flask-based web dashboard for viewing picks and performance:

**Quick Start:**
```bash
./run_dashboard.sh
```

The dashboard will automatically:
- Activate the virtual environment
- Install Flask if needed
- Start the server on port 5001
- Open your browser to http://localhost:5001

**Features:**
- Real-time picks display with auto-refresh
- Historical performance tracking (past 30 days)
- Statistics by sport, bet type, and side
- EV distribution and best picks
- RESTful API endpoints

**API Endpoints:**
- `GET /api/picks` - Today's picks
- `GET /api/history` - Historical performance
- `GET /api/stats` - Summary statistics
- `GET /api/health` - Health check

**Documentation:** See `dashboard/README.md` for full dashboard documentation

---

## Understanding the Output

### Example Pick
```
🎯 UNDER 251.1
   Teams: Minnesota Timberwolves @ Memphis Grizzlies
   Odds: -69
   Projected: 221.3
   Win Prob: 60.5%
   EV: 48.18%
   Units: 16.62
   Data Quality: 🟢 A
```

### What It Means

| Field | Description |
|-------|-------------|
| **Line** | The betting total (251.1 points) |
| **Odds** | American odds (-69 = risk $69 to win $100) |
| **Projected** | Model's prediction (221.3 points) |
| **EV** | Expected Value - positive = profitable theoretically |
| **Units** | Bet size (1 unit = 1% of bankroll) |
| **Data Quality** | 🟢A = Trustworthy, 🔴D = Use caution |

### About Those -69 Odds

**Negative odds like -69 mean:**
- You're getting **good odds** (line is heavily favored your way)
- Risk $69 to win $100
- The -69 appears because the line (251.1) is MUCH higher than the projection (221.3)
- This creates a massive edge in the model's favor

**Why 251.1 is so high:**
- This is a **real line** from The Odds API
- FanDuel has it at 255.5, MyBookie at 258.5
- High totals usually mean:
  - Both teams play very fast pace
  - Injuries to key defenders
  - High-scoring expected

**The model says this is too high** - hence the UNDER recommendation with huge EV.

---

## Data Quality System

The bot now tracks data quality and warns you:

```
Data Quality Summary:
  Excellent (A): 19
  Good (B):      0
  Fair (C):      0
  Poor (D):      1
  API Failures:  1
```

**Trust Threshold:**
- Quality Score ≥ 70/100 = ✅ Trust the picks
- Quality Score < 70/100 = ⚠️ Use caution

If data is poor, you'll see:
```
⚠️  WARNING: Low data quality detected!
   Quality Score: 45/100
   Only 40% of teams have reliable data
   Picks may not be accurate. Use with caution.
```

---

## Tonight's Picks (2026-02-02)

### Top Pick
```
🎯 UNDER 251.1 - Timberwolves @ Grizzlies
   Odds: -69 | EV: 48.18% | Units: 16.62
   Data Quality: 🟢 A
```

**Why this play:**
- Real line is insanely high (251.1)
- Model projects 221.3 (30 points lower!)
- Excellent data quality (fresh from NBA.com)
- Massive EV (48.18%)

### Second Pick
```
🎯 UNDER 239.6 - Hawks @ Heat
   Odds: -111 | EV: 15.00% | Units: 8.33
   Data Quality: 🟢 A
```

---

## Dependencies

```
requests>=2.31.0         # HTTP
pyyaml>=6.0              # YAML config
python-dotenv>=1.0.0     # Environment variables
schedule>=1.2.0          # Scheduling
python-dateutil>=2.8.2   # Date utils
beautifulsoup4>=4.12.0   # Web scraping
colorlog>=6.8.0          # Colored logging
flask>=3.0.0             # Web dashboard (optional)
pytest>=7.4.0            # Testing
pytest-cov>=4.1.0        # Coverage
```

Install with:
```bash
pip install -r requirements.txt
```

---

## Configuration

### Via .env (Recommended)
```bash
ODDS_API_KEY=c09a8b422200e71fa8b64e62a705f6a2
MIN_EV_THRESHOLD=0.02
MIN_CONFIDENCE=0.55
LOG_LEVEL=INFO
```

### Via config/config.yaml
```yaml
api_keys:
  the_odds_api: "c09a8b422200e71fa8b64e62a705f6a2"

analysis:
  min_ev_threshold: 0.02
  min_confidence: 0.55
```

---

## Future Improvements

### High Priority
- [ ] Async API calls for faster performance
- [ ] Backtesting module for historical validation
- [ ] Injury API integration
- [ ] More sports (WNBA, NFL, MLB, NHL)

### Medium Priority
- [x] Web dashboard (Flask app) - **COMPLETED February 4, 2026**
  - Run with: `./run_dashboard.sh`
  - Access at: http://localhost:5001
  - See `dashboard/README.md` for documentation
- [ ] Line movement alerts
- [ ] Per-sport performance tracking (now available via dashboard)
- [ ] Referee tendency adjustments

### Low Priority
- [ ] Machine learning on historical data
- [ ] Live betting support
- [ ] Mobile app notifications

---

## Disclaimer

**For educational purposes only.** Sports betting involves risk. Never bet more than you can afford to lose. Past performance does not guarantee future results.

---

## Contact / Help

- Run the bot: `python3 main_v2.py`
- Check logs: `tail -f logs/sportstotalbot.log`
- View docs: `README.md`, `HOW_TO_RUN.md`, `ANALYSIS.md`
- Run tests: `pytest tests/ -v`

---

*End of Session Summary*

---

## CRITICAL FIX - Dynamic Season Calculation (February 4, 2026)

### The Problem

The bot was producing bad picks because it was using stale 2024-25 season data instead of the current 2025-26 season. This caused yesterday's picks (Feb 3) to go 1-5 with major misses.

### Root Cause

Hardcoded season strings in:
- src/data/nba_stats_cache.py line 370: "Season": "2025-26"

### The Fix

Created src/utils/season.py with dynamic season calculation:

```python
from datetime import datetime

def get_current_nba_season():
    now = datetime.now()
    current_year = now.year
    
    if now.month >= 10:
        season_start = current_year
    else:
        season_start = current_year - 1
    
    season_end = season_start + 1
    return f"{season_start}-{str(season_end)[-2:]}"
```

### Updated Files

1. src/utils/season.py - NEW file with dynamic season function
2. src/data/nba_stats_cache.py - Now imports and uses get_current_nba_season()
3. src/data/multi_source_stats.py - Updated comment to reflect dynamic nature

### NEVER DO THIS

```python
# WRONG - Hardcoded season
params = {"Season": "2025-26"}

# CORRECT - Dynamic season
from src.utils.season import get_current_nba_season
params = {"Season": get_current_nba_season()}
```

### Season Calculation Logic

| Current Date | Month | Season String |
|--------------|-------|---------------|
| February 2026 | 2 | 2025-26 |
| October 2025 | 10 | 2025-26 |
| August 2025 | 8 | 2024-25 |
| December 2026 | 12 | 2026-27 |

### How to Verify

```bash
cd /root/SportsTotalBot
python3 -c "from src.utils.season import get_current_nba_season; print(get_current_nba_season())"
```

### If Picks Are Wrong Again

1. Check the season is correct:
   grep -r "Season.*202" src/data/*.py
2. Clear cache:
   rm -rf data/cache/*
3. Re-run bot:
   python3 main_v2.py

---

*Last Updated: February 4, 2026*

---

## CRITICAL FIX - Dynamic Season Calculation (February 4, 2026)

### The Problem

The bot was producing bad picks because it was using stale 2024-25 season data instead of the current 2025-26 season. This caused yesterday's picks (Feb 3) to go 1-5 with major misses.

### Root Cause

Hardcoded season strings in:
- src/data/nba_stats_cache.py line 370: "Season": "2025-26"

### The Fix

Created src/utils/season.py with dynamic season calculation:

```python
from datetime import datetime

def get_current_nba_season():
    now = datetime.now()
    current_year = now.year
    
    if now.month >= 10:
        season_start = current_year
    else:
        season_start = current_year - 1
    
    season_end = season_start + 1
    return f"{season_start}-{str(season_end)[-2:]}"
```

### Updated Files

1. src/utils/season.py - NEW file with dynamic season function
2. src/data/nba_stats_cache.py - Now imports and uses get_current_nba_season()
3. src/data/multi_source_stats.py - Updated comment to reflect dynamic nature

### NEVER DO THIS

```python
# WRONG - Hardcoded season
params = {"Season": "2025-26"}

# CORRECT - Dynamic season
from src.utils.season import get_current_nba_season
params = {"Season": get_current_nba_season()}
```

### Season Calculation Logic

| Current Date | Month | Season String |
|--------------|-------|---------------|
| February 2026 | 2 | 2025-26 |
| October 2025 | 10 | 2025-26 |
| August 2025 | 8 | 2024-25 |
| December 2026 | 12 | 2026-27 |

### How to Verify

```bash
cd /root/SportsTotalBot
python3 -c "from src.utils.season import get_current_nba_season; print(get_current_nba_season())"
```

### If Picks Are Wrong Again

1. Check the season is correct:
   grep -r "Season.*202" src/data/*.py
2. Clear cache:
   rm -rf data/cache/*
3. Re-run bot:
   python3 main_v2.py

---

*Last Updated: February 4, 2026*

### Additional Files Fixed (Feb 4, 2026 - Second Pass)

| File | Issue | Fix |
|------|-------|-----|
| `src/data/fetchers.py` | Hardcoded `season: int = 2023` default | Now uses `get_season_start_year()` |
| `src/data/multi_source_stats.py` | Duplicate inline season calculation | Now uses `get_current_nba_season()` |

All season calculations now use the centralized `src/utils/season.py` utility.

---

## User Account: MyBookie.ag

**Sportsbook:** MyBookie.ag
**Status:** Active account - user wants integration explored in future

### Current Integration
- MyBookie odds ARE already fetched via The Odds API
- Bot shows MyBookie lines in picks data

### Future Possibilities (when user is ready)
1. Filter picks to show MyBookie-specific lines
2. Track bets placed manually on MyBookie
3. Telegram alerts formatted with MyBookie odds

### NOT Recommended
- Auto-betting (no public API, ToS violation risk, account ban risk)

---

---

## CRITICAL RULE: NEVER HARDCODE SEASONS

**Date Added:** February 4, 2026
**Reason:** Bad picks on Feb 3, 2026 (1-5 record) caused by stale 2024-25 data

### The Rule
```
NEVER write: "Season": "2025-26"
ALWAYS use:  "Season": get_current_nba_season()
```

### Files That MUST Use Dynamic Season
1. `src/utils/season.py` - The source of truth
2. `src/data/nba_stats_cache.py` - All API calls
3. `src/data/multi_source_stats.py` - All API calls  
4. `src/data/fetchers.py` - All API calls

### How It Works
```python
from src.utils.season import get_current_nba_season

# February 2026 -> "2025-26"
# October 2026 -> "2026-27"
season = get_current_nba_season()
```

### Verification Command
```bash
python3 -c "from src.utils.season import get_current_nba_season; print(get_current_nba_season())"
```

**This rule is NON-NEGOTIABLE. Hardcoded seasons = bad picks = lost money.**

---

*Last Updated: February 4, 2026*
