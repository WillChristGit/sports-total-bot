#!/usr/bin/env python3
"""
Test script for Recursive Language Model Analyzer

Demonstrates how to use RLM to analyze large sports datasets
beyond context window limitations.

Usage:
    python test_rlm_analyzer.py [--provider glm|claude|openai]

Examples:
    # Test with GLM (default)
    python test_rlm_analyzer.py

    # Test with Claude
    python test_rlm_analyzer.py --provider claude

    # Test with sample data
    python test_rlm_analyzer.py --sample
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.analysis.recursive_analyzer import RecursiveAnalyzer, RLMConfig, create_analyzer
from src.data.models import Game, TeamStats, SportType
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_games(count: int = 50) -> list:
    """Generate test games for demonstration"""
    games = []
    teams = [
        "Lakers", "Celtics", "Warriors", "Nets", "Bucks",
        "Suns", "Heat", "Mavericks", "Nuggets", "76ers",
        "Clippers", "Raptors", "Timberwolves", "Jazz", "Grizzlies"
    ]

    base_time = datetime.now() + timedelta(hours=24)

    for i in range(count):
        home_idx = (i * 2) % len(teams)
        away_idx = (i * 2 + 1) % len(teams)

        game = Game(
            game_id=f"test_game_{i:04d}",
            sport=SportType.NBA,
            home_team=teams[home_idx],
            away_team=teams[away_idx],
            game_time=base_time + timedelta(hours=i)
        )
        games.append(game)

    return games


def generate_test_stats(teams: list) -> dict:
    """Generate test team statistics"""
    stats = {}

    for team in teams:
        stats[team] = TeamStats(
            team_id=team.lower().replace(" ", "_"),
            team_name=team,
            games_played=50,
            avg_points_scored=110.5 + hash(team) % 20,
            avg_points_allowed=108.3 + hash(team) % 15,
            offensive_rating=112.0 + hash(team) % 8,
            defensive_rating=110.0 + hash(team) % 8,
            pace=100.0 + hash(team) % 10
        )

    return stats


def test_basic_analysis(provider: str = "glm"):
    """Test basic RLM analysis with small dataset"""
    logger.info(f"Testing RLM with provider: {provider}")

    # Create analyzer
    analyzer = create_analyzer(provider=provider, max_chunk_size=10000)

    # Generate test data
    logger.info("Generating test data...")
    games = generate_test_games(20)
    stats = generate_test_stats([
        "Lakers", "Celtics", "Warriors", "Nets", "Bucks",
        "Suns", "Heat", "Mavericks", "Nuggets", "76ers"
    ])

    # Run analysis
    logger.info("Running RLM analysis...")
    result = analyzer.analyze_games(
        games=games,
        team_stats=stats,
        task="find_betting_edges"
    )

    # Print results
    print("\n" + "="*60)
    print("RLM ANALYSIS RESULTS")
    print("="*60)
    print(f"Recommendations: {len(result.recommendations)}")
    print(f"Chunks processed: {result.chunks_processed}")
    print(f"Depth reached: {result.depth_reached}")
    print(f"Tokens used: {result.total_tokens_used}")
    print(f"Estimated cost: ${result.estimated_cost:.4f}")
    print(f"Processing time: {result.processing_time:.2f}s")
    print("\nREASONING:")
    print(result.reasoning[:500])
    print("\n" + "="*60)

    return result


def test_large_dataset(provider: str = "glm"):
    """Test RLM with large dataset (demonstrates recursive splitting)"""
    logger.info(f"Testing RLM with large dataset (provider: {provider})")

    # Create analyzer with smaller chunk size to force recursion
    config = RLMConfig(
        provider=provider,
        max_chunk_size=5000,  # Small to trigger recursion
        max_depth=5
    )
    analyzer = RecursiveAnalyzer(config)

    # Generate large dataset
    logger.info("Generating large dataset (100 games)...")
    games = generate_test_games(100)
    teams = [
        "Lakers", "Celtics", "Warriors", "Nets", "Bucks",
        "Suns", "Heat", "Mavericks", "Nuggets", "76ers",
        "Clippers", "Raptors", "Timberwolves", "Jazz", "Grizzlies",
        "Pacers", "Hawks", "Knicks", "Thunder", "Blazers"
    ]
    stats = generate_test_stats(teams)

    # Run analysis
    logger.info("Running recursive analysis...")
    result = analyzer.analyze_games(
        games=games,
        team_stats=stats,
        task="find_betting_edges"
    )

    # Print results
    print("\n" + "="*60)
    print("LARGE DATASET RLM RESULTS")
    print("="*60)
    print(f"Games analyzed: {len(games)}")
    print(f"Recommendations: {len(result.recommendations)}")
    print(f"Chunks processed: {result.chunks_processed}")
    print(f"Max depth: {result.depth_reached}")
    print(f"Total tokens: {result.total_tokens_used}")
    print(f"Total cost: ${result.total_cost:.4f}")
    print(f"Processing time: {result.processing_time:.2f}s")
    print("\n" + "="*60)

    return result


def test_season_analysis(provider: str = "glm"):
    """Test analyzing entire season structure"""
    logger.info(f"Testing season analysis (provider: {provider})")

    analyzer = create_analyzer(provider=provider)

    # Create mock season data
    season_data = {
        "season": "2025-26",
        "league": "NBA",
        "games_analyzed": 1230,
        "teams": [
            {"name": team, "record": f"{40 + hash(team) % 20}-{20 + hash(team) % 20}"}
            for team in ["Lakers", "Celtics", "Warriors", "Nets", "Bucks"]
        ],
        "summary": "Complete 2025-26 NBA season analysis",
        "timestamp": datetime.now().isoformat()
    }

    result = analyzer.analyze_season(
        season_data=season_data,
        task="season_betting_analysis"
    )

    print("\n" + "="*60)
    print("SEASON ANALYSIS RESULTS")
    print("="*60)
    print(result.reasoning[:800])
    print("\n" + "="*60)

    return result


def test_with_real_data(provider: str = "glm"):
    """Test with real data if available"""
    logger.info("Testing with real sports data (if available)...")

    # Check for cached stats
    cache_dir = Path("data/cache")
    if not cache_dir.exists():
        logger.warning("No cached data found, skipping real data test")
        return None

    analyzer = create_analyzer(provider=provider)

    # Load cached team stats
    cache_files = list(cache_dir.glob("*.json"))
    if not cache_files:
        logger.warning("No cache files found")
        return None

    # Load first few cache files
    season_data = []
    for cache_file in cache_files[:5]:
        try:
            with open(cache_file) as f:
                data = json.load(f)
                season_data.append(data)
        except Exception as e:
            logger.debug(f"Failed to load {cache_file}: {e}")

    if not season_data:
        logger.warning("No valid cache data loaded")
        return None

    # Analyze
    logger.info(f"Analyzing {len(season_data)} cached files...")
    result = analyzer.analyze_season(
        season_data={"cached_stats": season_data},
        task="analyze_team_stats"
    )

    print("\n" + "="*60)
    print("REAL DATA ANALYSIS RESULTS")
    print("="*60)
    print(result.reasoning[:800])
    print("\n" + "="*60)

    return result


def main():
    """Main test runner"""
    load_dotenv()

    import argparse
    parser = argparse.ArgumentParser(description="Test RLM Analyzer")
    parser.add_argument("--provider", choices=["glm", "claude", "openai"],
                        default="glm", help="LLM provider")
    parser.add_argument("--test", choices=["basic", "large", "season", "real"],
                        default="basic", help="Test type")
    parser.add_argument("--sample", action="store_true",
                        help="Use sample data only")

    args = parser.parse_args()

    # Check API key
    if args.provider == "glm":
        if not os.getenv("GLM_API_KEY"):
            logger.error("GLM_API_KEY not found in environment")
            logger.error("Set it in .env file or export GLM_API_KEY=your_key")
            return 1

    # Run selected test
    try:
        if args.test == "basic":
            test_basic_analysis(args.provider)
        elif args.test == "large":
            test_large_dataset(args.provider)
        elif args.test == "season":
            test_season_analysis(args.provider)
        elif args.test == "real":
            test_with_real_data(args.provider)

        logger.info("Test completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
