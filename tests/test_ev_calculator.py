"""
Unit tests for EV calculator
"""

import unittest
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.data.models import Projection, OddsLine, SportType, BetType
from src.analysis.ev_calculator_v2 import EnhancedEVCalculator


class TestEVCalculator(unittest.TestCase):
    """Test EV calculation logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.calculator = EnhancedEVCalculator(min_ev_threshold=0.02)

    def test_calculate_ev_positive(self):
        """Test EV calculation for positive EV scenario"""
        projection = Projection(
            game_id="test1",
            sport=SportType.NBA,
            projected_home_score=115,
            projected_away_score=110,
            projected_total=225,
            confidence=0.60,
            model_version="test"
        )

        odds = OddsLine(
            game_id="test1",
            sport=SportType.NBA,
            bet_type=BetType.TOTALS,
            total_line=220,
            over_odds=-110,
            under_odds=-110
        )

        recs = self.calculator.calculate_totals_ev(projection, odds, min_confidence=0.525)

        # Should recommend OVER since projection (225) > line (220)
        over_recs = [r for r in recs if r.side.value == "over"]
        self.assertGreater(len(over_recs), 0)
        self.assertGreater(over_recs[0].ev, 0)

    def test_calculate_ev_negative(self):
        """Test EV calculation for negative EV scenario"""
        projection = Projection(
            game_id="test2",
            sport=SportType.NBA,
            projected_home_score=110,
            projected_away_score=110,
            projected_total=220,
            confidence=0.55,
            model_version="test"
        )

        odds = OddsLine(
            game_id="test2",
            sport=SportType.NBA,
            bet_type=BetType.TOTALS,
            total_line=220,
            over_odds=-110,
            under_odds=-110
        )

        recs = self.calculator.calculate_totals_ev(projection, odds, min_confidence=0.525)

        # With projection equal to line, EV should be minimal or negative
        # (depending on vig calculation)
        self.assertEqual(len(recs), 0)

    def test_under_recommendation(self):
        """Test UNDER bet recommendation"""
        projection = Projection(
            game_id="test3",
            sport=SportType.NBA,
            projected_home_score=108,
            projected_away_score=107,
            projected_total=215,
            confidence=0.60,
            model_version="test"
        )

        odds = OddsLine(
            game_id="test3",
            sport=SportType.NBA,
            bet_type=BetType.TOTALS,
            total_line=225,
            over_odds=-110,
            under_odds=-110
        )

        recs = self.calculator.calculate_totals_ev(projection, odds, min_confidence=0.525)

        # Should recommend UNDER since projection (215) < line (225)
        under_recs = [r for r in recs if r.side.value == "under"]
        self.assertGreater(len(under_recs), 0)

    def test_confidence_threshold(self):
        """Test that low confidence bets are filtered"""
        projection = Projection(
            game_id="test4",
            sport=SportType.NBA,
            projected_home_score=115,
            projected_away_score=105,
            projected_total=220,
            confidence=0.45,  # Low confidence
            model_version="test"
        )

        odds = OddsLine(
            game_id="test4",
            sport=SportType.NBA,
            bet_type=BetType.TOTALS,
            total_line=210,
            over_odds=-110,
            under_odds=-110
        )

        recs = self.calculator.calculate_totals_ev(projection, odds, min_confidence=0.525)

        # Should not recommend due to low confidence
        self.assertEqual(len(recs), 0)


class TestVigRemoval(unittest.TestCase):
    """Test vig/juice removal calculations"""

    def setUp(self):
        """Set up test fixtures"""
        self.calculator = EnhancedEVCalculator()

    def test_implied_probability_calculation(self):
        """Test implied probability calculation with vig removal"""
        # Standard -110/-110 odds
        over_prob, under_prob = self.calculator.calculate_implied_probability_after_vig(-110, -110)

        # Without vig, both should be 50%
        self.assertAlmostEqual(over_prob, 0.5, places=2)
        self.assertAlmostEqual(under_prob, 0.5, places=2)

    def test_imbalanced_odds(self):
        """Test with imbalanced odds"""
        # -150 / +130
        over_prob, under_prob = self.calculator.calculate_implied_probability_after_vig(-150, 130)

        # Sum should be 1.0 (vig removed)
        self.assertAlmostEqual(over_prob + under_prob, 1.0, places=2)
        # Favorite should have higher probability
        self.assertGreater(over_prob, under_prob)


if __name__ == '__main__':
    unittest.main()
