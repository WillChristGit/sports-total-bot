"""
Backtesting Module for SportsTotalBot

Validates model predictions against historical results to measure performance.
Provides insights into model accuracy and helps identify improvement areas.

Features:
- Load historical picks from database/CSV
- Fetch actual game results
- Compare projected vs actual totals
- Calculate: win rate, actual EV, ROI
- Break down by: confidence level, EV range, bet type, data quality
"""

import logging
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import sqlite3
import os

from ..data.models import SportType, BetType, BetSide
from ..storage.database import Database

logger = logging.getLogger(__name__)


@dataclass
class HistoricalPick:
    """A historical pick with projection and result"""
    # Pick details
    game_id: str
    date: str
    sport: str
    bet_type: str  # 'totals' or 'spreads'
    side: str      # 'over', 'under', 'home', 'away'
    line: float
    odds: int

    # Projection details
    projected_value: float
    ev: float
    win_probability: float
    confidence: float

    # Game details
    home_team: str
    away_team: str

    # Result details (if available)
    actual_result: Optional[float] = None  # Actual total or margin
    won: Optional[bool] = None
    profit_loss: Optional[float] = None

    # Data quality at time of pick
    data_quality: str = "C"

    # Reasoning
    reasoning: str = ""

    @property
    def units_won(self) -> float:
        """Calculate units won/lost (1 unit = risk amount)"""
        if self.won is None:
            return 0.0

        # Calculate profit based on American odds
        if self.odds > 0:
            profit = (self.odds / 100.0)
        else:
            profit = (100.0 / abs(self.odds))

        return profit if self.won else -1.0

    @property
    def actual_ev(self) -> float:
        """Calculate actual EV based on result"""
        if self.won is None:
            return 0.0
        return self.units_won


@dataclass
class PerformanceMetrics:
    """Overall performance metrics"""
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0  # Ties (line exactly hit)
    win_rate: float = 0.0
    expected_win_rate: float = 0.0  # Average model win probability
    total_units: float = 0.0
    roi_percent: float = 0.0
    avg_ev: float = 0.0
    actual_vs_expected: float = 0.0  # Difference between actual and expected performance


@dataclass
class BreakdownStats:
    """Breakdown statistics for a category"""
    category: str
    total_bets: int
    wins: int
    losses: int
    win_rate: float
    total_units: float
    roi_percent: float
    avg_ev: float
    avg_confidence: float


