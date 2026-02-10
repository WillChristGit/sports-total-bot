#!/usr/bin/env python3
"""
Test script for ResultsTracker

Tests the tracker with sample data and verifies functionality
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from results.tracker import ResultsTracker, PickResult


def test_pick_result():
    """Test PickResult data class"""
    print("Testing PickResult...")

    sample_pick = {
        'game_id': 'test123',
        'sport': 'nba',
        'bet_type': 'totals',
        'side': 'under',
        'line': 220.5,
        'odds': -110,
        'projected_value': 215.0,
        'ev': 0.05,
        'win_probability': 0.55,
        'confidence': 0.7,
        'home_team': 'Lakers',
        'away_team': 'Celtics',
        'game_time': '2026-02-05T19:00:00+00:00'
    }

    pick = PickResult(sample_pick)
    assert pick.game_id == 'test123'
    assert pick.bet_type == 'totals'
    assert pick.side == 'under'
    assert pick.line == 220.5

    print("✓ PickResult initialization works")
    print(f"  Pick dict: {json.dumps(pick.to_dict(), indent=2)}")


def test_team_normalization():
    """Test team name normalization"""
    print("\nTesting team name normalization...")

    tracker = ResultsTracker()

    test_cases = [
        ('Lakers', 'Los Angeles Lakers'),
        ('Celtics', 'Boston Celtics'),
        ('OKC', 'Oklahoma City Thunder'),
        ('Blazers', 'Portland Trail Blazers'),
        ('76ers', 'Philadelphia 76ers'),
    ]

    for input_name, expected_output in test_cases:
        result = tracker.normalize_team_name(input_name)
        assert result == expected_output, f"Expected {expected_output}, got {result}"
        print(f"✓ '{input_name}' → '{result}'")


def test_totals_evaluation():
    """Test totals pick evaluation"""
    print("\nTesting totals evaluation...")

    tracker = ResultsTracker()

    # Test UNDER pick
    under_pick = {
        'game_id': 'test1',
        'bet_type': 'totals',
        'side': 'under',
        'line': 220.5,
        'odds': -110,
        'home_team': 'Lakers',
        'away_team': 'Celtics'
    }

    # Under win scenario
    game_under_win = {
        'home_score': 105,
        'away_score': 98,
        'total': 203,
        'margin': 7
    }

    pick = PickResult(under_pick)
    status, profit = tracker.evaluate_totals_pick(pick, game_under_win)

    assert status == 'won', f"Expected 'won', got '{status}'"
    assert profit > 0, f"Expected positive profit, got {profit}"
    print(f"✓ UNDER 220.5 with actual 203: {status} (profit: ${profit:.2f})")

    # Under loss scenario
    game_under_loss = {
        'home_score': 118,
        'away_score': 115,
        'total': 233,
        'margin': 3
    }

    pick2 = PickResult(under_pick)
    status2, profit2 = tracker.evaluate_totals_pick(pick2, game_under_loss)

    assert status2 == 'lost', f"Expected 'lost', got '{status2}'"
    assert profit2 == -1.0, f"Expected -1.0 profit, got {profit2}"
    print(f"✓ UNDER 220.5 with actual 233: {status2} (profit: ${profit2:.2f})")

    # Test OVER pick
    over_pick = {
        'game_id': 'test2',
        'bet_type': 'totals',
        'side': 'over',
        'line': 220.5,
        'odds': -110,
        'home_team': 'Lakers',
        'away_team': 'Celtics'
    }

    game_over_win = {
        'home_score': 118,
        'away_score': 115,
        'total': 233,
        'margin': 3
    }

    pick3 = PickResult(over_pick)
    status3, profit3 = tracker.evaluate_totals_pick(pick3, game_over_win)

    assert status3 == 'won', f"Expected 'won', got '{status3}'"
    assert profit3 > 0, f"Expected positive profit, got {profit3}"
    print(f"✓ OVER 220.5 with actual 233: {status3} (profit: ${profit3:.2f})")


def test_spread_evaluation():
    """Test spread pick evaluation"""
    print("\nTesting spread evaluation...")

    tracker = ResultsTracker()

    # Test home favorite covering
    home_spread_pick = {
        'game_id': 'test3',
        'bet_type': 'spreads',
        'side': 'home',
        'line': -9.5,
        'odds': -110,
        'home_team': 'Lakers',
        'away_team': 'Celtics'
    }

    game_home_covers = {
        'home_score': 115,
        'away_score': 100,
        'total': 215,
        'margin': 15
    }

    pick = PickResult(home_spread_pick)
    status, profit = tracker.evaluate_spread_pick(pick, game_home_covers)

    assert status == 'won', f"Expected 'won', got '{status}'"
    print(f"✓ Home -9.5 with margin 15: {status} (profit: ${profit:.2f})")

    # Test home favorite not covering
    game_home_fails = {
        'home_score': 108,
        'away_score': 100,
        'total': 208,
        'margin': 8
    }

    pick2 = PickResult(home_spread_pick)
    status2, profit2 = tracker.evaluate_spread_pick(pick2, game_home_fails)

    assert status2 == 'lost', f"Expected 'lost', got '{status2}'"
    print(f"✓ Home -9.5 with margin 8: {status2} (profit: ${profit2:.2f})")

    # Test away dog covering
    away_spread_pick = {
        'game_id': 'test4',
        'bet_type': 'spreads',
        'side': 'away',
        'line': 9.5,
        'odds': -110,
        'home_team': 'Lakers',
        'away_team': 'Celtics'
    }

    pick3 = PickResult(away_spread_pick)
    status3, profit3 = tracker.evaluate_spread_pick(pick3, game_home_fails)

    assert status3 == 'won', f"Expected 'won', got '{status3}'"
    print(f"✓ Away +9.5 with margin 8: {status3} (profit: ${profit3:.2f})")


def test_summary_calculation():
    """Test summary statistics calculation"""
    print("\nTesting summary calculation...")

    tracker = ResultsTracker()

    # Create sample results
    sample_results = [
        {'status': 'won', 'profit_loss': 0.91, 'units': 5.0, 'bet_type': 'totals'},
        {'status': 'won', 'profit_loss': 0.91, 'units': 4.5, 'bet_type': 'totals'},
        {'status': 'lost', 'profit_loss': -1.0, 'units': 3.0, 'bet_type': 'spreads'},
        {'status': 'lost', 'profit_loss': -1.0, 'units': 4.0, 'bet_type': 'totals'},
        {'status': 'push', 'profit_loss': 0.0, 'units': 2.0, 'bet_type': 'totals'},
        {'status': 'pending', 'profit_loss': 0.0, 'units': 3.0, 'bet_type': 'spreads'},
    ]

    summary = tracker._calculate_summary(sample_results)

    assert summary['wins'] == 2, f"Expected 2 wins, got {summary['wins']}"
    assert summary['losses'] == 2, f"Expected 2 losses, got {summary['losses']}"
    assert summary['pushes'] == 1, f"Expected 1 push, got {summary['pushes']}"
    assert summary['pending'] == 1, f"Expected 1 pending, got {summary['pending']}"
    assert summary['total_bets'] == 5, f"Expected 5 total bets, got {summary['total_bets']}"

    expected_profit = 0.91 + 0.91 - 1.0 - 1.0 + 0.0  # -0.18
    assert abs(summary['total_profit'] - expected_profit) < 0.01, \
        f"Expected profit {expected_profit}, got {summary['total_profit']}"

    expected_win_rate = 50.0  # 2 wins / 4 decided
    assert summary['win_rate'] == expected_win_rate, \
        f"Expected win rate {expected_win_rate}, got {summary['win_rate']}"

    print(f"✓ Summary calculated correctly:")
    print(f"  Wins: {summary['wins']}, Losses: {summary['losses']}, Pushes: {summary['pushes']}")
    print(f"  Win Rate: {summary['win_rate']}%")
    print(f"  Total Profit: ${summary['total_profit']:.2f}")
    print(f"  ROI: {summary['roi']}%")


def test_load_picks():
    """Test loading picks from file"""
    print("\nTesting load_picks...")

    tracker = ResultsTracker()

    # Try to load today's picks or most recent
    picks = tracker.load_picks('20260204')

    if picks:
        print(f"✓ Loaded {len(picks)} picks from 2026-02-04")
        print(f"  Sample pick: {json.dumps(picks[0], indent=2)}")
    else:
        print("ℹ No picks found for 2026-02-04 (this is okay if no picks exist)")


def test_units_calculation():
    """Test Kelly Criterion units calculation"""
    print("\nTesting units calculation...")

    tracker = ResultsTracker()

    # High EV, low odds
    high_ev_pick = PickResult({
        'game_id': 'test1',
        'ev': 0.10,
        'odds': -110,
        'bet_type': 'totals',
        'side': 'under',
        'line': 220.5
    })

    units1 = tracker.calculate_units(high_ev_pick)
    print(f"✓ High EV (10%) pick: {units1} units")

    # Low EV
    low_ev_pick = PickResult({
        'game_id': 'test2',
        'ev': 0.02,
        'odds': -110,
        'bet_type': 'totals',
        'side': 'under',
        'line': 220.5
    })

    units2 = tracker.calculate_units(low_ev_pick)
    print(f"✓ Low EV (2%) pick: {units2} units")

    assert units1 > units2, "High EV should recommend more units"


def main():
    """Run all tests"""
    print("=" * 60)
    print("ResultsTracker Test Suite")
    print("=" * 60)

    try:
        test_pick_result()
        test_team_normalization()
        test_totals_evaluation()
        test_spread_evaluation()
        test_summary_calculation()
        test_units_calculation()
        test_load_picks()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
