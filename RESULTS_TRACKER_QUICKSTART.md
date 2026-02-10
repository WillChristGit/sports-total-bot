# SportsTotalBot Results Tracker - Quick Start Guide

## What Was Built

A complete results tracking system for SportsTotalBot that:
- Fetches final NBA scores from free APIs
- Compares picks to actual game results
- Calculates profit/loss, ROI, win rate, and units
- Saves historical performance data
- Provides detailed analytics

## File Structure

```
SportsTotalBot/
├── src/results/                          # Core module
│   ├── __init__.py                       # Package init
│   ├── tracker.py                        # Main tracker (738 lines)
│   └── README.md                         # Full documentation
│
├── data/results/                         # Output directory
│   └── 20260204_results.json             # Sample results file
│
├── test_results_tracker.py               # Test suite (all passing ✓)
├── demo_results_tracker.py               # Interactive demo
├── run_results_tracker.sh                # CLI runner
│
├── examples/
│   └── results_tracking_example.py       # Integration examples
│
└── RESULTS_TRACKER_SUMMARY.md            # Implementation summary
```

## Quick Start

### 1. Test the Installation

```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
python3 test_results_tracker.py
```

Expected output: All tests passing ✓

### 2. Run the Demo

```bash
python3 demo_results_tracker.py
```

This will:
- Load real picks from 2026-02-04
- Simulate game results
- Show evaluation logic
- Calculate metrics
- Save results to file

### 3. Track Real Results

```bash
# Track yesterday's results
./run_results_tracker.sh --latest

# Track specific date
./run_results_tracker.sh --date 2026-02-04

# Get 30-day report
./run_results_tracker.sh --report 30
```

## Key Features

### API Integration
- **balldontlie.io** (free, no key)
- **RapidAPI NBA** (optional, requires key)
- Automatic fallback between APIs

### Bet Type Support
- ✓ Totals (OVER/UNDER)
- ✓ Spreads (home/away)
- ✓ Moneyline (framework ready)

### Metrics Calculated
- Win Rate
- ROI (Return on Investment)
- Units (Half-Kelly Criterion)
- Profit/Loss (based on American odds)
- Record (W-L-P)

### Analytics
- By bet type (totals vs spreads)
- By side (over vs under, home vs away)
- By confidence level
- Historical trends (N-day reports)

## Output Format

Results saved to `data/results/YYYYMMDD_results.json`:

```json
{
  "date": "20260204",
  "tracked_at": "2026-02-05T06:18:59",
  "summary": {
    "wins": 6,
    "losses": 0,
    "pushes": 0,
    "pending": 1,
    "win_rate": 100.0,
    "total_profit": 5.37,
    "roi": 89.46,
    "by_type": {
      "totals": {"wins": 5, "losses": 0, "profit": 4.45},
      "spreads": {"wins": 1, "losses": 0, "profit": 0.92}
    }
  },
  "results": [
    {
      "game_id": "...",
      "bet_type": "totals",
      "side": "under",
      "line": 247.5,
      "odds": -112,
      "status": "won",
      "actual_total": 220,
      "profit_loss": 0.89,
      "units": 5.91,
      "result_reasoning": "Under 247.5: Actual total 220 (Under by 27.5)"
    }
  ]
}
```

## Python API Usage

```python
from src.results.tracker import ResultsTracker

# Initialize
tracker = ResultsTracker()

# Track results
results = tracker.track_results(date="2026-02-04")

# Access summary
summary = results['summary']
print(f"Record: {summary['wins']}-{summary['losses']}-{summary['pushes']}")
print(f"ROI: {summary['roi']}%")

# Get performance report
report = tracker.get_performance_report(days=30)
print(f"30-day profit: ${report['total_profit']:.2f}")

# Load historical data
historical = tracker.load_historical_results(days=7)
for day in historical:
    print(f"{day['date']}: {day['summary']['wins']}W")
```

## Integration Example

Add to your daily bot workflow:

```python
# In main_v2.py or similar
from src.results.tracker import ResultsTracker

def update_previous_results():
    """Track results from yesterday"""
    tracker = ResultsTracker()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    results = tracker.track_results(yesterday)

    if 'error' not in results:
        summary = results['summary']
        logger.info(f"Results for {yesterday}:")
        logger.info(f"  Record: {summary['wins']}-{summary['losses']}-{summary['pushes']}")
        logger.info(f"  ROI: {summary['roi']}%")
        logger.info(f"  Profit: ${summary['total_profit']:.2f}")
```

