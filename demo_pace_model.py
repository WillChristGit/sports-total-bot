#!/usr/bin/env python3
"""
Demonstration of the Improved Pace Model

This script shows how the new weighted pace calculation improves upon
the simple average model for different game scenarios.
"""

import sys
from datetime import datetime

sys.path.insert(0, '/Volumes/LegbaSSD/bots/SportsTotalBot')

from src.analysis.projections_v2 import EnhancedNBATotalsModel, AdvancedTeamStats
from src.data.models import Game, SportType


def create_team_stats(name, pace, ortg, drtg, points_scored=115, points_allowed=115):
    """Helper to create team stats"""
    return AdvancedTeamStats(
        team_id=name,
        team_name=name,
        games_played=50,
        avg_points_scored=points_scored,
        avg_points_allowed=points_allowed,
        offensive_rating=ortg,
        defensive_rating=drtg,
        pace=pace,
        efg_pct=0.500,
        tov_pct=0.140,
        orb_pct=0.250,
        ft_rate=0.200
    )


def demo_pace_calculation():
    """Demonstrate pace calculations for various scenarios"""
    model = EnhancedNBATotalsModel()

    print("=" * 80)
    print("IMPROVED PACE MODEL DEMONSTRATION")
    print("=" * 80)
    print()

    scenarios = [
        {
            "name": "Track Meet: Suns vs Kings",
            "description": "Two fast-paced teams with great offenses",
            "home": create_team_stats("Suns", pace=103.0, ortg=118.0, drtg=116.0),
            "away": create_team_stats("Kings", pace=102.0, ortg=116.0, drtg=118.0),
            "expected": "Very fast paced game"
        },
        {
            "name": "Rock Fight: Cavaliers vs Magic",
            "description": "Two slow-paced teams with elite defenses",
            "home": create_team_stats("Cavaliers", pace=97.0, ortg=112.0, drtg=108.0),
            "away": create_team_stats("Magic", pace=96.0, ortg=110.0, drtg=106.0),
            "expected": "Very slow paced game"
        },
        {
            "name": "Explosive Offense vs Bad Defense",
            "description": "Fast team with elite offense vs terrible defense",
            "home": create_team_stats("Suns", pace=103.0, ortg=118.0, drtg=118.0),
            "away": create_team_stats("Wizards", pace=99.0, ortg=110.0, drtg=120.0),
            "expected": "Faster than simple average suggests"
        },
        {
            "name": "Average Teams: Lakers vs Warriors",
            "description": "Two average-paced teams",
            "home": create_team_stats("Lakers", pace=100.0, ortg=115.0, drtg=115.0),
            "away": create_team_stats("Warriors", pace=100.0, ortg=115.0, drtg=115.0),
            "expected": "League average pace"
        },
        {
            "name": "Clash of Styles: Fast vs Slow",
            "description": "Fast team vs slow team",
            "home": create_team_stats("Suns", pace=103.0, ortg=118.0, drtg=116.0),
            "away": create_team_stats("Cavaliers", pace=97.0, ortg=112.0, drtg=108.0),
            "expected": "Pace toward faster team's preference"
        }
    ]

    for scenario in scenarios:
        print(f"SCENARIO: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Expected: {scenario['expected']}")

        home = scenario['home']
        away = scenario['away']

        # Old model: simple average
        old_pace = (home.pace + away.pace) / 2

        # New model: weighted calculation
        new_pace_factor = model._calculate_game_pace(home, away)
        new_pace = new_pace_factor * 100.0

        # Difference
        diff = new_pace - old_pace

        print(f"\nTeam Stats:")
        print(f"  {home.team_name:15s}: Pace={home.pace:.1f}, ORtg={home.offensive_rating:.1f}, DRtg={home.defensive_rating:.1f}")
        print(f"  {away.team_name:15s}: Pace={away.pace:.1f}, ORtg={away.offensive_rating:.1f}, DRtg={away.defensive_rating:.1f}")

        print(f"\nPace Calculation:")
        print(f"  Old Model (Simple Average): {old_pace:.1f} possessions")
        print(f"  New Model (Weighted):       {new_pace:.1f} possessions")
        print(f"  Difference:                 {diff:+.1f} possessions ({diff/old_pace*100:+.1f}%)")

        # Interpret the result
        if abs(diff) < 0.3:
            interpretation = "Minimal change from simple average"
        elif diff > 0.5:
            interpretation = "Significantly faster than average (matchup creates pace)"
        elif diff < -0.5:
            interpretation = "Significantly slower than average (defense suppresses pace)"
        elif diff > 0:
            interpretation = "Slightly faster than average"
        else:
            interpretation = "Slightly slower than average"

        print(f"  Interpretation:              {interpretation}")
        print()


