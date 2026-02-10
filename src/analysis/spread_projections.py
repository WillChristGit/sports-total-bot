"""
Spread projection models for calculating game point spreads

Uses the same efficiency metrics and team stats as the totals module
to project the margin of victory for each team.
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
import math

from ..data.models import Game, SportType
from .projections_v2 import AdvancedTeamStats, ScheduleInfo, FatigueCalculator, InjuryImpact

logger = logging.getLogger(__name__)


@dataclass
class SpreadProjection:
    """Projected outcome for point spread betting"""
    game_id: str
    sport: SportType

    # Score projections
    projected_home_score: float
    projected_away_score: float

    # The spread (positive = home favored, negative = away favored)
    projected_spread: float  # Home team margin

    # Confidence metrics
    confidence: float  # 0-1
    model_version: str

    # Component breakdown for transparency
    home_offensive_contribution: float
    home_defensive_contribution: float
    away_offensive_contribution: float
    away_defensive_contribution: float


class EnhancedNBASpreadModel:
    """
    Enhanced NBA spread projection model

    Projects the margin of victory using:
    - Offensive/defensive efficiency ratings
    - Four Factors analysis
    - Home court advantage
    - Schedule fatigue adjustments
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Weights for offensive vs defensive contribution
        self.offensive_weight = 0.6
        self.defensive_weight = 0.4

        # Home court advantage (can be configured)
        self.home_court_advantage = config.get('home_court_advantage', 3.5) if config else 3.5

        # League averages for normalization
        self.league_avg_ortg = 115.0
        self.league_avg_drtg = 115.0

        # Fatigue calculator
        self.fatigue_calc = FatigueCalculator()

    def project_game(
        self,
        game: Game,
        home_stats: AdvancedTeamStats,
        away_stats: AdvancedTeamStats,
        home_schedule: Optional[ScheduleInfo] = None,
        away_schedule: Optional[ScheduleInfo] = None,
        injury_impact: Optional[InjuryImpact] = None
    ) -> SpreadProjection:
        """
        Project the point spread for an NBA game

        Args:
            game: The game to project
            home_stats: Home team statistics
            away_stats: Away team statistics
            home_schedule: Home team schedule info
            away_schedule: Away team schedule info
            injury_impact: Optional injury impact data

        Returns:
            SpreadProjection with projected margin and confidence
        """
        # Calculate expected pace for the game (average of both teams)
        home_pace = home_stats.pace or 100.0
        away_pace = away_stats.pace or 100.0
        game_pace = (home_pace + away_pace) / 2

        # Calculate projected scores
        # Home team score = home offense vs away defense
        home_projected = self._calculate_team_score(
            home_stats, away_stats, is_home=True, game_pace=game_pace
        )

        # Away team score = away offense vs home defense
        away_projected = self._calculate_team_score(
            away_stats, home_stats, is_home=False, game_pace=game_pace
        )

        # Apply injury adjustments if available
        if injury_impact:
            home_projected -= injury_impact.home_offensive_impact * 0.7
            home_projected -= injury_impact.home_defensive_impact * 0.3
            away_projected -= injury_impact.away_offensive_impact * 0.7
            away_projected -= injury_impact.away_defensive_impact * 0.3

            # Log significant injuries
            if injury_impact.significant_injuries:
                logger.info(f"  Spread Injuries: {', '.join(injury_impact.significant_injuries[:2])}")

        # Apply fatigue adjustments
        if home_schedule and away_schedule:
            home_fatigue, away_fatigue = self.fatigue_calc.calculate_fatigue_impact(
                home_schedule, away_schedule
            )
            # Fatigue affects both offense and defense
            home_projected += home_fatigue * 0.5
            away_projected += away_fatigue * 0.5

        # Apply recent form adjustments
        home_projected = self._adjust_for_recent_form(home_projected, home_stats)
        away_projected = self._adjust_for_recent_form(away_projected, away_stats)

        # Round scores
        home_projected = round(home_projected, 1)
        away_projected = round(away_projected, 1)

        # Calculate spread (home score - away score)
        # Positive spread = home favored, Negative = away favored
        projected_spread = round(home_projected - away_projected, 1)

        # Calculate confidence
        confidence = self._calculate_confidence(home_stats, away_stats)

        # Calculate component breakdown for transparency (approximate)
        home_off_contrib = round((home_stats.offensive_rating / 100.0) * game_pace, 1)
        home_def_contrib = round(-(away_stats.offensive_rating / 100.0) * game_pace, 1)
        away_off_contrib = round((away_stats.offensive_rating / 100.0) * game_pace, 1)
        away_def_contrib = round(-(home_stats.offensive_rating / 100.0) * game_pace, 1)

        return SpreadProjection(
            game_id=game.game_id,
            sport=game.sport,
            projected_home_score=home_projected,
            projected_away_score=away_projected,
            projected_spread=projected_spread,
            confidence=round(confidence, 3),
            model_version="nba_spreads_v1.0",
            home_offensive_contribution=home_off_contrib,
            home_defensive_contribution=home_def_contrib,
            away_offensive_contribution=away_off_contrib,
            away_defensive_contribution=away_def_contrib
        )

    def _calculate_team_score(
        self,
        team_stats: AdvancedTeamStats,
        opp_stats: AdvancedTeamStats,
        is_home: bool,
        game_pace: float
    ) -> float:
        """
        Calculate expected points for a team

        Uses team's offensive rating vs opponent's defensive rating
        """
        # Team's offensive efficiency
        team_ortg = team_stats.offensive_rating

        # Opponent's defensive rating (higher = worse defense = more points allowed)
        opp_drtg = opp_stats.defensive_rating

        # Blend: what team typically scores + what opponent typically allows
        # Normalize against league average
        team_ortg_normalized = team_ortg / self.league_avg_ortg
        opp_drtg_normalized = opp_drtg / self.league_avg_drtg

        # Expected offensive rating for this matchup
        expected_ortg = (team_ortg_normalized * 0.6 + opp_drtg_normalized * 0.4) * self.league_avg_ortg

        # Convert to points: (ORtg / 100) * Pace
        expected_points = (expected_ortg / 100.0) * game_pace

        # Apply home court advantage
        if is_home:
            expected_points += (self.home_court_advantage * 0.6)
        else:
            expected_points -= (self.home_court_advantage * 0.4)

        return expected_points

    def _adjust_for_recent_form(
        self,
        projected_points: float,
        stats: AdvancedTeamStats
    ) -> float:
        """
        Adjust projection based on recent form
        """
        if not stats.last_5_points_scored or len(stats.last_5_points_scored) == 0:
            return projected_points

        # Simple average of recent games
        recent_avg = sum(stats.last_5_points_scored) / len(stats.last_5_points_scored)
        season_avg = stats.avg_points_scored

        # Form adjustment weight
        n = len(stats.last_5_points_scored)
        sample_size_factor = min(n / 10.0, 1.0)

        # Calculate variance for consistency
        if n > 1:
            mean = sum(stats.last_5_points_scored) / n
            variance = sum((x - mean) ** 2 for x in stats.last_5_points_scored) / n
            consistency_factor = max(0.5, 1.0 - (variance / 100.0))
        else:
            consistency_factor = 0.5

        form_weight = 0.3 * sample_size_factor * consistency_factor
        form_adjustment = (recent_avg - season_avg) * form_weight

        return projected_points + form_adjustment

    def _calculate_confidence(
        self,
        home_stats: AdvancedTeamStats,
        away_stats: AdvancedTeamStats
    ) -> float:
        """
        Calculate confidence in spread projection

        Spread projections are less certain than totals due to:
        - Higher variance in individual game margins
        - Luck factors (free throws, fouls, etc.)
        """
        # Base confidence (market is efficient)
        base_confidence = 0.50

        # Sample size bonus
        home_games = home_stats.games_played
        away_games = away_stats.games_played
        avg_games = (home_games + away_games) / 2

        sample_bonus = min(avg_games / 82.0, 1.0) * 8  # Up to 8% boost

        # Quality of teams (more games = more reliable stats)
        if home_games >= 20 and away_games >= 20:
            sample_bonus += 0.02

        confidence = base_confidence + sample_bonus

        # Spread confidence is lower than totals confidence
        # Cap at 60% for realism (spreads are harder to predict than totals)
        return min(confidence, 0.60)


def create_spread_projection_model(sport: SportType, config: dict = None):
    """Factory function to create spread projection model"""
    if sport == SportType.NBA:
        return EnhancedNBASpreadModel(config)
    else:
        logger.warning(f"Spread projections not implemented for {sport}")
        return None
