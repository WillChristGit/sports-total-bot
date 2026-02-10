#!/usr/bin/env python3
"""
Debug script to check what spread data is being received from The Odds API
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.fetchers import OddsAPIFetcher
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.environ.get('ODDS_API_KEY')

    if not api_key:
        print("ERROR: ODDS_API_KEY not found in environment")
        return 1

    print(f"Using API key: {api_key[:10]}...")
    print("\n" + "="*80)
    print("Fetching NBA games with totals AND spreads markets...")
    print("="*80 + "\n")

    fetcher = OddsAPIFetcher(api_key)

    try:
        games = fetcher.get_nba_games(markets="totals,spreads")

        print(f"Found {len(games)} games\n")

        for i, game in enumerate(games[:3], 1):  # Show first 3 games
            print(f"\n--- Game {i} ---")
            print(f"ID: {game.get('id')}")
            print(f"Match: {game.get('away_team')} @ {game.get('home_team')}")
            print(f"Time: {game.get('commence_time')}")

            # Check bookmakers and markets
            print(f"\nBookmakers: {len(game.get('bookmakers', []))}")

            for bm_idx, bookmaker in enumerate(game.get('bookmakers', [])[:2], 1):  # First 2 books
                print(f"\n  Bookmaker {bm_idx}: {bookmaker.get('title')}")
                print(f"  Markets: {len(bookmaker.get('markets', []))}")

                for market in bookmaker.get('markets', []):
                    market_key = market.get('key')
                    print(f"\n    Market: {market_key}")

                    if market_key == 'totals':
                        print("    ✅ TOTALS market found")
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('name')
                            point = outcome.get('point')
                            price = outcome.get('price')
                            print(f"      {name}: {point} @ {price}")

                    elif market_key == 'spreads':
                        print("    ✅ SPREADS market found")
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('name')
                            point = outcome.get('point')
                            price = outcome.get('price')
                            print(f"      {name}: {point} @ {price}")
                    else:
                        print(f"    ❓ Unknown market: {market_key}")

            # Save full game data to file for inspection
            if i == 1:
                with open('debug_game_data.json', 'w') as f:
                    json.dump(game, f, indent=2)
                print(f"\n  [Full data saved to debug_game_data.json]")

        # Save all games data
        with open('debug_all_games.json', 'w') as f:
            json.dump(games, f, indent=2)
        print(f"\n[All games saved to debug_all_games.json]")

        # Summary statistics
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        totals_count = 0
        spreads_count = 0
        games_with_both = 0

        for game in games:
            has_totals = False
            has_spreads = False

            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'totals':
                        has_totals = True
                    elif market.get('key') == 'spreads':
                        has_spreads = True

            if has_totals:
                totals_count += 1
            if has_spreads:
                spreads_count += 1
            if has_totals and has_spreads:
                games_with_both += 1

        print(f"Games with TOTALS market: {totals_count}/{len(games)}")
        print(f"Games with SPREADS market: {spreads_count}/{len(games)}")
        print(f"Games with BOTH markets: {games_with_both}/{len(games)}")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
