"""
EV (Expected Value) Calculator
"""

import logging
from typing import Dict, Optional
import math

from ..data.models import Projection, OddsLine, BetRecommendation, BetSide, SportType

logger = logging.getLogger(__name__)


class EVCalculator:
    """
    Calculate Expected Value for betting opportunities

    EV = (Probability of Win × Profit) - (Probability of Loss × Stake)
    """

    def __init__(self, min_ev_threshold: float = 0.02):
        """
        Args:
            min_ev_threshold: Minimum EV to recommend a bet (default 2%)
        """
        self.min_ev_threshold = min_ev_threshold

        # Model variance (should be calculated from backtesting)
        # NBA totals typically have MAD of ~11.5 points
        self.model_variance = 13.5

    def calculate_totals_ev(
        self,
        projection: Projection,
        odds: OddsLine,
        min_confidence: float = 0.55
    ) -> list:
        """
        Calculate EV for over/under bets

        Args:
            projection: Game projection from analysis
            odds: Current betting odds
            min_confidence: Minimum confidence to recommend

        Returns:
            List of BetRecommendation objects for +EV bets
        """
        recommendations = []

        if not odds.total_line:
            logger.warning(f"No total line available for game {projection.game_id}")
            return recommendations

        projected_total = projection.projected_total
        line = odds.total_line
        diff = projected_total - line

        # Calculate win probabilities based on projection difference
        # The larger the difference, the higher the confidence
        # Confidence already baked into projection, no double-adjustment
        over_win_prob = self._calculate_win_probability_from_diff(diff)
        under_win_prob = 1 - over_win_prob

        # Calculate OVER bet EV
        if odds.over_odds:
            over_ev = self._calculate_ev(over_win_prob, odds.over_odds)

            over_reasoning = (
                f"Projected total: {projected_total} vs Line: {line} "
                f"(Diff: {diff:+.1f}). "
                f"Over win prob: {over_win_prob:.1%}, EV: {over_ev:.2%}"
            )

            if over_ev > self.min_ev_threshold and over_win_prob >= min_confidence:
                recommendations.append(BetRecommendation(
                    game_id=projection.game_id,
                    sport=projection.sport,
                    bet_type=odds.bet_type,
                    side=BetSide.OVER,
                    line=line,
                    odds=odds.over_odds,
                    projected_value=projected_total,
                    ev=over_ev,
                    win_probability=over_win_prob,
                    confidence=projection.confidence,
                    reasoning=over_reasoning,
                    generated_at=None
                ))
                logger.info(f"Found +EV OVER: {line} / {odds.over_odds} "
                          f"(Proj: {projected_total}, EV: {over_ev:.2%})")

        # Calculate UNDER bet EV
        if odds.under_odds:
            under_ev = self._calculate_ev(under_win_prob, odds.under_odds)

            under_reasoning = (
                f"Projected total: {projected_total} vs Line: {line} "
                f"(Diff: {diff:+.1f}). "
                f"Under win prob: {under_win_prob:.1%}, EV: {under_ev:.2%}"
            )

            if under_ev > self.min_ev_threshold and under_win_prob >= min_confidence:
                recommendations.append(BetRecommendation(
                    game_id=projection.game_id,
                    sport=projection.sport,
                    bet_type=odds.bet_type,
                    side=BetSide.UNDER,
                    line=line,
                    odds=odds.under_odds,
                    projected_value=projected_total,
                    ev=under_ev,
                    win_probability=under_win_prob,
                    confidence=projection.confidence,
                    reasoning=under_reasoning,
                    generated_at=None
                ))
                logger.info(f"Found +EV UNDER: {line} / {odds.under_odds} "
                          f"(Proj: {projected_total}, EV: {under_ev:.2%})")

        return recommendations

    def _calculate_win_probability_from_diff(self, diff: float) -> float:
        """
        Convert projection difference to win probability

        Uses a sigmoid-like function to map point difference to probability
        Confidence is already baked into projection quality, so we use fixed variance.
        """
        # Use fixed model variance (confidence already in projection)
        sd = self.model_variance

        # Use simple approximation of normal distribution CDF
        # Using the error function approximation
        z = diff / sd
        # Approximation of cumulative normal distribution
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))

        # Market efficiency adjustment
        # NBA totals market is highly efficient - true edges are small
        # Using 0.20 to account for market efficiency (no double-adjustment)
        market_efficiency_factor = 0.20
        adjusted_prob = 0.5 + (cdf - 0.5) * market_efficiency_factor

        # Clamp to realistic range
        return max(0.35, min(0.65, adjusted_prob))

    def _adjust_probability_by_confidence(self, prob: float, confidence: float) -> float:
        """
        Adjust win probability by projection confidence

        Lower confidence = regression toward 50%
        """
        # Pull probability toward 50% based on lack of confidence
        confidence_factor = confidence  # 0 to 1
        adjusted = 0.5 + (prob - 0.5) * confidence_factor
        return adjusted

    def _calculate_ev(self, win_probability: float, american_odds: int) -> float:
        """
        Calculate Expected Value

        Args:
            win_probability: Probability of winning (0-1)
            american_odds: American odds (e.g., -110, +150)

        Returns:
            EV as a decimal (e.g., 0.05 = 5% EV)
        """
        # Calculate profit on win (assuming $100 bet)
        stake = 100
        if american_odds > 0:
            profit = american_odds
        else:
            profit = stake * (100 / abs(american_odds))

        # EV = (Win Prob × Profit) - (Loss Prob × Stake)
        ev = (win_probability * profit) - ((1 - win_probability) * stake)

        # Return as ROI percentage
        return ev / stake

    def american_to_implied_probability(self, american_odds: int) -> float:
        """
        Convert American odds to implied probability

        This is what the sportsbook thinks the win probability is
        """
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)

    def calculate_edge(
        self,
        your_probability: float,
        book_odds: int
    ) -> float:
        """
        Calculate your edge over the sportsbook

        Edge = Your Probability - Implied Probability
        """
        implied_prob = self.american_to_implied_probability(book_odds)
        return your_probability - implied_prob
