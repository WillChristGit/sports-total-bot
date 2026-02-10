# SportsTotalBot Web Dashboard

Complete Flask-based web dashboard for viewing sports betting picks, historical performance, and statistics.

## Features

- **Real-time Picks Display**: View today's betting predictions with auto-refresh every 60 seconds
- **Historical Performance**: Analyze past picks over configurable time periods
- **Summary Statistics**: View aggregated metrics including average EV, win probability, and more
- **RESTful API**: Clean JSON API for integration with other tools
- **CORS Enabled**: Access API from any origin
- **Graceful Error Handling**: Handles missing data and errors gracefully

## Quick Start

### Option 1: Using the launcher script (Recommended)

```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
./run_dashboard.sh
```

### Option 2: Direct Python execution

```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
./venv/bin/python dashboard.py
```

The dashboard will be available at **http://localhost:5001**

## API Endpoints

### 1. GET `/api/picks` - Today's Picks

Returns all betting picks for the current date.

**Query Parameters:**
- `refresh` (optional): Set to `true` to bypass cache and force reload from disk

**Response:**
```json
{
  "success": true,
  "date": "2026-02-04",
  "total_picks": 7,
  "picks": [
    {
      "game_id": "09a1c85451c2450418f5bcba90e220b9",
      "sport": "nba",
      "bet_type": "totals",
      "side": "under",
      "line": 247.5,
      "odds": -112,
      "projected_value": 228.5,
      "ev": 10.56,
      "win_probability": 58.41,
      "confidence": 70.0,
      "home_team": "Raptors",
      "away_team": "Minnesota Timberwolves",
      "game_time": "2026-02-05T00:42:00+00:00",
      "reasoning": "Projected: 228.5 vs Line: 247.5 (Diff: -19.0)..."
    }
  ],
  "cached": true,
  "last_updated": "2026-02-04T20:30:00Z"
}
```

### 2. GET `/api/history` - Historical Performance

Returns historical picks and performance summary.

**Query Parameters:**
- `days` (optional): Number of days to look back (default: 30, max: 90)

**Response:**
```json
{
  "success": true,
  "period_days": 30,
  "total_picks": 150,
  "picks": [...],
  "stats": {
    "total_picks": 150,
    "avg_ev": 11.67,
    "avg_win_probability": 57.47,
    "avg_confidence": 69.33,
    "best_pick": {
      "game_id": "...",
      "sport": "nba",
      "bet_type": "totals",
      "side": "under",
      "ev": 48.18,
      "win_probability": 60.5,
      "teams": "Minnesota Timberwolves @ Memphis Grizzlies"
    },
    "by_sport": {
      "nba": {"count": 150, "avg_ev": 11.67}
    },
    "by_bet_type": {
      "totals": {"count": 140, "avg_ev": 12.04},
      "spreads": {"count": 10, "avg_ev": 6.42}
    },
    "by_side": {
      "over": {"count": 70, "avg_ev": 11.5},
      "under": {"count": 80, "avg_ev": 11.8}
    },
    "ev_distribution": {
      "high_ev": 60,
      "medium_ev": 90,
      "low_ev": 0
    }
  }
}
```

### 3. GET `/api/stats` - Summary Statistics

Returns aggregated statistics for today or historical period.

**Query Parameters:**
- `period` (optional): `today` or `history` (default: `today`)
- `days` (optional): If `period=history`, number of days to look back (default: 30)

**Response:**
```json
{
  "success": true,
  "period": "today",
  "period_days": 1,
  "stats": {
    "total_picks": 7,
    "avg_ev": 8.52,
    "avg_win_probability": 56.84,
    "avg_confidence": 70.0,
    "best_pick": {...},
    "by_sport": {...},
    "by_bet_type": {...},
    "ev_distribution": {...}
  }
}
```

### 4. GET `/api/health` - Health Check

