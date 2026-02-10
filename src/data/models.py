"""
Data models for SportsTotalBot
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SportType(str, Enum):
    NBA = "nba"
    WNBA = "wnba"
    NCAA = "ncaab"  # NCAA Men's Basketball
    NFL = "nfl"
    MLB = "mlb"
    NHL = "nhl"


class BetType(str, Enum):
    SPREAD = "spreads"
    TOTALS = "totals"
    MONEYLINE = "h2h"


class BetSide(str, Enum):
    OVER = "over"
    UNDER = "under"
    HOME = "home"
    AWAY = "away"


@dataclass
class TeamStats:
    """Team statistics for analysis"""
    team_id: str
    team_name: str
    games_played: int

    # Offensive stats
    avg_points_scored: float
    avg_points_allowed: float
    offensive_rating: Optional[float] = None
    defensive_rating: Optional[float] = None

    # Pace/tempo
    pace: Optional[float] = None
    possessions_per_game: Optional[float] = None

    # Form
    last_5_points_scored: List[float] = None
    last_5_points_allowed: List[float] = None

    # Home/away splits
    home_points_scored: Optional[float] = None
    away_points_scored: Optional[float] = None


@dataclass
class Game:
    """Represents a scheduled game"""
    game_id: str
    sport: SportType
    home_team: str
    away_team: str
    game_time: datetime

    # Odds data
    home_team_score: Optional[int] = None
    away_team_score: Optional[int] = None
    is_completed: bool = False


@dataclass
class OddsLine:
    """Betting odds for a game"""
    game_id: str
    sport: SportType
    bet_type: BetType

    # For totals
    total_line: Optional[float] = None
    over_odds: Optional[int] = None  # American odds
    under_odds: Optional[int] = None

    # For spreads
    home_spread: Optional[float] = None
    home_spread_odds: Optional[int] = None
    away_spread: Optional[float] = None
    away_spread_odds: Optional[int] = None

    # For moneyline
    home_moneyline: Optional[int] = None
    away_moneyline: Optional[int] = None

    # Book info
    book_name: str = "consensus"
    update_time: datetime = None


@dataclass
class Projection:
    """Projected outcome from analysis"""
    game_id: str
    sport: SportType

    # Point projections
    projected_home_score: float
    projected_away_score: float
    projected_total: float

    # Confidence metrics
    confidence: float  # 0-1
    model_version: str


@dataclass
class BetRecommendation:
    """A bet recommendation with EV calculation"""
    game_id: str
    sport: SportType
    bet_type: BetType
    side: BetSide

    # The bet details
    line: float
    odds: int  # American odds

    # Analysis
    projected_value: float
    ev: float  # Expected value
    win_probability: float
    confidence: float

    # Reasoning
    reasoning: str

    # Timestamp
    generated_at: datetime = None

    # Data quality (added dynamically)
    data_quality: str = "C"  # A, B, C, D, F


@dataclass
class PickResult:
    """Result of a pick after game completion"""
    recommendation_id: str
    game_id: str
    won: bool
    actual_result: float
    line: float
    profit_loss: float

    # Recorded when
    recorded_at: datetime
