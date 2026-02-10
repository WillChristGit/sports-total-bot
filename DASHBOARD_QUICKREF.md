# SportsTotalBot Dashboard - Quick Reference

## Start the Dashboard

```bash
cd /Volumes/LegbaSSD/bots/SportsTotalBot
./run_dashboard.sh
```

Access at: **http://localhost:5001**

## API Endpoints

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /api/picks` | Today's picks | `curl http://localhost:5001/api/picks` |
| `GET /api/picks?refresh=true` | Force refresh | `curl http://localhost:5001/api/picks?refresh=true` |
| `GET /api/history` | Last 30 days | `curl http://localhost:5001/api/history` |
| `GET /api/history?days=7` | Last 7 days | `curl http://localhost:5001/api/history?days=7` |
| `GET /api/stats` | Today's stats | `curl http://localhost:5001/api/stats` |
| `GET /api/stats?period=history&days=14` | 14-day stats | `curl http://localhost:5001/api/stats?period=history&days=14` |
| `GET /api/health` | Health check | `curl http://localhost:5001/api/health` |

## Response Format

All endpoints return JSON with this structure:

```json
{
  "success": true/false,
  "data": {...},
  "error": "error message" (if success=false)
}
```

## Key Metrics

- **EV**: Expected Value (percentage)
- **Win Probability**: Predicted chance of winning (percentage)
- **Confidence**: Model confidence (percentage)
- **Line**: Betting line (e.g., 247.5 for totals)
- **Odds**: American odds (e.g., -110)

## Auto-Refresh

The dashboard automatically refreshes every 60 seconds. The API caches data for 60 seconds to reduce file I/O.

## File Structure

```
data/picks/
├── daily_picks_20260202.json
├── daily_picks_20260203.json
└── daily_picks_20260204.json

dashboard/
└── index.html (frontend)
```

## Troubleshooting

**Problem**: Port 5001 already in use
**Solution**: Change port in `dashboard.py` line 380

**Problem**: No picks showing
**Solution**: Check that `data/picks/daily_picks_YYYYMMDD.json` exists

**Problem**: CORS errors
**Solution**: Ensure flask-cors is installed: `pip install flask-cors`

## Statistics

The dashboard calculates:
- Total picks
- Average EV
- Average win probability
- Best pick (highest EV)
- Breakdown by sport, bet type, and side
- EV distribution (high/medium/low)
