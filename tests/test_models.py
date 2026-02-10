"""
Unit tests for data models
"""

import unittest
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.data.models import (
    Game, OddsLine, Projection, BetRecommendation,
    SportType, BetType, BetSide, TeamStats
)


class TestDataModels(unittest.TestCase):
    """Test data model creation and validation"""

    def test_game_creation(self):
        """Test Game model creation"""
        game = Game(
            game_id="test123",
            sport=SportType.NBA,
            home_team="Lakers",
            away_team="Warriors",
            game_time=datetime.now()
        )
        self.assertEqual(game.game_id, "test123")
        self.assertEqual(game.sport, SportType.NBA)
        self.assertEqual(game.home_team, "Lakers")
        self.assertFalse(game.is_completed)

    def test_odds_line_creation(self):
        """Test OddsLine model creation"""
        odds = OddsLine(
            game_id="test123",
            sport=SportType.NBA,
            bet_type=BetType.TOTALS,
            total_line=220.5,
            over_odds=-110,
            under_odds=-110
        )
        self.assertEqual(odds.total_line, 220.5)
        self.assertEqual(odds.over_odds, -110)

    def test_projection_creation(self):
        """Test Projection model creation"""
        projection = Projection(
            game_id="test123",
            sport=SportType.NBA,
            projected_home_score=110.5,
            projected_away_score=108.3,
            projected_total=218.8,
            confidence=0.65,
            model_version="test_v1"
        )
        self.assertAlmostEqual(projection.projected_total, 218.8, places=1)
        self.assertEqual(projection.confidence, 0.65)

    def test_bet_recommendation_creation(self):
        """Test BetRecommendation model creation"""
        rec = BetRecommendation(
            game_id="test123",
            sport=SportType.NBA,
            bet_type=BetType.TOTALS,
            side=BetSide.OVER,
            line=220.5,
            odds=-110,
            projected_value=225.0,
            ev=0.05,
            win_probability=0.55,
            confidence=0.60,
            reasoning="Test reasoning"
        )
        self.assertEqual(rec.side, BetSide.OVER)
        self.assertAlmostEqual(rec.ev, 0.05)
        self.assertEqual(rec.win_probability, 0.55)

    def test_team_stats_creation(self):
        """Test TeamStats model creation"""
        stats = TeamStats(
            team_id="1",
            team_name="Lakers",
            games_played=50,
            avg_points_scored=115.0,
            avg_points_allowed=112.0,
            offensive_rating=115.5,
            defensive_rating=112.5,
            pace=100.5
        )
        self.assertEqual(stats.team_name, "Lakers")
        self.assertEqual(stats.games_played, 50)


class TestEnumValues(unittest.TestCase):
    """Test enum values are correct"""

    def test_sport_type_values(self):
        """Test SportType enum"""
        self.assertEqual(SportType.NBA.value, "nba")
        self.assertEqual(SportType.WNBA.value, "wnba")
        self.assertEqual(SportType.NFL.value, "nfl")

    def test_bet_type_values(self):
        """Test BetType enum"""
        self.assertEqual(BetType.TOTALS.value, "totals")
        self.assertEqual(BetType.SPREAD.value, "spreads")

    def test_bet_side_values(self):
        """Test BetSide enum"""
        self.assertEqual(BetSide.OVER.value, "over")
        self.assertEqual(BetSide.UNDER.value, "under")


if __name__ == '__main__':
    unittest.main()
