"""
Projection models for calculating game totals
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math

from ..data.models import Game, TeamStats, Projection, SportType

logger = logging.getLogger(__name__)


class ProjectionModel:
    """Base class for projection models"""

    def __init__(self, config: dict = None):
        self.config = config or {}

    def project_game(self, game: Game, home_stats: TeamStats, away_stats: TeamStats) -> Projection:
        """Project the outcome of a game"""
        raise NotImplementedError


class NBATotalsModel(ProjectionModel):
    """
    NBA totals projection model using team efficiency and pace

    Methodology:
    1. Calculate each team's expected points based on offense vs defense
    2. Adjust for pace of play
    3. Apply home court advantage
    4. Account for recent form
    """

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.pace_weight = config.get('pace_weight', 0.8) if config else 0.8
        self.offense_weight = config.get('offense_weight', 0.5) if config else 0.5
        self.defense_weight = config.get('defense_weight', 0.5) if config else 0.5
        self.home_court_advantage = config.get('home_court_advantage', 3.0) if config else 3.0

        # League averages for normalization
        self.league_avg_pace = 100.0
        self.league_avg_pts = 115.0

    def project_game(
        self,
        game: Game,
        home_stats: TeamStats,
        away_stats: TeamStats,
        league_avg_pace: float = 100.0,
        league_avg_pts: float = 115.0
    ) -> Projection:
        """
        Project the total score for an NBA game

        Args:
            game: The game to project
            home_stats: Home team statistics
            away_stats: Away team statistics
            league_avg_pace: League average pace factor
            league_avg_pts: League average points per game

        Returns:
            Projection with projected scores and total
        """
        # Calculate expected pace for this game
        game_pace = self._calculate_game_pace(home_stats, away_stats, league_avg_pace)

        # Calculate expected points for each team
        home_projected = self._calculate_team_points(
            home_stats, away_stats, is_home=True, game_pace=game_pace, league_avg=league_avg_pts
        )

        away_projected = self._calculate_team_points(
            away_stats, home_stats, is_home=False, game_pace=game_pace, league_avg=league_avg_pts
        )

        # Apply recent form adjustment
        home_projected = self._adjust_for_recent_form(home_projected, home_stats)
        away_projected = self._adjust_for_recent_form(away_projected, away_stats)

        projected_total = home_projected + away_projected

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(home_stats, away_stats)

        return Projection(
            game_id=game.game_id,
            sport=game.sport,
            projected_home_score=round(home_projected, 1),
            projected_away_score=round(away_projected, 1),
            projected_total=round(projected_total, 1),
            confidence=round(confidence, 3),
            model_version="nba_totals_v1.0"
        )

    def _calculate_game_pace(self, home_stats: TeamStats, away_stats: TeamStats, league_avg: float) -> float:
        """
        Calculate the expected pace for a game

        Pace is the average number of possessions per game.
        Faster pace = more possessions = higher totals
        """
        home_pace = home_stats.pace or league_avg
        away_pace = away_stats.pace or league_avg

        # Average the two teams' paces
        game_pace = (home_pace + away_pace) / 2

        # Apply pace weight (how much pace affects scoring)
        pace_factor = (game_pace / league_avg) ** self.pace_weight

        return pace_factor

    def _calculate_team_points(
        self,
        team_stats: TeamStats,
        opp_stats: TeamStats,
        is_home: bool,
        game_pace: float,
        league_avg: float
    ) -> float:
        """
        Calculate expected points for a team

        Method: Blend of what team usually scores and what opponent usually allows
        """
        # Team's offensive strength
        offensive_strength = team_stats.avg_points_scored / league_avg

        # Opponent's defensive weakness (higher allowed = weaker defense)
        defensive_weakness = opp_stats.avg_points_allowed / league_avg

        # Blend the two
        expected_efficiency = (
            (offensive_strength * self.offense_weight) +
            (defensive_weakness * self.defense_weight)
        ) * league_avg

        # Apply pace adjustment
        expected_points = expected_efficiency * game_pace

        # Apply home court advantage
        if is_home:
            expected_points += self.home_court_advantage / 2
        else:
            expected_points -= self.home_court_advantage / 2

        return expected_points

    def _adjust_for_recent_form(self, projected_points: float, stats: TeamStats) -> float:
        """Adjust projection based on recent form (last 5 games)"""
        if not stats.last_5_points_scored or len(stats.last_5_points_scored) == 0:
            return projected_points

        # Calculate recent average
        recent_avg = sum(stats.last_5_points_scored) / len(stats.last_5_points_scored)

        # Calculate season average
        season_avg = stats.avg_points_scored

        # If team is playing better than season average, boost projection
        # If playing worse, reduce projection
        form_adjustment = (recent_avg - season_avg) * 0.3  # 30% weight on recent form

        return projected_points + form_adjustment

    def _calculate_confidence(self, home_stats: TeamStats, away_stats: TeamStats) -> float:
        """
        Calculate confidence in the projection

        Higher confidence when:
        - More games played (better sample size)
        - Consistent performance (low variance)
        """
        # Base confidence on games played
        games_factor = min(home_stats.games_played, away_stats.games_played) / 82.0

        # Start with base confidence
        confidence = 0.5 + (games_factor * 0.3)

        # Boost if both teams have 20+ games
        if home_stats.games_played >= 20 and away_stats.games_played >= 20:
            confidence += 0.1

        return min(confidence, 0.85)  # Max 85% confidence


class SimpleTotalsModel(ProjectionModel):
    """
    Simplified model for sports without detailed stats

    Uses basic averages and league-wide regression effects
    """

    def project_game(
        self,
        game: Game,
        home_stats: TeamStats,
        away_stats: TeamStats,
        league_avg_total: float = 200.0
    ) -> Projection:
        """Simple projection based on scoring averages"""
        home_projected = (
            home_stats.avg_points_scored + away_stats.avg_points_allowed
        ) / 2

        away_projected = (
            away_stats.avg_points_scored + home_stats.avg_points_allowed
        ) / 2

        projected_total = home_projected + away_projected

        # Regression toward league mean
        regressed_total = (projected_total + league_avg_total) / 2

        return Projection(
            game_id=game.game_id,
            sport=game.sport,
            projected_home_score=round(home_projected, 1),
            projected_away_score=round(away_projected, 1),
            projected_total=round(regressed_total, 1),
            confidence=0.5,  # Lower confidence for simple model
            model_version="simple_totals_v1.0"
        )


def create_projection_model(sport: SportType, config: dict = None) -> ProjectionModel:
    """Factory function to create appropriate projection model for a sport"""
    if sport == SportType.NBA:
        return NBATotalsModel(config)
    else:
        return SimpleTotalsModel(config)
