# SportsTotalBot - Quick Start Guide

## You're All Set Up!

Your API key is configured and the bot is working with real NBA data.

## How to Run It

### Option 1: Use the shell script (easiest)
```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
./run.sh
```

### Option 2: Run directly with V2 (recommended)
```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
source venv/bin/activate
python3 main_v2.py
```

### Option 3: Using environment variables
```bash
# Set your API key as environment variable
export ODDS_API_KEY="your_api_key_here"

# Run the bot
python3 main_v2.py
```

## Command Line Options

| Command | What it does |
|---------|--------------|
| `python3 main_v2.py` | Run full analysis on today's games |
| `python3 main_v2.py --performance` | Show historical performance report |
| `python3 main_v2.py --update-results` | Update completed game results |
| `python3 main_v2.py --log-level DEBUG` | Run with detailed logging |
| `pytest tests/ -v` | Run test suite |

## What You'll See

The bot will:
1. Fetch today's NBA games from The Odds API
2. Pull real team stats from NBA.com
3. Check for fatigue factors (back-to-backs, travel)
4. Calculate projections using efficiency metrics
5. Find +EV betting opportunities
6. Display picks with Kelly Criterion sizing

## Example Output

```
[INFO] Fetching games and odds...
[INFO] Found 11 games
[INFO] Analyzing: 76ers @ Clippers
[INFO]   Projection: 176.6 (Line: 218.5, Conf: 70%)
[INFO] Found +EV UNDER: 218.5 / -110

======================================================================
🎯 UNDER 218.5
   Teams: 76ers @ Clippers
   Odds: -110
   Projected: 176.6
   Win Prob: 60.5%
   EV: 15.50%
   Units: 8.53
======================================================================
```

## Understanding the Output

| Term | Meaning |
|------|---------|
| **EV** | Expected Value - positive = profitable bet theoretically |
| **Win Prob** | Model's estimated win probability |
| **Units** | Recommended bet size (1 unit = 1% of bankroll) |
| **Confidence** | How much data supports the projection |
| **Line** | The betting line from sportsbooks |

## Where Picks Are Saved

- `data/picks/daily_picks_YYYYMMDD.csv` - CSV format
- `data/picks/daily_picks_YYYYMMDD.json` - JSON format
- `data/sportstotalbot.db` - SQLite database

## Schedule It (Optional)

To run automatically every day at noon:

```bash
# Edit crontab
crontab -e

# Add this line:
0 12 * * * cd /Volumes/LegbaSSD/bots/SportsTotalBot && source venv/bin/activate && python3 main_v2.py
```

## Troubleshooting

### "Invalid API key configured!"
- Make sure your API key is set in `.env` or `config/config.yaml`
- Get a free key at https://the-odds-api.com/

### "Using league averages for..."
- NBA.com API is temporarily unavailable
- Bot falls back to league averages

### No picks found
- No +EV opportunities meet the thresholds
- Try lowering `MIN_EV_THRESHOLD` in config

## Need Help?

- Check the full README: `README.md`
- View analysis: `ANALYSIS.md`
- Check logs: `tail -f logs/sportstotalbot.log`