@dataclass
class BacktestReport:
    """Complete backtest report"""
    period_start: str
    period_end: str
    overall: PerformanceMetrics
    by_confidence: Dict[str, BreakdownStats]
    by_ev_range: Dict[str, BreakdownStats]
    by_bet_type: Dict[str, BreakdownStats]
    by_side: Dict[str, BreakdownStats]
    by_data_quality: Dict[str, BreakdownStats]
    best_picks: List[HistoricalPick]
    worst_picks: List[HistoricalPick]
    insights: List[str]

    def format_report(self) -> str:
        """Format the backtest report as a string"""
        lines = []
        lines.append("=" * 80)
        lines.append("SPORTSTOTALBOT - BACKTESTING REPORT")
        lines.append("=" * 80)
        lines.append(f"Period: {self.period_start} to {self.period_end}")
        lines.append("")

        # Overall Performance
        lines.append("OVERALL PERFORMANCE")
        lines.append("-" * 40)
        o = self.overall
        lines.append(f"Total Bets:        {o.total_bets}")
        lines.append(f"Wins:              {o.wins}")
        lines.append(f"Losses:            {o.losses}")
        lines.append(f"Pushes:            {o.pushes}")
        lines.append(f"Win Rate:          {o.win_rate:.1f}%")
        lines.append(f"Expected Win Rate: {o.expected_win_rate:.1f}%")
        lines.append(f"Total Units:       {o.total_units:+.2f}")
        lines.append(f"ROI:               {o.roi_percent:.1f}%")
        lines.append(f"Avg Model EV:      {o.avg_ev:.2f}%")
        lines.append("")

        # By Confidence
        lines.append("BY CONFIDENCE LEVEL")
        lines.append("-" * 40)
        for conf, stats in sorted(self.by_confidence.items(), key=lambda x: x[1].roi_percent, reverse=True):
            lines.append(f"{conf}: {stats.total_bets} bets, {stats.win_rate:.1f}% win rate, {stats.roi_percent:+.1f}% ROI")
        lines.append("")

        # By EV Range
        lines.append("BY EV RANGE")
        lines.append("-" * 40)
        for ev_range, stats in sorted(self.by_ev_range.items(), key=lambda x: x[1].roi_percent, reverse=True):
            lines.append(f"{ev_range}: {stats.total_bets} bets, {stats.win_rate:.1f}% win rate, {stats.roi_percent:+.1f}% ROI")
        lines.append("")

        # By Bet Type
        lines.append("BY BET TYPE")
        lines.append("-" * 40)
        for bet_type, stats in self.by_bet_type.items():
            lines.append(f"{bet_type.upper()}: {stats.total_bets} bets, {stats.win_rate:.1f}% win rate, {stats.roi_percent:+.1f}% ROI")
        lines.append("")

        # By Side
        lines.append("BY SIDE (OVER/UNDER)")
        lines.append("-" * 40)
        for side, stats in self.by_side.items():
            lines.append(f"{side.upper()}: {stats.total_bets} bets, {stats.win_rate:.1f}% win rate, {stats.roi_percent:+.1f}% ROI")
        lines.append("")

        # By Data Quality
        if self.by_data_quality:
            lines.append("BY DATA QUALITY")
            lines.append("-" * 40)
            for quality, stats in sorted(self.by_data_quality.items(), key=lambda x: x[0]):
                lines.append(f"Quality {quality}: {stats.total_bets} bets, {stats.win_rate:.1f}% win rate, {stats.roi_percent:+.1f}% ROI")
            lines.append("")

        # Insights
        lines.append("KEY INSIGHTS")
        lines.append("-" * 40)
        for insight in self.insights:
            lines.append(f"  - {insight}")
        lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)


