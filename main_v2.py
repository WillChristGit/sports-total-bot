#!/usr/bin/env python3
"""
SportsTotalBot - Main Entry Point (V2 - Enhanced)

An AI-powered sports betting analysis bot that identifies
positive EV (Expected Value) betting opportunities on sports totals.

V2 Improvements:
- Fixed bare except clause with proper error handling
- Added team name mapping between APIs
- Fixed odds parsing bug
- Enhanced projection model (efficiency metrics, fatigue)
- Enhanced EV calculator (Kelly sizing, line movement)
- Better error handling and logging
- Real NBA stats fetching
- Environment variable support
- Retry logic with exponential backoff
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Make src importable when running main_v2.py directly (e.g. python main_v2.py).
# For installed usage, run: pip install -e .  (uses pyproject.toml)
sys.path.insert(0, os.path.dirname(__file__))

# Import from src modules
from src.data.models import Game, SportType, BetType, OddsLine, BetSide
from src.data.fetchers import get_games_with_odds, NBAStatsFetcher
from src.data.nba_stats_cache import NBAStatsFetcher as NBAStatsCache
from src.data.multi_source_stats import MultiSourceStatsFetcher, DataQualityReport
from src.data.injury_fetcher import InjuryFetcher
from src.storage.database import Database
from src.analysis.projections_v2 import create_enhanced_projection_model, AdvancedTeamStats, ScheduleInfo, InjuryImpact
from src.analysis.spread_projections import create_spread_projection_model, SpreadProjection
from src.analysis.ev_calculator_v2 import EnhancedEVCalculator, LineMovement
from src.analysis.backtester import Backtester
from src.output.formatter import OutputFormatter, DiscordNotifier, TelegramNotifier
from src.config.loader import Config
from src.data.ncaa_injury_fetcher import NCAAInjuryFetcher
from src.utils.logging import setup_logging as configure_logging
from scripts.pick_tracker import PickTracker
import yaml

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


# Team name mappings between different APIs
TEAM_NAME_MAPPINGS = {
    # Odds API -> NBA API
    'Los Angeles Lakers': 'Lakers',
    'Los Angeles Clippers': 'Clippers',
    'Boston Celtics': 'Celtics',
    'Brooklyn Nets': 'Nets',
    'New York Knicks': 'Knicks',
    'Philadelphia 76ers': '76ers',
    'Toronto Raptors': 'Raptors',
    'Golden State Warriors': 'Warriors',
    'LA Clippers': 'Clippers',

    # Common abbreviations
    'LAL': 'Los Angeles Lakers',
    'LAC': 'Los Angeles Clippers',
    'BOS': 'Boston Celtics',
    'BKN': 'Brooklyn Nets',
    'NYK': 'New York Knicks',
    'PHI': 'Philadelphia 76ers',
    'TOR': 'Toronto Raptors',
    'GSW': 'Golden State Warriors',
    'MIL': 'Milwaukee Bucks',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers',
    'MIA': 'Miami Heat',
    'DAL': 'Dallas Mavericks',
    'SAS': 'San Antonio Spurs',
    'HOU': 'Houston Rockets',
    'DEN': 'Denver Nuggets',
    'UTA': 'Utah Jazz',
    'PHX': 'Phoenix Suns',
    'SAC': 'Sacramento Kings',
    'POR': 'Portland Trail Blazers',
    'OKC': 'Oklahoma City Thunder',
    'MIN': 'Minnesota Timberwolves',
}


def normalize_team_name(team_name: str) -> str:
    """Normalize team name using mapping"""
    return TEAM_NAME_MAPPINGS.get(team_name, team_name)

def validate_american_odds(price: int) -> bool:
    '''
    Validate American odds are within reasonable bounds.

    Rejects odds that are clearly bad data:
    - Odds more extreme than -200 or +200 are suspicious
    - These represent unrealistic betting lines

    Args:
        price: American odds (e.g., -110, +150)

    Returns:
        True if odds are valid, False otherwise
    '''
    # Reject extreme odds
    if price < -200 or price > 200:
        logging.warning(f"Rejected extreme odds: {price} (outside -200 to +200 range)")
        return False

    # Reject zero or near-zero odds
    if abs(price) < 10:
        logging.warning(f"Rejected near-zero odds: {price}")
        return False

    return True



def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration using the enhanced logging module"""
    return configure_logging(log_level=log_level)


