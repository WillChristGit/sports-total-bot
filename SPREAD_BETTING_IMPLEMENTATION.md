# Spread Betting Implementation

## Overview

This document describes the implementation of spread betting functionality for SportsTotalBot. The bot now generates picks for both **totals** (over/under) and **spreads** (point spread) for each NBA game.

## Implementation Date

February 4, 2026

## What Was Added

### 1. New Files Created

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/src/analysis/spread_projections.py`

A new module that projects the margin of victory for NBA games using:
- Offensive and defensive efficiency ratings
- Four Factors analysis (eFG%, TOV%, ORB%, FTR)
- Home court advantage
- Schedule fatigue adjustments
- Recent form adjustments

**Key Classes:**
- `SpreadProjection`: Dataclass containing projected scores and spread
- `EnhancedNBASpreadModel`: Main projection model for spreads

**Key Methods:**
- `project_game()`: Generates spread projection for a game
- `_calculate_team_score()`: Calculates expected points for a team
- `_calculate_confidence()`: Determines confidence in the projection

### 2. Modified Files

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/src/data/fetchers.py`

**Changes:**
- Updated `get_nba_games()` to fetch both totals and spreads from The Odds API
- Updated `get_wnba_games()` to fetch both totals and spreads
- Added `markets` parameter to control which markets to fetch

**Before:**
```python
"markets": "totals"
```

**After:**
```python
"markets": "totals,spreads"
```

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/main_v2.py`

**Changes:**
1. Added import for spread projection model:
   ```python
   from src.analysis.spread_projections import create_spread_projection_model, SpreadProjection
   ```

2. Updated `parse_odds_api_response()` to parse both totals and spreads:
   - Creates separate odds entries for totals and spreads
   - Keys format: `"{game_id}_totals"` and `"{game_id}_spreads"`

3. Updated `run_analysis()` to:
   - Create both totals and spreads projection models
   - Group odds by game ID
   - Generate both totals and spreads picks for each game
   - Calculate EV for both bet types

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/src/analysis/ev_calculator_v2.py`

**Changes:**
- Added `calculate_spreads_ev()` method to `EnhancedEVCalculator` class
- Calculates EV for both home and away spread bets
- Uses same Kelly Criterion approach as totals
- Accounts for higher variance in spreads (20% more than totals)

**Method Signature:**
```python
def calculate_spreads_ev(
    self,
    home_projected_score: float,
    away_projected_score: float,
    odds: OddsLine,
    confidence: float,
    min_confidence: float = 0.525,
    line_movement: Optional[LineMovement] = None
) -> List[EnhancedBetRecommendation]
```

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/src/output/formatter.py`

**Changes:**
1. Added `compact` parameter to `format_daily_picks()` for grouped output
2. Added `_format_compact_picks()` method to show both totals and spreads per game
3. Updated `_format_detailed_picks()` to separate totals and spreads sections
4. Updated `TelegramNotifier.send_picks()` to group picks by game
5. Added `_format_pick()` helper method for consistent formatting

**Compact Output Example:**
```
Boston Celtics @ Los Angeles Lakers - 8:00 PM ET
TOTAL: 🔽 UNDER 234.5 (EV: 8.2%)
SPREAD: Los Angeles Lakers -3.5 (EV: 5.1%)
```

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/src/data/models.py`

**Changes:**
- Added `data_quality` field to `BetRecommendation` dataclass
- Default value: "C" (on scale of A-F)

### 3. Test File Created

#### `/Volumes/LegbaSSD/bots/SportsTotalBot/test_spreads.py`

Test script to verify spread betting functionality:
- Tests spread projection model
- Tests spread EV calculator
- Shows example output format

**Run with:**
```bash
./venv/bin/python test_spreads.py
```

## How It Works

### Data Flow

```
1. Fetch Games (The Odds API)
   ↓
2. Parse Odds (totals + spreads)
   ↓
3. Fetch Team Stats (NBA.com)
   ↓
4. Generate Projections
   ├─ Totals Model → Projected Total
   └─ Spreads Model → Projected Scores & Spread
   ↓
5. Calculate EV
   ├─ Totals EV → Over/Under picks
   └─ Spreads EV → Home/Away picks
   ↓
6. Format Output
   ├─ Console (grouped by game)
   ├─ CSV/JSON files
   └─ Telegram notification
```

### Spread Projection Logic

The spread projection model calculates the expected score for each team:

```python
# Team's offensive rating vs opponent's defensive rating
expected_ortg = (team_ortg_normalized * 0.6 + opp_drtg_normalized * 0.4) * league_avg_ortg

# Convert to points
expected_points = (expected_ortg / 100.0) * game_pace

# Apply home court advantage
if is_home:
    expected_points += (home_court_advantage * 0.6)
else:
    expected_points -= (home_court_advantage * 0.4)
```

