#!/usr/bin/env python3
"""
Test script to verify OPP_PTS (opponent points allowed) fix.
Tests the NBAStatsCache to ensure teams now have non-zero avg_points_allowed values.
"""

import sys
import os
from pathlib import Path

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.data.nba_stats_cache import NBAStatsFetcher


def test_opponent_stats_fix():
    """Test that opponent points (OPP) are now fetched correctly"""
    print("=" * 70)
    print("Testing NBA Stats Cache - OPP_PTS Fix")
    print("=" * 70)

    fetcher = NBAStatsFetcher(cache_dir="data/cache")

    # Test a few well-known teams
    test_teams = [
        "Boston Celtics",
        "Los Angeles Lakers",
        "Golden State Warriors",
        "Phoenix Suns",
    ]

    print("\nFetching team stats to verify avg_points_allowed is no longer 0...\n")

    failures = []
    successes = []

    for team_name in test_teams:
        print(f"Testing {team_name}...", end=" ")
        stats = fetcher.get_team_stats(team_name)

        if stats:
            opp_pts = stats.get('avg_points_allowed', 0)
            pts_scored = stats.get('avg_points_scored', 0)
            off_rating = stats.get('offensive_rating', 0)
            def_rating = stats.get('defensive_rating', 0)

            if opp_pts > 0:
                print(f"✓ PASS")
                print(f"  - Points Scored: {pts_scored:.1f}")
                print(f"  - Points Allowed: {opp_pts:.1f}")
                print(f"  - Off Rating: {off_rating:.1f}")
                print(f"  - Def Rating: {def_rating:.1f}")
                successes.append(team_name)
            else:
                print(f"✗ FAIL - avg_points_allowed is still 0!")
                failures.append(team_name)
        else:
            print(f"✗ FAIL - Could not fetch stats")
            failures.append(team_name)
        print()

    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Successful: {len(successes)}/{len(test_teams)}")
    print(f"Failed: {len(failures)}/{len(test_teams)}")

    if failures:
        print(f"\nFailed teams: {', '.join(failures)}")
        return False
    else:
        print("\n✓ All tests passed! OPP_PTS fix is working correctly.")
        return True


if __name__ == "__main__":
    success = test_opponent_stats_fix()
    sys.exit(0 if success else 1)