def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load configuration from YAML file with environment variable overrides"""
    return Config(config_path)


def load_sports_config() -> dict:
    """Load sport-specific configuration"""
    try:
        with open('config/sports_config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.warning("Sports config file not found, using defaults")
        return {}
    except yaml.YAMLError as e:
        logging.warning(f"Error parsing sports config: {e}, using defaults")
        return {}


def validate_api_key(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        return False
    return len(api_key) > 10  # Basic validation


def validate_game_data(game_data: dict) -> bool:
    """Validate game data from API"""
    required_fields = ['id', 'home_team', 'away_team', 'commence_time']
    for field in required_fields:
        if field not in game_data:
            logging.warning(f"Invalid game data: missing {field}")
            return False
    return True


def parse_odds_api_response(raw_data: list, sport: SportType = SportType.NBA) -> tuple[dict, dict]:
    """
    Parse the Odds API response into Games and Odds objects

    V2 Fix: Properly aggregates odds from multiple bookmakers
    Now includes both totals and spreads

    Args:
        raw_data: Raw API response data
        sport: SportType to assign to games (NBA, NCAA, etc.)
    """
    if not raw_data:
        logging.warning("No data received from API")
        return {}, {}

    games = {}
    odds_dict = {}

    for game_data in raw_data:
        # Validate game data
        if not validate_game_data(game_data):
            continue

        game_id = game_data.get('id')

        # Parse game info
        home_team = normalize_team_name(game_data.get('home_team', ''))
        away_team = normalize_team_name(game_data.get('away_team', ''))

        try:
            game_time = datetime.fromisoformat(
                game_data.get('commence_time', '').replace('Z', '+00:00')
            )
        except ValueError as e:
            logging.warning(f"Invalid datetime for game {game_id}: {e}")
            continue

        game = Game(
            game_id=game_id,
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            game_time=game_time
        )
        games[game_id] = game

        # Aggregate odds from all bookmakers (using consensus)
        # For totals
        over_odds_list = []
        under_odds_list = []
        total_lines = []

        # For spreads
        home_spreads = []
        home_spread_odds = []
        away_spreads = []
        away_spread_odds = []

        for bookmaker in game_data.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                # Parse totals
                if market.get('key') == 'totals':
                    for outcome in market.get('outcomes', []):
                        line = outcome.get('point')
                        price = outcome.get('price')

                        if line is not None and price is not None:
                            # Validate odds before adding to list
                            if validate_american_odds(price):
                                total_lines.append(line)
                                if outcome.get('name') == 'Over':
                                    over_odds_list.append(price)
                                elif outcome.get('name') == 'Under':
                                    under_odds_list.append(price)

                # Parse spreads
                elif market.get('key') == 'spreads':
                    for outcome in market.get('outcomes', []):
                        line = outcome.get('point')
                        price = outcome.get('price')
                        name = normalize_team_name(outcome.get('name', ''))  # Normalize the outcome name too!

                        if line is not None and price is not None:
                            # Validate odds before adding to list
                            if validate_american_odds(price):
                                # Spread line is usually negative for favorite
                                # outcome.get('name') is team name
                                if name == home_team:
                                    home_spreads.append(abs(line))  # Store as positive for consistency
                                    home_spread_odds.append(price)
                                elif name == away_team:
                                    away_spreads.append(abs(line))  # Store as positive for consistency
                                    away_spread_odds.append(price)

        # Create totals odds if we have data
        if total_lines and over_odds_list and under_odds_list:
            avg_line = round(sum(total_lines) / len(total_lines), 1)  # Round to 1 decimal
            avg_over_odds = round(sum(over_odds_list) / len(over_odds_list))
            avg_under_odds = round(sum(under_odds_list) / len(under_odds_list))

            totals_odds = OddsLine(
                game_id=game_id,
                sport=sport,
                bet_type=BetType.TOTALS,
                total_line=avg_line,
                over_odds=avg_over_odds,
                under_odds=avg_under_odds,
                book_name="consensus",
                update_time=datetime.now()
            )
            odds_dict[f"{game_id}_totals"] = totals_odds

        # Create spreads odds if we have data
        if home_spreads and away_spreads and home_spread_odds and away_spread_odds:
            # Average the spreads (they should be the same or very close)
            avg_home_spread = round(sum(home_spreads) / len(home_spreads), 1)
            avg_away_spread = round(sum(away_spreads) / len(away_spreads), 1)
            avg_home_spread_odds = round(sum(home_spread_odds) / len(home_spread_odds))
            avg_away_spread_odds = round(sum(away_spread_odds) / len(away_spread_odds))

            spreads_odds = OddsLine(
                game_id=game_id,
                sport=sport,
                bet_type=BetType.SPREAD,
                home_spread=avg_home_spread,
                home_spread_odds=avg_home_spread_odds,
                away_spread=avg_away_spread,
                away_spread_odds=avg_away_spread_odds,
                book_name="consensus",
                update_time=datetime.now()
            )
            odds_dict[f"{game_id}_spreads"] = spreads_odds

    logging.info(f"Parsed {len(games)} games with odds")
    return games, odds_dict


def create_enhanced_team_stats(team_name: str, stats_cache: NBAStatsCache) -> AdvancedTeamStats:
    """
    Create enhanced team stats using real NBA data
    Falls back to league averages if data unavailable
    """
    # Get real stats from NBA.com
    real_stats = stats_cache.get_team_stats(team_name)

    if real_stats:
        return AdvancedTeamStats(
            team_id=real_stats['team_id'],
            team_name=real_stats['team_name'],
            games_played=real_stats['games_played'],
            avg_points_scored=real_stats['avg_points_scored'],
            avg_points_allowed=real_stats['avg_points_allowed'],
            offensive_rating=real_stats['offensive_rating'],
            defensive_rating=real_stats['defensive_rating'],
            efg_pct=real_stats.get('efg_pct', 0.520),
            tov_pct=real_stats.get('tov_pct', 0.135),
            orb_pct=real_stats.get('orb_pct', 0.260),
            ft_rate=real_stats.get('ft_rate', 0.210),
            pace=real_stats['pace'],
            last_5_points_scored=[],  # Would fetch from game log
            last_5_points_allowed=[]
        )
    else:
        # Fallback to league averages (2024-25 NBA averages)
        logging.getLogger(__name__).warning(f"Using league averages for {team_name}")
        return AdvancedTeamStats(
            team_id=team_name[:3].upper(),
            team_name=team_name,
            games_played=50,
            avg_points_scored=112.5,  # 2024-25 league avg
            avg_points_allowed=112.5,
            offensive_rating=114.0,
            defensive_rating=114.0,
            efg_pct=0.520,
            tov_pct=0.135,
            orb_pct=0.260,
            ft_rate=0.210,
            pace=99.5,  # 2024-25 league avg pace
            last_5_points_scored=[],
            last_5_points_allowed=[]
        )


def create_schedule_info(team_name: str, stats_cache: NBAStatsCache) -> ScheduleInfo:
    """Create schedule info using real NBA schedule data"""
    schedule_data = stats_cache.get_team_schedule(team_name)

    return ScheduleInfo(
        days_rest=schedule_data.get('days_rest', 2),
        is_back_to_back=schedule_data.get('is_back_to_back', False),
        is_third_in_4_days=schedule_data.get('is_third_in_4_days', False),
        travel_distance_miles=schedule_data.get('travel_distance_miles', 0),
        time_zone_changes=schedule_data.get('time_zone_changes', 0)
    )


def update_and_display_results(db: Database, logger: logging.Logger) -> dict:
    """
    Update results for completed games and display summary

    Returns:
        dict with results summary stats
    """
    logger.info("Updating results for completed games...")

    try:
        updated = db.update_results_for_completed_games()
        logger.info(f"Updated {len(updated)} game results")

        if updated:
            # Calculate summary stats
            completed = [r for r in updated if r.get('is_completed', False)]
            wins = sum(1 for r in completed if r.get('won', False) == 1)
            losses = len(completed) - wins
            total_pl = sum(r.get('profit_loss', 0) for r in completed)

            summary = {
                'updated_count': len(updated),
                'completed_count': len(completed),
                'wins': wins,
                'losses': losses,
                'win_rate': (wins / len(completed) * 100) if completed else 0,
                'profit_loss': total_pl
            }

            # Log summary to console
            logger.info("=" * 60)
            logger.info("📊 RESULTS UPDATE SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Games Updated:  {summary['updated_count']}")
            logger.info(f"Completed:      {summary['completed_count']}")
            logger.info(f"Results:        {summary['wins']}W - {summary['losses']}L")
            logger.info(f"Win Rate:       {summary['win_rate']:.1f}%")
            logger.info(f"Profit/Loss:    ${summary['profit_loss']:+.2f}")
            logger.info("=" * 60)

            return summary
        else:
            logger.info("No new results to update")
            return {
                'updated_count': 0,
                'completed_count': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'profit_loss': 0
            }

    except Exception as e:
        logger.error(f"Failed to update results: {e}")
        return {
            'updated_count': 0,
            'completed_count': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'profit_loss': 0
        }


def _fetch_and_parse_games(api_key: str, sport_key: str, sport_type: SportType,
                           db: Database, logger) -> tuple:
    """
    Fetch games with odds, parse into models, save to DB, and group by game_id.
    Returns (games dict, game_odds_map dict) or empty dicts on failure.
    """
    logger.info("Fetching games and odds...")
    try:
        raw_games = get_games_with_odds(api_key, sport=sport_key)
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        return {}, {}

    if not raw_games:
        logger.warning("No games found")
        return {}, {}

    logger.info(f"Found {len(raw_games)} games")
    games, odds_data = parse_odds_api_response(raw_games, sport_type)

    if not games:
        logger.warning("No valid games after parsing")
        return {}, {}

    for game in games.values():
        try:
            db.save_game(game)
        except Exception as e:
            logger.error(f"Failed to save game {game.game_id}: {e}")

    # Group odds by game_id so totals and spreads are co-located
    game_odds_map: dict = {}
    for odds_key, odds in odds_data.items():
        if '_totals' in odds_key:
            game_id = odds_key.replace('_totals', '')
            game_odds_map.setdefault(game_id, {})['totals'] = odds
        elif '_spreads' in odds_key:
            game_id = odds_key.replace('_spreads', '')
            game_odds_map.setdefault(game_id, {})['spreads'] = odds

    return games, game_odds_map


def _build_team_stats_for_game(game, stats_fetcher, stats_cache, sport_type: SportType) -> tuple:
    """
    Fetch and build AdvancedTeamStats + ScheduleInfo for both teams in a game.
    Returns (home_stats, away_stats, data_quality_grade, home_schedule, away_schedule).
    """
    if sport_type == SportType.NBA:
        home_data = stats_fetcher.get_team_stats(game.home_team)
        away_data = stats_fetcher.get_team_stats(game.away_team)

        def _to_advanced(team_name, data):
            return AdvancedTeamStats(
                team_id=str(stats_fetcher.team_name_to_id.get(team_name, team_name[:3])),
                team_name=team_name,
                games_played=data.games_played,
                avg_points_scored=data.points_per_game,
                avg_points_allowed=data.opp_points_per_game,
                offensive_rating=data.offensive_rating,
                defensive_rating=data.defensive_rating,
                efg_pct=data.efg_pct,
                tov_pct=data.tov_pct,
                orb_pct=data.orb_pct,
                ft_rate=data.ft_rate,
                pace=data.pace,
                last_5_points_scored=data.last_5_points_scored,
                last_5_points_allowed=[]
            )

        home_stats = _to_advanced(game.home_team, home_data)
        away_stats = _to_advanced(game.away_team, away_data)

        quality_map = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
        avg_score = (quality_map.get(home_data.data_quality.value, 2) +
                     quality_map.get(away_data.data_quality.value, 2)) / 2
        if avg_score >= 4.5:
            data_quality = "A"
        elif avg_score >= 3.5:
            data_quality = "B"
        elif avg_score >= 2.5:
            data_quality = "C"
        elif avg_score >= 1.5:
            data_quality = "D"
        else:
            data_quality = "F"

        home_schedule = create_schedule_info(game.home_team, stats_cache)
        away_schedule = create_schedule_info(game.away_team, stats_cache)

    else:  # NCAA
        home_dict, _ = stats_fetcher.get_team_stats(game.home_team)
        away_dict, _ = stats_fetcher.get_team_stats(game.away_team)

        def _to_ncaa_advanced(team_name, d):
            return AdvancedTeamStats(
                team_id=team_name[:3].upper(),
                team_name=team_name,
                games_played=25,
                avg_points_scored=d.get('points_per_game', 75.5),
                avg_points_allowed=d.get('opponent_points_per_game', 75.5),
                offensive_rating=d.get('offensive_rating', 105.0),
                defensive_rating=d.get('defensive_rating', 105.0),
                efg_pct=d.get('field_goal_pct', 0.450),
                tov_pct=0.150,
                orb_pct=0.300,
                ft_rate=0.250,
                pace=d.get('pace', 70.5),
                last_5_points_scored=[],
                last_5_points_allowed=[]
            )

        home_stats = _to_ncaa_advanced(game.home_team, home_dict)
        away_stats = _to_ncaa_advanced(game.away_team, away_dict)
        data_quality = "D"
        empty = ScheduleInfo(last_game_date=None, days_rest=2, is_back_to_back=False,
                             is_third_in_4_days=False, travel_distance_miles=0,
                             time_zone_changes=0)
        home_schedule = away_schedule = empty

    return home_stats, away_stats, data_quality, home_schedule, away_schedule


def _analyze_single_game(game, odds_map: dict, home_stats, away_stats,
                          home_schedule, away_schedule, injury_impact,
                          data_quality: str, totals_model, spreads_model,
                          ev_calc, min_conf: float, db: Database, logger) -> list:
    """
    Project totals and spreads for one game and calculate EV.
    Returns a list of EnhancedBetRecommendation objects.
    """
    recommendations = []
    sport_type = game.sport

    if 'totals' in odds_map:
        try:
            project_args = dict(game=game, home_stats=home_stats, away_stats=away_stats,
                                home_schedule=home_schedule, away_schedule=away_schedule)
            if sport_type == SportType.NBA and injury_impact:
                project_args['injury_impact'] = injury_impact

            totals_projection = totals_model.project_game(**project_args)
            logger.info(f"  Totals Projection: {totals_projection.projected_total} "
                        f"(Line: {odds_map['totals'].total_line:.1f}, "
                        f"Conf: {totals_projection.confidence:.0%})")

            totals_recs = ev_calc.calculate_totals_ev(
                totals_projection, odds_map['totals'], min_confidence=min_conf,
                home_stats=home_stats, away_stats=away_stats,
                home_schedule=home_schedule, away_schedule=away_schedule
            )
            for rec in totals_recs:
                rec.data_quality = data_quality
                try:
                    db.save_recommendation(rec)
                except Exception as e:
                    logger.error(f"Failed to save recommendation: {e}")
            recommendations.extend(totals_recs)

        except Exception as e:
            logger.error(f"Failed to generate totals projection for {game.game_id}: {e}")

    if spreads_model and 'spreads' in odds_map:
        try:
            spread_projection = spreads_model.project_game(
                game, home_stats, away_stats, home_schedule, away_schedule,
                injury_impact=injury_impact
            )
            logger.info(f"  Spread Projection: {spread_projection.projected_spread:+.1f} "
                        f"(Home: {spread_projection.projected_home_score}, "
                        f"Away: {spread_projection.projected_away_score}, "
                        f"Conf: {spread_projection.confidence:.0%})")

            spread_recs = ev_calc.calculate_spreads_ev(
                spread_projection.projected_home_score,
                spread_projection.projected_away_score,
                odds_map['spreads'], spread_projection.confidence,
                min_confidence=min_conf,
                home_stats=home_stats, away_stats=away_stats,
                home_schedule=home_schedule, away_schedule=away_schedule
            )
            for rec in spread_recs:
                rec.data_quality = data_quality
                try:
                    db.save_recommendation(rec)
                except Exception as e:
                    logger.error(f"Failed to save recommendation: {e}")
            recommendations.extend(spread_recs)

        except Exception as e:
            logger.error(f"Failed to generate spread projection for {game.game_id}: {e}")

    return recommendations


def run_analysis(config: Config, db: Database, sport_type: SportType = SportType.NBA) -> tuple:
    """
    Main analysis pipeline.

    Orchestrates: game fetching → stats enrichment → projection → EV filtering.

    Returns:
        (recommendations, games, quality_report, injury_reports)
    """
    logger = logging.getLogger(__name__)
    api_key = config.get('api_keys.the_odds_api', '')

    if not validate_api_key(api_key):
        logger.error("Invalid API key configured!")
        logger.info("Get a free API key at: https://the-odds-api.com/")
        logger.info("Add your key via ODDS_API_KEY env var or in config/config.yaml")
        return [], {}, None, {}

    sport_key = {SportType.NBA: 'nba', SportType.NCAA: 'ncaab'}.get(sport_type, 'nba')

    # Sport-specific stats fetcher
    if sport_type == SportType.NBA:
        stats_fetcher = MultiSourceStatsFetcher(odds_api_key=api_key)
    elif sport_type == SportType.NCAA:
        from src.data.ncaa_stats_fetcher import NCAAStatsFetcher
        stats_fetcher = NCAAStatsFetcher(
            cache_dir="data/cache/ncaa",
            sportsdataio_key=os.environ.get('SPORTSDATAIO_KEY', '')
        )
    else:
        stats_fetcher = MultiSourceStatsFetcher(odds_api_key=api_key)

    # Fetch and parse games
    games, game_odds_map = _fetch_and_parse_games(api_key, sport_key, sport_type, db, logger)
    if not games:
        return [], {}, None, {}

    # Models and EV calculator
    nba_config = load_sports_config().get('nba', {}).get('model', {})
    totals_model = create_enhanced_projection_model(sport_type, nba_config)
    spreads_model = create_spread_projection_model(sport_type, nba_config)
    ev_calc = EnhancedEVCalculator(min_ev_threshold=config.get('analysis.min_ev_threshold', 0.015))
    min_conf = config.get('analysis.min_confidence', 0.525)

    # Shared NBA stats cache — instantiated once, reused for all schedule lookups
    stats_cache = NBAStatsCache() if sport_type == SportType.NBA else None

    # Injury data
    injury_fetcher = None
    injury_reports: dict = {}
    if sport_type == SportType.NBA:
        logger.info("Fetching injury reports...")
        injury_fetcher = InjuryFetcher(cache_dir="data/cache/injuries")
        try:
            injury_fetcher.fetch_all_injuries()
            summary = injury_fetcher.log_injury_summary()
            if summary:
                logger.info(f"\n{summary}")
        except Exception as e:
            logger.warning(f"Failed to fetch injury data: {e}")
    elif sport_type == SportType.NCAA:
        try:
            ncaa_inj = NCAAInjuryFetcher(cache_dir="data/cache/ncaa/injuries")
            ncaa_inj.fetch_injuries()
            injury_reports = ncaa_inj.injuries
            logger.info(f"NCAA injury reports loaded for {len(injury_reports)} teams")
        except Exception as e:
            logger.warning(f"Failed to fetch NCAA injury data: {e}")

    recommendations = []

    for game_id, odds_map in game_odds_map.items():
        game = games.get(game_id)
        if not game:
            continue

        logger.info(f"Analyzing: {game.away_team} @ {game.home_team}")

        try:
            home_stats, away_stats, data_quality, home_schedule, away_schedule = \
                _build_team_stats_for_game(game, stats_fetcher, stats_cache, sport_type)
        except Exception as e:
            logger.error(f"Failed to build team stats for {game_id}: {e}")
            continue

        # Injury impact (NBA only)
        injury_impact = None
        if sport_type == SportType.NBA and injury_fetcher:
            try:
                inj_data = injury_fetcher.get_game_injury_impact(game.home_team, game.away_team)
                injury_impact = InjuryImpact(
                    home_offensive_impact=inj_data.get('home_offensive_impact', 0),
                    home_defensive_impact=inj_data.get('home_defensive_impact', 0),
                    away_offensive_impact=inj_data.get('away_offensive_impact', 0),
                    away_defensive_impact=inj_data.get('away_defensive_impact', 0),
                    pace_impact=inj_data.get('pace_impact', 0),
                    significant_injuries=inj_data.get('significant_injuries', [])
                )
                significant = inj_data.get('significant_injuries', [])
                if significant:
                    injury_reports[game_id] = ", ".join(significant[:3])
            except Exception as e:
                logger.debug(f"No injury data for {game.home_team} vs {game.away_team}: {e}")

        game_recs = _analyze_single_game(
            game, odds_map, home_stats, away_stats, home_schedule, away_schedule,
            injury_impact, data_quality, totals_model, spreads_model,
            ev_calc, min_conf, db, logger
        )
        recommendations.extend(game_recs)

    quality_report = stats_fetcher.get_quality_report() if sport_type == SportType.NBA else None
    return recommendations, games, quality_report, injury_reports


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='SportsTotalBot V2 - AI Sports Betting Analysis'
    )
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--log-level', default='INFO', help='Log level')
    parser.add_argument('--performance', action='store_true', help='Show performance report')
    parser.add_argument('--update-results', action='store_true', help='Update results')
    parser.add_argument('--use-v2', action='store_true', help='Use V2 enhanced models')
    parser.add_argument('--backtest', action='store_true', help='Run backtesting analysis')
    parser.add_argument('--backtest-days', type=int, default=30, help='Days to backtest (default: 30)')
    parser.add_argument('--backtest-start', type=str, help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--backtest-end', type=str, help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--sport', default='all', choices=['nba', 'ncaab', 'all'], help='Sport to analyze (default: all)')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.log_level)

    # Load config
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.info("Please ensure config/config.yaml exists with valid settings")
        return 1

    # Initialize database
    db_path = config.get('database.path', 'data/sportstotalbot.db')
    db = Database(db_path)

    # Handle special commands
    if args.performance:
        try:
            stats = db.get_performance_stats()
            formatter = OutputFormatter()
            print(formatter.format_performance_report(stats))
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
        return 0

    if args.update_results:
        logger.info("Updating results for completed games...")
        try:
            updated = db.update_results_for_completed_games()
            logger.info(f"Updated {len(updated)} results")
        except Exception as e:
            logger.error(f"Failed to update results: {e}")
        return 0

    if args.backtest:
        logger.info("Running backtesting analysis...")
        try:
            backtester = Backtester(db_path=db_path, picks_path="data/picks")

            # Run backtest
            report = backtester.backtest_picks(
                start_date=args.backtest_start,
                end_date=args.backtest_end,
                days_back=args.backtest_days
            )

            # Print report
            print("\n" + report.format_report())

            # Save results
            output_file = backtester.save_backtest_results(report)
            logger.info(f"Backtest results saved to {output_file}")

        except Exception as e:
            logger.error(f"Failed to run backtest: {e}", exc_info=True)
            return 1
        return 0

    # Run main analysis
    logger.info("Starting SportsTotalBot V2 analysis...")
    logger.info(f"Version: {config.get('bot.version', '2.0.0')}")

    # Determine which sports to analyze
    sports_to_analyze = []
    if args.sport == 'all':
        # Get sports from config
        configured_sports = config.get('sports', ['nba'])
        for sport in configured_sports:
            if sport == 'nba':
                sports_to_analyze.append(('nba', SportType.NBA))
            elif sport == 'ncaab':
                sports_to_analyze.append(('ncaab', SportType.NCAA))
    else:
        # Single sport requested
        if args.sport == 'nba':
            sports_to_analyze.append(('nba', SportType.NBA))
        elif args.sport == 'ncaab':
            sports_to_analyze.append(('ncaab', SportType.NCAA))

    logger.info(f"Analyzing sports: {[s[0] for s in sports_to_analyze]}")

    recommendations = []
    games = {}
    quality_report = None
    injury_reports = {}

    try:
        # Analyze each sport
        for sport_name, sport_type in sports_to_analyze:
            logger.info(f"\n{'='*60}")
            logger.info(f"Analyzing {sport_name.upper()}")
            logger.info(f"{'='*60}")

            sport_recs, sport_games, sport_quality, sport_injuries = run_analysis(config, db, sport_type)

            recommendations.extend(sport_recs)
            games.update(sport_games)
            if sport_quality:
                if quality_report is None:
                    quality_report = sport_quality
                else:
                    # Merge quality reports
                    quality_report.total_teams += sport_quality.total_teams
                    quality_report.excellent += sport_quality.excellent
                    quality_report.good += sport_quality.good
                    quality_report.fair += sport_quality.fair
                    quality_report.poor += sport_quality.poor
            injury_reports.update(sport_injuries)

        # Update results for completed games
        results_summary = update_and_display_results(db, logger)

        # Format and output picks
        formatter = OutputFormatter()
        # Use compact format for console (grouped by game showing both totals and spreads)
        report = formatter.format_daily_picks(recommendations, games, quality_report, compact=True, injury_reports=injury_reports)
        print("\n" + report)

        # Save to files
        if recommendations:
            try:
                csv_file = formatter.save_picks_to_csv(recommendations, games)
                json_file = formatter.save_picks_to_json(recommendations, games)
                logger.info(f"Saved picks to {csv_file} and {json_file}")
            except Exception as e:
                logger.error(f"Failed to save picks: {e}")

        # Export results tracking data if results were updated
        if results_summary and results_summary.get('updated_count', 0) > 0:
            try:
                tracker = PickTracker(db_path=db_path)
                # Export tracking data with recent results
                tracking_csv = tracker.export_to_csv(days=30)
                tracking_json = tracker.export_to_json(days=30)
                logger.info(f"Saved results tracking to {tracking_csv} and {tracking_json}")
            except Exception as e:
                logger.error(f"Failed to save results tracking: {e}")

        # Send to Discord if configured
        if recommendations:
            discord_webhook = config.get('output.discord_webhook', '')
            if discord_webhook:
                try:
                    notifier = DiscordNotifier(discord_webhook)
                    # Use compact format for Discord
                    compact_report = formatter.format_daily_picks(recommendations, games, quality_report, compact=True)
                    notifier.send_picks(compact_report)
                except Exception as e:
                    logger.error(f"Failed to send Discord notification: {e}")

            # Send to Telegram if configured
            telegram_token = config.get('output.telegram_token', '') or os.environ.get('TELEGRAM_TOKEN', '')
            telegram_chat_id = config.get('output.telegram_chat_id', '') or os.environ.get('TELEGRAM_CHAT_ID', '')
            if telegram_token and telegram_chat_id:
                try:
                    tg = TelegramNotifier(bot_token=telegram_token, chat_id=telegram_chat_id)
                    tg.send_picks(sorted(recommendations, key=lambda r: r.ev, reverse=True)[:3], quality_report, games)
                except Exception as e:
                    logger.error(f"Failed to send Telegram notification: {e}")


        logger.info(f"Analysis complete. Found {len(recommendations)} +EV bets.")

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
