#!/usr/bin/env python3
"""
Test script for alternative NBA stats sources.

This script tests the fallback chain when NBA.com API is blocked.
"""

import logging
from src.data.alternative_sources import (
    AlternativeStatsFetcher,
    NBAApiEndpoint,
    BallDontLieAPI,
    ESPNAPI,
    BasketballReferenceScraper,
    SportsDataIO
)

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

def test_individual_sources():
    """Test each alternative source individually"""
    test_team = "Boston Celtics"

    print(f"\n{'='*60}")
    print(f"Testing Alternative Sources for {test_team}")
    print(f"{'='*60}\n")

    results = {}

    # Test NBA API Endpoint
    print("1. Testing NBA API Endpoint...")
    nba_api = NBAApiEndpoint()
    stats = nba_api.get_team_stats(test_team)
    if stats:
        print(f"   SUCCESS: Source={stats['source']}, PPG={stats['points_per_game']:.1f}")
        results['nba_api'] = stats
    else:
        print("   FAILED")

    # Test BallDontLie (may require auth now)
    print("\n2. Testing BallDontLie API...")
    bdl = BallDontLieAPI()
    stats = bdl.get_team_stats(test_team)
    if stats:
        print(f"   SUCCESS: Source={stats['source']}, PPG={stats['points_per_game']:.1f}")
        results['balldontlie'] = stats
    else:
        print("   FAILED (API may require authentication)")

    # Test SportsData.io (requires API key)
    print("\n3. Testing SportsData.io...")
    sdio = SportsDataIO()  # No key provided
    stats = sdio.get_team_stats(test_team)
    if stats:
        print(f"   SUCCESS: Source={stats['source']}, PPG={stats['points_per_game']:.1f}")
        results['sportsdataio'] = stats
    else:
        print("   FAILED (no API key configured)")

    # Test ESPN API
    print("\n4. Testing ESPN API...")
    espn = ESPNAPI()
    stats = espn.get_team_stats(test_team)
    if stats:
        print(f"   SUCCESS: Source={stats['source']}, PPG={stats['points_per_game']:.1f}")
        results['espn'] = stats
    else:
        print("   FAILED")

    # Test Basketball-Reference scraper
    print("\n5. Testing Basketball-Reference Scraper...")
    bbr = BasketballReferenceScraper()
    stats = bbr.get_team_stats(test_team)
    if stats:
        print(f"   SUCCESS: Source={stats['source']}, PPG={stats['points_per_game']:.1f}")
        results['basketball-reference'] = stats
    else:
        print("   FAILED")

    print(f"\n{'='*60}")
    print(f"Summary: {len(results)}/5 sources working")
    print(f"{'='*60}")

    return results


def test_fallback_chain():
    """Test the complete fallback chain"""
    test_teams = ["Boston Celtics", "Los Angeles Lakers", "Golden State Warriors"]

    print(f"\n{'='*60}")
    print("Testing Complete Fallback Chain")
    print(f"{'='*60}\n")

    fetcher = AlternativeStatsFetcher()

    for team in test_teams:
        print(f"\nFetching {team}...")
        stats = fetcher.get_team_stats(team)

        if stats:
            print(f"  Source: {stats['source']}")
            print(f"  PPG: {stats['points_per_game']:.1f}")
            print(f"  OPPG: {stats['opp_points_per_game']:.1f}")
            print(f"  Pace: {stats['pace']:.1f}")
            print(f"  ORtg: {stats['offensive_rating']:.1f}")
            print(f"  DRtg: {stats['defensive_rating']:.1f}")
        else:
            print("  FAILED: All sources failed")

    print(f"\n{'='*60}")
    print("Success Report:")
    print(f"{'='*60}")
    for source, count in fetcher.get_success_report().items():
        print(f"  {source}: {count} teams")


def test_multi_source_integration():
    """Test integration with MultiSourceStatsFetcher"""
    from src.data.multi_source_stats import MultiSourceStatsFetcher

    print(f"\n{'='*60}")
    print("Testing MultiSourceStatsFetcher Integration")
    print(f"{'='*60}\n")

    fetcher = MultiSourceStatsFetcher(
        cache_dir='data/cache',
        odds_api_key='test',
        sportsdataio_key=None
    )

    test_teams = ["Boston Celtics", "Miami Heat", "Dallas Mavericks"]

    for team in test_teams:
        stats = fetcher.get_team_stats(team)
        print(f"{team:25} | Source: {stats.data_source.value:15} | "
              f"Quality: {stats.data_quality.value} | PPG: {stats.points_per_game:.1f}")

    report = fetcher.get_quality_report()
    print(f"\nQuality Score: {report.quality_score:.1f}/100")
    print(f"Should Trust Picks: {report.should_trust_picks}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print(" Alternative NBA Stats Sources Test Suite")
    print("="*60)

    # Test individual sources
    test_individual_sources()

    # Test fallback chain
    test_fallback_chain()

    # Test integration
    test_multi_source_integration()

    print("\n" + "="*60)
    print(" Test Suite Complete")
    print("="*60)
