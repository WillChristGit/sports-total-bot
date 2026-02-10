# SportsTotalBot - Spread Betting Output Example

This document shows example output from the updated bot with spread betting support.

## Console Output (Compact Mode - Default)

```
======================================================================
SportsTotalBot Daily Picks - 2026-02-04 18:00
======================================================================

--- NBA ---

Boston Celtics @ Los Angeles Lakers - 8:00 PM ET
TOTAL: 🔽 UNDER 234.5 (EV: 8.2%)
SPREAD: Los Angeles Lakers -3.5 (EV: 5.1%)

Miami Heat @ Orlando Magic - 7:30 PM ET
TOTAL: 🔼 OVER 220.5 (EV: 4.3%)

Golden State Warriors @ Phoenix Suns - 9:00 PM ET
TOTAL: 🔽 UNDER 228.0 (EV: 6.8%)
SPREAD: Phoenix Suns +2.5 (EV: 3.2%)

======================================================================
Total picks: 5

Data Quality Summary:
  Excellent (A): 6
  Good (B):      0
  Fair (C):      0
  Poor (D):      0
```

## Console Output (Detailed Mode)

```
======================================================================
SportsTotalBot Daily Picks - 2026-02-04 18:00
======================================================================

--- NBA TOTALS ---

🎯 UNDER 234.5
   Teams: Boston Celtics @ Los Angeles Lakers
   Odds: -105
   Projected Total: 223.0
   Win Prob: 56.5%
   EV: 8.2%
   Confidence: 58.0%
   Units: 2.4
   Data Quality: 🟢 A
   Reasoning: Projected: 223.0 vs Line: 234.5 (Diff: -11.5). Win Prob: 56.5%, EV: 8.18%.

🎯 OVER 220.5
   Teams: Miami Heat @ Orlando Magic
   Odds: -108
   Projected Total: 228.3
   Win Prob: 54.2%
   EV: 4.3%
   Confidence: 56.0%
   Units: 1.9
   Data Quality: 🟢 A
   Reasoning: Projected: 228.3 vs Line: 220.5 (Diff: +7.8). Win Prob: 54.2%, EV: 4.31%.

--- NBA SPREADS ---

🎯 HOME -3.5
   Teams: Boston Celtics @ Los Angeles Lakers
   Odds: -110
   Projected Margin: +7.0
   Win Prob: 54.0%
   EV: 5.1%
   Confidence: 55.0%
   Units: 1.8
   Data Quality: 🟢 A
   Reasoning: Projected Margin: +7.0 vs Line: -3.5. Win Prob: 54.0%, EV: 5.12%.

🎯 AWAY +2.5
   Teams: Golden State Warriors @ Phoenix Suns
   Odds: -105
   Projected Margin: +4.0
   Win Prob: 53.5%
   EV: 3.2%
   Confidence: 54.0%
   Units: 1.4
   Data Quality: 🟢 A
   Reasoning: Projected Margin: +4.0 vs Line: +2.5. Win Prob: 53.5%, EV: 3.21%.

======================================================================
Total picks: 5

Data Quality Summary:
  Excellent (A): 6
  Good (B):      0
  Fair (C):      0
  Poor (D):      0
```

## Telegram Notification

```
SportsTotalBot Daily Picks
Feb 04, 2026 06:00 PM
-------------------------------

Boston Celtics @ Los Angeles Lakers - 8:00 PM
TOTAL: 🔽 UNDER 234.5 (EV: 8.2%)
SPREAD: Los Angeles Lakers -3.5 (EV: 5.1%)
-------------------------------

Miami Heat @ Orlando Magic - 7:30 PM
TOTAL: 🔼 OVER 220.5 (EV: 4.3%)
-------------------------------

Golden State Warriors @ Phoenix Suns - 9:00 PM
TOTAL: 🔽 UNDER 228.0 (EV: 6.8%)
SPREAD: Phoenix Suns +2.5 (EV: 3.2%)
-------------------------------

Data Quality: 100/100
```

## CSV Output (data/picks/daily_picks_20260204.csv)

