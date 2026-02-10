#!/usr/bin/env python3
"""
Debug script to see what the Opponent MeasureType returns from NBA.com API
"""

import sys
import os
import json

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.data.nba_stats_cache import NBAStatsFetcher
from src.utils.season import get_current_nba_season


def debug_opponent_api():
    """Debug the opponent stats API response"""
    print("=" * 70)
    print("Debugging NBA.com Opponent Stats API")
    print("=" * 70)

    fetcher = NBAStatsFetcher(cache_dir="data/cache")

    # Test with Celtics
    team_name = "Boston Celtics"
    normalized_name = fetcher.normalize_team_name(team_name)
    team_id = fetcher.team_name_to_id.get(normalized_name)

    print(f"\nTeam: {team_name}")
    print(f"Team ID: {team_id}")
    print(f"Season: {get_current_nba_season()}")

    # First, check Base MeasureType (what we were using)
    print("\n" + "=" * 70)
    print("1. BASE MeasureType (original - doesn't have OPP_PTS)")
    print("=" * 70)

    url = "https://stats.nba.com/stats/leaguedashteamstats"
    params = {
        "LeagueID": "00",
        "Season": get_current_nba_season(),
        "SeasonType": "Regular Season",
        "MeasureType": "Base",
        "PerMode": "PerGame",
    }

    data = fetcher._make_request(url, params, use_cache=False)

    if data and 'resultSets' in data:
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']

        print(f"\nAvailable columns ({len(headers)}):")
        for i, h in enumerate(headers):
            print(f"  [{i}] {h}")

        for row in rows:
            if row[0] == team_id:
                team_dict = dict(zip(headers, row))
                print(f"\n{'PTS' in team_dict} - PTS column exists: {team_dict.get('PTS', 'NOT FOUND')}")
                print(f"{'OPP_PTS' in team_dict} - OPP_PTS column exists: {team_dict.get('OPP_PTS', 'NOT FOUND')}")
                print(f"{'DEF_RATING' in team_dict} - DEF_RATING exists: {team_dict.get('DEF_RATING', 'NOT FOUND')}")
                break

    # Now check Opponent MeasureType
    print("\n" + "=" * 70)
    print("2. OPPONENT MeasureType (should have opponent stats)")
    print("=" * 70)

    params["MeasureType"] = "Opponent"
    data = fetcher._make_request(url, params, use_cache=False)

    if data and 'resultSets' in data:
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']

        print(f"\nAvailable columns ({len(headers)}):")
        for i, h in enumerate(headers):
            print(f"  [{i}] {h}")

        for row in rows:
            if row[0] == team_id:
                team_dict = dict(zip(headers, row))
                print(f"\nStats from Opponent MeasureType for {team_name}:")
                print(f"  PTS (points opponents score against us): {team_dict.get('PTS', 'NOT FOUND')}")
                print(f"  FG_PCT: {team_dict.get('FG_PCT', 'NOT FOUND')}")
                print(f"  FG3_PCT: {team_dict.get('FG3_PCT', 'NOT FOUND')}")
                print(f"  REB: {team_dict.get('REB', 'NOT FOUND')}")
                print(f"  AST: {team_dict.get('AST', 'NOT FOUND')}")
                print(f"  OFF_RATING: {team_dict.get('OFF_RATING', 'NOT FOUND')}")
                print(f"  DEF_RATING: {team_dict.get('DEF_RATING', 'NOT FOUND')}")
                print(f"  TEAM_NAME: {team_dict.get('TEAM_NAME', 'NOT FOUND')}")
                break
    else:
        print("ERROR: No data returned from Opponent MeasureType!")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    debug_opponent_api()
