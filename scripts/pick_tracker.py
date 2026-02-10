"""
Pick tracking and performance dashboard for SportsTotalBot
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.storage.database import Database
from src.output.formatter import OutputFormatter
import json


class PickTracker:
    """Track and analyze all picks"""

    def __init__(self, db_path: str = "data/sportstotalbot.db"):
        self.db = Database(db_path)
        self.formatter = OutputFormatter()

    def get_all_picks(self, days: int = 30) -> list:
        """Get all picks within the last N days"""
        import sqlite3

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    r.id,
                    r.game_id,
                    r.sport,
                    r.bet_type,
                    r.side,
                    r.line,
                    r.odds,
                    r.projected_value,
                    r.ev,
                    r.win_probability,
                    r.confidence,
                    r.reasoning,
                    r.created_at,
                    g.home_team,
                    g.away_team,
                    g.game_time,
                    g.home_score,
                    g.away_score,
                    g.is_completed,
                    res.id as result_id,
                    res.won,
                    res.actual_result,
                    res.profit_loss
                FROM recommendations r
                LEFT JOIN games g ON r.game_id = g.game_id
                LEFT JOIN results res ON r.id = res.recommendation_id
                WHERE r.created_at >= ?
                ORDER BY r.created_at DESC
            """, (cutoff_date,))

            return [dict(row) for row in cursor.fetchall()]

    def calculate_performance_metrics(self, picks: list) -> dict:
        """Calculate detailed performance metrics"""
        total = len(picks)
        if total == 0:
            return self._empty_metrics()

        # Separate completed vs pending
        completed = [p for p in picks if p['is_completed'] and p['result_id'] is not None]
        pending = [p for p in picks if not p['is_completed'] or p['result_id'] is None]

        # Basic stats
        wins = sum(1 for p in completed if p['won'] == 1)
        losses = len(completed) - wins
        win_rate = (wins / len(completed) * 100) if completed else 0

        # Profit/Loss
        total_pl = sum(p['profit_loss'] or 0 for p in completed)

        # ROI
        total_wagered = len(completed) * 100  # Assuming $100 per bet
        roi = (total_pl / total_wagered * 100) if total_wagered > 0 else 0

        # Average EV
        avg_ev = sum(p['ev'] for p in picks) / len(picks) if picks else 0

        # By bet type
        over_bets = [p for p in completed if p['side'] == 'over']
        under_bets = [p for p in completed if p['side'] == 'under']

        over_wins = sum(1 for p in over_bets if p['won'] == 1)
        under_wins = sum(1 for p in under_bets if p['won'] == 1)

        over_win_rate = (over_wins / len(over_bets) * 100) if over_bets else 0
        under_win_rate = (under_wins / len(under_bets) * 100) if under_bets else 0

        # Streak
        streak = self._calculate_streak(completed)

        # Best and worst
        best_bet = max(completed, key=lambda x: x['profit_loss'] or 0) if completed else None
        worst_bet = min(completed, key=lambda x: x['profit_loss'] or 0) if completed else None

        return {
            'total_bets': total,
            'completed_bets': len(completed),
            'pending_bets': len(pending),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'total_profit_loss': round(total_pl, 2),
            'roi': round(roi, 2),
            'avg_ev': round(avg_ev, 4),
            'over_bets': len(over_bets),
            'over_wins': over_wins,
            'over_win_rate': round(over_win_rate, 2),
            'under_bets': len(under_bets),
            'under_wins': under_wins,
            'under_win_rate': round(under_win_rate, 2),
            'current_streak': streak,
            'best_bet': best_bet,
            'worst_bet': worst_bet,
            'start_date': picks[-1]['created_at'] if picks else None,
            'end_date': picks[0]['created_at'] if picks else None,
        }

    def _calculate_streak(self, completed: list) -> dict:
        """Calculate current win/loss streak"""
        if not completed:
            return {'type': 'none', 'length': 0}

        streak_type = 'none'
        streak_length = 0
        current_type = None

        for pick in reversed(completed):  # Most recent first
            if pick['won'] == 1:
                if current_type is None or current_type == 'win':
                    streak_type = 'win'
                    streak_length += 1
                    current_type = 'win'
                else:
                    break
            else:
                if current_type is None or current_type == 'loss':
                    streak_type = 'loss'
                    streak_length += 1
                    current_type = 'loss'
                else:
                    break

        return {'type': streak_type, 'length': streak_length}

    def _empty_metrics(self) -> dict:
        """Return empty metrics dict"""
        return {
            'total_bets': 0,
            'completed_bets': 0,
            'pending_bets': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'total_profit_loss': 0,
            'roi': 0,
            'avg_ev': 0,
            'over_bets': 0,
            'over_wins': 0,
            'over_win_rate': 0,
            'under_bets': 0,
            'under_wins': 0,
            'under_win_rate': 0,
            'current_streak': {'type': 'none', 'length': 0},
            'best_bet': None,
            'worst_bet': None,
            'start_date': None,
            'end_date': None,
        }

    def generate_dashboard(self, days: int = 30) -> str:
        """Generate a text-based dashboard"""
        picks = self.get_all_picks(days)
        metrics = self.calculate_performance_metrics(picks)

        lines = []
        lines.append("=" * 70)
        lines.append("📊 SPORTSTOTALBOT - PERFORMANCE DASHBOARD")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        lines.append("📈 SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Period:          Last {days} days")
        if metrics['start_date']:
            start = datetime.fromisoformat(metrics['start_date']).strftime('%Y-%m-%d')
            end = datetime.fromisoformat(metrics['end_date']).strftime('%Y-%m-%d')
            lines.append(f"Date Range:      {start} to {end}")
        lines.append(f"Total Bets:      {metrics['total_bets']}")
        lines.append(f"Completed:       {metrics['completed_bets']}")
        lines.append(f"Pending:         {metrics['pending_bets']}")
        lines.append("")

        # Performance
        lines.append("💰 PERFORMANCE")
        lines.append("-" * 70)
        lines.append(f"Wins:           {metrics['wins']} 🎯")
        lines.append(f"Losses:         {metrics['losses']} ❌")
        lines.append(f"Win Rate:       {metrics['win_rate']}%")

        # Streak
        streak = metrics['current_streak']
        if streak['type'] == 'win':
            emoji = "🔥"
        elif streak['type'] == 'loss':
            emoji = "📉"
        else:
            emoji = "➖"
        lines.append(f"Current Streak: {streak['length']} {streak['type'].upper()} {emoji}")

        lines.append("")
        lines.append(f"Total P/L:       ${metrics['total_profit_loss']:+.2f}")
        lines.append(f"ROI:             {metrics['roi']}%")
        lines.append(f"Avg EV:          {metrics['avg_ev']:.2%}")
        lines.append("")

        # By Bet Type
        lines.append("📊 BY BET TYPE")
        lines.append("-" * 70)
        lines.append(f"OVER Bets:      {metrics['over_bets']} ({metrics['over_wins']}-{metrics['over_bets']-metrics['over_wins']}) = {metrics['over_win_rate']}%")
        lines.append(f"UNDER Bets:     {metrics['under_bets']} ({metrics['under_wins']}-{metrics['under_bets']-metrics['under_wins']}) = {metrics['under_win_rate']}%")
        lines.append("")

        # Best and Worst
        if metrics['best_bet']:
            lines.append("⭐ BEST BET")
            lines.append("-" * 70)
            lines.append(f"  {metrics['best_bet']['away_team']} @ {metrics['best_bet']['home_team']}")
            lines.append(f"  {metrics['best_bet']['side'].upper()} {metrics['best_bet']['line']} @ {metrics['best_bet']['odds']}")
            lines.append(f"  Profit: +${metrics['best_bet']['profit_loss']:.2f}")
            lines.append("")

        if metrics['worst_bet']:
            lines.append("💩 WORST BET")
            lines.append("-" * 70)
            lines.append(f"  {metrics['worst_bet']['away_team']} @ {metrics['worst_bet']['home_team']}")
            lines.append(f"  {metrics['worst_bet']['side'].upper()} {metrics['worst_bet']['line']} @ {metrics['worst_bet']['odds']}")
            lines.append(f"  Profit: ${metrics['worst_bet']['profit_loss']:.2f}")
            lines.append("")

        # Recent Picks
        lines.append("📋 RECENT PICKS (Last 10)")
        lines.append("-" * 70)
        for pick in picks[:10]:
            date = datetime.fromisoformat(pick['created_at']).strftime('%m/%d %H:%M')
            teams = f"{pick['away_team']} @ {pick['home_team']}"
            bet = f"{pick['side'].upper()} {pick['line']}"

            if pick['result_id']:
                result = "✅ WON" if pick['won'] else "❌ LOST"
                pl = f"${pick['profit_loss']:+.0f}"
            else:
                result = "⏳ PENDING"
                pl = ""

            lines.append(f"  {date} | {bet:15} | {teams:30} | {result:12} | {pl:>6}")

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def export_to_csv(self, days: int = 30, filename: str = None) -> str:
        """Export all picks to CSV"""
        import csv

        picks = self.get_all_picks(days)

        if not filename:
            filename = f"data/picks/tracking_{datetime.now().strftime('%Y%m%d')}.csv"

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Date', 'Away Team', 'Home Team', 'Bet Type', 'Side', 'Line',
                'Odds', 'Projected', 'EV', 'Win Prob', 'Result', 'Profit/Loss'
            ])

            for pick in picks:
                date = datetime.fromisoformat(pick['created_at']).strftime('%Y-%m-%d')
                result = "WON" if pick.get('won') else ("LOST" if pick.get('won') == 0 else "PENDING")

                writer.writerow([
                    date,
                    pick['away_team'],
                    pick['home_team'],
                    pick['bet_type'],
                    pick['side'],
                    pick['line'],
                    pick['odds'],
                    f"{pick['projected_value']:.1f}",
                    f"{pick['ev']:.2%}",
                    f"{pick['win_probability']:.1%}",
                    result,
                    f"{pick.get('profit_loss', 0):+.2f}" if pick.get('profit_loss') else ''
                ])

        return filename

    def export_to_json(self, days: int = 30, filename: str = None) -> str:
        """Export picks and metrics to JSON"""
        picks = self.get_all_picks(days)
        metrics = self.calculate_performance_metrics(picks)

        if not filename:
            filename = f"data/picks/tracking_{datetime.now().strftime('%Y%m%d')}.json"

        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'metrics': {
                'total_bets': metrics['total_bets'],
                'completed_bets': metrics['completed_bets'],
                'pending_bets': metrics['pending_bets'],
                'wins': metrics['wins'],
                'losses': metrics['losses'],
                'win_rate_pct': metrics['win_rate'],
                'total_profit_loss': metrics['total_profit_loss'],
                'roi_pct': metrics['roi'],
                'avg_ev': metrics['avg_ev'],
                'current_streak': metrics['current_streak'],
            },
            'picks': []
        }

        for pick in picks:
            export_data['picks'].append({
                'date': pick['created_at'],
                'game': f"{pick['away_team']} @ {pick['home_team']}",
                'bet': f"{pick['side'].upper()} {pick['line']}",
                'odds': pick['odds'],
                'projected': pick['projected_value'],
                'ev': round(pick['ev'], 4),
                'win_probability': round(pick['win_probability'], 4),
                'result': 'WON' if pick.get('won') else ('LOST' if pick.get('won') == 0 else 'PENDING'),
                'profit_loss': pick.get('profit_loss')
            })

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        return filename


def main():
    """CLI for the pick tracker"""
    import argparse

    parser = argparse.ArgumentParser(description='SportsTotalBot Pick Tracker')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--export-csv', action='store_true', help='Export to CSV')
    parser.add_argument('--export-json', action='store_true', help='Export to JSON')
    parser.add_argument('--db', default='data/sportstotalbot.db', help='Database path')

    args = parser.parse_args()

    tracker = PickTracker(args.db)

    # Show dashboard
    print("\n" + tracker.generate_dashboard(args.days))

    # Export if requested
    if args.export_csv:
        csv_file = tracker.export_to_csv(args.days)
        print(f"\n✅ Exported to CSV: {csv_file}")

    if args.export_json:
        json_file = tracker.export_to_json(args.days)
        print(f"✅ Exported to JSON: {json_file}")


if __name__ == '__main__':
    main()
