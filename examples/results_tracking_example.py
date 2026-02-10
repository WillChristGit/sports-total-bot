#!/usr/bin/env python3
"""
Example: Integrating Results Tracker with SportsTotalBot

Shows how to add results tracking to your daily workflow
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from results.tracker import ResultsTracker


def example_daily_workflow():
    """
    Example daily workflow:
    1. Track yesterday's results
    2. Display performance report
    3. Check latest results
    """
    print("=" * 70)
    print("SportsTotalBot - Daily Results Tracking Workflow")
    print("=" * 70)

    tracker = ResultsTracker()

    # 1. Track yesterday's results
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"\n1. Tracking results for {yesterday}...")

    results = tracker.track_results(yesterday)

    if 'error' in results:
        print(f"  ✗ Error: {results['error']}")
    else:
        summary = results['summary']
        print(f"  ✓ Tracked {results['matched_count']}/{results['picks_count']} picks")
        print(f"  Record: {summary['wins']}W-{summary['losses']}L-{summary['pushes']}P")
        print(f"  Win Rate: {summary['win_rate']}%")
        print(f"  Profit: ${summary['total_profit']:.2f}")
        print(f"  ROI: {summary['roi']:.2f}%")

    # 2. Get 7-day performance report
    print("\n2. Generating 7-day performance report...")
    report = tracker.get_performance_report(days=7)

    if report['days_with_picks'] > 0:
        print(f"  Days with picks: {report['days_with_picks']}")
        print(f"  Total bets: {report['total_bets']}")
        print(f"  Record: {report['wins']}W-{report['losses']}L-{report['pushes']}P")
        print(f"  Win Rate: {report['win_rate']}%")
        print(f"  Total Profit: ${report['total_profit']:.2f}")
        print(f"  ROI: {report['roi']:.2f}%")

        # Show best and worst days
        if report['daily_results']:
            best_day = max(report['daily_results'], key=lambda x: x['profit'])
            worst_day = min(report['daily_results'], key=lambda x: x['profit'])

            print(f"\n  Best day: {best_day['date']} (+${best_day['profit']:.2f})")
            print(f"  Worst day: {worst_day['date']} (${worst_day['profit']:.2f})")
    else:
        print("  ℹ No picks found in last 7 days")

    # 3. Check latest results
    print("\n3. Checking latest results...")
    latest = tracker.track_latest_results()

    if 'error' not in latest and latest['picks_count'] > 0:
        summary = latest['summary']
        print(f"  Latest picks: {latest['picks_count']}")
        print(f"  Matched: {latest['matched_count']}")
        print(f"  Pending: {summary['pending']}")

        # Show individual results
        if latest['results']:
            print("\n  Recent results:")
            for result in latest['results'][:5]:  # Show first 5
                status = result['status'].upper()
                teams = f"{result['away_team']} @ {result['home_team']}"
                bet = f"{result['bet_type']} {result['side']} {result['line']}"
                profit = result['profit_loss']

                icon = {
                    'WON': '✓',
                    'LOST': '✗',
                    'PUSH': '⊘',
                    'PENDING': '⏳'
                }.get(status, '?')

                print(f"    {icon} {teams} | {bet} | {status} | ${profit:.2f}")
    else:
        print("  ℹ No recent picks found")

    print("\n" + "=" * 70)
    print("Workflow complete!")
    print("=" * 70)


def example_bet_analysis():
    """
    Example: Analyze specific bet types and performance
    """
    print("\n" + "=" * 70)
    print("Bet Type Analysis")
    print("=" * 70)

    tracker = ResultsTracker()

    # Load recent results
    report = tracker.get_performance_report(days=30)

    if report['days_with_picks'] == 0:
        print("No data available for analysis")
        return

    # Analyze by loading individual day results
    historical = tracker.load_historical_results(days=30)

    totals_bets = []
    spread_bets = []

    for day_data in historical:
        for result in day_data.get('results', []):
            if result['status'] == 'pending':
                continue

            if result['bet_type'] == 'totals':
                totals_bets.append(result)
            elif result['bet_type'] == 'spreads':
                spread_bets.append(result)

    print(f"\nTotals Bets: {len(totals_bets)}")
    if totals_bets:
        wins = sum(1 for b in totals_bets if b['status'] == 'won')
        losses = sum(1 for b in totals_bets if b['status'] == 'lost')
        profit = sum(b['profit_loss'] for b in totals_bets)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        print(f"  Record: {wins}W-{losses}L")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Profit: ${profit:.2f}")

        # Over vs Under
        overs = [b for b in totals_bets if b['side'] == 'over']
        unders = [b for b in totals_bets if b['side'] == 'under']

        print(f"\n  OVER bets: {len(overs)}")
        if overs:
            over_wins = sum(1 for b in overs if b['status'] == 'won')
            over_profit = sum(b['profit_loss'] for b in overs)
            print(f"    Wins: {over_wins}/{len(overs)}")
            print(f"    Profit: ${over_profit:.2f}")

        print(f"\n  UNDER bets: {len(unders)}")
        if unders:
            under_wins = sum(1 for b in unders if b['status'] == 'won')
            under_profit = sum(b['profit_loss'] for b in unders)
            print(f"    Wins: {under_wins}/{len(unders)}")
            print(f"    Profit: ${under_profit:.2f}")

    print(f"\nSpread Bets: {len(spread_bets)}")
    if spread_bets:
        wins = sum(1 for b in spread_bets if b['status'] == 'won')
        losses = sum(1 for b in spread_bets if b['status'] == 'lost')
        profit = sum(b['profit_loss'] for b in spread_bets)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        print(f"  Record: {wins}W-{losses}L")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Profit: ${profit:.2f}")

        # Home vs Away
        home_picks = [b for b in spread_bets if b['side'] == 'home']
        away_picks = [b for b in spread_bets if b['side'] == 'away']

        print(f"\n  HOME picks: {len(home_picks)}")
        if home_picks:
            home_wins = sum(1 for b in home_picks if b['status'] == 'won')
            home_profit = sum(b['profit_loss'] for b in home_picks)
            print(f"    Wins: {home_wins}/{len(home_picks)}")
            print(f"    Profit: ${home_profit:.2f}")

        print(f"\n  AWAY picks: {len(away_picks)}")
        if away_picks:
            away_wins = sum(1 for b in away_picks if b['status'] == 'won')
            away_profit = sum(b['profit_loss'] for b in away_picks)
            print(f"    Wins: {away_wins}/{len(away_picks)}")
            print(f"    Profit: ${away_profit:.2f}")

    print("\n" + "=" * 70)


def example_confidence_analysis():
    """
    Example: Analyze performance by confidence level
    """
    print("\n" + "=" * 70)
    print("Confidence Level Analysis")
    print("=" * 70)

    tracker = ResultsTracker()
    historical = tracker.load_historical_results(days=30)

    # Group by confidence
    confidence_groups = {
        'high (0.7+)': [],
        'medium (0.6-0.69)': [],
        'low (<0.6)': []
    }

    for day_data in historical:
        for result in day_data.get('results', []):
            if result['status'] == 'pending':
                continue

            confidence = result.get('confidence', 0.5)

            if confidence >= 0.7:
                confidence_groups['high (0.7+)'].append(result)
            elif confidence >= 0.6:
                confidence_groups['medium (0.6-0.69)'].append(result)
            else:
                confidence_groups['low (<0.6)'].append(result)

    print("\nPerformance by confidence level:\n")

    for group_name, bets in confidence_groups.items():
        if not bets:
            print(f"{group_name}: No data")
            continue

        wins = sum(1 for b in bets if b['status'] == 'won')
        losses = sum(1 for b in bets if b['status'] == 'lost')
        pushes = sum(1 for b in bets if b['status'] == 'push')
        profit = sum(b['profit_loss'] for b in bets)

        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        avg_ev = sum(b.get('ev', 0) for b in bets) / len(bets)

        print(f"{group_name}:")
        print(f"  Total bets: {len(bets)}")
        print(f"  Record: {wins}W-{losses}L-{pushes}P")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg EV: {avg_ev:.2%}")
        print(f"  Profit: ${profit:.2f}")
        print()


if __name__ == '__main__':
    example_daily_workflow()
    example_bet_analysis()
    example_confidence_analysis()
