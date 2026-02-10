"""
Enhanced EV (Expected Value) Calculator - V2

Improvements from V1:
- Better probability distribution using model-specific variance
- Proper vig/juice adjustment
- Kelly Criterion for bet sizing
- Line movement analysis
- More conservative confidence thresholds based on market efficiency
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math
from dataclasses import dataclass, field

from ..data.models import Projection, OddsLine, BetRecommendation, BetSide, SportType, BetType

# Type hint for AdvancedTeamStats (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .projections_v2 import AdvancedTeamStats, ScheduleInfo

logger = logging.getLogger(__name__)


@dataclass
class LineMovement:
    """Track how a betting line has moved"""
    opening_line: float
    opening_over_odds: int
    opening_under_odds: int
    current_line: float
    current_over_odds: int
    current_under_odds: int
    hours_since_open: int = 0


@dataclass
class EnhancedBetRecommendation(BetRecommendation):
    """Enhanced recommendation with additional fields"""
    units: float = 1.0  # Kelly-recommended units
    line_movement_edge: float = 0.0  # Additional edge from line movement
    confidence_interval: Tuple[float, float] = (0.0, 0.0)  # CI for win probability


class LineMovementAnalyzer:
    """
    Analyze line movement for additional edge

    Sharp money moves lines early; public money moves late
    """

    def analyze_line_movement(
        self,
        movement: Optional[LineMovement],
        your_projection: float
    ) -> Tuple[float, str]:
        """
        Calculate additional edge from line movement

        Returns:
            (edge_adjustment, reasoning)
        """
        if not movement:
            return 0.0, ""

        line_diff = movement.current_line - movement.opening_line
        proj_vs_opening = your_projection - movement.opening_line
        proj_vs_current = your_projection - movement.current_line

        edge = 0.0
        reasoning = ""

        # Early sharp move in your direction (good sign)
        if movement.hours_since_open < 4:
            if (line_diff > 0 and proj_vs_opening > 0) or (line_diff < 0 and proj_vs_opening < 0):
                edge = 0.02
                reasoning = "Line moved early in your direction (sharp action)"

        # Reverse line movement (possible overreaction)
        elif movement.hours_since_open > 12:
            if abs(proj_vs_current) < abs(proj_vs_opening):
                edge = 0.015
                reasoning = "Reverse line movement suggests overreaction"

        # Steam move (rapid movement in your direction)
        if abs(line_diff) >= 2.0:
            if (line_diff > 0 and proj_vs_current > 0) or (line_diff < 0 and proj_vs_current < 0):
                edge = 0.025
                reasoning = "Steam move aligns with projection"

        return edge, reasoning


class KellyBetSizing:
    """
    Kelly Criterion for optimal bet sizing

    Formula: f* = (bp - q) / b
    Where: b = net odds, p = win probability, q = loss probability
    """

    def calculate_kelly_fraction(
        self,
        win_probability: float,
        decimal_odds: float
    ) -> float:
        """Calculate optimal bet size as fraction of bankroll"""
        b = decimal_odds - 1  # Net odds
        p = win_probability
        q = 1 - p

        if b <= 0:
            return 0.0

        f_star = (b * p - q) / b

        # Use Half-Kelly for safety (industry standard)
        return max(0.0, f_star * 0.5)

    def calculate_units(
        self,
        win_probability: float,
        american_odds: int
    ) -> float:
        """
        Calculate recommended bet in units

        1 unit = 1% of bankroll typically
        Returns: Number of units (typically 0-3)
        """
        # Convert to decimal odds
        if american_odds > 0:
            decimal_odds = american_odds / 100.0 + 1
        else:
            decimal_odds = 100.0 / abs(american_odds) + 1

        kelly_fraction = self.calculate_kelly_fraction(win_probability, decimal_odds)

        # Convert to units (1% of bankroll = 1 unit)
        units = kelly_fraction * 100

        return round(units, 2)


class VarianceCalculator:
    """
    Calculate game-specific variance for EV calculations

    Different games have different volatility based on:
    - Pace (faster pace = more variance)
    - Team consistency (variance in recent scores)
    - Projected total (higher totals = more variance)
    - Schedule fatigue (B2B, travel = more variance)
    - Matchup characteristics
    """

    # Base variance for NBA totals (from historical MAD)
    BASE_VARIANCE = 13.5

    # League average pace for normalization
    LEAGUE_AVG_PACE = 100.0

    def calculate_adaptive_variance(
        self,
        home_stats: 'AdvancedTeamStats',
        away_stats: 'AdvancedTeamStats',
        projected_total: float,
        home_schedule: Optional['ScheduleInfo'] = None,
        away_schedule: Optional['ScheduleInfo'] = None
    ) -> float:
        """
        Calculate game-specific variance based on matchup characteristics

        Args:
            home_stats: Home team's advanced stats
            away_stats: Away team's advanced stats
            projected_total: Projected total points for the game
            home_schedule: Optional schedule info for home team
            away_schedule: Optional schedule info for away team

        Returns:
            Adaptive variance value for this specific game
        """
        variance = self.BASE_VARIANCE
        adjustments = []

        # 1. Pace Impact: Higher pace = more possessions = more variance
        pace_adjustment = self._calculate_pace_variance(home_stats, away_stats)
        variance += pace_adjustment
        if abs(pace_adjustment) > 0.5:
            avg_pace = (home_stats.pace + away_stats.pace) / 2
            adjustments.append(f"Pace {avg_pace:.1f} ({pace_adjustment:+.1f})")

        # 2. Consistency Impact: More variance in recent scores = higher uncertainty
        consistency_adjustment = self._calculate_consistency_variance(
            home_stats, away_stats
        )
        variance += consistency_adjustment
        if abs(consistency_adjustment) > 0.5:
            adjustments.append(f"Consistency ({consistency_adjustment:+.1f})")

        # 3. Total Impact: Higher projected totals = more room for variance
        total_adjustment = self._calculate_total_variance(projected_total)
        variance += total_adjustment
        if abs(total_adjustment) > 0.5:
            adjustments.append(f"Total {projected_total:.1f} ({total_adjustment:+.1f})")

        # 4. Schedule Fatigue: Tired teams = more unpredictable
        fatigue_adjustment = self._calculate_fatigue_variance(
            home_schedule, away_schedule
        )
        variance += fatigue_adjustment
        if abs(fatigue_adjustment) > 0.5:
            adjustments.append(f"Fatigue ({fatigue_adjustment:+.1f})")

        # 5. Youth/Experience Impact: Younger teams = more variance
        youth_adjustment = self._calculate_youth_variance(home_stats, away_stats)
        variance += youth_adjustment
        if abs(youth_adjustment) > 0.5:
            adjustments.append(f"Youth ({youth_adjustment:+.1f})")

        # Log the variance calculation for debugging
        if adjustments:
            logger.debug(
                f"Variance calculation: Base {self.BASE_VARIANCE} -> "
                f"Final {variance:.1f} | Adjustments: {', '.join(adjustments)}"
            )

        # Clamp variance to reasonable bounds (8 to 20 points SD)
        return max(8.0, min(20.0, variance))

    def _calculate_pace_variance(
        self,
        home_stats: 'AdvancedTeamStats',
        away_stats: 'AdvancedTeamStats'
    ) -> float:
        """
        Higher pace games have more variance

        Formula: variance *= (pace / 100.0) * 1.2
        """
        home_pace = home_stats.pace or self.LEAGUE_AVG_PACE
        away_pace = away_stats.pace or self.LEAGUE_AVG_PACE
        avg_pace = (home_pace + away_pace) / 2

        # Pace factor: games 10% faster than average get ~10% more variance
        pace_factor = (avg_pace / self.LEAGUE_AVG_PACE)

        # Adjustment relative to base variance
        # Base variance is 13.5, so we add/subtract from that
        adjustment = (pace_factor - 1.0) * self.BASE_VARIANCE * 0.8

        return adjustment

    def _calculate_consistency_variance(
        self,
        home_stats: 'AdvancedTeamStats',
        away_stats: 'AdvancedTeamStats'
    ) -> float:
        """
        Calculate variance based on team consistency

        More volatility in recent scores = higher game variance
        """
        home_std = self._calculate_score_std(home_stats)
        away_std = self._calculate_score_std(away_stats)

        # Average standard deviation
        avg_std = (home_std + away_std) / 2

        # NBA teams typically have 10-15 point std dev in scoring
        # If teams are more volatile, increase game variance
        # Expected std is ~12, so deviation from that drives adjustment
        consistency_factor = (avg_std - 12.0) / 3.0  # Normalize
        adjustment = consistency_factor * 2.0  # Scale to points

        return adjustment

    def _calculate_score_std(self, stats: 'AdvancedTeamStats') -> float:
        """Calculate standard deviation of recent scores"""
        if not stats.last_5_points_scored or len(stats.last_5_points_scored) < 2:
            return 12.0  # Default league average

        scores = stats.last_5_points_scored
        n = len(scores)
        mean = sum(scores) / n
        variance = sum((x - mean) ** 2 for x in scores) / n

        return math.sqrt(variance)

    def _calculate_total_variance(self, projected_total: float) -> float:
        """
        Higher projected totals have more variance

        A 240-point game has more room for error than a 200-point game
        """
        # Average NBA total is ~225
        avg_total = 225.0

        # For every 10 points above average, add 0.5 points variance
        diff = projected_total - avg_total
        adjustment = (diff / 10.0) * 0.5

        return adjustment

    def _calculate_fatigue_variance(
        self,
        home_schedule: Optional['ScheduleInfo'],
        away_schedule: Optional['ScheduleInfo']
    ) -> float:
        """
        Tired teams lead to more unpredictable games

        Back-to-backs, travel, time zone changes increase variance
        """
        adjustment = 0.0

        if not home_schedule or not away_schedule:
            return adjustment

        # Check for back-to-backs
        if home_schedule.is_back_to_back:
            adjustment += 1.0
        if away_schedule.is_back_to_back:
            adjustment += 1.0

        # Check for 3 in 4 nights (even more fatigue)
        if home_schedule.is_third_in_4_days:
            adjustment += 0.5
        if away_schedule.is_third_in_4_days:
            adjustment += 0.5

        # Time zone changes increase unpredictability
        adjustment += abs(home_schedule.time_zone_changes) * 0.3
        adjustment += abs(away_schedule.time_zone_changes) * 0.3

        return adjustment

    def _calculate_youth_variance(
        self,
        home_stats: 'AdvancedTeamStats',
        away_stats: 'AdvancedTeamStats'
    ) -> float:
        """
        Younger, less experienced teams are more volatile

        Using games_played as a proxy (early season = less data)
        """
        home_games = home_stats.games_played
        away_games = away_stats.games_played
        avg_games = (home_games + away_games) / 2

        # Early season (games < 20) has more variance
        # As season progresses, teams stabilize
        if avg_games < 10:
            return 2.0  # Very early season - high variance
        elif avg_games < 20:
            return 1.0  # Still forming
        elif avg_games < 40:
            return 0.5  # Stabilizing
        else:
            return 0.0  # Established patterns


class EnhancedEVCalculator:
    """
    Enhanced EV calculator with better probability modeling

    Improvements:
    - Model-specific variance instead of fixed SD
    - Proper vig adjustment
    - Kelly Criterion sizing
    - Line movement analysis
    - More realistic confidence thresholds
    - Configurable market efficiency factor
    - Dynamic adjustment based on line movement
    - Adaptive game-specific variance calculation
    """

    def __init__(self, min_ev_threshold: float = 0.015):
        """
        Args:
            min_ev_threshold: Minimum EV to recommend (default 1.5%, more conservative)
        """
        self.min_ev_threshold = min_ev_threshold

        # Market efficiency settings (defaults - can be overridden via config)
        # NBA markets are highly efficient - model gets 25%, market gets 75%
        self.base_market_efficiency = 0.25
        self.min_win_prob = 0.42
        self.max_win_prob = 0.58

        # Model variance (should be calculated from backtesting)
        # NBA totals typically have MAD of ~11.5 points
        self.historical_mad = 11.5
        self.model_variance = 13.5

        # Line movement analyzer
        self.line_analyzer = LineMovementAnalyzer()

        # Kelly calculator
        self.kelly = KellyBetSizing()

        # Variance calculator for adaptive game-specific variance
        self.variance_calc = VarianceCalculator()

    def calculate_totals_ev(
        self,
        projection: Projection,
        odds: OddsLine,
        min_confidence: float = 0.525,  # More conservative (breakeven)
        line_movement: Optional[LineMovement] = None,
        home_stats: Optional['AdvancedTeamStats'] = None,
        away_stats: Optional['AdvancedTeamStats'] = None,
        home_schedule: Optional['ScheduleInfo'] = None,
        away_schedule: Optional['ScheduleInfo'] = None
    ) -> List[EnhancedBetRecommendation]:
        """
        Calculate EV for over/under bets with enhancements

        Args:
            projection: Game projection from analysis
            odds: Current betting odds
            min_confidence: Minimum win probability (default 52.5% = breakeven)
            line_movement: Optional line movement data
            home_stats: Optional home team stats for adaptive variance
            away_stats: Optional away team stats for adaptive variance
            home_schedule: Optional home schedule info for adaptive variance
            away_schedule: Optional away schedule info for adaptive variance

        Returns:
            List of enhanced bet recommendations
        """
        recommendations = []

        if not odds.total_line:
            logger.warning(f"No total line available for game {projection.game_id}")
            return recommendations

        projected_total = projection.projected_total
        line = odds.total_line
        diff = projected_total - line

        # Calculate adaptive variance if team stats provided
        if home_stats and away_stats:
            variance = self.variance_calc.calculate_adaptive_variance(
                home_stats, away_stats, projected_total, home_schedule, away_schedule
            )
            logger.debug(f"Using adaptive variance {variance:.1f} for game {projection.game_id}")
        else:
            variance = self.model_variance

        # Calculate line movement edge
        line_move_edge, line_move_reasoning = self.line_analyzer.analyze_line_movement(
            line_movement, projected_total
        )

        # Calculate win probabilities with adaptive variance
        # Confidence already baked into projection, no double-adjustment
        over_win_prob = self._calculate_win_probability_enhanced(
            diff, projection, line_movement, variance
        )
        under_win_prob = 1 - over_win_prob

        # Add line movement edge
        over_win_prob += line_move_edge
        under_win_prob -= line_move_edge

        # Calculate OVER bet EV
        if odds.over_odds:
            over_ev = self._calculate_ev(over_win_prob, odds.over_odds)

            over_reasoning = (
                f"Projected: {projected_total} vs Line: {line} (Diff: {diff:+.1f}). "
                f"Win Prob: {over_win_prob:.1%}, EV: {over_ev:.2%}. {line_move_reasoning}"
            )

            if over_ev > self.min_ev_threshold and over_win_prob >= min_confidence:
                if not self._validate_ev_result(over_ev, over_win_prob, odds.over_odds, projection.game_id):
                    logger.warning(f"Skipping suspicious OVER bet: {projection.game_id}")
                else:
                    units = self.kelly.calculate_units(over_win_prob, odds.over_odds)

                    recommendations.append(EnhancedBetRecommendation(
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
                    generated_at=datetime.now(),
                    units=units,
                    line_movement_edge=line_move_edge
                ))
                logger.info(f"Found +EV OVER: {line} / {odds.over_odds} "
                          f"(Proj: {projected_total}, EV: {over_ev:.2%}, Units: {units})")

        # Calculate UNDER bet EV
        if odds.under_odds:
            under_ev = self._calculate_ev(under_win_prob, odds.under_odds)

            under_reasoning = (
                f"Projected: {projected_total} vs Line: {line} (Diff: {diff:+.1f}). "
                f"Win Prob: {under_win_prob:.1%}, EV: {under_ev:.2%}. {line_move_reasoning}"
            )

            if under_ev > self.min_ev_threshold and under_win_prob >= min_confidence:
                if not self._validate_ev_result(under_ev, under_win_prob, odds.under_odds, projection.game_id):
                    logger.warning(f"Skipping suspicious UNDER bet: {projection.game_id}")
                else:
                    units = self.kelly.calculate_units(under_win_prob, odds.under_odds)

                    recommendations.append(EnhancedBetRecommendation(
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
                    generated_at=datetime.now(),
                    units=units,
                    line_movement_edge=line_move_edge
                ))
                logger.info(f"Found +EV UNDER: {line} / {odds.under_odds} "
                          f"(Proj: {projected_total}, EV: {under_ev:.2%}, Units: {units})")

        return recommendations

    def _calculate_win_probability_enhanced(
        self,
        diff: float,
        projection: Projection,
        line_movement: Optional[LineMovement] = None,
        variance: Optional[float] = None
    ) -> float:
        """
        Calculate win probability using adaptive model variance

        Confidence is already baked into the projection quality,
        so we use variance (fixed or adaptive) and market efficiency adjustment.

        Args:
            diff: Difference between projection and line
            projection: Game projection
            line_movement: Optional line movement for dynamic adjustment
            variance: Optional game-specific variance (uses base if not provided)

        Returns:
            Adjusted win probability (clamped to configured range)
        """
        # Use adaptive variance if provided, otherwise use base model variance
        sd = variance if variance is not None else self.model_variance

        # Calculate z-score
        z = diff / sd

        # Use error function for normal CDF
        cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))

        # Dynamic market efficiency adjustment based on line movement
        market_efficiency_factor = self._get_dynamic_market_efficiency(
            diff, line_movement
        )

        adjusted_prob = 0.5 + (cdf - 0.5) * market_efficiency_factor

        # Clamp to configured range (allows for stronger edges when confident)
        return max(self.min_win_prob, min(self.max_win_prob, adjusted_prob))

    def _get_dynamic_market_efficiency(
        self,
        diff: float,
        line_movement: Optional[LineMovement]
    ) -> float:
        """
        Calculate dynamic market efficiency factor based on line movement

        - Higher (0.50) when line movement agrees with projection
        - Lower (0.30) when line movement disagrees
        - Base (0.40) for no line movement or neutral

        Args:
            diff: Difference between projection and current line
            line_movement: Optional line movement data

        Returns:
            Market efficiency factor to apply
        """
        factor = self.base_market_efficiency

        if not line_movement:
            return factor

        line_diff = line_movement.current_line - line_movement.opening_line

        # Line moved in same direction as projection (increase confidence)
        if (line_diff > 0 and diff > 0) or (line_diff < 0 and diff < 0):
            return factor + 0.10

        # Line moved opposite to projection (decrease confidence)
        if (line_diff > 0 and diff < 0) or (line_diff < 0 and diff > 0):
            return factor - 0.10

        return factor

    def _calculate_ev(self, win_probability: float, american_odds: int) -> float:
        """Calculate Expected Value"""
        stake = 100

        if american_odds > 0:
            profit = american_odds
        else:
            profit = stake * (100 / abs(american_odds))

        ev = (win_probability * profit) - ((1 - win_probability) * stake)
        return ev / stake


    def _validate_ev_result(self, ev: float, win_probability: float, american_odds: int, game_id: str = "") -> bool:
        '''
        Sanity check for EV calculations to catch impossible values.

        EV over 20% is extremely rare and likely indicates bad data.

        Args:
            ev: Calculated expected value
            win_probability: Win probability used
            american_odds: American odds used
            game_id: Optional game ID for logging

        Returns:
            True if EV is reasonable, False if suspicious
        '''
        if ev > 0.20:  # 20% EV threshold
            logging.error(
                f"SUSPICIOUS EV DETECTED: {ev:.2%} for game {game_id}. "
                f"Win Prob: {win_probability:.1%}, Odds: {american_odds}. "
                f"This is likely bad data - rejecting this bet recommendation."
            )
            return False

        # Also flag EV over 15% as unusual
        if ev > 0.15:
            logging.warning(
                f"Unusually high EV detected: {ev:.2%} for game {game_id}. "
                f"Win Prob: {win_probability:.1%}, Odds: {american_odds}. "
                f"Verify odds data quality."
            )

        return True


    def calculate_implied_probability_after_vig(
        self,
        over_odds: int,
        under_odds: int
    ) -> Tuple[float, float]:
        """
        Calculate true implied probabilities after removing vig

        This is the bookmaker's actual probability assessment
        """
        # Convert to decimal probabilities
        if over_odds > 0:
            over_prob = 100 / (over_odds + 100)
        else:
            over_prob = abs(over_odds) / (abs(over_odds) + 100)

        if under_odds > 0:
            under_prob = 100 / (under_odds + 100)
        else:
            under_prob = abs(under_odds) / (abs(under_odds) + 100)

        # Remove vig (normalize to sum to 1)
        total_prob = over_prob + under_prob
        true_over_prob = over_prob / total_prob if total_prob > 0 else 0.5
        true_under_prob = under_prob / total_prob if total_prob > 0 else 0.5

        return true_over_prob, true_under_prob

    def calculate_spreads_ev(
        self,
        home_projected_score: float,
        away_projected_score: float,
        odds: OddsLine,
        confidence: float,
        min_confidence: float = 0.525,
        line_movement: Optional[LineMovement] = None,
        home_stats: Optional['AdvancedTeamStats'] = None,
        away_stats: Optional['AdvancedTeamStats'] = None,
        home_schedule: Optional['ScheduleInfo'] = None,
        away_schedule: Optional['ScheduleInfo'] = None
    ) -> List[EnhancedBetRecommendation]:
        """
        Calculate EV for spread bets (home/away)

        Args:
            home_projected_score: Projected score for home team
            away_projected_score: Projected score for away team
            odds: Current betting odds (must include spread data)
            confidence: Projection confidence (0-1)
            min_confidence: Minimum win probability (default 52.5%)
            line_movement: Optional line movement data
            home_stats: Optional home team stats for adaptive variance
            away_stats: Optional away team stats for adaptive variance
            home_schedule: Optional home schedule info for adaptive variance
            away_schedule: Optional away schedule info for adaptive variance

        Returns:
            List of enhanced bet recommendations for spreads
        """
        recommendations = []

        if not odds.home_spread or not odds.away_spread:
            logger.warning(f"No spread data available for game {odds.game_id}")
            return recommendations

        # Calculate projected margin (home - away)
        projected_margin = home_projected_score - away_projected_score
        projected_total = home_projected_score + away_projected_score

        # For home bet: we need home to win by more than the spread
        # Line is negative when home is favored
        home_line = -odds.home_spread  # Convert to negative for favorite
        away_line = odds.away_spread    # Positive for underdog

        # Calculate win probabilities
        # Home covers if: (home_score - away_score) > home_spread
        # Which is: projected_margin > home_spread

        # For spread bets:
        # - If home is favored by 5.5 points: home_spread = 5.5 (stored as positive)
        # - Home covers if home wins by MORE than 5.5 points
        # - Away covers if away wins OR home wins by LESS than 5.5 points

        # Home covers if projected_margin > home_spread
        home_diff = projected_margin - odds.home_spread

        # Away covers if -projected_margin + away_spread > 0
        # Or: away_spread > projected_margin
        away_diff = odds.away_spread - projected_margin

        # Calculate adaptive variance if team stats provided
        if home_stats and away_stats:
            spread_variance = self.variance_calc.calculate_adaptive_variance(
                home_stats, away_stats, projected_total, home_schedule, away_schedule
            )
            logger.debug(f"Using adaptive variance {spread_variance:.1f} for spreads in game {odds.game_id}")
        else:
            spread_variance = self.model_variance

        # Home win probability (no double-adjustment - confidence already in projection)
        home_z = home_diff / spread_variance
        home_win_prob = 0.5 * (1 + math.erf(home_z / math.sqrt(2)))

        # Away win probability (no double-adjustment - confidence already in projection)
        away_z = away_diff / spread_variance
        away_win_prob = 0.5 * (1 + math.erf(away_z / math.sqrt(2)))

        # Dynamic market efficiency adjustment for spreads
        home_efficiency = self._get_dynamic_market_efficiency(home_diff, line_movement)
        away_efficiency = self._get_dynamic_market_efficiency(away_diff, line_movement)

        home_win_prob = 0.5 + (home_win_prob - 0.5) * home_efficiency
        away_win_prob = 0.5 + (away_win_prob - 0.5) * away_efficiency

        # Clamp to configured range (allows for stronger edges when confident)
        home_win_prob = max(self.min_win_prob, min(self.max_win_prob, home_win_prob))
        away_win_prob = max(self.min_win_prob, min(self.max_win_prob, away_win_prob))

        # Calculate line movement edge
        line_move_edge, line_move_reasoning = self.line_analyzer.analyze_line_movement(
            line_movement, projected_margin
        )

        # Add line movement edge to probabilities
        home_win_prob += line_move_edge
        away_win_prob -= line_move_edge

        # Calculate HOME spread bet EV
        if odds.home_spread_odds:
            home_ev = self._calculate_ev(home_win_prob, odds.home_spread_odds)

            home_reasoning = (
                f"Projected Margin: {projected_margin:+.1f} vs Line: {-home_line:.1f}. "
                f"Win Prob: {home_win_prob:.1%}, EV: {home_ev:.2%}. {line_move_reasoning}"
            )

            if home_ev > self.min_ev_threshold and home_win_prob >= min_confidence:
                if not self._validate_ev_result(home_ev, home_win_prob, odds.home_spread_odds, odds.game_id):
                    logger.warning(f"Skipping suspicious HOME spread bet: {odds.game_id}")
                else:
                    units = self.kelly.calculate_units(home_win_prob, odds.home_spread_odds)

                    recommendations.append(EnhancedBetRecommendation(
                    game_id=odds.game_id,
                    sport=odds.sport,
                    bet_type=BetType.SPREAD,
                    side=BetSide.HOME,
                    line=-home_line,  # Negative for home favorite
                    odds=odds.home_spread_odds,
                    projected_value=projected_margin,
                    ev=home_ev,
                    win_probability=home_win_prob,
                    confidence=confidence,
                    reasoning=home_reasoning,
                    generated_at=datetime.now(),
                    units=units,
                    line_movement_edge=line_move_edge
                ))
                logger.info(f"Found +EV HOME spread: {-home_line:.1f} / {odds.home_spread_odds} "
                          f"(Proj Margin: {projected_margin:+.1f}, EV: {home_ev:.2%}, Units: {units})")

        # Calculate AWAY spread bet EV
        if odds.away_spread_odds:
            away_ev = self._calculate_ev(away_win_prob, odds.away_spread_odds)

            away_reasoning = (
                f"Projected Margin: {projected_margin:+.1f} vs Line: {away_line:.1f}. "
                f"Win Prob: {away_win_prob:.1%}, EV: {away_ev:.2%}. {line_move_reasoning}"
            )

            if away_ev > self.min_ev_threshold and away_win_prob >= min_confidence:
                if not self._validate_ev_result(away_ev, away_win_prob, odds.away_spread_odds, odds.game_id):
                    logger.warning(f"Skipping suspicious AWAY spread bet: {odds.game_id}")
                else:
                    units = self.kelly.calculate_units(away_win_prob, odds.away_spread_odds)

                    recommendations.append(EnhancedBetRecommendation(
                    game_id=odds.game_id,
                    sport=odds.sport,
                    bet_type=BetType.SPREAD,
                    side=BetSide.AWAY,
                    line=away_line,
                    odds=odds.away_spread_odds,
                    projected_value=-projected_margin,  # Store as away's perspective
                    ev=away_ev,
                    win_probability=away_win_prob,
                    confidence=confidence,
                    reasoning=away_reasoning,
                    generated_at=datetime.now(),
                    units=units,
                    line_movement_edge=line_move_edge
                ))
                logger.info(f"Found +EV AWAY spread: {away_line:.1f} / {odds.away_spread_odds} "
                          f"(Proj Margin: {projected_margin:+.1f}, EV: {away_ev:.2%}, Units: {units})")

        return recommendations
