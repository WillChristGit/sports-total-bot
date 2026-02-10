"""
Enhanced projection models for calculating game totals - V2

Improvements from V1:
- Uses offensive/defensive rating (per 100 possessions) instead of raw PPG
- Adds schedule fatigue adjustments (rest days, back-to-back, travel)
- Adds exponential decay for recent form
- Adds Four Factors analysis (eFG%, TOV%, ORB%, FTR)
- Better confidence modeling
- Injury impact adjustments (NEW)
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math
from dataclasses import dataclass

from ..data.models import Game, TeamStats, Projection, SportType

logger = logging.getLogger(__name__)


@dataclass
class InjuryImpact:
    """Injury impact data for a game"""
    home_offensive_impact: float = 0.0
    home_defensive_impact: float = 0.0
    away_offensive_impact: float = 0.0
    away_defensive_impact: float = 0.0
    pace_impact: float = 0.0
    significant_injuries: List[str] = None

    def __post_init__(self):
        if self.significant_injuries is None:
            self.significant_injuries = []

    @property
    def total_impact(self) -> float:
        """Total impact on game total"""
        return (self.home_offensive_impact + self.away_offensive_impact +
                self.home_defensive_impact + self.away_defensive_impact)


@dataclass
class ScheduleInfo:
    """Schedule context for fatigue analysis"""
    last_game_date: Optional[datetime] = None
    days_rest: int = 0
    is_back_to_back: bool = False
    is_third_in_4_days: bool = False
    travel_distance_miles: Optional[float] = None
    time_zone_changes: int = 0


@dataclass
class AdvancedTeamStats(TeamStats):
    """Extended stats with Four Factors and efficiency metrics"""
    # Efficiency metrics (points per 100 possessions)
    offensive_rating: float = 110.0  # Points per 100 possessions
    defensive_rating: float = 110.0  # Points allowed per 100 possessions

    # Four Factors
    efg_pct: float = 0.500  # Effective Field Goal %
    tov_pct: float = 0.140  # Turnover rate
    orb_pct: float = 0.250  # Offensive rebounding %
    ft_rate: float = 0.200  # Free throw rate

    # Pace (possessions per game)
    pace: float = 100.0

    # Pace allowed (possessions per game opponents average against this team)
    pace_allowed: Optional[float] = None


class FatigueCalculator:
    """
    Calculate fatigue impacts on game totals

    Research-backed values:
    - Back-to-back: -1.8 points impact
    - 3 in 4 nights: -2.5 points impact
    - Travel: -0.5 points per 1000 miles
    - Time zone change: -0.8 points per zone
    """

    B2B_PENALTY = -1.8
    THIRD_IN_4_PENALTY = -2.5
    TRAVEL_PENALTY_PER_1000 = -0.5
    TZ_CHANGE_PENALTY = -0.8
    REST_ADVANTAGE_PER_DAY = 0.6

    def calculate_fatigue_impact(
        self,
        home_schedule: Optional[ScheduleInfo],
        away_schedule: Optional[ScheduleInfo]
    ) -> Tuple[float, float]:
        """
        Calculate fatigue impact for both teams

        Returns:
            (home_fatigue_impact, away_fatigue_impact) in points
        """
        home_impact = 0.0
        away_impact = 0.0

        if not home_schedule or not away_schedule:
            return home_impact, away_impact

        # Back-to-back penalties
        if home_schedule.is_back_to_back:
            home_impact += self.B2B_PENALTY
        if away_schedule.is_back_to_back:
            away_impact += self.B2B_PENALTY

        # 3 in 4 nights
        if home_schedule.is_third_in_4_days:
            home_impact += self.THIRD_IN_4_PENALTY
        if away_schedule.is_third_in_4_days:
            away_impact += self.THIRD_IN_4_PENALTY

        # Travel fatigue (away team only usually)
        if away_schedule.travel_distance_miles:
            away_impact += (
                away_schedule.travel_distance_miles / 1000.0 * self.TRAVEL_PENALTY_PER_1000
            )

        # Time zone changes
        away_impact += away_schedule.time_zone_changes * self.TZ_CHANGE_PENALTY

        # Rest advantage
        rest_diff = home_schedule.days_rest - away_schedule.days_rest
        if rest_diff > 0:
            home_impact += rest_diff * self.REST_ADVANTAGE_PER_DAY
        elif rest_diff < 0:
            away_impact += abs(rest_diff) * self.REST_ADVANTAGE_PER_DAY

        return home_impact, away_impact


class EnhancedNBATotalsModel:
    """
    Enhanced NBA totals projection model

    Improvements over V1:
    - Uses offensive/defensive rating (efficiency metrics)
    - Four Factors analysis
    - Schedule fatigue adjustments
    - Exponential decay for recent form
    - Bayesian confidence modeling
    - Injury impact adjustments (NEW)
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Injury adjustment weights
        # How much to trust injury data vs. season stats
        self.injury_weight = config.get('injury_weight', 0.7) if config else 0.7

        # Weights for Four Factors (based on Dean Oliver's research)
        self.efg_weight = 0.40
        self.tov_weight = 0.25
        self.reb_weight = 0.20
        self.ft_weight = 0.15

        # Other weights
        self.pace_weight = config.get('pace_weight', 0.8) if config else 0.8
        self.home_court_advantage = config.get('home_court_advantage', 3.0) if config else 3.0

        # League averages (2025-26 season)
        self.league_avg_pace = 100.0
        self.league_avg_ortg = 115.0
        self.league_avg_drtg = 115.0

        # Pace model weights
        # Offensive pace preference: how much team's own pace matters
        self.offensive_pace_weight = 0.35
        # Defensive pace impact: how much opponent's defense affects pace
        self.defensive_pace_weight = 0.25
        # Matchup interaction: how styles interact
        self.matchup_pace_weight = 0.40

        # Scenario adjustments
        self.playoff_pace_modifier = -2.5  # Playoff games are slower
        self.b2b_pace_modifier = -1.2      # Back-to-back games are slower
        self.high_total_threshold = 235.0   # High totals usually indicate faster pace
        self.high_total_pace_boost = 1.5

        # Fatigue calculator
        self.fatigue_calc = FatigueCalculator()

    def project_game(
        self,
        game: Game,
        home_stats: AdvancedTeamStats,
        away_stats: AdvancedTeamStats,
        home_schedule: Optional[ScheduleInfo] = None,
        away_schedule: Optional[ScheduleInfo] = None,
        total_line: Optional[float] = None,
        is_playoff_game: bool = False,
        injury_impact: Optional[InjuryImpact] = None
    ) -> Projection:
        """
        Project the total score for an NBA game

        Args:
            game: The game to project
            home_stats: Home team statistics
            away_stats: Away team statistics
            home_schedule: Home team schedule info (for fatigue/pace)
            away_schedule: Away team schedule info (for fatigue/pace)
            total_line: The betting total line (informs pace expectation)
            is_playoff_game: Whether this is a playoff game (slower pace)
            injury_impact: Optional injury impact data for adjustments

        Returns:
            Projection with projected scores and confidence
        """
        # Calculate game pace with all factors
        game_pace = self._calculate_game_pace(
            home_stats,
            away_stats,
            home_schedule=home_schedule,
            away_schedule=away_schedule,
            total_line=total_line,
            is_playoff_game=is_playoff_game,
            injury_impact=injury_impact
        )

        # Calculate expected points using efficiency metrics
        home_projected = self._calculate_team_points_enhanced(
            home_stats, away_stats, is_home=True, game_pace=game_pace
        )

        away_projected = self._calculate_team_points_enhanced(
            away_stats, home_stats, is_home=False, game_pace=game_pace
        )

        # Apply fatigue adjustments
        if home_schedule and away_schedule:
            home_fatigue, away_fatigue = self.fatigue_calc.calculate_fatigue_impact(
                home_schedule, away_schedule
            )
            # Fatigue affects offense more than defense
            home_projected += home_fatigue * 0.6
            away_projected += away_fatigue * 0.6

        # Apply injury adjustments
        if injury_impact:
            home_projected, away_projected = self._apply_injury_adjustments(
                home_projected, away_projected, injury_impact
            )

            # Log significant injuries
            if injury_impact.significant_injuries:
                logger.info(f"  Injuries: {', '.join(injury_impact.significant_injuries[:3])}")

        # Apply recent form with exponential decay
        home_projected = self._adjust_for_recent_form_exponential(home_projected, home_stats)
        away_projected = self._adjust_for_recent_form_exponential(away_projected, away_stats)

        projected_total = home_projected + away_projected

        # Calculate confidence using Bayesian approach
        confidence = self._calculate_bayesian_confidence(home_stats, away_stats)

        return Projection(
            game_id=game.game_id,
            sport=game.sport,
            projected_home_score=round(home_projected, 1),
            projected_away_score=round(away_projected, 1),
            projected_total=round(projected_total, 1),
            confidence=round(confidence, 3),
            model_version="nba_totals_v2.1"  # Version bump for injury support
        )

    def _calculate_game_pace(
        self,
        home_stats: AdvancedTeamStats,
        away_stats: AdvancedTeamStats,
        home_schedule: Optional[ScheduleInfo] = None,
        away_schedule: Optional[ScheduleInfo] = None,
        total_line: Optional[float] = None,
        is_playoff_game: bool = False,
        injury_impact: Optional[InjuryImpact] = None
    ) -> float:
        """
        Calculate expected pace for the game using advanced modeling.

        The new model accounts for:
        1. Offensive pace preference (how fast each team wants to play)
        2. Defensive pace impact (how much each team's defense slows/accelerates)
        3. Matchup interactions (fast offense vs bad defense = faster pace)
        4. Scenario factors (playoffs, back-to-back, high totals)
        5. Injury impacts (stars out = slower pace)

        Returns: pace factor (multiplier for possessions)
        """
        home_pace = home_stats.pace or self.league_avg_pace
        away_pace = away_stats.pace or self.league_avg_pace

        # Apply injury pace impact
        # Stars being out typically slows the game
        if injury_impact and injury_impact.pace_impact != 0:
            pace_adjustment = injury_impact.pace_impact * self.injury_weight
            home_pace += pace_adjustment / 2
            away_pace += pace_adjustment / 2

        # Calculate pace allowed for each team
        # Pace allowed = how many possessions opponents average against this team
        home_pace_allowed = self._calculate_pace_allowed(home_stats)
        away_pace_allowed = self._calculate_pace_allowed(away_stats)

        # 1. OFFENSIVE PACE COMPONENT
        # What pace does each team prefer to play?
        offensive_component = (home_pace + away_pace) / 2

        # 2. DEFENSIVE PACE COMPONENT
        # How much pace do opponents get against each defense?
        # Good defenses often force slower pace
        defensive_component = (home_pace_allowed + away_pace_allowed) / 2

        # 3. MATCHUP INTERACTION COMPONENT
        # This is the key insight: pace depends on offensive style vs defensive style
        # Fast team vs bad defense = even faster than average
        # Slow team vs good defense = even slower than average

        # Calculate how each team's offense interacts with opponent's defense
        # Home offense vs Away defense
        home_vs_away_def = self._calculate_matchup_pace(
            offensive_pace=home_pace,
            opponent_pace_allowed=away_pace_allowed,
            offensive_rating=home_stats.offensive_rating,
            opponent_defensive_rating=away_stats.defensive_rating
        )

        # Away offense vs Home defense
        away_vs_home_def = self._calculate_matchup_pace(
            offensive_pace=away_pace,
            opponent_pace_allowed=home_pace_allowed,
            offensive_rating=away_stats.offensive_rating,
            opponent_defensive_rating=home_stats.defensive_rating
        )

        matchup_component = (home_vs_away_def + away_vs_home_def) / 2

        # Combine components with weights
        raw_game_pace = (
            offensive_component * self.offensive_pace_weight +
            defensive_component * self.defensive_pace_weight +
            matchup_component * self.matchup_pace_weight
        )

        # 4. SCENARIO ADJUSTMENTS

        # Playoff games are typically slower (more defense, fewer transition buckets)
        if is_playoff_game:
            raw_game_pace += self.playoff_pace_modifier

        # Back-to-back games are slower (fatigue reduces transition)
        if home_schedule and home_schedule.is_back_to_back:
            raw_game_pace += self.b2b_pace_modifier * 0.5
        if away_schedule and away_schedule.is_back_to_back:
            raw_game_pace += self.b2b_pace_modifier * 0.5

        # High total lines indicate faster-paced games are expected
        # This can be used as a signal that the market expects faster pace
        if total_line and total_line > self.high_total_threshold:
            raw_game_pace += self.high_total_pace_boost

        # Ensure pace stays within realistic bounds
        min_pace = 95.0
        max_pace = 105.0
        raw_game_pace = max(min_pace, min(max_pace, raw_game_pace))

        # Convert to pace factor (multiplier for possessions)
        pace_factor = (raw_game_pace / self.league_avg_pace) ** self.pace_weight

        logger.debug(
            f"Pace calculation: raw={raw_game_pace:.1f}, factor={pace_factor:.3f}, "
            f"home_pace={home_pace:.1f}, away_pace={away_pace:.1f}, "
            f"home_allowed={home_pace_allowed:.1f}, away_allowed={away_pace_allowed:.1f}"
        )

        return pace_factor

    def _calculate_pace_allowed(self, stats: AdvancedTeamStats) -> float:
        """
        Estimate the pace that opponents average against this team.

        This represents how many possessions the opponent typically gets
        when playing against this team's defense.

        If we have pace_allowed data, use it. Otherwise estimate from:
        1. The team's own pace (teams play at similar pace both ways)
        2. Adjusted by defensive quality (bad defenses give more possessions)
        """
        if stats.pace_allowed and stats.pace_allowed > 0:
            return stats.pace_allowed

        # Estimate pace allowed from defensive rating
        # Bad defenses (high drtg) tend to allow more possessions
        drtg = stats.defensive_rating or self.league_avg_drtg
        own_pace = stats.pace or self.league_avg_pace

        # Defensive efficiency ratio
        # Higher drtg = worse defense = more opponent possessions
        drtg_ratio = drtg / self.league_avg_drtg

        # Estimate: bad defenses allow ~5% more pace, good defenses ~5% less
        estimated_pace_allowed = own_pace * (1 + (drtg_ratio - 1.0) * 0.5)

        return estimated_pace_allowed

    def _calculate_matchup_pace(
        self,
        offensive_pace: float,
        opponent_pace_allowed: float,
        offensive_rating: float,
        opponent_defensive_rating: float
    ) -> float:
        """
        Calculate expected pace when an offense faces a defense.

        Key insights:
        1. Fast offenses vs bad defenses = EXPLOSIVE pace (faster than either alone)
        2. Slow offenses vs good defenses = GLACIAL pace (slower than either alone)
        3. Mismatched styles tend toward the faster pace (fast team dictates tempo)

        Formula:
        - Base expectation: average of offensive pace and defensive pace allowed
        - Offensive quality multiplier: Good offenses can impose their will more
        - Defensive quality multiplier: Bad defenses get exploited more
        """
        # Base pace expectation
        base_pace = (offensive_pace + opponent_pace_allowed) / 2

        # Offensive quality factor
        # Great offenses (high ortg) can dictate tempo more effectively
        ortg_ratio = offensive_rating / self.league_avg_ortg

        # Defensive quality factor
        # Bad defenses (high drtg) allow opponents to play faster
        drtg_ratio = opponent_defensive_rating / self.league_avg_drtg

        # Interaction effect
        # When good offense meets bad defense: pace amplifies
        # When bad offense meets good defense: pace suppresses
        quality_mismatch = (ortg_ratio - 1.0) * (drtg_ratio - 1.0)

        # The amplification factor
        # If both ratios are > 1 (good offense, bad defense): big positive boost
        # If both ratios are < 1 (bad offense, good defense): negative boost
        amplification = quality_mismatch * 10.0  # Up to +/- 5 possessions

        # Calculate matchup pace
        matchup_pace = base_pace + amplification

        return matchup_pace

    def _apply_injury_adjustments(
        self,
        home_projected: float,
        away_projected: float,
        injury_impact: InjuryImpact
    ) -> Tuple[float, float]:
        """
        Apply injury adjustments to projected scores

        Injury impacts are calculated by the injury fetcher based on:
        - Player importance (star, starter, role player)
        - Injury status (out, day-to-day, questionable)
        - Position (affects defense more for bigs)

        Args:
            home_projected: Home team projected points
            away_projected: Away team projected points
            injury_impact: Injury impact data

        Returns:
            (adjusted_home_projected, adjusted_away_projected)
        """
        # Apply offensive impact (scoring reductions)
        # Star out: -5 to -8 points
        # Starter out: -3 to -5 points
        # Role player out: -1 to -2 points
        home_projected -= injury_impact.home_offensive_impact * self.injury_weight
        away_projected -= injury_impact.away_offensive_impact * self.injury_weight

        # Apply defensive impact
        # When defenders are out, opponent scores more
        # So we subtract from our team's projection (meaning opponent adds)
        home_projected -= injury_impact.home_defensive_impact * self.injury_weight * 0.5
        away_projected -= injury_impact.away_defensive_impact * self.injury_weight * 0.5

        return home_projected, away_projected

    def _calculate_team_points_enhanced(
        self,
        team_stats: AdvancedTeamStats,
        opp_stats: AdvancedTeamStats,
        is_home: bool,
        game_pace: float
    ) -> float:
        """
        Calculate expected points using offensive/defensive rating

        Uses efficiency metrics (points per 100 possessions) instead of raw PPG
        """
        # Blend team's offensive rating with opponent's defensive rating
        team_ortg = team_stats.offensive_rating
        opp_drtg = opp_stats.defensive_rating

        # What we expect: blend of what team scores and what opponent allows
        expected_rating = (team_ortg * 0.6) + ((220 - opp_drtg) * 0.4)

        # Apply pace to get expected points
        # Expected points = (ORtg / 100) * Pace
        expected_points = (expected_rating / 100.0) * game_pace * 100

        # Apply home court advantage
        hca = self.home_court_advantage
        if is_home:
            expected_points += (hca * 0.6)
        else:
            expected_points -= (hca * 0.4)

        return expected_points

    def _adjust_for_recent_form_exponential(
        self,
        projected_points: float,
        stats: AdvancedTeamStats
    ) -> float:
        """
        Adjust projection using exponentially weighted recent form

        More recent games get higher weight
        """
        if not stats.last_5_points_scored or len(stats.last_5_points_scored) == 0:
            return projected_points

        # Calculate exponential weights (more recent = higher weight)
        n = len(stats.last_5_points_scored)
        decay_rate = 0.15
        weights = [math.exp(-decay_rate * i) for i in range(n)]
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        # Calculate weighted average (most recent is index 0)
        recent_avg = sum(
            score * weight for score, weight in zip(reversed(stats.last_5_points_scored), weights)
        )

        season_avg = stats.avg_points_scored

        # Form weight depends on sample size
        sample_size_factor = min(n / 10.0, 1.0)

        # Calculate variance for consistency
        if n > 1:
            mean = sum(stats.last_5_points_scored) / n
            variance = sum((x - mean) ** 2 for x in stats.last_5_points_scored) / n
            consistency_factor = max(0.5, 1.0 - (variance / 100.0))
        else:
            consistency_factor = 0.5

        form_weight = 0.4 * sample_size_factor * consistency_factor
        form_adjustment = (recent_avg - season_avg) * form_weight

        return projected_points + form_adjustment

    def _calculate_bayesian_confidence(
        self,
        home_stats: AdvancedTeamStats,
        away_stats: AdvancedTeamStats
    ) -> float:
        """
        Calculate confidence using Bayesian approach

        Updates confidence based on sample size and model performance
        """
        # Prior (weakly informative)
        alpha_prior = 52
        beta_prior = 48

        # Sample size (games played)
        home_games = home_stats.games_played
        away_games = away_stats.games_played
        avg_games = (home_games + away_games) / 2

        # Estimate based on sample size
        # With more data, we're more confident in our model
        sample_bonus = min(avg_games / 82.0, 1.0) * 10  # Up to 10% boost

        # Posterior confidence
        base_confidence = 0.52  # Market is efficient
        confidence = base_confidence + sample_bonus * 0.3

        # Boost if both teams have significant data
        if home_games >= 20 and away_games >= 20:
            confidence += 0.05

        return min(confidence, 0.70)  # Cap at 70% for realism


def create_enhanced_projection_model(sport: SportType, config: dict = None):
    """Factory function to create enhanced projection model"""
    if sport == SportType.NBA:
        return EnhancedNBATotalsModel(config)
    else:
        # For other sports, use simple model
        from .projections import SimpleTotalsModel
        return SimpleTotalsModel()
