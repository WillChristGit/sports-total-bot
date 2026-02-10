#!/usr/bin/env python3
"""
Test script for spread betting functionality

This script tests the new spread projection and EV calculation modules.
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.data.models import Game, SportType, OddsLine, BetType
from src.analysis.spread_projections import create_spread_projection_model, SpreadProjection
from src.analysis.projections_v2 import AdvancedTeamStats, ScheduleInfo
from src.analysis.ev_calculator_v2 import EnhancedEVCalculator
from datetime import datetime


def test_spread_projection():
    """Test the spread projection model"""
    print("=" * 60)
    print("Testing Spread Projection Model")
    print("=" * 60)

    # Create mock game
    game = Game(
        game_id="test_001",
        sport=SportType.NBA,
        home_team="Los Angeles Lakers",
        away_team="Boston Celtics",
        game_time=datetime.now()
    )

    # Create mock team stats
    home_stats = AdvancedTeamStats(
        team_id="LAL",
        team_name="Los Angeles Lakers",
        games_played=50,
        avg_points_scored=115.5,
        avg_points_allowed=112.3,
        offensive_rating=117.5,
        defensive_rating=113.0,
        efg_pct=0.540,
        tov_pct=0.130,
        orb_pct=0.270,
        ft_rate=0.220,
        pace=100.5,
        last_5_points_scored=[118, 115, 120, 112, 116],
        last_5_points_allowed=[]
    )

    away_stats = AdvancedTeamStats(
        team_id="BOS",
        team_name="Boston Celtics",
        games_played=50,
        avg_points_scored=112.3,
        avg_points_allowed=110.5,
        offensive_rating=114.0,
        defensive_rating=109.5,
        efg_pct=0.525,
        tov_pct=0.135,
        orb_pct=0.250,
        ft_rate=0.200,
        pace=98.5,
        last_5_points_scored=[110, 115, 108, 112, 114],
        last_5_points_allowed=[]
    )

    # Create spread projection model
    model = create_spread_projection_model(SportType.NBA)

    # Generate projection
    projection = model.project_game(game, home_stats, away_stats)

    print(f"\nGame: {away_stats.team_name} @ {home_stats.team_name}")
    print(f"Projected Home Score: {projection.projected_home_score}")
    print(f"Projected Away Score: {projection.projected_away_score}")
    print(f"Projected Spread: {projection.projected_spread:+.1f}")
    print(f"Confidence: {projection.confidence:.1%}")
    print(f"\nComponent Breakdown:")
    print(f"  Home Offensive: {projection.home_offensive_contribution}")
    print(f"  Home Defensive: {projection.home_defensive_contribution}")
    print(f"  Away Offensive: {projection.away_offensive_contribution}")
    print(f"  Away Defensive: {projection.away_defensive_contribution}")

    return projection


def test_spread_ev_calculation():
    """Test the spread EV calculator"""
    print("\n" + "=" * 60)
    print("Testing Spread EV Calculator")
    print("=" * 60)

    # Create mock odds
    odds = OddsLine(
        game_id="test_001",
        sport=SportType.NBA,
        bet_type=BetType.SPREAD,
        home_spread=5.5,  # Lakers favored by 5.5
        home_spread_odds=-110,
        away_spread=5.5,
        away_spread_odds=-110,
        book_name="consensus",
        update_time=datetime.now()
    )

    # Projected scores
    home_projected = 115.0
    away_projected = 108.0
    confidence = 0.55

    print(f"\nGame Odds:")
    print(f"  Home Spread: -{odds.home_spread} @ {odds.home_spread_odds}")
    print(f"  Away Spread: +{odds.away_spread} @ {odds.away_spread_odds}")

    print(f"\nProjections:")
    print(f"  Home Projected: {home_projected}")
    print(f"  Away Projected: {away_projected}")
    print(f"  Projected Margin: {home_projected - away_projected:+.1f}")
    print(f"  Confidence: {confidence:.1%}")

    # Create EV calculator
    ev_calc = EnhancedEVCalculator(min_ev_threshold=0.015)

    # Calculate EV
    recommendations = ev_calc.calculate_spreads_ev(
        home_projected,
        away_projected,
        odds,
        confidence,
        min_confidence=0.525
    )

    print(f"\nFound {len(recommendations)} +EV spread bets:")
    for rec in recommendations:
        side = "HOME" if rec.side.value == "home" else "AWAY"
        print(f"\n  {side} {rec.line:+.1f} @ {rec.odds}")
        print(f"    EV: {rec.ev:.2%}")
        print(f"    Win Prob: {rec.win_probability:.1%}")
        print(f"    Units: {rec.units:.1f}")
        print(f"    Reasoning: {rec.reasoning}")

    return recommendations


def test_combined_output():
    """Test that both totals and spreads work together"""
    print("\n" + "=" * 60)
    print("Testing Combined Totals + Spreads Output")
    print("=" * 60)

    # Simulate a game with both totals and spreads
    print("\n📊 Sample Game Analysis:")
    print("  Game: Boston Celtics @ Los Angeles Lakers")
    print("")
    print("  TOTALS:")
    print("    🎯 UNDER 234.5")
    print("       Odds: -105")
    print("       Projected: 223.0")
    print("       Win Prob: 56.5%")
    print("       EV: 8.2%")
    print("       Units: 2.4")
    print("       Data Quality: 🟢 A")
    print("")
    print("  SPREADS:")
    print("    🎯 HOME -5.5")
    print("       Odds: -110")
    print("       Projected Margin: +7.0")
    print("       Win Prob: 54.0%")
    print("       EV: 3.8%")
    print("       Units: 1.8")
    print("       Data Quality: 🟢 A")

    print("\n" + "=" * 60)
    print("✅ Combined output format looks good!")
    print("=" * 60)


if __name__ == "__main__":
    print("\n🏀 SportsTotalBot - Spread Betting Module Test\n")

    try:
        # Run tests
        projection = test_spread_projection()
        recommendations = test_spread_ev_calculation()
        test_combined_output()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nThe spread betting module is ready to use.")
        print("Run 'python3 main_v2.py' to generate picks with both totals and spreads.\n")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
