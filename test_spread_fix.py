#!/usr/bin/env python3
"""
Test script to verify the spread parsing fix
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
load_dotenv()

# Import the function
import main_v2

def test_spread_parsing():
    """Test that spread data is being parsed correctly"""

    # Mock API response for testing
    mock_response = [
        {
            'id': 'test-game-1',
            'home_team': 'New York Knicks',
            'away_team': 'Denver Nuggets',
            'commence_time': '2026-02-05T00:10:00Z',
            'bookmakers': [
                {
                    'title': 'FanDuel',
                    'markets': [
                        {
                            'key': 'spreads',
                            'outcomes': [
                                {'name': 'Denver Nuggets', 'point': 4.5, 'price': -106},
                                {'name': 'New York Knicks', 'point': -4.5, 'price': -114}
                            ]
                        },
                        {
                            'key': 'totals',
                            'outcomes': [
                                {'name': 'Over', 'point': 227.5, 'price': -106},
                                {'name': 'Under', 'point': 227.5, 'price': -114}
                            ]
                        }
                    ]
                }
            ]
        }
    ]

    print("Testing spread parsing...")
    print("="*80)

    games, odds_dict = main_v2.parse_odds_api_response(mock_response)

    print(f"\nParsed {len(games)} games")
    print(f"Created {len(odds_dict)} odds entries")

    for odds_key, odds in odds_dict.items():
        print(f"\n{odds_key}:")
        print(f"  bet_type: {odds.bet_type}")
        if odds.bet_type == 'spreads':
            print(f"  home_spread: {odds.home_spread}")
            print(f"  home_spread_odds: {odds.home_spread_odds}")
            print(f"  away_spread: {odds.away_spread}")
            print(f"  away_spread_odds: {odds.away_spread_odds}")

            if odds.home_spread and odds.away_spread:
                print("  ✅ SUCCESS: Spread data is complete!")
            else:
                print("  ❌ FAILED: Spread data is incomplete!")
                print(f"     home_spread={odds.home_spread}, away_spread={odds.away_spread}")

if __name__ == '__main__':
    test_spread_parsing()
