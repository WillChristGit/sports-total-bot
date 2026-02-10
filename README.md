# SportsTotalBot

AI-powered sports betting analysis bot that identifies positive EV (Expected Value) betting opportunities on sports totals (over/under bets).

## Features

- **Real-Time NBA Stats**: Fetches live team statistics from NBA.com API
- **Statistical Projections**: Uses offensive/defensive rating, pace, Four Factors, and recent form
- **Fatigue Modeling**: Adjusts for back-to-back games, rest days, and travel
- **EV Calculator**: Identifies +EV betting opportunities with Kelly Criterion sizing
- **Performance Tracking**: SQLite database to track all picks and results
- **Multiple Output Formats**: Console, CSV, JSON, and Discord notifications
- **Environment Variable Support**: Secure configuration with `.env` file
- **Retry Logic**: Exponential backoff for resilient API calls
- **Comprehensive Tests**: Pytest suite for reliability
- **Web Dashboard**: Flask-based dashboard for viewing picks and performance (NEW!)

## Installation

### Prerequisites

- Python 3.9+
- API key from [The Odds API](https://the-odds-api.com/) (free tier available)

### Setup

```bash
# Clone or navigate to the directory
cd /Volumes/LegbaSSD/bots/SportsTotalBot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your ODDS_API_KEY
```

### Configuration

Edit `.env` file (recommended) or `config/config.yaml`:

```bash
# .env file
ODDS_API_KEY=your_api_key_here

# Optional
DISCORD_WEBHOOK=
MIN_EV_THRESHOLD=0.02
MIN_CONFIDENCE=0.55
LOG_LEVEL=INFO
```

## Usage

### Daily Analysis

```bash
# Activate virtual environment first
source venv/bin/activate

# Run analysis on today's games
python3 main_v2.py
```

### View Performance

```bash
python3 main_v2.py --performance
```

### Update Results

```bash
python3 main_v2.py --update-results
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Web Dashboard (NEW!)

```bash
# Start the web dashboard (auto-opens browser)
./run_dashboard.sh

# Or manually:
source venv/bin/activate
python dashboard.py
```

The dashboard provides:
- Real-time picks display with auto-refresh
- Historical performance tracking
- Statistics by sport, bet type, and side
- RESTful API for integrations

**Dashboard URL:** http://localhost:5001

**API Endpoints:**
- `GET /api/picks` - Today's picks
- `GET /api/history` - Historical performance
- `GET /api/stats` - Summary statistics
- `GET /api/health` - Health check

**Documentation:** See `dashboard/README.md` for full details

### Options

```
--config PATH        Config file path (default: config/config.yaml)
--log-level LEVEL    Log level (DEBUG, INFO, WARNING, ERROR)
--performance        Show performance report
--update-results     Update results for completed games
```

## How It Works

1. **Data Collection**: Fetches upcoming games from The Odds API
2. **Real Stats**: Pulls live team stats from NBA.com (offensive/defensive rating, pace, eFG%, etc.)
3. **Fatigue Analysis**: Checks schedule for back-to-backs, rest days, travel
4. **Projections**: Calculates projected totals using efficiency metrics
5. **EV Calculation**: Compares projections to betting lines with proper vig adjustment
6. **Kelly Sizing**: Recommends bet sizes using Half-Kelly Criterion
7. **Recommendations**: Outputs only +EV bets meeting confidence thresholds

## Project Structure

```
/Volumes/LegbaSSD/bots/SportsTotalBot/
├── config/               # Configuration files
├── src/
│   ├── data/            # Data models and API fetchers
│   │   ├── models.py           # Dataclasses for Game, Odds, Projection
│   │   ├── fetchers.py         # API fetchers with retry logic
│   │   └── nba_stats_cache.py  # Live NBA stats from NBA.com
│   ├── analysis/        # Statistical models
│   │   ├── projections_v2.py   # Enhanced projection model
│   │   └── ev_calculator_v2.py # EV calculator with Kelly sizing
│   ├── storage/         # Database layer
│   │   └── database.py         # SQLite operations
│   ├── output/          # Formatters and notifiers
│   │   └── formatter.py        # Output formatting
│   ├── config/          # Configuration management
│   │   └── loader.py           # Environment-aware config loader
│   └── utils/           # Utilities
│       ├── logging.py          # Structured logging
│       └── retry.py            # Exponential backoff retry
├── tests/               # Pytest test suite
├── scripts/             # Utility scripts
├── data/                # Historical data and picks
├── logs/                # Application logs
├── dashboard/           # Web dashboard files (NEW!)
│   ├── index.html              # Dashboard interface
│   ├── styles.css              # Dashboard styling
│   ├── app.js                  # Frontend JavaScript
│   └── README.md               # Dashboard documentation
├── dashboard.py         # Flask web server (NEW!)
├── run_dashboard.sh     # Dashboard launcher script (NEW!)
└── main_v2.py           # Main entry point
```

## Example Output

```
======================================================================
SportsTotalBot Daily Picks - 2026-02-02 21:17
======================================================================

--- NBA ---

🎯 UNDER 219.7
   Teams: Phoenix Suns @ Portland Trail Blazers
   Odds: -108
   Projected: 176.6
   Win Prob: 60.5%
   EV: 16.52%
   Confidence: 70.0%
   Units: 8.92
   Reasoning: Projected: 176.6 vs Line: 219.7 (Diff: -43.1)...

🎯 UNDER 218.5
   Teams: 76ers @ Clippers
   Odds: -110
   Projected: 176.6
   Win Prob: 60.5%
   EV: 15.50%
   Units: 8.53

======================================================================
Total picks: 9
```

## Understanding the Metrics

| Metric | Description |
|--------|-------------|
| **EV** | Expected Value - positive % indicates profitable bet |
| **Win Prob** | Model's estimated probability of winning |
| **Confidence** | How much historical data supports the projection |
| **Units** | Recommended bet size (1 unit = 1% of bankroll) |

## V3 Improvements

The bot has been significantly improved with:

1. **Real NBA Data** - Live stats from NBA.com instead of mock data
2. **Security** - Environment variable support via `.env` file
3. **Reliability** - Retry logic with exponential backoff for API calls
4. **Testing** - Comprehensive pytest test suite
5. **Formatting** - Clean numeric output (no more `238.83333333333334`)
6. **Logging** - Structured, colored logging with JSON support
7. **Caching** - Smart caching for NBA stats to reduce API calls

## Disclaimer

This tool is for educational and entertainment purposes only. Sports betting involves risk. Never bet more than you can afford to lose. Past performance does not guarantee future results.

## License

MIT License
