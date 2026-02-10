"""
Real-time NBA stats fetcher using nba_api (NBA.com unofficial API)
Scrapes live team stats without requiring API keys
"""

import requests
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.season import get_current_nba_season
import hashlib

logger = logging.getLogger(__name__)


class NBAStatsFetcher:
    """
    Fetch NBA stats from NBA.com using their public endpoints
    No API key required - uses public stats.nba.com endpoints
    """

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.nba.com/stats/',
            'Origin': 'https://www.nba.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })

        # NBA team ID mappings
        self.team_id_to_name = {
            1610612737: "Atlanta Hawks",
            1610612738: "Boston Celtics",
            1610612751: "Brooklyn Nets",
            1610612766: "Charlotte Hornets",
            1610612741: "Chicago Bulls",
            1610612739: "Cleveland Cavaliers",
            1610612742: "Dallas Mavericks",
            1610612743: "Denver Nuggets",
            1610612765: "Detroit Pistons",
            1610612744: "Golden State Warriors",
            1610612745: "Houston Rockets",
            1610612754: "Indiana Pacers",
            1610612746: "Los Angeles Clippers",
            1610612747: "Los Angeles Lakers",
            1610612763: "Memphis Grizzlies",
            1610612748: "Miami Heat",
            1610612749: "Milwaukee Bucks",
            1610612750: "Minnesota Timberwolves",
            1610612740: "New Orleans Pelicans",
            1610612752: "New York Knicks",
            1610612753: "Orlando Magic",
            1610612755: "Philadelphia 76ers",
            1610612756: "Phoenix Suns",
            1610612757: "Portland Trail Blazers",
            1610612758: "Sacramento Kings",
            1610612759: "San Antonio Spurs",
            1610612760: "Oklahoma City Thunder",
            1610612761: "Toronto Raptors",
            1610612762: "Utah Jazz",
            1610612764: "Washington Wizards",
        }

        self.team_name_to_id = {v: k for k, v in self.team_id_to_name.items()}

        # Short name mappings
        self.short_name_map = {
            "ATL": "Atlanta Hawks",
            "BOS": "Boston Celtics",
            "BKN": "Brooklyn Nets",
            "CHA": "Charlotte Hornets",
            "CHI": "Chicago Bulls",
            "CLE": "Cleveland Cavaliers",
            "DAL": "Dallas Mavericks",
            "DEN": "Denver Nuggets",
            "DET": "Detroit Pistons",
            "GSW": "Golden State Warriors",
            "HOU": "Houston Rockets",
            "IND": "Indiana Pacers",
            "LAC": "Los Angeles Clippers",
            "LAL": "Los Angeles Lakers",
            "MEM": "Memphis Grizzlies",
            "MIA": "Miami Heat",
            "MIL": "Milwaukee Bucks",
            "MIN": "Minnesota Timberwolves",
            "NOP": "New Orleans Pelicans",
            "NYK": "New York Knicks",
            "ORL": "Orlando Magic",
            "PHI": "Philadelphia 76ers",
            "PHX": "Phoenix Suns",
            "POR": "Portland Trail Blazers",
            "SAC": "Sacramento Kings",
            "SAS": "San Antonio Spurs",
            "TOR": "Toronto Raptors",
            "UTA": "Utah Jazz",
            "OKC": "Oklahoma City Thunder",
            "WAS": "Washington Wizards",
            "76ers": "Philadelphia 76ers",
            "Celtics": "Boston Celtics",
            "Nets": "Brooklyn Nets",
            "Knicks": "New York Knicks",
            "Clippers": "Los Angeles Clippers",
            "Lakers": "Los Angeles Lakers",
            "Warriors": "Golden State Warriors",
            "Rockets": "Houston Rockets",
            "Raptors": "Toronto Raptors",
            "Pacers": "Indiana Pacers",
            "Bucks": "Milwaukee Bucks",
            "Bulls": "Chicago Bulls",
            "Cavaliers": "Cleveland Cavaliers",
            "Heat": "Miami Heat",
            "Mavericks": "Dallas Mavericks",
            "Grizzlies": "Memphis Grizzlies",
            "Hawks": "Atlanta Hawks",
            "Hornets": "Charlotte Hornets",
            "Magic": "Orlando Magic",
            "Pelicans": "New Orleans Pelicans",
            "Pistons": "Detroit Pistons",
            "Nuggets": "Denver Nuggets",
            "Suns": "Phoenix Suns",
            "Blazers": "Portland Trail Blazers",
            "Kings": "Sacramento Kings",
            "Spurs": "San Antonio Spurs",
            "Jazz": "Utah Jazz",
            "Thunder": "Oklahoma City Thunder",
            "Wizards": "Washington Wizards",
            "Timberwolves": "Minnesota Timberwolves",
        }

    def normalize_team_name(self, team_name: str) -> str:
        """Normalize various team name formats to full name"""
        return self.short_name_map.get(team_name, team_name)

    def _get_cache_path(self, endpoint: str, params: dict = None) -> Path:
        """Generate cache file path for a request"""
        cache_key = f"{endpoint}_{json.dumps(params or {}, sort_keys=True)}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{cache_hash}.json"

    def _load_from_cache(self, cache_path: Path, max_age_hours: int = 6) -> Optional[dict]:
        """Load data from cache if fresh enough"""
        if not cache_path.exists():
            return None

        try:
            cache_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age = datetime.now() - cache_time

            if age < timedelta(hours=max_age_hours):
                with open(cache_path) as f:
                    return json.load(f)
            else:
                logger.debug(f"Cache expired for {cache_path.name}")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

        return None

    def _save_to_cache(self, cache_path: Path, data: dict):
        """Save data to cache"""
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def _make_request(
        self,
        url: str,
        params: dict = None,
        use_cache: bool = True,
        max_age_hours: int = 6
    ) -> Optional[dict]:
        """Make request to NBA.com with caching"""
        cache_path = self._get_cache_path(url, params)

        if use_cache:
            cached = self._load_from_cache(cache_path, max_age_hours)
            if cached:
                logger.debug(f"Using cached data for {url}")
                return cached

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if use_cache:
                self._save_to_cache(cache_path, data)

            return data

        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def _fetch_opponent_stats(self, team_id: int, season: str) -> Optional[dict]:
        """
        Fetch opponent stats (defensive stats) for a team using MeasureType=Opponent.
        This returns stats that opponents accumulate against this team, including points allowed.
        """
        url = "https://stats.nba.com/stats/leaguedashteamstats"
        params = {
            "LeagueID": "00",
            "Season": season,
            "SeasonType": "Regular Season",
            "MeasureType": "Opponent",  # CRITICAL: This returns opponent stats against this team
            "PerMode": "PerGame",
            "PlusMinus": "N",
            "PaceAdjust": "N",
            "Rank": "N",
            "Outcome": "",
            "Location": "",
            "Month": "0",
            "SeasonSegment": "",
            "DateFrom": "",
            "DateTo": "",
            "OpponentTeamID": "0",
            "VsConference": "",
            "VsDivision": "",
            "GameScope": "",
            "PlayerExperience": "",
            "PlayerPosition": "",
            "StarterBench": "",
            "GameSegment": "",
            "Period": "0",
            "ShotClockRange": "",
            "LastNGames": "0",
        }

        data = self._make_request(url, params, max_age_hours=6)

        if not data or 'resultSets' not in data:
            return None

        try:
            headers = data['resultSets'][0]['headers']
            rows = data['resultSets'][0]['rowSet']

            for row in rows:
                if row[0] == team_id:  # TEAM_ID is first column
                    return dict(zip(headers, row))

        except Exception as e:
            logger.error(f"Error parsing opponent stats: {e}")

        return None

    def get_team_stats(self, team_name: str) -> Optional[dict]:
        """
        Get current season stats for a team
        Returns team stats including offensive/defensive ratings, pace, etc.
        """
        normalized_name = self.normalize_team_name(team_name)
        team_id = self.team_name_to_id.get(normalized_name)

        if not team_id:
            logger.warning(f"Team ID not found for: {team_name}")
            return None

        # Get current season (using utility)
        season = get_current_nba_season()  # FIXED: Use utility function

        # NBA.com league dash team stats endpoint
        url = "https://stats.nba.com/stats/leaguedashteamstats"
        params = {
            "LeagueID": "00",
            "Season": season,
            "Season": get_current_nba_season(),
            "SeasonType": "Regular Season",
            "MeasureType": "Base",
            "PerMode": "PerGame",
            "PlusMinus": "N",
            "PaceAdjust": "N",
            "Rank": "N",
            "Outcome": "",
            "Location": "",
            "Month": "0",
            "SeasonSegment": "",
            "DateFrom": "",
            "DateTo": "",
            "OpponentTeamID": "0",
            "VsConference": "",
            "VsDivision": "",
            "GameScope": "",
            "PlayerExperience": "",
            "PlayerPosition": "",
            "StarterBench": "",
            "GameSegment": "",
            "Period": "0",
            "ShotClockRange": "",
            "LastNGames": "0",
        }

        data = self._make_request(url, params, max_age_hours=6)

        if not data or 'resultSets' not in data:
            logger.warning(f"No stats data returned for {team_name}")
            return None

        try:
            headers = data['resultSets'][0]['headers']
            rows = data['resultSets'][0]['rowSet']

            for row in rows:
                if row[0] == team_id:  # TEAM_ID is first column
                    team_dict = dict(zip(headers, row))

                    # CRITICAL FIX: Fetch opponent stats separately to get OPP_PTS
                    # The Base MeasureType doesn't include opponent points allowed
                    opponent_stats = self._fetch_opponent_stats(team_id, season)
                    if opponent_stats:
                        # Merge opponent stats into team_dict
                        # The Opponent MeasureType returns columns prefixed with OPP_
                        # OPP_PTS = average points opponents score against this team (points allowed)
                        team_dict.update({
                            'OPP_PTS': opponent_stats.get('OPP_PTS', 0),  # Points allowed per game
                        })

                    return self._parse_team_stats(team_dict)

        except Exception as e:
            logger.error(f"Error parsing stats for {team_name}: {e}")

        return None

    def _parse_team_stats(self, raw_stats: dict) -> dict:
        """Parse raw NBA stats into our format with calculated pace/ratings"""
        pts = raw_stats.get('PTS', 0) or 0
        fga = raw_stats.get('FGA', 0) or 0
        fta = raw_stats.get('FTA', 0) or 0
        oreb = raw_stats.get('OREB', 0) or 0
        tov = raw_stats.get('TOV', 0) or 0
        mins = raw_stats.get('MIN', 48.0) or 48.0

        possessions = fga + 0.44 * fta - oreb + tov

        pace = raw_stats.get('PACE', 0)
        if not pace and mins > 0:
            pace = possessions * 48.0 / mins

        offensive_rating = raw_stats.get('OFF_RATING', 0)
        if not offensive_rating and possessions > 0:
            offensive_rating = (pts / possessions) * 100.0

        defensive_rating = raw_stats.get('DEF_RATING', 0)
        opp_pts = raw_stats.get('OPP_PTS', 0) or 0
        if not defensive_rating and possessions > 0 and opp_pts > 0:
            defensive_rating = (opp_pts / possessions) * 100.0
        elif not defensive_rating:
            plus_minus = raw_stats.get('PLUS_MINUS', 0) or 0
            if offensive_rating > 0:
                defensive_rating = offensive_rating - plus_minus
            else:
                defensive_rating = 114.0

        return {
            'team_id': str(raw_stats.get('TEAM_ID', '')),
            'team_name': raw_stats.get('TEAM_NAME', ''),
            'games_played': raw_stats.get('GP', 0),
            'avg_points_scored': pts,
            'avg_points_allowed': opp_pts,
            'offensive_rating': round(offensive_rating, 1),
            'defensive_rating': round(defensive_rating, 1),
            'pace': round(pace, 1),
            'efg_pct': raw_stats.get('EFG_PCT', 0) or 0.50,
            'tov_pct': raw_stats.get('TOV_PCT', 0) or 0.14,
            'orb_pct': raw_stats.get('OREB_PCT', 0) or 0.26,
            'ft_rate': raw_stats.get('FTA_RATE', 0) or 0.21,
            'possessions': round(possessions, 1),
        }


    def get_team_last_5_games(self, team_name: str) -> List[float]:
        """
        Get points scored in last 5 games
        Returns list of points scored in recent games
        """
        normalized_name = self.normalize_team_name(team_name)
        team_id = self.team_name_to_id.get(normalized_name)

        if not team_id:
            return []

        # Use score endpoint to get recent games
        url = "https://stats.nba.com/stats/leaguedashteamstats"
        params = {
            "LeagueID": "00",
            "Season": get_current_nba_season(),
            "SeasonType": "Regular Season",
            "MeasureType": "Base",
            "PerMode": "PerGame",
            "LastNGames": "5",
        }

        # This is simplified - in production you'd use the game log endpoint
        # For now, return empty and let model use season averages
        return []

    def get_team_schedule(self, team_name: str) -> dict:
        """
        Get schedule information for fatigue calculations
        Returns rest days, back-to-back status, travel info
        """
        normalized_name = self.normalize_team_name(team_name)
        team_id = self.team_name_to_id.get(normalized_name)

        if not team_id:
            return {
                'days_rest': 2,
                'is_back_to_back': False,
                'is_third_in_4_days': False,
                'travel_distance_miles': 0,
                'time_zone_changes': 0,
            }

        # Get current season (using utility) scoreboard
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        data = self._make_request(url, max_age_hours=1)

        # Get team's game log
        url = f"https://stats.nba.com/stats/teamgamelog"
        params = {
            "TeamID": team_id,
            "LeagueID": "00",
            "Season": get_current_nba_season(),
            "Season": get_current_nba_season(),
            "SeasonType": "Regular Season",
            "Sorter": "DATE",
        }

        log_data = self._make_request(url, params, max_age_hours=6)

        if log_data and 'resultSets' in log_data:
            try:
                headers = log_data['resultSets'][0]['headers']
                rows = log_data['resultSets'][0]['rowSet']

                if len(rows) >= 2:
                    # Get last 2 games to calculate rest
                    last_game = rows[0]
                    second_last = rows[1]

                    # Find game date index
                    game_date_idx = headers.index('GAME_DATE')

                    # Parse dates and calculate rest
                    from datetime import datetime
                    def _parse_date(s):
                        # Handle various date formats from NBA API
                        # NBA.com returns uppercase month abbreviations like "APR 13, 2025"
                        formats = [
                            '%Y-%m-%dT%H:%M:%S',  # ISO format
                            '%Y-%m-%d',           # Simple date
                            '%m/%d/%Y',           # US format
                            '%b %d, %Y',          # Lowercase "Apr 13, 2025"
                            '%B %d, %Y',          # Full month name "April 13, 2025"
                        ]
                        
                        for fmt in formats:
                            try:
                                return datetime.strptime(s.strip(), fmt)
                            except ValueError:
                                continue
                        
                        # If all else fails, try case-insensitive month parsing for "APR 13, 2025" format
                        try:
                            parts = s.strip().split()
                            if len(parts) == 3:
                                month_map = {
                                    'JAN': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'APR': 'Apr',
                                    'MAY': 'May', 'JUN': 'Jun', 'JUL': 'Jul', 'AUG': 'Aug',
                                    'SEP': 'Sep', 'OCT': 'Oct', 'NOV': 'Nov', 'DEC': 'Dec'
                                }
                                parts[0] = month_map.get(parts[0].upper(), parts[0])
                                return datetime.strptime(' '.join(parts), '%b %d, %Y')
                        except Exception as e:
                            logger.debug(f"Failed to parse date with fallback: {s}, error: {e}")
                        
                        logger.warning(f"Failed to parse date: {s}, using current time")
                        return datetime.now()
                    last_date = _parse_date(last_game[game_date_idx])
                    today = datetime.now()
                    days_rest = (today - last_date.replace(tzinfo=None)).days

                    # Check for back-to-back
                    if len(rows) >= 2:
                        second_date = _parse_date(second_last[game_date_idx])
                        is_b2b = (last_date - second_date.replace(tzinfo=None)).days <= 1
                    else:
                        is_b2b = False

                    # Check 3 in 4 nights
                    is_3in4 = False
                    if len(rows) >= 3:
                        third_date = _parse_date(rows[2][game_date_idx])
                        if (last_date - third_date.replace(tzinfo=None)).days <= 3:
                            is_3in4 = True

                    return {
                        'days_rest': max(1, days_rest),
                        'is_back_to_back': is_b2b,
                        'is_third_in_4_days': is_3in4,
                        'travel_distance_miles': 0,  # Would need location data
                        'time_zone_changes': 0,  # Would need location data
                    }

            except Exception as e:
                logger.error(f"Error parsing schedule for {team_name}: {e}")

        # Default fallback
        return {
            'days_rest': 2,
            'is_back_to_back': False,
            'is_third_in_4_days': False,
            'travel_distance_miles': 0,
            'time_zone_changes': 0,
        }

    def get_all_team_stats(self) -> Dict[str, dict]:
        """Get stats for all NBA teams"""
        stats = {}

        for team_name in self.team_name_to_id.values():
            team_stats = self.get_team_stats(team_name)
            if team_stats:
                stats[team_name] = team_stats

        return stats