**Spread = Home Projected Score - Away Projected Score**

- Positive spread = Home team favored
- Negative spread = Away team favored

### EV Calculation for Spreads

Similar to totals, but with adjustments for spread variance:

```python
# Spreads have higher variance than totals
spread_variance = model_variance * 1.2

# Calculate win probability
home_diff = projected_margin - spread_line
home_z = home_diff / spread_variance
home_win_prob = 0.5 * (1 + erf(home_z / sqrt(2)))

# Apply market efficiency adjustment
home_win_prob = 0.5 + (home_win_prob - 0.5) * 0.30
```

## Output Format

### Console Output (Compact Mode)

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

======================================================================
Total picks: 3
```

### Console Output (Detailed Mode)

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
```

### Telegram Output

```
*SportsTotalBot Daily Picks*
*Feb 04, 2026 06:00 PM*
-------------------------------

*Boston Celtics @ Los Angeles Lakers - 8:00 PM*
TOTAL: 🔽 UNDER 234.5 (EV: 8.2%)
SPREAD: Los Angeles Lakers -3.5 (EV: 5.1%)
-------------------------------

Data Quality: 85/100
```

## Configuration

No configuration changes required. The bot will automatically generate both totals and spreads picks when you run:

```bash
python3 main_v2.py
```

To use detailed output instead of compact:

```python
# In main_v2.py, change:
report = formatter.format_daily_picks(recommendations, games, quality_report, compact=True)

# To:
report = formatter.format_daily_picks(recommendations, games, quality_report, compact=False)
```

## Key Differences: Totals vs Spreads

| Aspect | Totals | Spreads |
|--------|--------|---------|
| **Line Type** | Single number (e.g., 234.5) | Two numbers (e.g., Lakers -3.5, Celtics +3.5) |
| **Projection** | Total points scored | Margin of victory |
| **Variance** | Base variance | 1.2x base variance (higher uncertainty) |
| **Confidence Cap** | 70% | 60% (harder to predict) |
| **Market Efficiency** | 35% factor | 30% factor (more efficient) |
| **Home Court** | Applied to pace | Applied directly to score |

## Testing

Run the test script to verify everything works:

```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
./venv/bin/python test_spreads.py
```

Expected output:
```
🏀 SportsTotalBot - Spread Betting Module Test

============================================================
Testing Spread Projection Model
============================================================
Game: Boston Celtics @ Los Angeles Lakers
Projected Home Score: 115.9
Projected Away Score: 111.6
Projected Spread: +4.3
Confidence: 60.0%

✅ All tests passed!
```

## Troubleshooting

### No spread picks generated

**Possible causes:**
1. No spread odds available from The Odds API
2. Projected margin too close to the line (low EV)
3. Confidence too low (below 52.5% threshold)

**Solution:** Check the logs for detailed information:
```bash
tail -f logs/sportstotalbot.log
```

### Spread projections seem off

**Check:**
1. Team stats are being fetched correctly (data quality should be A or B)
2. Recent games data is available
3. Home court advantage is applied (3.5 points default)

### EV calculations seem wrong

**Verify:**
1. Min EV threshold (default 1.5%)
2. Min confidence (default 52.5%)
3. Kelly Criterion is being applied for units

## Future Improvements

### Potential Enhancements

1. **Alternate Spreads:** -7.5, +7.5, etc.
2. **First Half Spreads:** Project 1st half score margin
3. **Live Spreads:** Adjust projections during game
4. **Team Trends:** Factor in historical spread performance
5. **Referee Effects:** Some refs favor home teams more

### Data Improvements

1. **Injury Data:** Adjust for key player injuries
2. **Rest Days:** More granular fatigue modeling
3. **Travel Distance:** Better travel adjustment
4. **Altitude:** Factor in high-altitude venues

## Integration with Existing Code

The spread betting functionality integrates seamlessly with existing totals functionality:

- **Same team stats** are used for both projections
- **Same EV calculator** handles both bet types
- **Same output formatter** displays both types
- **Same database schema** stores both types
- **Same Telegram notifications** send both types

No breaking changes were made to existing functionality.

## Files Summary

### New Files
- `src/analysis/spread_projections.py` - Spread projection model
- `test_spreads.py` - Test script

### Modified Files
- `src/data/fetchers.py` - Fetch spreads from API
- `main_v2.py` - Generate both totals and spreads picks
- `src/analysis/ev_calculator_v2.py` - Calculate spread EV
- `src/output/formatter.py` - Display both bet types
- `src/data/models.py` - Added data_quality field

## Conclusion

The spread betting implementation is complete and ready to use. The bot now provides comprehensive analysis for both totals and spreads, giving you more opportunities to find +EV bets.

For questions or issues, refer to the test script or check the logs.

---

*Last Updated: February 4, 2026*
