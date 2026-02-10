#!/usr/bin/env python3
"""
Test script for NBA Injury Fetcher

Tests the injury fetcher module by:
1. Fetching injury data from ESPN
2. Parsing injury reports
3. Calculating impact for a sample game
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.data.injury_fetcher import InjuryFetcher, PlayerInjury, InjuryStatus, PlayerImportance

def test_injury_fetcher():
    """Test the injury fetcher functionality"""
    print("=" * 60)
    print("NBA Injury Fetcher Test")
    print("=" * 60)

    # Create fetcher
    cache_dir = "data/cache/injuries"
    fetcher = InjuryFetcher(cache_dir=cache_dir)

    print("\n1. Fetching injury data...")
    try:
        reports = fetcher.fetch_all_injuries(force_refresh=False)
        print(f"   Found {len(reports)} teams with injury data")
    except Exception as e:
        print(f"   Error: {e}")
        return False

    if not reports:
        print("   No injury reports found. The cache may be empty or scraping failed.")
        print("   Trying force refresh...")
        try:
            reports = fetcher.fetch_all_injuries(force_refresh=True)
            print(f"   Found {len(reports)} teams with injury data")
        except Exception as e:
            print(f"   Force refresh also failed: {e}")
            return False

    print("\n2. Sample injury reports:")
    for team_name in sorted(list(reports.keys()))[:5]:
        report = reports[team_name]
        print(f"\n   {team_name}:")
        for injury in report.injuries[:3]:
            print(f"     - {injury.player_name} ({injury.position}): {injury.status.value}")
            print(f"       Impact Score: {injury.impact_score:.1f}")
        print(f"   Team Offensive Impact: {report.total_offensive_impact:.1f}")
        print(f"   Team Defensive Impact: {report.total_defensive_impact:.1f}")

    print("\n3. Testing game impact calculation:")
    # Test with a few team combinations
    test_games = [
        ("Los Angeles Lakers", "Golden State Warriors"),
        ("Boston Celtics", "Milwaukee Bucks"),
    ]

    for home, away in test_games:
        print(f"\n   {away} @ {home}:")
        impact = fetcher.get_game_injury_impact(home, away)

        print(f"     Home Offensive Impact: {impact['home_offensive_impact']:.1f}")
        print(f"     Home Defensive Impact: {impact['home_defensive_impact']:.1f}")
        print(f"     Away Offensive Impact: {impact['away_offensive_impact']:.1f}")
        print(f"     Away Defensive Impact: {impact['away_defensive_impact']:.1f}")
        print(f"     Total Impact: {impact['total_impact']:.1f}")
        print(f"     Pace Impact: {impact['pace_impact']:.1f}")

        if impact['significant_injuries']:
            print(f"     Significant Injuries: {', '.join(impact['significant_injuries'][:3])}")
        else:
            print(f"     No significant injuries")

    print("\n4. Testing impact calculation logic:")
    # Create test injuries
    star_out = PlayerInjury(
        player_name="Test Star",
        team="Test Team",
        position="PG",
        status=InjuryStatus.OUT,
        importance=PlayerImportance.STAR
    )
    print(f"   Star OUT impact: {star_out.impact_score:.1f} points")

    starter_out = PlayerInjury(
        player_name="Test Starter",
        team="Test Team",
        position="SF",
        status=InjuryStatus.OUT,
        importance=PlayerImportance.STARTER
    )
    print(f"   Starter OUT impact: {starter_out.impact_score:.1f} points")

    role_dtd = PlayerInjury(
        player_name="Test Role",
        team="Test Team",
        position="C",
        status=InjuryStatus.DAY_TO_DAY,
        importance=PlayerImportance.ROLE_PLAYER
    )
    print(f"   Role Day-To-Day impact: {role_dtd.impact_score:.1f} points")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_injury_fetcher()
    sys.exit(0 if success else 1)
