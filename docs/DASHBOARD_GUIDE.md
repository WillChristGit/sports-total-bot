# SportsTotalBot Dashboard Guide

## 🌐 Web Dashboard

Your personal performance dashboard is running at:

**http://localhost:5000**

### What You'll See

```
┌─────────────────────────────────────────────────────────────┐
│                    📊 SportsTotalBot                        │
│              Performance Dashboard                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Total   │ │ Win     │ │ Profit  │ │  ROI    │           │
│  │  Bets   │ │  Rate   │ │  /Loss  │ │         │           │
│  │   2     │ │  0%     │ │  $0.00  │ │  0.0%   │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│                                                             │
│  📋 Recent Picks                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Date │ Game         │ Bet        │ EV  │ Result │    │  │
│  │ 02/02│ 76ers @ CLIP │ OVER 218.6 │ 5.8%│ PENDING │    │  │
│  │ 02/02│ Rockets @ IND│ OVER 218.7 │ 5.1%│ PENDING │    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  📈 By Bet Type                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ OVER  │ 0 bets │ 0-0 │ 0%                          │  │  │
│  │ UNDER │ 0 bets │ 0-0 │ 0%                          │  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Auto-refreshes every 60 seconds                            │
└─────────────────────────────────────────────────────────────┘
```

### Features

| Feature | Description |
|---------|-------------|
| **Real-time Metrics** | Total bets, win rate, profit/loss, ROI |
| **Current Streak** | Shows win/loss streak with emoji |
| **Recent Picks** | Last 20 picks with results |
| **By Bet Type** | Breakdown of OVER vs UNDER performance |
| **Auto-refresh** | Updates every 60 seconds |
| **Color Coding** | Green = positive, Red = negative |

### Color Legend

| Color | Meaning |
|-------|---------|
| 🟢 Green | Win rate ≥ 52% or positive P/L |
| 🟡 Yellow | Win rate 50-51% or breakeven |
| 🔴 Red | Win rate < 50% or negative P/L |

### Status Indicators

| Status | Meaning |
|--------|---------|
| ✅ WON | Bet won |
| ❌ LOST | Bet lost |
| ⏳ PENDING | Game not finished |

---

## 📊 Text Dashboard

For a quick terminal view:

```bash
./track.sh
```

Output example:
```
======================================================================
📊 SPORTSTOTALBOT - PERFORMANCE DASHBOARD
======================================================================

📈 SUMMARY
----------------------------------------------------------------------
Period:          Last 30 days
Total Bets:      2
Completed:       0
Pending:         2

💰 PERFORMANCE
----------------------------------------------------------------------
Wins:           0 🎯
Losses:         0 ❌
Win Rate:       0%
Current Streak: 0 NONE ➖

Total P/L:       $+0.00
ROI:             0%
Avg EV:          5.48%
```

---

## 💾 Export Data

### Export to CSV and JSON

```bash
./track.sh --export
```

Creates:
- `data/picks/tracking_YYYYMMDD.csv` - Spreadsheet compatible
- `data/picks/tracking_YYYYMMDD.json` - Full data export

### CSV Format

```csv
Date,Away Team,Home Team,Bet Type,Side,Line,Odds,Projected,EV,Win Prob,Result,Profit/Loss
2026-02-02,Philadelphia 76ers,Los Angeles Clippers,totals,OVER,218.6,-109,224.6,5.84%,55.2%,PENDING,
2026-02-02,Houston Rockets,Indiana Pacers,totals,OVER,218.7,-110,224.6,5.13%,55.1%,PENDING,
```

---

## 🔧 Troubleshooting

### Dashboard won't load

```bash
# Make sure Flask is installed
pip install flask

# Restart the dashboard
./track.sh --web
```

### Dashboard not updating

Click the **🔄 Refresh** button or wait for auto-refresh (60 seconds).

### Wrong data showing

```bash
# Update completed game results first
./run.sh --update-results

# Then refresh dashboard
```

---

## 📱 Mobile Access

The dashboard works on mobile! Access from your phone:

1. Make sure you're on the same network as your Mac
2. Find your Mac's IP address:
   ```bash
   ipconfig getifaddr en0
   ```
3. Open `http://YOUR-IP:5000` on your phone

---

## 🔔 Next Steps

1. **Run daily**: `./run.sh` to get new picks
2. **Track results**: `./track.sh` to see performance
3. **Update games**: `./run.sh --update-results` after games finish
4. **Build sample size**: Need 50+ bets to trust the model

---

**Dashboard URL**: http://localhost:5000
**Refresh rate**: Every 60 seconds
**Data source**: `data/sportstotalbot.db`
