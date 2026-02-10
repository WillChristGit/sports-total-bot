#!/usr/bin/env python3
"""
SportsTotalBot - Main Bot Module (V2 - Enhanced)

This file contains the main logic with proper imports.
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Import from sibling modules (same package)
from .data.models import Game, SportType, BetType, OddsLine
from .data.fetchers import get_games_with_odds
from .storage.database import Database
from .analysis.projections_v2 import create_enhanced_projection_model, AdvancedTeamStats, ScheduleInfo
from .analysis.ev_calculator_v2 import EnhancedEVCalculator
from .output.formatter import OutputFormatter, DiscordNotifier
import yaml


# Team name mappings
TEAM_NAME_MAPPINGS = {
    'LAL': 'Los Angeles Lakers', 'BOS': 'Boston Celtics',
    'BKN': 'Brooklyn Nets', 'NYK': 'New York Knicks',
    'PHI': 'Philadelphia 76ers', 'TOR': 'Toronto Raptors',
    'GSW': 'Golden State Warriors', 'MIL': 'Milwaukee Bucks',
}


def normalize_team_name(team_name: str) -> str:
    return TEAM_NAME_MAPPINGS.get(team_name, team_name)


def setup_logging(log_level: str = "INFO"):
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(), logging.FileHandler('logs/sportstotalbot.log')]
    )
    return logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> dict:
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config: {e}")
        raise


def load_sports_config() -> dict:
    try:
        with open('config/sports_config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except:
        return {}


def validate_api_key(api_key: str) -> bool:
    return api_key and api_key != "YOUR_API_KEY_HERE" and len(api_key) > 10


def validate_game_data(game_data: dict) -> bool:
    required = ['id', 'home_team', 'away_team', 'commence_time']
    return all(field in game_data for field in required)


def parse_odds_api_response(raw_data: list) -> tuple:
    if not raw_data:
        return {}, {}

    games = {}
    odds_dict = {}

    for game_data in raw_data:
        if not validate_game_data(game_data):
            continue

        game_id = game_data.get('id')
        sport = SportType.NBA
        home_team = game_data.get('home_team', '')
        away_team = game_data.get('away_team', '')

        try:
            game_time = datetime.fromisoformat(game_data.get('commence_time', '').replace('Z', '+00:00'))
        except ValueError:
            continue

        game = Game(game_id=game_id, sport=sport, home_team=home_team, away_team=away_team, game_time=game_time)
        games[game_id] = game

        # Aggregate odds
        over_odds, under_odds, total_lines = [], [], []
        for bookmaker in game_data.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market.get('key') == 'totals':
                    for outcome in market.get('outcomes', []):
                        line, price = outcome.get('point'), outcome.get('price')
                        if line is not None and price is not None:
                            total_lines.append(line)
                            if outcome.get('name') == 'Over':
                                over_odds.append(price)
                            elif outcome.get('name') == 'Under':
                                under_odds.append(price)

        if total_lines and over_odds and under_odds:
            odds = OddsLine(
                game_id=game_id, sport=sport, bet_type=BetType.TOTALS,
                total_line=sum(total_lines) / len(total_lines),
                over_odds=round(sum(over_odds) / len(over_odds)),
                under_odds=round(sum(under_odds) / len(under_odds)),
                book_name="consensus", update_time=datetime.now()
            )
            odds_dict[game_id] = odds

    logging.info(f"Parsed {len(games)} games with odds")
    return games, odds_dict


def create_enhanced_team_stats(team_name: str) -> AdvancedTeamStats:
    return AdvancedTeamStats(
        team_id=team_name[:3].upper(), team_name=team_name, games_played=50,
        avg_points_scored=115.0, avg_points_allowed=114.0,
        offensive_rating=115.5, defensive_rating=114.5,
        efg_pct=0.520, tov_pct=0.135, orb_pct=0.260, ft_rate=0.210,
        pace=100.5, last_5_points_scored=[110, 115, 120, 112, 118],
        last_5_points_allowed=[115, 112, 118, 120, 116]
    )


def create_schedule_info() -> ScheduleInfo:
    return ScheduleInfo(days_rest=2, is_back_to_back=False, is_third_in_4_days=False)


def run_analysis(config: dict, db: Database):
    logger = logging.getLogger(__name__)
    api_key = config.get('api_keys', {}).get('the_odds_api', '')

    if not validate_api_key(api_key):
        logger.error("Invalid API key! Get one at https://the-odds-api.com/")
        return [], {}

    try:
        raw_games = get_games_with_odds(api_key, sport="nba")
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        return [], {}

    if not raw_games:
        logger.warning("No games found (NBA off-season?)")
        return [], {}

    logger.info(f"Found {len(raw_games)} games")
    games, odds_data = parse_odds_api_response(raw_games)

    for game in games.values():
        db.save_game(game)

    sports_config = load_sports_config()
    nba_config = sports_config.get('nba', {}).get('model', {})
    model = create_enhanced_projection_model(SportType.NBA, nba_config)

    min_ev = config.get('analysis', {}).get('min_ev_threshold', 0.015)
    min_conf = config.get('analysis', {}).get('min_confidence', 0.525)
    ev_calc = EnhancedEVCalculator(min_ev_threshold=min_ev)

    recommendations = []

    for game_id, odds in odds_data.items():
        game = games.get(game_id)
        if not game:
            continue

        logger.info(f"Analyzing: {game.away_team} @ {game.home_team}")

        home_stats = create_enhanced_team_stats(game.home_team)
        away_stats = create_enhanced_team_stats(game.away_team)
        home_schedule = create_schedule_info()
        away_schedule = create_schedule_info()

        try:
            projection = model.project_game(game, home_stats, away_stats, home_schedule, away_schedule)
        except Exception as e:
            logger.error(f"Projection failed: {e}")
            continue

        logger.info(f"  Projection: {projection.projected_total} (Line: {odds.total_line}, Conf: {projection.confidence:.0%})")

        try:
            recs = ev_calc.calculate_totals_ev(projection, odds, min_confidence=min_conf)
        except Exception as e:
            logger.error(f"EV calculation failed: {e}")
            continue

        for rec in recs:
            db.save_recommendation(rec)
            recommendations.append(rec)

    return recommendations, games


def main():
    parser = argparse.ArgumentParser(description='SportsTotalBot V2')
    parser.add_argument('--config', default='config/config.yaml')
    parser.add_argument('--log-level', default='INFO')
    parser.add_argument('--performance', action='store_true')
    parser.add_argument('--update-results', action='store_true')

    args = parser.parse_args()
    logger = setup_logging(args.log_level)

    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return 1

    db = Database(config.get('database', {}).get('path', 'data/sportstotalbot.db'))

    if args.performance:
        stats = db.get_performance_stats()
        formatter = OutputFormatter()
        print(formatter.format_performance_report(stats))
        return 0

    if args.update_results:
        logger.info("Updating results...")
        updated = db.update_results_for_completed_games()
        logger.info(f"Updated {len(updated)} results")
        return 0

    logger.info("Starting SportsTotalBot V2 analysis...")

    try:
        recommendations, games = run_analysis(config, db)
        formatter = OutputFormatter()
        report = formatter.format_daily_picks(recommendations, games)
        print("\n" + report)

        if recommendations:
            formatter.save_picks_to_csv(recommendations, games)
            formatter.save_picks_to_json(recommendations, games)
            logger.info(f"Saved picks for {len(recommendations)} bets")

        logger.info(f"Analysis complete. Found {len(recommendations)} +EV bets.")

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