## Advanced Analytics

Run the example script:

```bash
python3 examples/results_tracking_example.py
```

This provides:
- Daily workflow demonstration
- Bet type breakdown (totals vs spreads)
- Side analysis (over vs under, home vs away)
- Confidence level analysis
- Best/worst day identification

## Configuration

### Optional API Key

Add to `.env` for backup API:

```bash
RAPID_API_KEY=your_key_here
```

Get free key at: https://rapidapi.com/api-sports/api/api-nba

### Custom Paths

```bash
./run_results_tracker.sh \
  --date 2026-02-04 \
  --picks-dir /path/to/picks \
  --results-dir /path/to/results
```

## Understanding the Metrics

### Win Rate
```
Win Rate = (Wins / (Wins + Losses)) × 100
```
Percentage of non-pushed bets that won.

### ROI
```
ROI = (Total Profit / Total Bets) × 100
```
Percentage return on $1 per bet.

### Units
```
Units = (EV / (Decimal Odds - 1)) × 100 × 0.5
```
Half-Kelly Criterion, capped at 10 units max.

### Profit/Loss
Based on American odds:
- Positive (+150): Win $1.50 on $1 bet
- Negative (-110): Win $0.91 on $1 bet

## Troubleshooting

### No picks found
Ensure `data/picks/daily_picks_YYYYMMDD.json` exists.

### No game results
- Check games have completed (status = "Final")
- Try different date
- Verify API is accessible

### API errors
- balldontlie.io: May be rate-limited, wait and retry
- RapidAPI: Check API key is valid

### Pending picks
Games that:
- Haven't started
- Haven't completed
- Couldn't be matched

## Testing

All tests pass:

```bash
$ python3 test_results_tracker.py
============================================================
ResultsTracker Test Suite
============================================================
Testing PickResult... ✓
Testing team name normalization... ✓
Testing totals evaluation... ✓
Testing spread evaluation... ✓
Testing summary calculation... ✓
Testing units calculation... ✓
Testing load_picks... ✓
============================================================
All tests passed! ✓
============================================================
```

## Demo Output

```bash
$ python3 demo_results_tracker.py
======================================================================
SportsTotalBot Results Tracker - Demo
======================================================================

1. Loading picks from 2026-02-04...
✓ Loaded 7 picks

2. Simulating game results...
✓ Created 5 mock game results

3. Evaluating picks against results...
...

SUMMARY
======================================================================
Record: 6W - 0L - 0P
Win Rate: 100.0%
Total Profit: $5.37
Total Units: 30.0
ROI: 89.46%

By Bet Type:
  TOTALS: 5W-0L-0P, Profit: $4.45
  SPREADS: 1W-0L-0P, Profit: $0.92

======================================================================
✓ Results saved to data/results/20260204_results.json
```

## Documentation

- **Full Docs**: `src/results/README.md`
- **Summary**: `RESULTS_TRACKER_SUMMARY.md`
- **Tests**: `test_results_tracker.py`
- **Demo**: `demo_results_tracker.py`
- **Examples**: `examples/results_tracking_example.py`

## What's Next

The tracker is production-ready. Consider:

1. **Daily Integration**: Add to main bot workflow
2. **Dashboard**: Display results in web dashboard
3. **Notifications**: Send results via Telegram/Discord
4. **Database**: Store results in SQLite for queries
5. **Charts**: Visual performance trends
6. **More Sports**: Extend to NFL, MLB, NHL

## Summary

✅ **Complete Implementation**
- 738-line core tracker module
- Free API integration (balldontlie.io)
- Totals and spread evaluation
- Profit/loss calculation
- Performance metrics (ROI, win rate, units)
- Historical tracking and reporting
- Advanced analytics
- Full documentation
- Comprehensive tests (all passing)
- CLI and Python API
- Demo and examples

✅ **Production Ready**
- Graceful error handling
- API fallback
- Team name normalization
- Pending game handling
- Extensible architecture

✅ **Well Documented**
- README with usage examples
- Quick start guide
- Implementation summary
- Inline code comments
- Test suite documentation

The results tracker is fully functional and ready to use!
