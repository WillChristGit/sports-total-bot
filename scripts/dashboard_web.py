"""
Web dashboard for SportsTotalBot pick tracking
"""

from flask import Flask, render_template_string, jsonify
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.pick_tracker import PickTracker

app = Flask(__name__)
tracker = PickTracker()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SportsTotalBot Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }

        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }

        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-label { color: #888; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }

        .positive { color: #00ff88; }
        .negative { color: #ff4757; }
        .neutral { color: #ffd700; }

        .section {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .section h2 {
            margin-bottom: 15px;
            color: #00d4ff;
            font-size: 1.3em;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th { color: #888; font-weight: normal; text-transform: uppercase; font-size: 0.85em; }
        tr:hover { background: rgba(255,255,255,0.02); }

        .won { color: #00ff88; }
        .lost { color: #ff4757; }
        .pending { color: #ffd700; }

        .refresh-btn {
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            border: none;
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            margin: 10px auto;
            display: block;
        }
        .refresh-btn:hover { transform: scale(1.05); }

        .streak {
            font-size: 1.2em;
            padding: 5px 15px;
            border-radius: 20px;
            display: inline-block;
        }
        .streak-win { background: rgba(0,255,136,0.2); }
        .streak-loss { background: rgba(255,71,87,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 SportsTotalBot</h1>
        <p class="subtitle">Performance Dashboard • Last updated: <span id="updated">{{ updated }}</span></p>

        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Total Bets</div>
                <div class="metric-value">{{ metrics.total_bets }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value {% if metrics.win_rate >= 52 %}positive{% elif metrics.win_rate >= 50 %}neutral{% else %}negative{% endif %}">
                    {{ metrics.win_rate }}%
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Profit/Loss</div>
                <div class="metric-value {% if metrics.total_profit_loss >= 0 %}positive{% else %}negative{% endif %}">
                    ${{ "%.2f"|format(metrics.total_profit_loss) }}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">ROI</div>
                <div class="metric-value {% if metrics.roi >= 0 %}positive{% else %}negative{% endif %}">
                    {{ "%.2f"|format(metrics.roi) }}%
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Current Streak</div>
                <div class="metric-value">
                    {% if metrics.current_streak.type == 'win' %}
                        <span class="streak streak-win">🔥 {{ metrics.current_streak.length }}W</span>
                    {% elif metrics.current_streak.type == 'loss' %}
                        <span class="streak streak-loss">📉 {{ metrics.current_streak.length }}L</span>
                    {% else %}
                        <span>-</span>
                    {% endif %}
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg EV</div>
                <div class="metric-value {% if metrics.avg_ev >= 0.02 %}positive{% elif metrics.avg_ev >= 0 %}neutral{% else %}negative{% endif %}">
                    {{ "%.2f"|format(metrics.avg_ev * 100) }}%
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📋 Recent Picks</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Game</th>
                        <th>Bet</th>
                        <th>Odds</th>
                        <th>EV</th>
                        <th>Result</th>
                        <th>P/L</th>
                    </tr>
                </thead>
                <tbody>
                    {% for pick in picks[:20] %}
                    <tr>
                        <td>{{ pick.date }}</td>
                        <td>{{ pick.game }}</td>
                        <td>{{ pick.bet }}</td>
                        <td>{{ pick.odds }}</td>
                        <td {% if pick.ev >= 0.02 %}class="positive"{% endif %}>{{ "%.1f"|format(pick.ev * 100) }}%</td>
                        <td class="{% if pick.result == 'WON' %}won{% elif pick.result == 'LOST' %}lost{% else %}pending{% endif %}">
                            {{ pick.result }}
                        </td>
                        <td class="{% if pick.profit_loss and pick.profit_loss >= 0 %}positive{% elif pick.profit_loss %}negative{% endif %}">
                            {% if pick.profit_loss %}${{{ "%.0f"|format(pick.profit_loss) }}}{% else %}-{% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📈 By Bet Type</h2>
            <table>
                <tr>
                    <th>Bet Type</th>
                    <th>Total</th>
                    <th>Wins</th>
                    <th>Losses</th>
                    <th>Win Rate</th>
                </tr>
                <tr>
                    <td>OVER</td>
                    <td>{{ metrics.over_bets }}</td>
                    <td>{{ metrics.over_wins }}</td>
                    <td>{{ metrics.over_bets - metrics.over_wins }}</td>
                    <td class="{% if metrics.over_win_rate >= 52 %}positive{% elif metrics.over_win_rate >= 50 %}neutral{% else %}negative{% endif %}">
                        {{ "%.1f"|format(metrics.over_win_rate) }}%
                    </td>
                </tr>
                <tr>
                    <td>UNDER</td>
                    <td>{{ metrics.under_bets }}</td>
                    <td>{{ metrics.under_wins }}</td>
                    <td>{{ metrics.under_bets - metrics.under_wins }}</td>
                    <td class="{% if metrics.under_win_rate >= 52 %}positive{% elif metrics.under_win_rate >= 50 %}neutral{% else %}negative{% endif %}">
                        {{ "%.1f"|format(metrics.under_win_rate) }}%
                    </td>
                </tr>
            </table>
        </div>
    </div>

    <script>
        // Auto-refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    picks = tracker.get_all_picks(30)
    metrics = tracker.calculate_performance_metrics(picks)

    # Format picks for template
    formatted_picks = []
    for pick in picks[:20]:
        formatted_picks.append({
            'date': datetime.fromisoformat(pick['created_at']).strftime('%m/%d %I:%M %p'),
            'game': f"{pick['away_team']} @ {pick['home_team']}",
            'bet': f"{pick['side'].upper()} {pick['line']}",
            'odds': pick['odds'],
            'ev': pick['ev'],
            'result': 'WON' if pick.get('won') else ('LOST' if pick.get('won') == 0 else 'PENDING'),
            'profit_loss': pick.get('profit_loss')
        })

    return render_template_string(
        HTML_TEMPLATE,
        metrics=metrics,
        picks=formatted_picks,
        updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


@app.route('/api/metrics')
def api_metrics():
    picks = tracker.get_all_picks(30)
    metrics = tracker.calculate_performance_metrics(picks)
    return jsonify(metrics)


@app.route('/api/picks')
def api_picks():
    import json
    from flask import response

    data = tracker.export_to_json(30)
    with open(data, 'r') as f:
        return jsonify(json.load(f))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