Returns server health status.

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-02-04T20:30:00Z",
  "app": "SportsTotalBot Dashboard",
  "version": "1.0.0"
}
```

## Data Format

### Pick Files

Pick data is stored in JSON files in the `data/picks/` directory with the naming pattern:
```
daily_picks_YYYYMMDD.json
```

Example: `daily_picks_20260204.json`

### Pick Structure

Each pick contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | string | Unique identifier for the game |
| `sport` | string | Sport type (e.g., "nba", "nfl") |
| `bet_type` | string | Type of bet ("totals", "spreads", "moneyline") |
| `side` | string | Bet side ("over", "under", "home", "away") |
| `line` | float | Betting line |
| `odds` | int | American odds (e.g., -110) |
| `projected_value` | float | Projected value by the model |
| `ev` | float | Expected value (decimal, converted to % in API) |
| `win_probability` | float | Predicted win probability (decimal, converted to % in API) |
| `confidence` | float | Model confidence (decimal, converted to % in API) |
| `home_team` | string | Home team name |
| `away_team` | string | Away team name |
| `game_time` | string | ISO 8601 datetime of game start |
| `reasoning` | string | Explanation of the pick |

## Configuration

### Caching

The API implements intelligent caching for the `/api/picks` endpoint:
- Cache duration: 60 seconds
- Cache can be bypassed with `?refresh=true` query parameter
- Cache is automatically refreshed when new data is available

### File Paths

- **Data directory**: `data/`
- **Picks directory**: `data/picks/`
- **Dashboard static files**: `dashboard/`

### Server Settings

- **Host**: `0.0.0.0` (all interfaces)
- **Port**: `5001`
- **Debug mode**: `True` (development)

## Frontend Integration

The dashboard serves static files from the `dashboard/` directory. The main frontend file is `dashboard/index.html`.

### Example API Call (JavaScript)

```javascript
// Fetch today's picks
async function loadPicks() {
  const response = await fetch('/api/picks');
  const data = await response.json();

  if (data.success) {
    console.log(`Found ${data.total_picks} picks`);
    data.picks.forEach(pick => {
      console.log(`${pick.away_team} @ ${pick.home_team}`);
      console.log(`  EV: ${pick.ev}%, Win Prob: ${pick.win_probability}%`);
    });
  }
}

// Auto-refresh every 60 seconds
setInterval(loadPicks, 60000);
```

### Example API Call (cURL)

```bash
# Get today's picks
curl http://localhost:5001/api/picks

# Force refresh from disk
curl http://localhost:5001/api/picks?refresh=true

# Get historical performance (last 30 days)
curl http://localhost:5001/api/history

# Get historical performance (last 7 days)
curl http://localhost:5001/api/history?days=7

# Get summary statistics
curl http://localhost:5001/api/stats

# Get historical statistics (last 14 days)
curl http://localhost:5001/api/stats?period=history&days=14
```

## Statistics Calculation

The dashboard calculates the following statistics:

### Basic Metrics
- **Total Picks**: Number of picks in the dataset
- **Average EV**: Mean expected value across all picks
- **Average Win Probability**: Mean predicted win probability
- **Average Confidence**: Mean model confidence

### Best Pick
- Identifies the pick with the highest EV
- Displays teams, EV, and win probability

### Grouped Statistics
- **By Sport**: Aggregates picks by sport type
- **By Bet Type**: Aggregates picks by bet type (totals, spreads, etc.)
- **By Side**: Aggregates picks by side (over/under/home/away)

### EV Distribution
- **High EV**: Picks with EV > 10%
- **Medium EV**: Picks with EV between 5-10%
- **Low EV**: Picks with EV < 5%

## Error Handling

The API handles errors gracefully:

### Missing Pick Files
If no pick file exists for the current date, the API returns:
```json
{
  "success": true,
  "date": "2026-02-04",
  "total_picks": 0,
  "picks": [],
  "cached": false
}
```

### Invalid JSON Files
If a pick file contains invalid JSON, the API logs an error and returns an empty list.

### 404 Errors
Static file requests return a 404 with a descriptive message if the file is not found.

### 500 Errors
Internal server errors are caught and logged, with a generic error message returned to the client.

## Production Deployment

For production use, consider:

1. **Use a production WSGI server** (e.g., gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 dashboard:app
   ```

2. **Disable debug mode**:
   ```python
   # In dashboard.py, change:
   app.run(debug=True)  # Development
   # to:
   app.run(debug=False)  # Production
   ```

3. **Set up environment variables** for sensitive configuration

4. **Add authentication** if the dashboard should be private

5. **Enable HTTPS** using a reverse proxy (nginx, Apache)

## Troubleshooting

### Port already in use
If port 5001 is already in use, you can change it in `dashboard.py`:
```python
app.run(host='0.0.0.0', port=5002)  # Use port 5002 instead
```

### Module not found errors
Ensure all dependencies are installed:
```bash
./venv/bin/pip install -r requirements.txt
```

### Empty picks list
Check that pick files exist in `data/picks/` with the correct naming pattern:
```bash
ls -la data/picks/daily_picks_*.json
```

### CORS errors
CORS is enabled for all origins. If you experience CORS issues, ensure `flask-cors` is installed:
```bash
./venv/bin/pip install flask-cors
```

## Dependencies

- Flask >= 3.0.0
- Flask-CORS >= 4.0.0
- Python 3.8+

## License

Part of the SportsTotalBot project.

## Support

For issues or questions, please refer to the main project documentation.
