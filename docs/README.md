# SportsTotalBot

AI-powered sports betting analysis bot that identifies positive EV (Expected Value) betting opportunities on sports totals (over/under bets).

## Features

- **Multi-Sport Support**: NBA (initially), with expandability to WNBA, NFL, MLB, NHL
- **Statistical Projections**: Uses team efficiency, pace, and recent form to project game totals
- **EV Calculator**: Identifies +EV betting opportunities by comparing projections to market odds
- **Performance Tracking**: Database to track all picks and results
- **Multiple Output Formats**: Console, CSV, JSON, and Discord notifications

## Installation

### Prerequisites

- Python 3.9+
- API key from [The Odds API](https://the-odds-api.com/) (free tier available)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your API key:
```bash
cp config/config.yaml config/config.yaml.local
# Edit config/config.yaml.local and add your API key
```

3. Run the bot:
```bash
python main.py
```

## Usage

### Daily Analysis

Run the bot to analyze today's games:
```bash
python main.py
```

### View Performance

Check historical performance:
```bash
python main.py --performance
```

### Update Results

Update results for completed games:
```bash
python main.py --update-results
```

### Options

```
--config PATH        Config file path (default: config/config.yaml)
--log-level LEVEL    Log level (default: INFO)
--performance        Show performance report
--update-results     Update results for completed games
--dry-run            Run without saving to database
```

## Configuration

Edit `config/config.yaml`:

```yaml
api_keys:
  the_odds_api: "YOUR_API_KEY_HERE"

analysis:
  min_ev_threshold: 0.02  # Minimum 2% EV to recommend
  min_confidence: 0.55    # Minimum 55% win probability

output:
  discord_webhook: ""     # Optional Discord webhook URL
```

## How It Works

1. **Data Collection**: Fetches upcoming games and current odds from APIs
2. **Statistical Analysis**: Calculates team projections using:
   - Offensive/defensive efficiency
   - Pace of play
   - Recent form
   - Home court advantage
3. **EV Calculation**: Compares projections to betting lines
4. **Recommendations**: Outputs only +EV bets that meet confidence thresholds

## Disclaimer

This tool is for educational and entertainment purposes only. Sports betting involves risk. Never bet more than you can afford to lose. Past performance does not guarantee future results.

## License

MIT License - See LICENSE file for details