```csv
Game ID,Sport,Bet Type,Side,Line,Odds,Projected Value,EV,Win Probability,Confidence,Home Team,Away Team,Game Time,Reasoning
game_001,nba,totals,under,234.5,-105,223.0,0.0818,0.5650,0.5800,Los Angeles Lakers,Boston Celtics,2026-02-04 20:00,Projected: 223.0 vs Line: 234.5 (Diff: -11.5). Win Prob: 56.5%, EV: 8.18%.
game_001,nba,spreads,home,-3.5,-110,7.0,0.0512,0.5400,0.5500,Los Angeles Lakers,Boston Celtics,2026-02-04 20:00,Projected Margin: +7.0 vs Line: -3.5. Win Prob: 54.0%, EV: 5.12%.
game_002,nba,totals,over,220.5,-108,228.3,0.0431,0.5420,0.5600,Orlando Magic,Miami Heat,2026-02-04 19:30,Projected: 228.3 vs Line: 220.5 (Diff: +7.8). Win Prob: 54.2%, EV: 4.31%.
game_003,nba,totals,under,228.0,-110,221.5,0.0680,0.5580,0.5700,Phoenix Suns,Golden State Warriors,2026-02-04 21:00,Projected: 221.5 vs Line: 228.0 (Diff: -6.5). Win Prob: 55.8%, EV: 6.80%.
game_003,nba,spreads,away,2.5,-105,4.0,0.0321,0.5350,0.5400,Phoenix Suns,Golden State Warriors,2026-02-04 21:00,Projected Margin: +4.0 vs Line: +2.5. Win Prob: 53.5%, EV: 3.21%.
```

## JSON Output (data/picks/daily_picks_20260204.json)

```json
[
  {
    "game_id": "game_001",
    "sport": "nba",
    "bet_type": "totals",
    "side": "under",
    "line": 234.5,
    "odds": -105,
    "projected_value": 223.0,
    "ev": 0.0818,
    "win_probability": 0.565,
    "confidence": 0.58,
    "home_team": "Los Angeles Lakers",
    "away_team": "Boston Celtics",
    "game_time": "2026-02-04T20:00:00",
    "reasoning": "Projected: 223.0 vs Line: 234.5 (Diff: -11.5). Win Prob: 56.5%, EV: 8.18%."
  },
  {
    "game_id": "game_001",
    "sport": "nba",
    "bet_type": "spreads",
    "side": "home",
    "line": -3.5,
    "odds": -110,
    "projected_value": 7.0,
    "ev": 0.0512,
    "win_probability": 0.54,
    "confidence": 0.55,
    "home_team": "Los Angeles Lakers",
    "away_team": "Boston Celtics",
    "game_time": "2026-02-04T20:00:00",
    "reasoning": "Projected Margin: +7.0 vs Line: -3.5. Win Prob: 54.0%, EV: 5.12%."
  }
]
```

## Key Differences in Output

### Totals
- **Line**: Single number (e.g., 234.5)
- **Side**: OVER or UNDER
- **Projected Value**: Total combined score
- **Symbol**: 🔼 for OVER, 🔽 for UNDER

### Spreads
- **Line**: Negative for favorite, positive for underdog (e.g., -3.5, +2.5)
- **Side**: HOME or AWAY
- **Projected Value**: Margin of victory
- **Team Name**: Always shown to clarify which team

## Reading Spread Picks

Example: `SPREAD: Los Angeles Lakers -3.5 (EV: 5.1%)`

This means:
- **Los Angeles Lakers** are favored to win by 3.5 points
- To cover the spread, they must win by **more than 3.5 points**
- The model predicts they'll win by **7.0 points** (the edge)
- **EV: 5.1%** means this bet has positive expected value
- If you bet $100, you expect to win $105.10 on average

Example: `SPREAD: Phoenix Suns +2.5 (EV: 3.2%)`

This means:
- **Phoenix Suns** are underdogs (+2.5)
- They can **lose by up to 2 points** and still cover
- The model predicts they'll lose by only 1 point (or win!)
- **EV: 3.2%** means positive expected value

## Understanding the Numbers

### Spread Line
- **Negative (e.g., -3.5)**: Team is favored
- **Positive (e.g., +2.5)**: Team is underdog

### Projected Margin
- **Positive**: Home team expected to win
- **Negative**: Away team expected to win
- The model's predicted margin of victory

### Edge
- Difference between projected margin and spread line
- Larger edge = more confident in the pick
- Example: Projected +7.0 vs Line -3.5 = 10.5 point edge

### Win Probability
- Likelihood the spread will cover
- Accounts for market efficiency
- Capped at 65% for realism

### EV (Expected Value)
- Positive EV = profitable bet in the long run
- Negative EV = unprofitable bet
- The bot only shows +EV bets

### Units (Kelly Criterion)
- Recommended bet size
- 1 unit = 1% of bankroll
- Higher EV + higher confidence = more units

## Data Quality Indicator

- 🟢 **A**: Fresh data from NBA.com (most reliable)
- 🟡 **B**: Cached < 6 hours
- 🟠 **C**: Cached < 24 hours
- 🔴 **D**: League averages (use caution)
- ⚫ **F**: No data (do not trust)

Always check data quality before placing bets!

---

*For implementation details, see SPREAD_BETTING_IMPLEMENTATION.md*
