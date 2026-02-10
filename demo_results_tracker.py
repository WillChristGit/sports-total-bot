#!/usr/bin/env python3
"""
Demo script for ResultsTracker with mock API responses

Shows how the tracker evaluates picks with sample game results
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from results.tracker import ResultsTracker, PickResult


def mock_track_results_demo():
    """Demonstrate results tracking with mock data"""

    print("=" * 70)
    print("SportsTotalBot Results Tracker - Demo")
    print("=" * 70)

    # Initialize tracker
    tracker = ResultsTracker()

    # Load real picks from 2026-02-04
    print("\n1. Loading picks from 2026-02-04...")
    picks = tracker.load_picks('20260204')

    if not picks:
        print("✗ No picks found for this date")
        return

    print(f"✓ Loaded {len(picks)} picks")

    # Create mock game results simulating completed games
    print("\n2. Simulating game results...")

    mock_games = [
        {
            'game_id': '09a1c85451c2450418f5bcba90e220b9',
            'home_team': 'Toronto Raptors',
            'away_team': 'Minnesota Timberwolves',
            'home_score': 108,
            'away_score': 112,
            'total': 220,
            'margin': -4,
            'status': 'Final'
        },
        {
            'game_id': '720fb0aa5ec9b76d0ba6782d87da5d6e',
            'home_team': 'Milwaukee Bucks',
            'away_team': 'New Orleans Pelicans',
            'home_score': 115,
            'away_score': 105,
            'total': 220,
            'margin': 10,
            'status': 'Final'
        },
        {
            'game_id': '8b816f6d79780a1772852263e815b070',
            'home_team': 'Houston Rockets',
            'away_team': 'Boston Celtics',
            'home_score': 112,
            'away_score': 118,
            'total': 230,
            'margin': -6,
            'status': 'Final'
        },
        {
            'game_id': '7eb233edb6e9e03622d300ca7dd2c1df',
            'home_team': 'San Antonio Spurs',
            'away_team': 'Oklahoma City Thunder',
            'home_score': 105,
            'away_score': 118,
            'total': 223,
            'margin': -13,
            'status': 'Final'
        },
        {
            'game_id': '4336bce3a2a2e0e4ab7b6bd8f79693d8',
            'home_team': 'Sacramento Kings',
            'away_team': 'Memphis Grizzlies',
            'home_score': 110,
            'away_score': 115,
            'total': 225,
            'margin': -5,
            'status': 'Final'
        }
    ]

    print(f"✓ Created {len(mock_games)} mock game results")

    # Evaluate each pick
    print("\n3. Evaluating picks against results...")
    print("-" * 70)

    results = []
    for pick_data in picks:
        pick = PickResult(pick_data)
        game = tracker.match_game_to_pick(pick_data, mock_games)

        if game:
            print(f"\nGame: {pick.away_team} @ {pick.home_team}")
            print(f"  Pick: {pick.bet_type.upper()} {pick.side.upper()} {pick.line}")
            print(f"  Actual: {game['away_team']} {game['away_score']} - {game['home_team']} {game['home_score']} (Total: {game['total']})")

            if pick.bet_type == 'totals':
                status, profit = tracker.evaluate_totals_pick(pick, game)
            elif pick.bet_type == 'spreads':
                status, profit = tracker.evaluate_spread_pick(pick, game)
            else:
                print(f"  ✗ Unsupported bet type: {pick.bet_type}")
                continue

            pick.profit_loss = profit
            pick.units = tracker.calculate_units(pick)

            status_icon = {
                'won': '✓',
                'lost': '✗',
                'push': '⊘',
                'pending': '⏳'
            }.get(status, '?')

            print(f"  Result: {status_icon} {status.upper()}")
            print(f"  Profit: ${profit:.2f}")
            print(f"  Reasoning: {pick.result_reasoning}")

            results.append(pick.to_dict())
        else:
            print(f"\n⏳ Game: {pick.away_team} @ {pick.home_team}")
            print(f"  No result found (game may not have started)")
            results.append(pick.to_dict())

    # Calculate summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    summary = tracker._calculate_summary(results)

    print(f"\nTotal Picks: {len(picks)}")
    print(f"Matched Results: {len([r for r in results if r['status'] != 'pending'])}")
    print(f"Pending: {summary['pending']}")
    print(f"\nRecord: {summary['wins']}W - {summary['losses']}L - {summary['pushes']}P")
    print(f"Win Rate: {summary['win_rate']}%")
    print(f"Total Profit: ${summary['total_profit']:.2f}")
    print(f"Total Units: {summary['total_units']:.1f}")
    print(f"ROI: {summary['roi']:.2f}%")

    print("\nBy Bet Type:")
    for bet_type, stats in summary['by_type'].items():
        if stats['wins'] + stats['losses'] + stats['pushes'] > 0:
            print(f"\n  {bet_type.upper()}:")
            print(f"    Record: {stats['wins']}W-{stats['losses']}L-{stats['pushes']}P")
            print(f"    Profit: ${stats['profit']:.2f}")

    # Save results
    print("\n" + "=" * 70)
    print("4. Saving results...")
    print("=" * 70)

    tracker._save_results('20260204', results, summary)

    print("✓ Results saved to data/results/20260204_results.json")

    # Show sample output file
    print("\n5. Sample output (first result):")
    print("-" * 70)
    if results:
        print(json.dumps(results[0], indent=2))

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nThe results tracker successfully:")
    print("  ✓ Loaded picks from daily_picks_YYYYMMDD.json")
    print("  ✓ Matched picks to game results")
    print("  ✓ Evaluated totals (OVER/UNDER) picks")
    print("  ✓ Evaluated spread picks")
    print("  ✓ Calculated profit/loss based on odds")
    print("  ✓ Computed win rate, ROI, and units")
    print("  ✓ Saved results to JSON file")
    print("\nTo use with real data:")
    print("  ./run_results_tracker.sh --date 2026-02-04")
    print("  ./run_results_tracker.sh --latest")
    print("  ./run_results_tracker.sh --report 30")


if __name__ == '__main__':
    mock_track_results_demo()
