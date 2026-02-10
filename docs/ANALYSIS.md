# SportsTotalBot - Analysis & Improvement Report

**Date:** 2026-02-02
**Version:** V2 (Enhanced)
**Status:** Complete

---

## Executive Summary

SportsTotalBot is an AI-powered sports betting analysis bot designed to identify positive EV (Expected Value) betting opportunities on game totals (over/under bets). This report documents the initial implementation, analysis findings, and V2 improvements.

---

## Initial Implementation (V1)

### What Was Built

The initial version included:

1. **Data Pipeline**
   - API integration with The Odds API for live odds
   - NBA stats fetching (with fallback to mock data)
   - SQLite database for persistence

2. **Analysis Engine**
   - NBA totals projection model
   - EV calculator for identifying +EV bets
   - Confidence-based filtering

3. **Output System**
   - Console reports
   - CSV/JSON export
   - Optional Discord notifications

4. **File Structure**
```
/Volumes/LegbaSSD/bots/SportsTotalBot/
├── config/           # Configuration files
├── src/
│   ├── data/        # Data models and API fetchers
│   ├── analysis/    # Projection and EV models
│   ├── storage/     # Database layer
│   └── output/      # Formatters and notifiers
├── scripts/         # Scheduled and backtesting scripts
├── data/            # Historical data and picks
├── logs/            # Application logs
└── venv/            # Python virtual environment
```

---

## Analysis Results

Two specialized agents were deployed to analyze the codebase:

### Agent 1: Code Quality Analysis

**Key Findings:**

| Issue | Severity | Description |
|-------|----------|-------------|
| Bare except clause | Critical | Silent error hiding in config loading |
| Odds parsing bug | High | Overwrites instead of aggregating bookmaker data |
| No team name mapping | High | API team names don't match |
| Missing error handling | Medium | No retry logic for API failures |
| Security concern | Medium | API keys in plain text config |
| Performance | Low | Sequential API calls, no caching |

**Specific Issues Found:**

```python
# CRITICAL: Bare except clause (line 173)
try:
    with open('config/sports_config.yaml', 'r') as f:
        sports_config = yaml.safe_load(f)
except:  # ← Catches ALL exceptions silently!
    pass
```

```python
# BUG: Odds overwriting (line 115)
odds_list[game_id] = odds  # Overwrites instead of aggregating
```

### Agent 2: Statistical Model Analysis

**Key Findings:**

| Issue | Impact | Description |
|-------|--------|-------------|
| Uses raw PPG | High | Should use offensive/defensive rating (per 100 possessions) |
| No fatigue modeling | High | Missing rest days, back-to-back, travel factors |
| Probability too conservative | Medium | 14-point SD with 0.3-0.7 range clamping |
| Missing Four Factors | Medium | No eFG%, TOV%, ORB%, FTR analysis |
| No injury impact | Medium | Player absences not modeled |
| No line movement tracking | Low | Opening vs closing line signals ignored |
| Confidence thresholds | Medium | 55% min too aggressive for efficient markets |

**Professional Comparison:**

Research from professional betting sources shows:
- **Pace is the single best predictor** of total score
- **Offensive/Defensive Rating** (per 100 possessions) is the industry standard
- **Four Factors** (eFG%, TOV%, ORB%, FTR) explain 95% of game outcomes
- **Fatigue significantly impacts** totals (-1.8 pts for B2B, -2.5 for 3-in-4)
- **NBA totals market is highly efficient** - true edges are 1-3%

---

## V2 Improvements

Based on the analysis, V2 was implemented with the following enhancements:

### 1. Code Quality Fixes

#### Fixed Bare Except Clause
```python
# V2: Proper exception handling
try:
    with open('config/sports_config.yaml', 'r') as f:
        sports_config = yaml.safe_load(f)
except FileNotFoundError:
    logging.warning("Sports config file not found, using defaults")
    sports_config = {}
except yaml.YAMLError as e:
    logging.warning(f"Error parsing sports config: {e}, using defaults")
    sports_config = {}
```

#### Added Team Name Mapping
```python
TEAM_NAME_MAPPINGS = {
    'LAL': 'Los Angeles Lakers',
    'LAC': 'Los Angeles Clippers',
    # ... comprehensive mappings
}

def normalize_team_name(team_name: str) -> str:
    return TEAM_NAME_MAPPINGS.get(team_name, team_name)
```

#### Fixed Odds Aggregation
```python
# V2: Properly aggregates from multiple bookmakers
over_odds_list = []
under_odds_list = []
for bookmaker in game_data.get('bookmakers', []):
    for market in bookmaker.get('markets', []):
        # Collect all odds
        over_odds_list.append(price)

# Use consensus (average)
avg_over_odds = round(sum(over_odds_list) / len(over_odds_list))
```

### 2. Enhanced Statistical Model

#### Uses Efficiency Metrics
```python
@dataclass
class AdvancedTeamStats(TeamStats):
    # Points per 100 possessions (industry standard)
    offensive_rating: float = 110.0
    defensive_rating: float = 110.0

    # Four Factors (Dean Oliver)
    efg_pct: float = 0.500   # Effective FG%
    tov_pct: float = 0.140   # Turnover rate
    orb_pct: float = 0.250   # Offensive rebounding%
    ft_rate: float = 0.200   # Free throw rate
```

#### Added Fatigue Modeling
```python
class FatigueCalculator:
    B2B_PENALTY = -1.8           # Back-to-back
    THIRD_IN_4_PENALTY = -2.5    # 3 games in 4 nights
    TRAVEL_PENALTY_PER_1000 = -0.5
    TZ_CHANGE_PENALTY = -0.8
    REST_ADVANTAGE_PER_DAY = 0.6
```