def demo_scenario_factors():
    """Demonstrate scenario-based pace adjustments"""
    model = EnhancedNBATotalsModel()

    print("=" * 80)
    print("SCENARIO FACTOR DEMONSTRATION")
    print("=" * 80)
    print()

    # Base teams
    home = create_team_stats("Lakers", pace=100.0, ortg=115.0, drtg=115.0)
    away = create_team_stats("Warriors", pace=100.0, ortg=115.0, drtg=115.0)

    scenarios = [
        ("Regular Season", None, None, None, False),
        ("Playoff Game", None, None, None, True),
        ("High Total Line (240)", None, None, 240.0, False),
        ("Back-to-Back", True, None, None, False),
    ]

    print(f"Base teams: {home.team_name} (pace={home.pace:.1f}) vs {away.team_name} (pace={away.pace:.1f})")
    print(f"Simple average: {(home.pace + away.pace) / 2:.1f} possessions")
    print()

    for name, is_b2b, _, total, is_playoff in scenarios:
        from src.analysis.projections_v2 import ScheduleInfo

        schedule_home = ScheduleInfo(is_back_to_back=is_b2b or False) if is_b2b else None
        schedule_away = ScheduleInfo(is_back_to_back=is_b2b or False) if is_b2b else None

        pace_factor = model._calculate_game_pace(
            home, away,
            home_schedule=schedule_home,
            away_schedule=schedule_away,
            total_line=total,
            is_playoff_game=is_playoff
        )
        pace = pace_factor * 100.0

        print(f"{name:25s}: {pace:.1f} possessions")

    print()


def demo_full_projections():
    """Demonstrate full game projections with the new model"""
    model = EnhancedNBATotalsModel()

    print("=" * 80)
    print("FULL GAME PROJECTION EXAMPLES")
    print("=" * 80)
    print()

    games = [
        {
            "name": "Suns @ Kings",
            "description": "High-scoring affair expected",
            "home": create_team_stats("Kings", pace=102.0, ortg=116.0, drtg=118.0, points_scored=118),
            "away": create_team_stats("Suns", pace=103.0, ortg=118.0, drtg=116.0, points_scored=117),
        },
        {
            "name": "Cavaliers @ Magic",
            "description": "Low-scoring defensive battle",
            "home": create_team_stats("Magic", pace=96.0, ortg=110.0, drtg=106.0, points_scored=108),
            "away": create_team_stats("Cavaliers", pace=97.0, ortg=112.0, drtg=108.0, points_scored=110),
        }
    ]

    for game_info in games:
        game = Game(
            game_id="demo",
            sport=SportType.NBA,
            home_team=game_info['home'].team_name,
            away_team=game_info['away'].team_name,
            game_time=datetime.now()
        )

        print(f"GAME: {game_info['name']}")
        print(f"Description: {game_info['description']}")
        print()

        projection = model.project_game(game, game_info['home'], game_info['away'])

        print(f"Projection:")
        print(f"  Home Score: {projection.projected_home_score:.1f}")
        print(f"  Away Score: {projection.projected_away_score:.1f}")
        print(f"  Total:      {projection.projected_total:.1f}")
        print(f"  Confidence: {projection.confidence:.1%}")
        print(f"  Model:      {projection.model_version}")
        print()


if __name__ == "__main__":
    demo_pace_calculation()
    demo_scenario_factors()
    demo_full_projections()

    print("=" * 80)
    print("SUMMARY OF IMPROVEMENTS")
    print("=" * 80)
    print()
    print("The new pace model provides:")
    print("  1. Offensive pace weighting (35%) - team's preferred tempo")
    print("  2. Defensive pace impact (25%) - how much defense allows")
    print("  3. Matchup interactions (40%) - style clash dynamics")
    print("  4. Scenario adjustments - playoffs, B2B, high totals")
    print()
    print("Key insight: Fast offense vs bad defense creates FASTER pace than")
    print("simple average would suggest. Slow offense vs good defense creates")
    print("SLOWER pace. The new model captures these dynamics.")
    print()
