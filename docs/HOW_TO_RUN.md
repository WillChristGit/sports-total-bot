# SportsTotalBot - Quick Start

## You're All Set Up!

Your API key is configured and the bot is working.

## How to Run It

### Option 1: Use the shell script (easiest)
```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
./run.sh
```

### Option 2: Run directly
```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
source venv/bin/activate
python -c "import sys; sys.path.insert(0, '.'); from src.bot import main; main()"
```

## Other Commands

| Command | What it does |
|---------|--------------|
| `./run.sh --performance` | See your historical results |
| `./run.sh --update-results` | Update completed game results |

## What You Just Saw

The bot analyzed 7 NBA games and found **2 +EV bets**:

- **76ers @ Clippers OVER 218.6** - 5.84% EV, 3.18 units
- **Rockets @ Pacers OVER 218.7** - 5.13% EV, 2.82 units

These picks are saved to:
- `data/picks/daily_picks_20260202.csv`
- `data/picks/daily_picks_20260202.json`

## Understanding the Output

| Term | Meaning |
|------|---------|
| **EV** | Expected Value - positive = good bet |
| **Win Prob** | How likely the bet is to win |
| **Units** | How much to bet (1 unit = 1% of bankroll) |
| **Confidence** | How confident the model is |

## Schedule It (Optional)

To run automatically every day at noon:

```bash
# Edit crontab
crontab -e

# Add this line:
0 12 * * * cd /Volumes/LegbaSSD/bots/SportsTotalBot && ./run.sh
```

## Need Help?

Check the full analysis: `ANALYSIS.md`