class Backtester:
    """
    Backtesting engine for SportsTotalBot

    Loads historical picks, matches them with actual results,
    and calculates performance metrics.
    """

    def __init__(self, db_path: str = "data/sportstotalbot.db", picks_path: str = "data/picks"):
        self.db_path = db_path
        self.picks_path = picks_path
        self.db = Database(db_path)

        # NBA API for fetching historical results
        self.nba_game_url = "https://stats.nba.com/stats/scoreboardv2"

    def backtest_picks(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days_back: int = 30
    ) -> BacktestReport:
        """
        Run backtest on historical picks

        Args:
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            days_back: Number of days to look back if dates not specified

        Returns:
            BacktestReport with all metrics and insights
        """
        # Determine date range
        if end_date is None:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")

        if start_date is None:
            start_date = end_date - timedelta(days=days_back)
        else:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")

        logger.info(f"Running backtest from {start_date.date()} to {end_date.date()}")

        # Load historical picks
        picks = self._load_historical_picks(start_date, end_date)
        logger.info(f"Loaded {len(picks)} historical picks")

        # Fetch actual results for incomplete picks
        picks = self._fetch_results_for_picks(picks)
        logger.info(f"Found results for {sum(1 for p in picks if p.won is not None)} picks")

        # Calculate metrics
        overall = self._calculate_overall_metrics(picks)

        # Breakdowns
        by_confidence = self._analyze_by_confidence(picks)
        by_ev_range = self._analyze_by_ev_range(picks)
        by_bet_type = self._analyze_by_category(picks, "bet_type")
        by_side = self._analyze_by_category(picks, "side")
        by_data_quality = self._analyze_by_category(picks, "data_quality")

        # Find best/worst picks
        completed_picks = [p for p in picks if p.won is not None]
        best_picks = sorted(completed_picks, key=lambda p: p.units_won, reverse=True)[:5]
        worst_picks = sorted(completed_picks, key=lambda p: p.units_won)[:5]

        # Generate insights
        insights = self._generate_insights(picks, overall, by_confidence, by_ev_range)

        return BacktestReport(
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            overall=overall,
            by_confidence=by_confidence,
            by_ev_range=by_ev_range,
            by_bet_type=by_bet_type,
            by_side=by_side,
            by_data_quality=by_data_quality,
            best_picks=best_picks,
            worst_picks=worst_picks,
            insights=insights
        )

    def _load_historical_picks(self, start_date: datetime, end_date: datetime) -> List[HistoricalPick]:
        """Load historical picks from CSV files and database"""
        picks = []

        # Load from CSV files first
        picks.extend(self._load_picks_from_csv(start_date, end_date))

        # Load from database recommendations table
        picks.extend(self._load_picks_from_database(start_date, end_date))

        # Remove duplicates (by game_id + bet_type + side)
        seen = set()
        unique_picks = []
        for pick in picks:
            key = (pick.game_id, pick.bet_type, pick.side)
            if key not in seen:
                seen.add(key)
                unique_picks.append(pick)

        # Load results from results_log.csv if available
        if unique_picks:
            unique_picks = self._load_results_from_results_log(unique_picks)

        return unique_picks

    def _load_picks_from_csv(self, start_date: datetime, end_date: datetime) -> List[HistoricalPick]:
        """Load picks from daily CSV files"""
        picks = []
        picks_dir = Path(self.picks_path)

        if not picks_dir.exists():
            return picks

        # Check each day's CSV file
        current_date = start_date
        while current_date <= end_date:
            filename = f"daily_picks_{current_date.strftime('%Y%m%d')}.csv"
            filepath = picks_dir / filename

            if filepath.exists():
                try:
                    with open(filepath, 'r', newline='') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            try:
                                pick = HistoricalPick(
                                    game_id=row['Game ID'],
                                    date=current_date.strftime("%Y-%m-%d"),
                                    sport=row['Sport'],
                                    bet_type=row['Bet Type'],
                                    side=row['Side'],
                                    line=float(row['Line']),
                                    odds=int(row['Odds']),
                                    projected_value=float(row['Projected Value']),
                                    ev=float(row['EV']),
                                    win_probability=float(row['Win Probability']),
                                    confidence=float(row['Confidence']),
                                    home_team=row['Home Team'],
                                    away_team=row['Away Team'],
                                    reasoning=row.get('Reasoning', '')
                                )
                                picks.append(pick)
                            except (ValueError, KeyError) as e:
                                logger.warning(f"Skipping invalid row in {filename}: {e}")
                except Exception as e:
                    logger.error(f"Failed to load {filename}: {e}")

            current_date += timedelta(days=1)

        return picks

    def _load_picks_from_database(self, start_date: datetime, end_date: datetime) -> List[HistoricalPick]:
        """Load picks from database recommendations table"""
        picks = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT
                        r.game_id,
                        r.created_at,
                        r.sport,
                        r.bet_type,
                        r.side,
                        r.line,
                        r.odds,
                        r.projected_value,
                        r.ev,
                        r.win_probability,
                        r.confidence,
                        r.reasoning,
                        g.home_team,
                        g.away_team,
                        g.home_score,
                        g.away_score,
                        g.is_completed,
                        res.won,
                        res.actual_result,
                        res.profit_loss
                    FROM recommendations r
                    JOIN games g ON r.game_id = g.game_id
                    LEFT JOIN results res ON r.id = res.recommendation_id
                    WHERE DATE(r.created_at) >= ?
                    AND DATE(r.created_at) <= ?
                    ORDER BY r.created_at
                """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))

                for row in cursor.fetchall():
                    # Parse date from created_at
                    try:
                        created_at = datetime.fromisoformat(row['created_at'])
                        date_str = created_at.strftime("%Y-%m-%d")
                    except:
                        date_str = start_date.strftime("%Y-%m-%d")

                    pick = HistoricalPick(
                        game_id=row['game_id'],
                        date=date_str,
                        sport=row['sport'],
                        bet_type=row['bet_type'],
                        side=row['side'],
                        line=row['line'],
                        odds=row['odds'],
                        projected_value=row['projected_value'],
                        ev=row['ev'],
                        win_probability=row['win_probability'],
                        confidence=row['confidence'],
                        home_team=row['home_team'],
                        away_team=row['away_team'],
                        reasoning=row['reasoning'] or '',
                        actual_result=row['actual_result'],
                        won=row['won'] if row['won'] is not None else None,
                        profit_loss=row['profit_loss'] if row['profit_loss'] is not None else None
                    )

                    # If we have scores but no result, calculate it
                    if pick.won is None and row['home_score'] and row['away_score']:
                        pick = self._calculate_pick_result(pick, row['home_score'], row['away_score'])

                    picks.append(pick)

        except Exception as e:
            logger.error(f"Failed to load picks from database: {e}")

        return picks

    def _load_results_from_results_log(self, picks: List[HistoricalPick]) -> List[HistoricalPick]:
        """
        Load results from results_log.csv and merge with picks

        The results_log.csv format: date,game,pick,line,projected,actual,result,units_won
        """
        results_log_path = Path(self.picks_path) / "results_log.csv"

        if not results_log_path.exists():
            return picks

        try:
            with open(results_log_path, 'r', newline='') as f:
                reader = csv.DictReader(f)

                # Build a list of result entries
                results_list = []
                for row in reader:
                    # Skip comment lines
                    if row.get('date', '').startswith('#'):
                        continue

                    game = row.get('game', '')
                    pick_str = row.get('pick', '')
                    side = pick_str.split()[0] if pick_str else ''
                    line = float(row.get('line', 0))
                    actual = float(row.get('actual', 0))
                    result = row.get('result', '')
                    units_won = float(row.get('units_won', 0))

                    results_list.append({
                        'game': game,
                        'side': side,
                        'line': line,
                        'actual': actual,
                        'result': result,
                        'units_won': units_won
                    })

            # Match results to picks with fuzzy matching
            for pick in picks:
                # Our picks have: Home Team, Away Team in CSV
                # So game is: Away @ Home
                # Create variations to match results_log format
                game_names_to_try = [
                    f"{pick.away_team} @ {pick.home_team}",  # Standard: "Utah Jazz @ Indiana Pacers"
                    f"{pick.away_team}@{pick.home_team}",
                    # Common abbreviations (shorten team names)
                    f"{pick.away_team.replace('Utah Jazz', 'Jazz').replace('Portland Trail Blazers', 'Blazers').replace('Oklahoma City Thunder', 'Thunder').replace('Golden State Warriors', 'Warriors').replace('Los Angeles ', '').replace('San Antonio ', '').replace('New York ', '').replace('Oklahoma City ', '')} @ {pick.home_team.replace('Indiana Pacers', 'Pacers').replace('Portland Trail Blazers', 'Blazers').replace('Oklahoma City Thunder', 'Thunder').replace('Golden State Warriors', 'Warriors').replace('Los Angeles ', '').replace('San Antonio ', '').replace('New York ', '').replace('Washington ', '').replace('New Orleans ', '')}",
                ]

                for result_entry in results_list:
                    # Check if any of our game name formats match
                    # Match if result game is contained in any of our variations OR vice versa
                    matched = False
                    for name in game_names_to_try:
                        # Check if result game string is a substring of our game name
                        if result_entry['game'] in name or name in result_entry['game']:
                            matched = True
                            break
                        # Also check if the key teams match (first word of away, last word of home)
                        result_parts = result_entry['game'].split(' @ ')
                        if len(result_parts) == 2:
                            result_away = result_parts[0].split()[-1]  # Last word of away team
                            result_home = result_parts[1].split()[-1]    # Last word of home team
                            if result_away in pick.away_team and result_home in pick.home_team:
                                matched = True
                                break

                    if matched:
                        # Check side and line
                        if (result_entry['side'].upper() == pick.side.upper() and
                            abs(result_entry['line'] - pick.line) < 0.5):
                            pick.actual_result = result_entry['actual']
                            pick.won = (result_entry['result'] == 'WIN')
                            pick.profit_loss = result_entry['units_won']
                            break

        except Exception as e:
            logger.warning(f"Failed to load results from results_log.csv: {e}")

        return picks

    def _calculate_pick_result(self, pick: HistoricalPick, home_score: int, away_score: int) -> HistoricalPick:
        """Calculate if a pick won based on actual scores"""
        pick.actual_result = home_score + away_score

        if pick.bet_type == 'totals':
            if pick.side == 'over':
                # Check if total went over the line
                # Push if exactly on line
                if abs(pick.actual_result - pick.line) < 0.5:
                    pick.won = None  # Push
                else:
                    pick.won = pick.actual_result > pick.line
            else:  # under
                if abs(pick.actual_result - pick.line) < 0.5:
                    pick.won = None  # Push
                else:
                    pick.won = pick.actual_result < pick.line
        elif pick.bet_type == 'spreads':
            margin = home_score - away_score
            if pick.side == 'home':
                # Home covers if home wins by more than spread
                if abs(margin - pick.line) < 0.5:
                    pick.won = None  # Push
                else:
                    pick.won = margin > pick.line
            else:  # away
                if abs(margin + pick.line) < 0.5:
                    pick.won = None  # Push
                else:
                    pick.won = margin < -pick.line

        # Calculate profit/loss
        if pick.won is not None:
            pick.profit_loss = pick.units_won
        else:
            pick.profit_loss = 0.0  # Push

        return pick

    def _fetch_results_for_picks(self, picks: List[HistoricalPick]) -> List[HistoricalPick]:
        """
        Fetch actual game results for picks that don't have them

        For completed games, we calculate the result from scores.
        For NBA games, we could use an API, but we'll rely on database first.
        """
        updated_picks = []

        for pick in picks:
            # Skip if we already have a result
            if pick.won is not None:
                updated_picks.append(pick)
                continue

            # Try to get scores from database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("""
                        SELECT home_score, away_score, is_completed
                        FROM games
                        WHERE game_id = ?
                    """, (pick.game_id,))

                    row = cursor.fetchone()
                    if row and row['home_score'] and row['away_score']:
                        pick = self._calculate_pick_result(pick, row['home_score'], row['away_score'])

            except Exception as e:
                logger.debug(f"Could not fetch result for {pick.game_id}: {e}")

            updated_picks.append(pick)

        return updated_picks

    def _calculate_overall_metrics(self, picks: List[HistoricalPick]) -> PerformanceMetrics:
        """Calculate overall performance metrics"""
        completed = [p for p in picks if p.won is not None]

        if not completed:
            return PerformanceMetrics()

        wins = sum(1 for p in completed if p.won)
        losses = sum(1 for p in completed if not p.won)
        pushes = sum(1 for p in picks if p.won is None)
        win_rate = wins / len(completed) * 100 if completed else 0

        expected_win_rate = sum(p.win_probability for p in completed) / len(completed) * 100 if completed else 0

        total_units = sum(p.units_won for p in completed)
        roi_percent = (total_units / len(completed) * 100) if completed else 0

        avg_ev = sum(p.ev for p in completed) / len(completed) * 100 if completed else 0

        actual_vs_expected = roi_percent - avg_ev

        return PerformanceMetrics(
            total_bets=len(completed),
            wins=wins,
            losses=losses,
            pushes=pushes,
            win_rate=win_rate,
            expected_win_rate=expected_win_rate,
            total_units=total_units,
            roi_percent=roi_percent,
            avg_ev=avg_ev,
            actual_vs_expected=actual_vs_expected
        )

    def _analyze_by_confidence(self, picks: List[HistoricalPick]) -> Dict[str, BreakdownStats]:
        """Analyze performance by confidence level"""
        completed = [p for p in picks if p.won is not None]
        if not completed:
            return {}

        # Group by confidence ranges
        buckets = {
            "Very High (>=75%)": [],
            "High (65-74%)": [],
            "Medium (55-64%)": [],
            "Low (<55%)": []
        }

        for pick in completed:
            conf_pct = pick.confidence * 100
            if conf_pct >= 75:
                buckets["Very High (>=75%)"].append(pick)
            elif conf_pct >= 65:
                buckets["High (65-74%)"].append(pick)
            elif conf_pct >= 55:
                buckets["Medium (55-64%)"].append(pick)
            else:
                buckets["Low (<55%)"].append(pick)

        return {name: self._calc_breakdown_stats(bucket_picks)
                for name, bucket_picks in buckets.items() if bucket_picks}

    def _analyze_by_ev_range(self, picks: List[HistoricalPick]) -> Dict[str, BreakdownStats]:
        """Analyze performance by EV range"""
        completed = [p for p in picks if p.won is not None]
        if not completed:
            return {}

        # Group by EV ranges
        buckets = {
            "Excellent (>=15%)": [],
            "Good (10-14.9%)": [],
            "Moderate (5-9.9%)": [],
            "Marginal (2-4.9%)": []
        }

        for pick in completed:
            ev_pct = pick.ev * 100
            if ev_pct >= 15:
                buckets["Excellent (>=15%)"].append(pick)
            elif ev_pct >= 10:
                buckets["Good (10-14.9%)"].append(pick)
            elif ev_pct >= 5:
                buckets["Moderate (5-9.9%)"].append(pick)
            else:
                buckets["Marginal (2-4.9%)"].append(pick)

        return {name: self._calc_breakdown_stats(bucket_picks)
                for name, bucket_picks in buckets.items() if bucket_picks}

    def _analyze_by_category(self, picks: List[HistoricalPick], category: str) -> Dict[str, BreakdownStats]:
        """Analyze performance by any category (bet_type, side, data_quality)"""
        completed = [p for p in picks if p.won is not None]
        if not completed:
            return {}

        # Group by category value
        buckets = defaultdict(list)
        for pick in completed:
            value = getattr(pick, category, "Unknown")
            buckets[value].append(pick)

        return {name: self._calc_breakdown_stats(bucket_picks)
                for name, bucket_picks in buckets.items()}

    def _calc_breakdown_stats(self, picks: List[HistoricalPick]) -> BreakdownStats:
        """Calculate statistics for a group of picks"""
        if not picks:
            return None

        wins = sum(1 for p in picks if p.won)
        losses = sum(1 for p in picks if not p.won)
        win_rate = wins / len(picks) * 100

        total_units = sum(p.units_won for p in picks)
        roi_percent = (total_units / len(picks) * 100)

        avg_ev = sum(p.ev for p in picks) / len(picks) * 100
        avg_confidence = sum(p.confidence for p in picks) / len(picks) * 100

        # Determine category name from first pick
        category = picks[0].bet_type if len(picks) == 1 else "mixed"

        return BreakdownStats(
            category=category,
            total_bets=len(picks),
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_units=total_units,
            roi_percent=roi_percent,
            avg_ev=avg_ev,
            avg_confidence=avg_confidence
        )

    def _generate_insights(
        self,
        picks: List[HistoricalPick],
        overall: PerformanceMetrics,
        by_confidence: Dict[str, BreakdownStats],
        by_ev_range: Dict[str, BreakdownStats]
    ) -> List[str]:
        """Generate actionable insights from the backtest"""
        insights = []

        completed = [p for p in picks if p.won is not None]
        if not completed:
            return ["No completed picks to analyze."]

        # Overall performance
        if overall.roi_percent > 5:
            insights.append(f"Model is PROFITABLE with {overall.roi_percent:.1f}% ROI")
        elif overall.roi_percent > 0:
            insights.append(f"Model is slightly profitable with {overall.roi_percent:.1f}% ROI")
        elif overall.roi_percent > -5:
            insights.append(f"Model is slightly unprofitable at {overall.roi_percent:.1f}% ROI - needs tuning")
        else:
            insights.append(f"Model is LOSING MONEY at {overall.roi_percent:.1f}% ROI - major revision needed")

        # Win rate vs expected
        diff = overall.win_rate - overall.expected_win_rate
        if abs(diff) > 5:
            if diff > 0:
                insights.append(f"Actual win rate ({overall.win_rate:.1f}%) exceeds expectations ({overall.expected_win_rate:.1f}%)")
            else:
                insights.append(f"Actual win rate ({overall.win_rate:.1f}%) below expectations ({overall.expected_win_rate:.1f}%) - model may be overconfident")

        # Confidence calibration
        if by_confidence:
            high_conf = next((s for s in by_confidence.values() if "High" in s.category), None)
            if high_conf:
                if high_conf.roi_percent < 0:
                    insights.append(f"High confidence picks underperforming - consider adjusting confidence calculations")
                else:
                    insights.append(f"High confidence picks performing well - trust these picks")

        # EV range analysis
        if by_ev_range:
            best_ev = max(by_ev_range.items(), key=lambda x: x[1].roi_percent)
            worst_ev = min(by_ev_range.items(), key=lambda x: x[1].roi_percent)
            insights.append(f"Best EV range: {best_ev[0]} at {best_ev[1].roi_percent:.1f}% ROI")
            insights.append(f"Worst EV range: {worst_ev[0]} at {worst_ev[1].roi_percent:.1f}% ROI")

        # Side analysis
        overs = [p for p in completed if p.side == 'over']
        unders = [p for p in completed if p.side == 'under']
        if overs and unders:
            overs_roi = sum(p.units_won for p in overs) / len(overs) * 100
            unders_roi = sum(p.units_won for p in unders) / len(unders) * 100
            if abs(overs_roi - unders_roi) > 5:
                better = "OVER" if overs_roi > unders_roi else "UNDER"
                insights.append(f"{better} bets significantly outperforming ({max(overs_roi, unders_roi):.1f}% vs {min(overs_roi, unders_roi):.1f}% ROI)")

        # Sample size warning
        if overall.total_bets < 30:
            insights.append(f"Small sample size ({overall.total_bets} bets) - results may not be statistically significant")

        return insights

    def save_backtest_results(self, report: BacktestReport, output_path: str = None) -> str:
        """
        Save backtest results to file

        Args:
            report: The backtest report to save
            output_path: Optional output path (default: data/results/backtest_YYYYMMDD.json)

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = f"data/results/backtest_{datetime.now().strftime('%Y%m%d')}.json"

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        # Convert report to dict
        report_dict = {
            'period_start': report.period_start,
            'period_end': report.period_end,
            'overall': asdict(report.overall),
            'by_confidence': {k: asdict(v) for k, v in report.by_confidence.items()},
            'by_ev_range': {k: asdict(v) for k, v in report.by_ev_range.items()},
            'by_bet_type': {k: asdict(v) for k, v in report.by_bet_type.items()},
            'by_side': {k: asdict(v) for k, v in report.by_side.items()},
            'by_data_quality': {k: asdict(v) for k, v in report.by_data_quality.items()},
            'best_picks': [asdict(p) for p in report.best_picks],
            'worst_picks': [asdict(p) for p in report.worst_picks],
            'insights': report.insights,
            'generated_at': datetime.now().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Saved backtest results to {output_path}")
        return output_path


def calculate_performance_metrics(picks_with_results: List[HistoricalPick]) -> PerformanceMetrics:
    """
    Calculate performance metrics from a list of picks with results

    Args:
        picks_with_results: List of HistoricalPick objects with won/results set

    Returns:
        PerformanceMetrics object
    """
    if not picks_with_results:
        return PerformanceMetrics()

    backtester = Backtester()
    return backtester._calculate_overall_metrics(picks_with_results)


def analyze_by_confidence(picks_with_results: List[HistoricalPick]) -> Dict[str, BreakdownStats]:
    """
    See how different confidence levels perform

    Args:
        picks_with_results: List of HistoricalPick objects with won/results set

    Returns:
        Dict mapping confidence ranges to BreakdownStats
    """
    backtester = Backtester()
    return backtester._analyze_by_confidence(picks_with_results)


def analyze_by_ev_range(picks_with_results: List[HistoricalPick]) -> Dict[str, BreakdownStats]:
    """
    See how different EV ranges perform

    Args:
        picks_with_results: List of HistoricalPick objects with won/results set

    Returns:
        Dict mapping EV ranges to BreakdownStats
    """
    backtester = Backtester()
    return backtester._analyze_by_ev_range(picks_with_results)
