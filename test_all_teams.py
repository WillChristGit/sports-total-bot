#!/usr/bin/env python3
"""
Test all NBA teams to verify OPP_PTS fix works for everyone.
"""

import sys
import os
from pathlib import Path

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.data.nba_stats_cache import NBAStatsFetcher


def test_all_teams():
    """Test that all teams have non-zero avg_points_allowed"""
    print("=" * 70)
    print("Testing ALL NBA Teams - OPP_PTS Fix Verification")
    print("=" * 70)

    fetcher = NBAStatsFetcher(cache_dir="data/cache")

    all_stats = fetcher.get_all_team_stats()

    print(f"\nTotal teams fetched: {len(all_stats)}")

    failures = []
    zero_opp_teams = []
    valid_teams = []

    for team_name, stats in all_stats.items():
        opp_pts = stats.get('avg_points_allowed', 0)
        pts_scored = stats.get('avg_points_scored', 0)

        if opp_pts == 0:
            zero_opp_teams.append(team_name)
            failures.append(team_name)
        else:
            valid_teams.append((team_name, pts_scored, opp_pts))

    if zero_opp_teams:
        print(f"\n❌ TEAMS WITH ZERO OPP_PTS ({len(zero_opp_teams)}):")
        for team in zero_opp_teams:
            print(f"  - {team}")

    print(f"\n✓ TEAMS WITH VALID OPP_PTS ({len(valid_teams)}):")
    print(f"{'Team':<30} {'Pts For':<10} {'Pts Against':<15}")
    print("-" * 60)
    for team, pts_for, pts_against in sorted(valid_teams):
        print(f"{team:<30} {pts_for:<10.1f} {pts_against:<15.1f}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total teams: {len(all_stats)}")
    print(f"Valid OPP_PTS: {len(valid_teams)}")
    print(f"Zero OPP_PTS: {len(zero_opp_teams)}")

    # Calculate league averages
    if valid_teams:
        avg_pts_for = sum(t[1] for t in valid_teams) / len(valid_teams)
        avg_pts_against = sum(t[2] for t in valid_teams) / len(valid_teams)
        print(f"\nLeague Average Points Scored: {avg_pts_for:.1f}")
        print(f"League Average Points Allowed: {avg_pts_against:.1f}")

    if failures:
        print(f"\n❌ FAILED: {len(failures)} teams still have zero OPP_PTS")
        return False
    else:
        print(f"\n✓ SUCCESS: All teams have valid OPP_PTS values!")
        return True


if __name__ == "__main__":
    success = test_all_teams()
    sys.exit(0 if success else 1)