#### Bayesian Confidence
```python
def _calculate_bayesian_confidence(self, home_stats, away_stats):
    # Prior (weakly informative)
    alpha_prior = 52
    beta_prior = 48

    # Update with sample size
    sample_bonus = min(avg_games / 82.0, 1.0) * 10

    # More realistic confidence
    base_confidence = 0.52  # Market is efficient
    confidence = base_confidence + sample_bonus * 0.3

    return min(confidence, 0.70)  # Cap at 70%
```

### 3. Enhanced EV Calculator

#### Model-Specific Variance
```python
def _calculate_win_probability_enhanced(self, diff, projection):
    # Adjust SD based on model confidence
    confidence_adjusted_sd = (
        self.model_variance * (1.5 - projection.confidence)
    )

    # More realistic market efficiency factor
    market_efficiency_factor = 0.35
    adjusted_prob = 0.5 + (cdf - 0.5) * market_efficiency_factor

    return max(0.35, min(0.65, adjusted_prob))
```

#### Kelly Criterion Sizing
```python
class KellyBetSizing:
    def calculate_units(self, win_probability, american_odds):
        kelly_fraction = self.calculate_kelly_fraction(...)
        # Use Half-Kelly for safety
        units = kelly_fraction * 100 * 0.5
        return round(units, 2)
```

#### Line Movement Analysis
```python
class LineMovementAnalyzer:
    def analyze_line_movement(self, movement, your_projection):
        # Early sharp move in your direction (good)
        if movement.hours_since_open < 4:
            if line_move_aligns:
                return 0.02, "Sharp action confirms your pick"

        # Reverse line movement (possible overreaction)
        if movement.hours_since_open > 12:
            if possible_overreaction:
                return 0.015, "Overreaction creates value"
```

### 4. More Conservative Thresholds

| Setting | V1 | V2 | Rationale |
|---------|----|----|-----------|
| Min EV | 2% | 1.5% | More realistic for efficient markets |
| Min Confidence | 55% | 52.5% | Breakeven with standard vig |
| Max Confidence | 85% | 70% | More realistic cap |

---

## Files Created/Modified

### New Files (V2)
- `src/analysis/projections_v2.py` - Enhanced projection model
- `src/analysis/ev_calculator_v2.py` - Enhanced EV calculator
- `main_v2.py` - Improved main entry point

### Modified Files
- `requirements.txt` - Simplified to core dependencies only
- `src/analysis/projections.py` - Removed numpy dependency
- `src/analysis/ev_calculator.py` - Removed scipy dependency

---

## Installation & Usage

### Prerequisites
- Python 3.9+
- API key from https://the-odds-api.com/ (free tier available)

### Setup
```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
Edit `config/config.yaml`:
```yaml
api_keys:
  the_odds_api: "YOUR_API_KEY_HERE"

analysis:
  min_ev_threshold: 0.015  # 1.5%
  min_confidence: 0.525    # 52.5%
```

### Running
```bash
# Use V2 (enhanced models)
./venv/bin/python main_v2.py

# View performance
./venv/bin/python main_v2.py --performance

# Update completed game results
./venv/bin/python main_v2.py --update-results
```

---

## Next Steps (Future Improvements)

### High Priority
1. **Real NBA API Integration** - Replace mock stats with live data
2. **Team ID Mapping** - Proper database of team IDs across APIs
3. **Historical Data** - Implement backtesting capability
4. **Async API Calls** - Improve performance with concurrent requests

### Medium Priority
5. **Injury API Integration** - Track player injuries and impact
6. **Referee Tendencies** - Officiating crew adjustments
7. **Venue Factors** - Arena-specific pace adjustments
8. **Caching Layer** - Reduce redundant API calls

### Low Priority
9. **Machine Learning** - Train models on historical data
10. **More Sports** - Add WNBA, NFL, MLB, NHL support
11. **Live Odds** - Real-time line monitoring
12. **Web Dashboard** - Frontend for viewing picks

---

## Disclaimer

**This tool is for educational and entertainment purposes only.**

- Sports betting involves significant financial risk
- Past performance does not guarantee future results
- The NBA totals market is highly efficient
- Even professional bettors typically operate on 1-3% edges
- Never bet more than you can afford to lose
- This is not financial advice

---

## References

### Research Sources
1. [NBA Betting Strategy 2026 - TopEndSports](https://www.topendsports.com/betting-guides/sport-specific/nba/strategy.htm)
2. [Predicting NBA Betting Lines - Stanford](https://cs229.stanford.edu/proj2013/ChengDadeLipmanMills-PredictingTheBettingLineInNBAGames.pdf)
3. [Betting the Buzzer - CMU Statistics](https://www.stat.cmu.edu/capstoneresearch/spring2024/460files/team6.pdf)
4. [Rest Days Factor - NBAStuffer](https://www.nbastuffer.com/rest-days-factor-nba-scheduling/)
5. [NBA Home Court Advantage - Wharton](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Nba.pdf)

### Tools Used
- The Odds API (https://the-odds-api.com/)
- API-NBA (https://api-nba-v1.p.rapidapi.com)
- Python 3.14
- SQLite

---

## Agent Analysis IDs

- **Code Quality Analysis Agent:** `aba8286`
- **Statistical Model Analysis Agent:** `aeb74af`

These agents can be resumed for further analysis if needed.

---

**End of Report**
