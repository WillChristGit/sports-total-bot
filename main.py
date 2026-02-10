#!/usr/bin/env python3
"""
SportsTotalBot - Main Entry Point

An AI-powered sports betting analysis bot that identifies
positive EV (Expected Value) betting opportunities on sports totals.
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data.models import Game, SportType, BetType, OddsLine
from data.fetchers import get_games_with_odds, NBAStatsFetcher
from storage.database import Database
from analysis.projections import create_projection_model
from analysis.ev_calculator import EVCalculator
from output.formatter import OutputFormatter, DiscordNotifier
import yaml


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/sportstotalbot.log')
        ]
    )

    # Add colorlog if available
    try:
        import colorlog
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logging.getLogger().addHandler(handler)
    except ImportError:
        pass

    return logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def parse_odds_api_response(raw_data: list) -> tuple[dict, dict]:
    """
    Parse the Odds API response into Games and Odds objects

    Returns:
        Tuple of (games_dict, odds_dict)
    """
    games = {}
    odds_list = {}

    for game_data in raw_data:
        game_id = game_data.get('id')
        sport = SportType.NBA  # Default to NBA for now

        # Parse game info
        home_team = game_data.get('home_team')
        away_team = game_data.get('away_team')
        game_time = datetime.fromisoformat(game_data.get('commence_time').replace('Z', '+00:00'))

        game = Game(
            game_id=game_id,
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            game_time=game_time
        )
        games[game_id] = game

        # Parse odds
        for bookmaker in game_data.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market.get('key') == 'totals':
                    for outcome in market.get('outcomes', []):
                        if outcome.get('name') == 'Over':
                            total_line = outcome.get('point')
                            over_odds = outcome.get('price')

                            # Create odds line
                            odds = OddsLine(
                                game_id=game_id,
                                sport=sport,
                                bet_type=BetType.TOTALS,
                                total_line=total_line,
                                over_odds=over_odds,
                                under_odds=None,  # Will be filled from next outcome
                                book_name=bookmaker.get('title', 'unknown'),
                                update_time=datetime.now()
                            )
                        elif outcome.get('name') == 'Under':
                            # Update the odds object with under odds
                            if game_id in odds_list:
                                odds_list[game_id].under_odds = outcome.get('price')

                    # Store the odds
                    odds_list[game_id] = odds

    return games, odds_list


def run_analysis(config: dict, db: Database) -> list:
    """
    Main analysis pipeline

    1. Fetch games and odds
    2. Get team statistics
    3. Generate projections
    4. Calculate EV
    5. Return recommendations
    """
    logger = logging.getLogger(__name__)
    api_key = config.get('api_keys', {}).get('the_odds_api', '')

    if not api_key or api_key == "YOUR_API_KEY_HERE":
        logger.error("No API key configured! Please set the_odds_api in config/config.yaml")
        logger.info("Get a free API key at: https://the-odds-api.com/")
        return []

    # Fetch games with odds
    logger.info("Fetching games and odds...")
    raw_games = get_games_with_odds(api_key, sport="nba")

    if not raw_games:
        logger.warning("No games found")
        return []

    logger.info(f"Found {len(raw_games)} games")

    # Parse into models
    games, odds_data = parse_odds_api_response(raw_games)

    # Save games to database
    for game in games.values():
        db.save_game(game)

    # Fetch team stats
    logger.info("Fetching team statistics...")
    stats_fetcher = NBAStatsFetcher()
    team_stats = stats_fetcher.get_team_stats()

    # Create team stats lookup
    stats_by_team = {}
    for stats in team_stats:
        team_name = stats.get('team_name', '')
        # Map to a format that matches odds API
        # This would need proper team name mapping
        stats_by_team[team_name] = stats

    # Get sport-specific config
    sports_config = {}
    try:
        with open('config/sports_config.yaml', 'r') as f:
            sports_config = yaml.safe_load(f)
    except:
        pass

    nba_config = sports_config.get('nba', {}).get('model', {})

    # Create projection model
    model = create_projection_model(SportType.NBA, nba_config)

    # Create EV calculator
    min_ev = config.get('analysis', {}).get('min_ev_threshold', 0.02)
    min_conf = config.get('analysis', {}).get('min_confidence', 0.55)
    ev_calc = EVCalculator(min_ev_threshold=min_ev)

    recommendations = []

    # Analyze each game
    for game_id, odds in odds_data.items():
        game = games.get(game_id)

        if not game:
            continue

        logger.info(f"Analyzing: {game.away_team} @ {game.home_team}")

        # For MVP, use simple stats based on team names
        # In production, would properly map team IDs
        home_stats = create_mock_stats(game.home_team)
        away_stats = create_mock_stats(game.away_team)

        # Generate projection
        projection = model.project_game(game, home_stats, away_stats)

        logger.info(f"  Projection: {projection.projected_total} (Line: {odds.total_line})")

        # Calculate EV
        recs = ev_calc.calculate_totals_ev(projection, odds, min_confidence=min_conf)

        for rec in recs:
            db.save_recommendation(rec)
            recommendations.append(rec)

    return recommendations, games


def create_mock_stats(team_name: str):
    """Create mock team stats for MVP"""
    from data.models import TeamStats

    # These would be real stats in production
    return TeamStats(
        team_id=team_name[:3].upper(),
        team_name=team_name,
        games_played=50,
        avg_points_scored=115.0,
        avg_points_allowed=114.0,
        offensive_rating=115.0,
        defensive_rating=114.0,
        pace=100.0,
        last_5_points_scored=[110, 115, 120, 112, 118],
        last_5_points_allowed=[115, 112, 118, 120, 116]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='SportsTotalBot - AI Sports Betting Analysis')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--log-level', default='INFO', help='Log level')
    parser.add_argument('--performance', action='store_true', help='Show performance report')
    parser.add_argument('--update-results', action='store_true', help='Update results for completed games')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving to database')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.log_level)

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error(f"Config file not found: {args.config}")
        logger.info("Please copy config/config.yaml.example to config/config.yaml and add your API keys")
        return 1

    # Initialize database
    db = Database(config.get('database', {}).get('path', 'data/sportstotalbot.db'))

    # Handle special commands
    if args.performance:
        stats = db.get_performance_stats()
        formatter = OutputFormatter()
        print(formatter.format_performance_report(stats))
        return 0

    if args.update_results:
        logger.info("Updating results for completed games...")
        updated = db.update_results_for_completed_games()
        logger.info(f"Updated {len(updated)} results")
        return 0

    # Run main analysis
    logger.info("Starting SportsTotalBot analysis...")
    logger.info(f"Version {config.get('bot', {}).get('version', '1.0.0')}")

    try:
        recommendations, games = run_analysis(config, db)

        # Format and output
        formatter = OutputFormatter()
        report = formatter.format_daily_picks(recommendations, games)
        print("\n" + report)

        # Save to files
        if recommendations:
            csv_file = formatter.save_picks_to_csv(recommendations, games)
            json_file = formatter.save_picks_to_json(recommendations, games)
            logger.info(f"Saved picks to {csv_file} and {json_file}")

            # Send to Discord if configured
            discord_webhook = config.get('output', {}).get('discord_webhook', '')
            if discord_webhook:
                notifier = DiscordNotifier(discord_webhook)
                notifier.send_picks(report)

        logger.info(f"Analysis complete. Found {len(recommendations)} +EV bets.")

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
