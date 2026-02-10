"""
Results Tracker for SportsTotalBot

Fetches final NBA scores from free APIs and compares them to picks
to calculate performance metrics (W/L record, ROI, units, win rate).

Supported APIs:
1. balldontlie.io (free tier, no key required)
2. TheSportsDB (free, optional API key for higher limits)
3. RapidAPI NBA (requires API key)

Usage:
    tracker = ResultsTracker()
    results = tracker.track_results(date="2026-02-04")
    # Or track latest picks:
    results = tracker.track_latest_results()
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import requests

# Setup logging
logger = logging.getLogger(__name__)


class APIConfig:
    """Configuration for various score APIs"""

    # balldontlie.io - Free NBA API
    BALLDONTLIE_BASE = "https://api.balldontlie.io/v1"
    BALLDONTLIE_GAMES = f"{BALLDONTLIE_BASE}/games"

    # TheSportsDB - Free sports API
    THESPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
    THESPORTSDB_EVENTS = f"{THESPORTSDB_BASE}/eventsseasonleague.php"

    # RapidAPI NBA API (requires key)
    RAPIDAPI_BASE = "https://api-nba-v1.p.rapidapi.com"
    RAPIDAPI_GAMES = f"{RAPIDAPI_BASE}/games"
    RAPIDAPI_HEADERS = {
        "x-rapidapi-host": "api-nba-v1.p.rapidapi.com",
        "x-rapidapi-key": ""  # Set from environment
    }


class PickResult:
    """Represents the result of a single pick"""

    def __init__(self, pick_data: Dict[str, Any], game_result: Optional[Dict] = None):
        self.pick_data = pick_data
        self.game_result = game_result or {}

        # Parse pick data
        self.game_id = pick_data.get('game_id', '')
        self.sport = pick_data.get('sport', 'nba')
        self.bet_type = pick_data.get('bet_type', 'totals')
        self.side = pick_data.get('side', 'under')
        self.line = pick_data.get('line', 0.0)
        self.odds = pick_data.get('odds', -110)
        self.projected_value = pick_data.get('projected_value', 0.0)
        self.ev = pick_data.get('ev', 0.0)
        self.win_probability = pick_data.get('win_probability', 0.0)
        self.confidence = pick_data.get('confidence', 0.0)
        self.home_team = pick_data.get('home_team', '')
        self.away_team = pick_data.get('away_team', '')
        self.game_time = pick_data.get('game_time', '')

        # Result fields
        self.status = 'pending'  # pending, won, lost, push, cancelled
        self.actual_total = None
        self.actual_home_score = None
        self.actual_away_score = None
        self.actual_margin = None
        self.profit_loss = 0.0
        self.units = 0.0
        self.result_reasoning = ''

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'game_id': self.game_id,
            'sport': self.sport,
            'bet_type': self.bet_type,
            'side': self.side,
            'line': self.line,
            'odds': self.odds,
            'projected_value': self.projected_value,
            'ev': self.ev,
            'win_probability': self.win_probability,
            'confidence': self.confidence,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'game_time': self.game_time,
            'status': self.status,
            'actual_total': self.actual_total,
            'actual_home_score': self.actual_home_score,
            'actual_away_score': self.actual_away_score,
            'actual_margin': self.actual_margin,
            'profit_loss': self.profit_loss,
            'units': self.units,
            'result_reasoning': self.result_reasoning
        }


class ResultsTracker:
    """
    Tracks betting results by fetching final scores and comparing to picks
    """

    def __init__(self, picks_dir: Optional[str] = None, results_dir: Optional[str] = None):
        """
        Initialize the results tracker

        Args:
            picks_dir: Directory containing daily_picks_YYYYMMDD.json files
            results_dir: Directory to save result files
        """
        # Set default paths
        project_root = Path(__file__).parent.parent.parent
        self.picks_dir = Path(picks_dir) if picks_dir else project_root / "data" / "picks"
        self.results_dir = Path(results_dir) if results_dir else project_root / "data" / "results"

        # Ensure results directory exists
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Load API keys from environment
        self.rapidapi_key = os.getenv('RAPID_API_KEY', '')
        if self.rapidapi_key:
            APIConfig.RAPIDAPI_HEADERS['x-rapidapi-key'] = self.rapidapi_key

        # Team name normalization mapping (for API matching)
        self.team_name_map = self._build_team_name_map()

        logger.info(f"ResultsTracker initialized. Picks dir: {self.picks_dir}, Results dir: {self.results_dir}")

    def _build_team_name_map(self) -> Dict[str, str]:
        """
        Build mapping of various team name formats to standardized names
        Helps match team names from different APIs
        """
        return {
            # Standard NBA team names
            'Lakers': 'Los Angeles Lakers',
            'LA Lakers': 'Los Angeles Lakers',
            'Celtics': 'Boston Celtics',
            'Warriors': 'Golden State Warriors',
            'GS Warriors': 'Golden State Warriors',
            'Nets': 'Brooklyn Nets',
            'Knicks': 'New York Knicks',
            '76ers': 'Philadelphia 76ers',
            'Sixers': 'Philadelphia 76ers',
            'Raptors': 'Toronto Raptors',
            'Bulls': 'Chicago Bulls',
            'Cavaliers': 'Cleveland Cavaliers',
            'Cavs': 'Cleveland Cavaliers',
            'Pistons': 'Detroit Pistons',
            'Pacers': 'Indiana Pacers',
            'Bucks': 'Milwaukee Bucks',
            'Timberwolves': 'Minnesota Timberwolves',
            'T-Wolves': 'Minnesota Timberwolves',
            'Pelicans': 'New Orleans Pelicans',
            'Thunder': 'Oklahoma City Thunder',
            'OKC': 'Oklahoma City Thunder',
            'Blazers': 'Portland Trail Blazers',
            'Trail Blazers': 'Portland Trail Blazers',
            'Jazz': 'Utah Jazz',
            'Nuggets': 'Denver Nuggets',
            'Timberwolves': 'Minnesota Timberwolves',
            'Grizzlies': 'Memphis Grizzlies',
            'Kings': 'Sacramento Kings',
            'Mavericks': 'Dallas Mavericks',
            'Mavs': 'Dallas Mavericks',
            'Rockets': 'Houston Rockets',
            'Spurs': 'San Antonio Spurs',
            'Suns': 'Phoenix Suns',
            'Clippers': 'Los Angeles Clippers',
            'LA Clippers': 'Los Angeles Clippers',
            'Hawks': 'Atlanta Hawks',
            'Hornets': 'Charlotte Hornets',
            'Heat': 'Miami Heat',
            'Magic': 'Orlando Magic',
            'Wizards': 'Washington Wizards',
        }

    def normalize_team_name(self, name: str) -> str:
        """Normalize team name to standard format"""
        return self.team_name_map.get(name, name)

    def load_picks(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Load picks from daily_picks_YYYYMMDD.json file

        Args:
            date_str: Date in format YYYY-MM-DD or YYYYMMDD

        Returns:
            List of pick dictionaries
        """
        # Convert YYYY-MM-DD to YYYYMMDD
        if '-' in date_str:
            date_str = date_str.replace('-', '')

        picks_file = self.picks_dir / f"daily_picks_{date_str}.json"

        if not picks_file.exists():
            logger.warning(f"Picks file not found: {picks_file}")
            return []

        try:
            with open(picks_file, 'r') as f:
                picks = json.load(f)

            if not isinstance(picks, list):
                logger.error(f"Invalid picks format in {picks_file}")
                return []

            logger.info(f"Loaded {len(picks)} picks from {picks_file}")
            return picks

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing {picks_file}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading picks from {picks_file}: {e}")
            return []

    def fetch_scores_balldontlie(self, date: datetime) -> List[Dict]:
        """
        Fetch NBA scores from balldontlie.io API (free, no key required)

        Args:
            date: Date to fetch scores for

        Returns:
            List of game results with scores
        """
        try:
            # Format dates for API
            start_date = date.strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')

            params = {
                'start_date': start_date,
                'end_date': end_date,
                'per_page': 100
            }

            logger.info(f"Fetching scores from balldontlie.io for {start_date}")
            response = requests.get(
                APIConfig.BALLDONTLIE_GAMES,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                games = data.get('data', [])

                logger.info(f"Retrieved {len(games)} games from balldontlie.io")
                return self._normalize_balldontlie_games(games)
            else:
                logger.warning(f"balldontlie.io returned status {response.status_code}")
                return []

        except requests.RequestException as e:
            logger.error(f"Error fetching from balldontlie.io: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error with balldontlie.io: {e}")
            return []

    def _normalize_balldontlie_games(self, games: List[Dict]) -> List[Dict]:
        """Normalize balldontlie.io game data to standard format"""
        normalized = []

        for game in games:
            try:
                # Extract scores
                home_score = game.get('home_team_score')
                away_score = game.get('visitor_team_score')
                status = game.get('status', '')

                # Only include completed games
                if status != 'Final' or home_score is None or away_score is None:
                    continue

                # Get team names
                home_team = game.get('home_team', {}).get('full_name', '')
                away_team = game.get('visitor_team', {}).get('full_name', '')

                # Calculate total and margin
                total = home_score + away_score
                margin = home_score - away_score

                normalized.append({
                    'game_id': str(game.get('id', '')),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'total': total,
                    'margin': margin,
                    'status': status,
                    'date': game.get('date', ''),
                    'season': game.get('season', '')
                })
            except Exception as e:
                logger.debug(f"Error normalizing game: {e}")
                continue

        return normalized

    def fetch_scores_rapidapi(self, date: datetime) -> List[Dict]:
        """
        Fetch NBA scores from RapidAPI NBA API (requires API key)

        Args:
            date: Date to fetch scores for

        Returns:
            List of game results with scores
        """
        if not self.rapidapi_key:
            logger.warning("RapidAPI key not configured, skipping")
            return []

        try:
            date_str = date.strftime('%Y-%m-%d')

            logger.info(f"Fetching scores from RapidAPI for {date_str}")
            response = requests.get(
                APIConfig.RAPIDAPI_GAMES,
                headers=APIConfig.RAPIDAPI_HEADERS,
                params={'date': date_str},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                games = data.get('response', [])

                logger.info(f"Retrieved {len(games)} games from RapidAPI")
                return self._normalize_rapidapi_games(games)
            else:
                logger.warning(f"RapidAPI returned status {response.status_code}")
                return []

        except requests.RequestException as e:
            logger.error(f"Error fetching from RapidAPI: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error with RapidAPI: {e}")
            return []

    def _normalize_rapidapi_games(self, games: List[Dict]) -> List[Dict]:
        """Normalize RapidAPI game data to standard format"""
        normalized = []

        for game in games:
            try:
                scores = game.get('scores', {})
                home_score = scores.get('home', {}).get('points')
                away_score = scores.get('away', {}).get('points')
                status = game.get('status', {}).get('long', '')

                # Only include completed games
                if status != 'Finished' or home_score is None or away_score is None:
                    continue

                home_team = game.get('teams', {}).get('home', {}).get('name', '')
                away_team = game.get('teams', {}).get('away', {}).get('name', '')

                total = home_score + away_score
                margin = home_score - away_score

                normalized.append({
                    'game_id': str(game.get('id', '')),
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_score': home_score,
                    'away_score': away_score,
                    'total': total,
                    'margin': margin,
                    'status': status,
                    'date': game.get('date', {}).get('start', '')
                })
            except Exception as e:
                logger.debug(f"Error normalizing game: {e}")
                continue

        return normalized

    def match_game_to_pick(self, pick: Dict, games: List[Dict]) -> Optional[Dict]:
        """
        Match a game result to a pick using team names and other identifiers

        Args:
            pick: Pick dictionary
            games: List of game results

        Returns:
            Matching game result or None
        """
        pick_home = self.normalize_team_name(pick.get('home_team', ''))
        pick_away = self.normalize_team_name(pick.get('away_team', ''))
        pick_id = pick.get('game_id', '')
        pick_time = pick.get('game_time', '')

        # First try exact game ID match
        for game in games:
            if game.get('game_id') == pick_id:
                return game

        # Then try team name matching
        for game in games:
            game_home = self.normalize_team_name(game.get('home_team', ''))
            game_away = self.normalize_team_name(game.get('away_team', ''))

            # Check if teams match (in either order for safety)
            if (game_home == pick_home and game_away == pick_away):
                return game

        logger.debug(f"No match found for pick: {pick_away} @ {pick_home}")
        return None

    def evaluate_totals_pick(self, pick: PickResult, game: Dict) -> Tuple[str, float]:
        """
        Evaluate a totals (over/under) pick against actual game result

        Args:
            pick: PickResult object
            game: Game result dictionary

        Returns:
            Tuple of (status: str, profit_loss: float)
            Status: 'won', 'lost', 'push', 'pending'
        """
        actual_total = game.get('total', 0)
        line = pick.line
        side = pick.side
        odds = pick.odds

        pick.actual_total = actual_total
        pick.actual_home_score = game.get('home_score')
        pick.actual_away_score = game.get('away_score')

        # Calculate profit/loss based on American odds
        def calculate_profit(odds: int, stake: float = 1.0) -> float:
            """Calculate profit on $1 bet"""
            if odds > 0:
                return (odds / 100) * stake
            else:
                return (100 / abs(odds)) * stake

        # Determine win/loss
        if side == 'over':
            if actual_total > line:
                # Won by at least 0.5 points (no push on totals usually)
                profit = calculate_profit(odds)
                pick.status = 'won'
                pick.result_reasoning = f"Over {line}: Actual total {actual_total} (Over by {actual_total - line:.1f})"
                return 'won', profit
            elif actual_total == line:
                # Exact push (rare for totals with .5)
                pick.status = 'push'
                pick.result_reasoning = f"Push: Actual total {actual_total} equals line {line}"
                return 'push', 0.0
            else:
                # Lost
                profit = -1.0  # Lost the stake
                pick.status = 'lost'
                pick.result_reasoning = f"Over {line}: Actual total {actual_total} (Under by {line - actual_total:.1f})"
                return 'lost', profit
        else:  # under
            if actual_total < line:
                # Won
                profit = calculate_profit(odds)
                pick.status = 'won'
                pick.result_reasoning = f"Under {line}: Actual total {actual_total} (Under by {line - actual_total:.1f})"
                return 'won', profit
            elif actual_total == line:
                # Push
                pick.status = 'push'
                pick.result_reasoning = f"Push: Actual total {actual_total} equals line {line}"
                return 'push', 0.0
            else:
                # Lost
                profit = -1.0
                pick.status = 'lost'
                pick.result_reasoning = f"Under {line}: Actual total {actual_total} (Over by {actual_total - line:.1f})"
                return 'lost', profit

    def evaluate_spread_pick(self, pick: PickResult, game: Dict) -> Tuple[str, float]:
        """
        Evaluate a spread pick against actual game result

        Args:
            pick: PickResult object
            game: Game result dictionary

        Returns:
            Tuple of (status: str, profit_loss: float)
        """
        actual_margin = game.get('margin', 0)  # Positive = home won by this much
        line = pick.line  # Spread line (e.g., -9.7 means home favored by 9.7)
        side = pick.side  # 'home' or 'away'
        odds = pick.odds

        pick.actual_margin = actual_margin
        pick.actual_home_score = game.get('home_score')
        pick.actual_away_score = game.get('away_score')

        def calculate_profit(odds: int, stake: float = 1.0) -> float:
            """Calculate profit on $1 bet"""
            if odds > 0:
                return (odds / 100) * stake
            else:
                return (100 / abs(odds)) * stake

        # Determine covered side
        # If line is negative, home is favored
        # If line is positive, away is favored
        # The line represents how much the favored team must win by

        if side == 'home':
            # Betting on home team to cover
            # Need: home_score + line > away_score
            # Or: actual_margin > -line
            needed_margin = -line  # Convert line to margin needed

            if actual_margin > needed_margin:
                # Won (covered)
                profit = calculate_profit(odds)
                pick.status = 'won'
                pick.result_reasoning = f"Home {-line}: Home won by {actual_margin} (Covered by {actual_margin - needed_margin:.1f})"
                return 'won', profit
            elif abs(actual_margin - needed_margin) < 0.01:
                # Push
                pick.status = 'push'
                pick.result_reasoning = f"Push: Home margin {actual_margin} equals spread {needed_margin}"
                return 'push', 0.0
            else:
                # Lost (didn't cover)
                profit = -1.0
                pick.status = 'lost'
                pick.result_reasoning = f"Home {-line}: Home won by {actual_margin} (Failed to cover by {needed_margin - actual_margin:.1f})"
                return 'lost', profit
        else:  # away
            # Betting on away team to cover
            # Need: away_score + line > home_score
            # Or: actual_margin < line
            needed_margin = line

            if actual_margin < needed_margin:
                # Won (covered)
                profit = calculate_profit(odds)
                pick.status = 'won'
                pick.result_reasoning = f"Away {line}: Home won by {actual_margin} (Away covered by {needed_margin - actual_margin:.1f})"
                return 'won', profit
            elif abs(actual_margin - needed_margin) < 0.01:
                # Push
                pick.status = 'push'
                pick.result_reasoning = f"Push: Home margin {actual_margin} equals spread {needed_margin}"
                return 'push', 0.0
            else:
                # Lost
                profit = -1.0
                pick.status = 'lost'
                pick.result_reasoning = f"Away {line}: Home won by {actual_margin} (Away failed to cover by {actual_margin - needed_margin:.1f})"
                return 'lost', profit

    def calculate_units(self, pick: PickResult) -> float:
        """
        Calculate recommended units for a pick based on Kelly Criterion

        Args:
            pick: PickResult object

        Returns:
            Units to bet (1 unit = 1% of bankroll)
        """
        # Use Half-Kelly Criterion
        # Units = (EV / (odds multiplier)) * 100 * 0.5

        ev = pick.ev
        odds = pick.odds

        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = 1 + (odds / 100)
        else:
            decimal_odds = 1 + (100 / abs(odds))

        # Half-Kelly
        if decimal_odds > 1:
            kelly_units = (ev / (decimal_odds - 1)) * 100
        else:
            kelly_units = 0

        half_kelly = max(0, min(kelly_units * 0.5, 10))  # Cap at 10 units

        return round(half_kelly, 2)

    def track_results(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method: Load picks, fetch scores, evaluate results, save to file

        Args:
            date: Date string in format YYYY-MM-DD or YYYYMMDD.
                  If None, uses today's date.

        Returns:
            Dictionary with results summary and individual pick results
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # Parse date
        if '-' in date:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
        else:
            date_obj = datetime.strptime(date, '%Y%m%d')

        date_str = date_obj.strftime('%Y%m%d')

        logger.info(f"Tracking results for date: {date}")

        # Load picks
        picks = self.load_picks(date_str)
        if not picks:
            logger.warning(f"No picks found for {date}")
            return {
                'date': date,
                'picks_count': 0,
                'results': [],
                'summary': self._empty_summary()
            }

        # Fetch scores from available APIs
        games = []
        for fetch_func in [self.fetch_scores_balldontlie, self.fetch_scores_rapidapi]:
            try:
                games = fetch_func(date_obj)
                if games:
                    logger.info(f"Using {fetch_func.__name__} - got {len(games)} games")
                    break
            except Exception as e:
                logger.warning(f"{fetch_func.__name__} failed: {e}")
                continue

        if not games:
            logger.error("Failed to fetch scores from all APIs")
            return {
                'date': date,
                'picks_count': len(picks),
                'results': [],
                'summary': self._empty_summary(),
                'error': 'Failed to fetch game scores'
            }

        # Evaluate each pick
        results = []
        for pick_data in picks:
            pick = PickResult(pick_data)
            game = self.match_game_to_pick(pick_data, games)

            if game:
                pick.game_result = game

                # Evaluate based on bet type
                if pick.bet_type == 'totals':
                    status, profit_loss = self.evaluate_totals_pick(pick, game)
                elif pick.bet_type == 'spreads':
                    status, profit_loss = self.evaluate_spread_pick(pick, game)
                else:
                    logger.warning(f"Unsupported bet type: {pick.bet_type}")
                    continue

                pick.profit_loss = profit_loss
                pick.units = self.calculate_units(pick)
                results.append(pick.to_dict())
            else:
                # No matching game found - leave as pending
                logger.debug(f"No game result found for pick: {pick.away_team} @ {pick.home_team}")
                results.append(pick.to_dict())

        # Calculate summary statistics
        summary = self._calculate_summary(results)

        # Save results
        self._save_results(date_str, results, summary)

        return {
            'date': date,
            'picks_count': len(picks),
            'matched_count': len([r for r in results if r.get('status') != 'pending']),
            'results': results,
            'summary': summary
        }

    def track_latest_results(self, days_back: int = 1) -> Dict[str, Any]:
        """
        Track results for the most recent picks file

        Args:
            days_back: How many days back to look for picks

        Returns:
            Dictionary with results summary
        """
        # Find the most recent picks file
        for i in range(days_back + 1):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y%m%d')
            picks_file = self.picks_dir / f"daily_picks_{date_str}.json"

            if picks_file.exists():
                logger.info(f"Found picks file: {picks_file}")
                return self.track_results(date.strftime('%Y-%m-%d'))

        logger.warning(f"No picks files found in last {days_back} days")
        return {
            'error': f'No picks found in last {days_back} days'
        }

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary dictionary"""
        return {
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'pending': 0,
            'total_bets': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'total_units': 0.0,
            'roi': 0.0,
            'by_type': {
                'totals': {'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0.0},
                'spreads': {'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0.0}
            }
        }

    def _calculate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate summary statistics from results

        Args:
            results: List of pick result dictionaries

        Returns:
            Summary statistics dictionary
        """
        summary = self._empty_summary()

        for result in results:
            status = result.get('status', 'pending')
            bet_type = result.get('bet_type', 'totals')
            profit = result.get('profit_loss', 0.0)

            # Count by status
            if status == 'won':
                summary['wins'] += 1
            elif status == 'lost':
                summary['losses'] += 1
            elif status == 'push':
                summary['pushes'] += 1
            elif status == 'pending':
                summary['pending'] += 1

            # Only count profit/units for non-pending
            if status != 'pending':
                summary['total_profit'] += profit
                summary['total_units'] += result.get('units', 0.0)

            # By bet type
            if bet_type in summary['by_type']:
                if status == 'won':
                    summary['by_type'][bet_type]['wins'] += 1
                elif status == 'lost':
                    summary['by_type'][bet_type]['losses'] += 1
                elif status == 'push':
                    summary['by_type'][bet_type]['pushes'] += 1

                if status != 'pending':
                    summary['by_type'][bet_type]['profit'] += profit

        # Calculate totals
        summary['total_bets'] = summary['wins'] + summary['losses'] + summary['pushes']

        # Win rate (excluding pushes)
        decided_bets = summary['wins'] + summary['losses']
        summary['win_rate'] = (summary['wins'] / decided_bets * 100) if decided_bets > 0 else 0.0

        # ROI (profit / total bets)
        # Assuming $1 per bet
        summary['roi'] = (summary['total_profit'] / decided_bets * 100) if decided_bets > 0 else 0.0

        # Round values
        summary['win_rate'] = round(summary['win_rate'], 2)
        summary['total_profit'] = round(summary['total_profit'], 2)
        summary['total_units'] = round(summary['total_units'], 2)
        summary['roi'] = round(summary['roi'], 2)

        return summary

    def _save_results(self, date_str: str, results: List[Dict], summary: Dict) -> None:
        """
        Save results to JSON file

        Args:
            date_str: Date in YYYYMMDD format
            results: List of result dictionaries
            summary: Summary statistics dictionary
        """
        results_file = self.results_dir / f"{date_str}_results.json"

        output_data = {
            'date': date_str,
            'tracked_at': datetime.now().isoformat(),
            'summary': summary,
            'results': results
        }

        try:
            with open(results_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            logger.info(f"Results saved to {results_file}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")

    def load_historical_results(self, days: int = 30) -> List[Dict]:
        """
        Load historical results from the last N days

        Args:
            days: Number of days to look back

        Returns:
            List of historical result summaries
        """
        results = []
        end_date = datetime.now()

        for i in range(days):
            date = end_date - timedelta(days=i)
            date_str = date.strftime('%Y%m%d')
            results_file = self.results_dir / f"{date_str}_results.json"

            if results_file.exists():
                try:
                    with open(results_file, 'r') as f:
                        data = json.load(f)
                        results.append(data)
                except Exception as e:
                    logger.warning(f"Error loading {results_file}: {e}")
                    continue

        return results

    def get_performance_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate performance report over last N days

        Args:
            days: Number of days to include

        Returns:
            Performance report dictionary
        """
        historical = self.load_historical_results(days)

        if not historical:
            return {
                'period_days': days,
                'days_with_picks': 0,
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'pushes': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'roi': 0.0,
                'daily_results': []
            }

        # Aggregate statistics
        total_bets = 0
        total_wins = 0
        total_losses = 0
        total_pushes = 0
        total_profit = 0.0

        daily_results = []
        for day_data in historical:
            summary = day_data.get('summary', {})
            total_bets += summary.get('total_bets', 0)
            total_wins += summary.get('wins', 0)
            total_losses += summary.get('losses', 0)
            total_pushes += summary.get('pushes', 0)
            total_profit += summary.get('total_profit', 0.0)

            daily_results.append({
                'date': day_data.get('date', ''),
                'bets': summary.get('total_bets', 0),
                'wins': summary.get('wins', 0),
                'losses': summary.get('losses', 0),
                'profit': summary.get('total_profit', 0.0)
            })

        # Calculate overall statistics
        decided_bets = total_wins + total_losses
        win_rate = (total_wins / decided_bets * 100) if decided_bets > 0 else 0.0
        roi = (total_profit / decided_bets * 100) if decided_bets > 0 else 0.0

        return {
            'period_days': days,
            'days_with_picks': len(historical),
            'total_bets': total_bets,
            'wins': total_wins,
            'losses': total_losses,
            'pushes': total_pushes,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'roi': round(roi, 2),
            'daily_results': daily_results
        }


def main():
    """CLI interface for results tracking"""
    import argparse

    parser = argparse.ArgumentParser(description='Track SportsTotalBot results')
    parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--latest', action='store_true', help='Track latest picks')
    parser.add_argument('--report', type=int, default=30, help='Generate N-day performance report')
    parser.add_argument('--picks-dir', type=str, help='Override picks directory')
    parser.add_argument('--results-dir', type=str, help='Override results directory')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize tracker
    tracker = ResultsTracker(
        picks_dir=args.picks_dir,
        results_dir=args.results_dir
    )

    if args.latest:
        # Track latest picks
        results = tracker.track_latest_results()
        print(json.dumps(results, indent=2))
    elif args.report:
        # Generate performance report
        report = tracker.get_performance_report(args.report)
        print(json.dumps(report, indent=2))
    else:
        # Track specific date
        results = tracker.track_results(args.date)
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
