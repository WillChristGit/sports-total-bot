"""
Alternative NBA Stats Data Sources
Fetches NBA team statistics from multiple APIs when NBA.com is blocked.

Sources tried in priority order:
1. balldontlie.io - Free NBA API, no key needed
2. api.sportsdata.io - Free tier available
3. ESPN API - Public endpoints
4. the-odds-api.com - Check if they have team stats
5. Web scraping fallback - basketball-reference.com

Author: SportsTotalBot
Date: 2026-02-06
"""

import requests
import json
import logging
import time
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

from src.utils.season import get_current_nba_season
from src.utils.retry import retry_on_exception

logger = logging.getLogger(__name__)


class DataSourceError(Exception):
    """Base exception for data source errors"""
    pass


class BallDontLieAPI:
    """
    balldontlie.io API - Free NBA stats, no API key required

    API Docs: https://balldontlie.io/docs
    Rate Limit: 60 requests/minute
    """

    BASE_URL = "https://api.balldontlie.io/v1"

    # Team name mappings (balldontlie uses different names)
    TEAM_MAPPINGS = {
        "Atlanta Hawks": "ATL",
        "Boston Celtics": "BOS",
        "Brooklyn Nets": "BKN",
        "Charlotte Hornets": "CHA",
        "Chicago Bulls": "CHI",
        "Cleveland Cavaliers": "CLE",
        "Dallas Mavericks": "DAL",
        "Denver Nuggets": "DEN",
        "Detroit Pistons": "DET",
        "Golden State Warriors": "GSW",
        "Houston Rockets": "HOU",
        "Indiana Pacers": "IND",
        "Los Angeles Clippers": "LAC",
        "Los Angeles Lakers": "LAL",
        "Memphis Grizzlies": "MEM",
        "Miami Heat": "MIA",
        "Milwaukee Bucks": "MIL",
        "Minnesota Timberwolves": "MIN",
        "New Orleans Pelicans": "NOP",
        "New York Knicks": "NYK",
        "Oklahoma City Thunder": "OKC",
        "Orlando Magic": "ORL",
        "Philadelphia 76ers": "PHI",
        "Phoenix Suns": "PHX",
        "Portland Trail Blazers": "POR",
        "Sacramento Kings": "SAC",
        "San Antonio Spurs": "SAS",
        "Toronto Raptors": "TOR",
        "Utah Jazz": "UTA",
        "Washington Wizards": "WAS",
    }

    # Reverse mapping from abbreviation to full name
    ABBREV_TO_FULL = {v: k for k, v in TEAM_MAPPINGS.items()}

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })

        # Cache for team stats to avoid repeated API calls
        self._stats_cache = {}

    def _get_team_id(self, team_name: str) -> Optional[int]:
        """Get balldontlie team ID from team name"""
        # Try direct full name match
        abbrev = self.TEAM_MAPPINGS.get(team_name)
        if not abbrev:
            # Try to find partial match
            for full, abbr in self.TEAM_MAPPINGS.items():
                if team_name.lower() in full.lower() or full.lower() in team_name.lower():
                    abbrev = abbr
                    break

        if not abbrev:
            return None

        # Fetch teams to get ID
        try:
            url = f"{self.BASE_URL}/teams"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'data' in data:
                for team in data['data']:
                    if team.get('abbreviation') == abbrev:
                        return team.get('id')
        except Exception as e:
            logger.debug(f"Failed to get team ID for {team_name}: {e}")

        return None

    @retry_on_exception((requests.RequestException, DataSourceError), max_retries=3)
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """
        Get team statistics from balldontlie.io

        Returns:
            Dict with keys: points_per_game, opp_points_per_game, pace,
                          offensive_rating, defensive_rating, etc.
        """
        # Check cache first
        if team_name in self._stats_cache:
            return self._stats_cache[team_name]

        team_id = self._get_team_id(team_name)
        if not team_id:
            logger.debug(f"Could not find balldontlie ID for {team_name}")
            return None

        try:
            # Get current season
            season = get_current_nba_season()
            season_year = int(season.split('-')[0])

            # Get team stats
            url = f"{self.BASE_URL}/stats"
            params = {
                'team_ids[]': team_id,
                'season': season_year,
                'per_page': 1,  # Just need aggregate
                'postseason': False,
            }

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data or not data['data']:
                logger.debug(f"No stats data for {team_name} from balldontlie")
                return None

            # Parse response
            stats_data = data['data'][0]

            # Calculate derived stats
            points = stats_data.get('pts', 0) or 0
            opp_points = stats_data.get('pts', 0) or 0  # API limitation
            games = stats_data.get('games', 1) or 1

            # Estimate pace and ratings from available data
            pace = stats_data.get('pace', 99.5)
            if not pace:
                pace = 99.5  # League average

            # Estimate offensive/defensive rating
            offensive_rating = stats_data.get('off_rating', 114.0)
            defensive_rating = stats_data.get('def_rating', 114.0)

            result = {
                'points_per_game': points / games if games > 0 else points,
                'opp_points_per_game': opp_points,  # Limited by API
                'offensive_rating': offensive_rating,
                'defensive_rating': defensive_rating,
                'pace': pace,
                'efg_pct': stats_data.get('fg_pct', 0.520) / 100.0,
                'tov_pct': stats_data.get('turnover', 0.135),
                'orb_pct': stats_data.get('oreb', 0.260),
                'ft_rate': stats_data.get('ftm', 0.210),
                'games_played': games,
                'source': 'balldontlie',
            }

            # Cache the result
            self._stats_cache[team_name] = result
            logger.info(f"Fetched {team_name} stats from balldontlie.io")
            return result

        except Exception as e:
            logger.warning(f"BallDontLie API error for {team_name}: {e}")
            return None


class SportsDataIO:
    """
    api.sportsdata.io - NBA stats with free tier

    API Docs: https://sportsdata.io/developers/api-documentation/nba
    Free Tier: 500 requests/month
    Requires API key (set as SPORTSDATAIO_KEY in .env)
    """

    BASE_URL = "https://api.sportsdata.io/v3/nba"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({
                'Ocp-Apim-Subscription-Key': api_key,
            })

        self._stats_cache = {}

    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)

    @retry_on_exception((requests.RequestException, DataSourceError), max_retries=3)
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """Get team statistics from SportsData.io"""
        if not self.is_available():
            logger.debug("SportsData.io API key not configured")
            return None

        # Check cache
        if team_name in self._stats_cache:
            return self._stats_cache[team_name]

        try:
            # Get current season
            season = get_current_nba_season()
            season_year = int(season.split('-')[0])

            # SportsData.io uses different team format - need to map
            team_abbrev = self._map_team_name(team_name)
            if not team_abbrev:
                return None

            # Get team stats endpoint
            url = f"{self.BASE_URL}/scores/json/TeamSeasonStats/{season_year}"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Find the team
            team_data = None
            if isinstance(data, list):
                for team in data:
                    if team.get('Key') == team_abbrev or team.get('Abbreviation') == team_abbrev:
                        team_data = team
                        break

            if not team_data:
                logger.debug(f"Could not find {team_name} in SportsData.io response")
                return None

            result = {
                'points_per_game': team_data.get('PointsPerGame', 112.5),
                'opp_points_per_game': team_data.get('OpponentPointsPerGame', 112.5),
                'offensive_rating': team_data.get('OffensiveRating', 114.0),
                'defensive_rating': team_data.get('DefensiveRating', 114.0),
                'pace': team_data.get('Pace', 99.5),
                'efg_pct': team_data.get('EffectiveFieldGoalPercentage', 52.0) / 100.0,
                'tov_pct': team_data.get('TurnoverPercentage', 13.5),
                'orb_pct': team_data.get('OffensiveReboundPercentage', 26.0),
                'ft_rate': team_data.get('FreeThrowRate', 21.0),
                'games_played': team_data.get('Games', 0),
                'source': 'sportsdataio',
            }

            self._stats_cache[team_name] = result
            logger.info(f"Fetched {team_name} stats from SportsData.io")
            return result

        except Exception as e:
            logger.warning(f"SportsData.io error for {team_name}: {e}")
            return None

    def _map_team_name(self, team_name: str) -> Optional[str]:
        """Map team name to SportsData.io abbreviation"""
        mapping = {
            "Atlanta Hawks": "ATL",
            "Boston Celtics": "BOS",
            "Brooklyn Nets": "BKN",
            "Charlotte Hornets": "CHA",
            "Chicago Bulls": "CHI",
            "Cleveland Cavaliers": "CLE",
            "Dallas Mavericks": "DAL",
            "Denver Nuggets": "DEN",
            "Detroit Pistons": "DET",
            "Golden State Warriors": "GSW",
            "Houston Rockets": "HOU",
            "Indiana Pacers": "IND",
            "Los Angeles Clippers": "LAC",
            "Los Angeles Lakers": "LAL",
            "Memphis Grizzlies": "MEM",
            "Miami Heat": "MIA",
            "Milwaukee Bucks": "MIL",
            "Minnesota Timberwolves": "MIN",
            "New Orleans Pelicans": "NOP",
            "New York Knicks": "NYK",
            "Oklahoma City Thunder": "OKC",
            "Orlando Magic": "ORL",
            "Philadelphia 76ers": "PHI",
            "Phoenix Suns": "PHX",
            "Portland Trail Blazers": "POR",
            "Sacramento Kings": "SAC",
            "San Antonio Spurs": "SAS",
            "Toronto Raptors": "TOR",
            "Utah Jazz": "UTA",
            "Washington Wizards": "WAS",
        }
        return mapping.get(team_name)


class ESPNAPI:
    """
    ESPN Public API - No API key required

    Base URL: https://site.api.espn.com/apis/site/v2/sports/basketball/nba
    Note: Limited stats available, returns defaults for most metrics
    """

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })

        self._stats_cache = {}

    def _get_team_id(self, team_name: str) -> Optional[str]:
        """Get ESPN team ID"""
        # ESPN uses specific IDs
        team_ids = {
            "Atlanta Hawks": "1",
            "Boston Celtics": "2",
            "Brooklyn Nets": "17",
            "Charlotte Hornets": "30",
            "Chicago Bulls": "4",
            "Cleveland Cavaliers": "5",
            "Dallas Mavericks": "6",
            "Denver Nuggets": "7",
            "Detroit Pistons": "8",
            "Golden State Warriors": "9",
            "Houston Rockets": "10",
            "Indiana Pacers": "11",
            "Los Angeles Clippers": "12",
            "Los Angeles Lakers": "13",
            "Memphis Grizzlies": "29",
            "Miami Heat": "14",
            "Milwaukee Bucks": "15",
            "Minnesota Timberwolves": "16",
            "New Orleans Pelicans": "3",
            "New York Knicks": "18",
            "Oklahoma City Thunder": "25",
            "Orlando Magic": "19",
            "Philadelphia 76ers": "20",
            "Phoenix Suns": "21",
            "Portland Trail Blazers": "22",
            "Sacramento Kings": "23",
            "San Antonio Spurs": "24",
            "Toronto Raptors": "28",
            "Utah Jazz": "26",
            "Washington Wizards": "27",
        }
        return team_ids.get(team_name)

    @retry_on_exception((requests.RequestException, DataSourceError), max_retries=2)
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """
        Get team statistics from ESPN

        Note: ESPN API provides limited team stats. This is primarily a fallback
        to verify connectivity rather than a reliable stats source.
        """
        team_id = self._get_team_id(team_name)
        if not team_id:
            return None

        # Check cache
        cache_key = f"espn_{team_name}"
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        try:
            # Get team info with stats
            url = f"{self.BASE_URL}/teams/{team_id}"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract stats from the response
            team_data = data.get('team', {})
            stats = team_data.get('record', {})

            # ESPN provides limited stats, need to estimate
            result = {
                'points_per_game': team_data.get('averagePoints', 112.5),
                'opp_points_per_game': team_data.get('averagePointsAllowed', 112.5),
                'offensive_rating': 114.0,  # Not directly available
                'defensive_rating': 114.0,  # Not directly available
                'pace': 99.5,  # Not directly available
                'efg_pct': 0.520,
                'tov_pct': 0.135,
                'orb_pct': 0.260,
                'ft_rate': 0.210,
                'games_played': stats.get('items', [{}])[0].get('value', '0-0').split('-')[0] if stats.get('items') else 0,
                'source': 'espn',
            }

            self._stats_cache[cache_key] = result
            logger.info(f"Fetched {team_name} stats from ESPN API")
            return result

        except Exception as e:
            logger.warning(f"ESPN API error for {team_name}: {e}")
            return None


class NBAApiEndpoint:
    """
    NBA.com public stats endpoint (same as NBA.com but with different headers)

    This is essentially the same as the NBA.com API but with a more robust
    header configuration that may work when the primary endpoint is blocked.
    """

    BASE_URL = "https://stats.nba.com/stats"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.nba.com',
            'Referer': 'https://www.nba.com/stats/',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        })

        # Team ID mappings
        self.team_ids = {
            "Atlanta Hawks": 1610612737,
            "Boston Celtics": 1610612738,
            "Brooklyn Nets": 1610612751,
            "Charlotte Hornets": 1610612766,
            "Chicago Bulls": 1610612741,
            "Cleveland Cavaliers": 1610612739,
            "Dallas Mavericks": 1610612742,
            "Denver Nuggets": 1610612743,
            "Detroit Pistons": 1610612765,
            "Golden State Warriors": 1610612744,
            "Houston Rockets": 1610612745,
            "Indiana Pacers": 1610612754,
            "Los Angeles Clippers": 1610612746,
            "Los Angeles Lakers": 1610612747,
            "Memphis Grizzlies": 1610612763,
            "Miami Heat": 1610612748,
            "Milwaukee Bucks": 1610612749,
            "Minnesota Timberwolves": 1610612750,
            "New Orleans Pelicans": 1610612740,
            "New York Knicks": 1610612752,
            "Oklahoma City Thunder": 1610612760,
            "Orlando Magic": 1610612753,
            "Philadelphia 76ers": 1610612755,
            "Phoenix Suns": 1610612756,
            "Portland Trail Blazers": 1610612757,
            "Sacramento Kings": 1610612758,
            "San Antonio Spurs": 1610612759,
            "Toronto Raptors": 1610612761,
            "Utah Jazz": 1610612762,
            "Washington Wizards": 1610612764,
        }

        self._stats_cache = {}

    @retry_on_exception((requests.RequestException, DataSourceError), max_retries=2)
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """Get team stats from NBA.com stats endpoint"""
        team_id = self.team_ids.get(team_name)
        if not team_id:
            return None

        # Check cache
        cache_key = f"nba_api_{team_name}"
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        try:
            season = get_current_nba_season()

            url = f"{self.BASE_URL}/leaguedashteamstats"
            params = {
                "LeagueID": "00",
                "Season": season,
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

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 500:
                logger.debug("NBA API endpoint returning 500 errors")
                return None

            response.raise_for_status()
            data = response.json()

            if 'resultSets' not in data or not data['resultSets']:
                return None

            headers = data['resultSets'][0]['headers']
            rows = data['resultSets'][0]['rowSet']

            for row in rows:
                if row[0] == team_id:
                    team_dict = dict(zip(headers, row))

                    result = {
                        'points_per_game': team_dict.get('PTS', 112.5),
                        'opp_points_per_game': team_dict.get('OPP_PTS', 112.5),
                        'offensive_rating': team_dict.get('OFF_RATING', 114.0),
                        'defensive_rating': team_dict.get('DEF_RATING', 114.0),
                        'pace': team_dict.get('PACE', 99.5),
                        'efg_pct': team_dict.get('EFG_PCT', 52.0) / 100.0,
                        'tov_pct': team_dict.get('TOV_PCT', 13.5),
                        'orb_pct': team_dict.get('OREB_PCT', 26.0),
                        'ft_rate': team_dict.get('FTA_RATE', 21.0),
                        'games_played': team_dict.get('GP', 0),
                        'source': 'nba_api',
                    }

                    self._stats_cache[cache_key] = result
                    logger.info(f"Fetched {team_name} stats from NBA API endpoint")
                    return result

        except Exception as e:
            logger.warning(f"NBA API endpoint error for {team_name}: {e}")
            return None


class BasketballReferenceScraper:
    """
    Web scraper for basketball-reference.com

    Fallback when all APIs fail.
    Parses HTML tables for team stats.
    """

    BASE_URL = "https://www.basketball-reference.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        self._stats_cache = {}

    def _map_team_to_url(self, team_name: str) -> Optional[str]:
        """Map team name to basketball-reference URL slug"""
        url_slugs = {
            "Atlanta Hawks": "ATL",
            "Boston Celtics": "BOS",
            "Brooklyn Nets": "BRK",
            "Charlotte Hornets": "CHO",
            "Chicago Bulls": "CHI",
            "Cleveland Cavaliers": "CLE",
            "Dallas Mavericks": "DAL",
            "Denver Nuggets": "DEN",
            "Detroit Pistons": "DET",
            "Golden State Warriors": "GSW",
            "Houston Rockets": "HOU",
            "Indiana Pacers": "IND",
            "Los Angeles Clippers": "LAC",
            "Los Angeles Lakers": "LAL",
            "Memphis Grizzlies": "MEM",
            "Miami Heat": "MIA",
            "Milwaukee Bucks": "MIL",
            "Minnesota Timberwolves": "MIN",
            "New Orleans Pelicans": "NOP",
            "New York Knicks": "NYK",
            "Oklahoma City Thunder": "OKC",
            "Orlando Magic": "ORL",
            "Philadelphia 76ers": "PHI",
            "Phoenix Suns": "PHO",
            "Portland Trail Blazers": "POR",
            "Sacramento Kings": "SAC",
            "San Antonio Spurs": "SAS",
            "Toronto Raptors": "TOR",
            "Utah Jazz": "UTA",
            "Washington Wizards": "WAS",
        }
        return url_slugs.get(team_name)

    @retry_on_exception((requests.RequestException, DataSourceError), max_retries=2)
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """
        Scrape team stats from basketball-reference.com

        Uses the per-game stats table which is more reliable than season totals.
        Looks for the "Team Stats Per Game" section and extracts the Team Total row.
        """
        slug = self._map_team_to_url(team_name)
        if not slug:
            return None

        # Check cache
        cache_key = f"bbr_{team_name}"
        if cache_key in self._stats_cache:
            return self._stats_cache[cache_key]

        try:
            # Get current season for URL
            season = get_current_nba_season()
            season_year = int(season.split('-')[0])

            # Use the specific season page
            url = f"{self.BASE_URL}/teams/{slug}/{season_year}.html"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML (simple parsing without BeautifulSoup dependency)
            html = response.text

            import re

            # Look for the "Team Stats Per Game" table
            # The Team Total row has class="totals_row" or is the row after "Team Total" text
            # Let's find the per-game section and extract from there

            # Find the per-game section
            per_game_pattern = r'<div[^>]*id="all_team_and_oponent"[^>]*>.*?<table[^>]*>.*?</table>'
            per_game_match = re.search(per_game_pattern, html, re.DOTALL)

            if not per_game_match:
                # Try alternative pattern
                per_game_pattern = r'Team Stats Per Game.*?<tbody>(.*?)</tbody>'
                per_game_match = re.search(per_game_pattern, html, re.DOTALL)

            if per_game_match:
                table_html = per_game_match.group(1) if per_game_match.groups() else per_game_match.group(0)

                # Find the "Team Total" row (usually marked with class="totals_row" or contains "Team Total")
                # Look for row with class="totals_row"
                total_row_pattern = r'<tr[^>]*class="[^"]*totals_row[^"]*"[^>]*>(.*?)</tr>'
                total_row_match = re.search(total_row_pattern, table_html, re.DOTALL)

                if not total_row_match:
                    # Try finding row with "Team Total" text nearby
                    total_row_pattern = r'Team Total.*?<tr[^>]*>(.*?)</tr>'
                    total_row_match = re.search(total_row_pattern, table_html, re.DOTALL | re.IGNORECASE)

                if total_row_match:
                    row_html = total_row_match.group(1)

                    # Extract all data-stat values
                    td_pattern = r'<td[^>]*data-stat="(\w+)"[^>]*>\s*([\d.]+)\s*</td>'
                    stats_found = dict(re.findall(td_pattern, row_html))

                    # Extract per-game stats
                    # Common stats: g (games), pts (points), trb (rebounds), ast (assists), stl (steals), blk (blocks), tov (turnovers)
                    ppg = float(stats_found.get('pts', 0)) if stats_found.get('pts') else 112.5
                    games = int(stats_found.get('g', 0)) if stats_found.get('g') else 0

                    # Estimate opponent points from defensive data if available
                    opp_pts = 112.5  # Default

                    result = {
                        'points_per_game': ppg if ppg > 50 else 112.5,  # Sanity check
                        'opp_points_per_game': opp_pts,
                        'offensive_rating': 114.0,  # Would need more complex calculation
                        'defensive_rating': 114.0,
                        'pace': 99.5,
                        'efg_pct': 0.520,
                        'tov_pct': float(stats_found.get('tov', 13.5)) if stats_found.get('tov') else 0.135,
                        'orb_pct': 0.260,
                        'ft_rate': 0.210,
                        'games_played': games,
                        'source': 'basketball-reference',
                    }

                    self._stats_cache[cache_key] = result
                    logger.info(f"Scraped {team_name} stats from basketball-reference.com (PPG: {ppg:.1f})")
                    return result

            logger.debug(f"Could not parse team stats for {team_name} from basketball-reference")
            return None

        except Exception as e:
            logger.warning(f"Basketball-Reference scrape error for {team_name}: {e}")
            return None


class AlternativeStatsFetcher:
    """
    Main class for fetching stats from alternative sources.

    Tries sources in priority order:
    1. NBA API Endpoint (alternative NBA.com with different headers)
    2. balldontlie.io (free, no key) - Currently requires auth
    3. SportsData.io (free tier, needs key)
    4. basketball-reference.com scraping (free, no key)
    5. ESPN API (free, no key) - Limited data
    6. League averages (last resort)
    """

    LEAGUE_AVERAGES = {
        'points_per_game': 112.5,
        'opp_points_per_game': 112.5,
        'offensive_rating': 114.0,
        'defensive_rating': 114.0,
        'pace': 99.5,
        'efg_pct': 0.520,
        'tov_pct': 0.135,
        'orb_pct': 0.260,
        'ft_rate': 0.210,
        'games_played': 0,
        'source': 'league_average',
    }

    def __init__(self, sportsdataio_key: Optional[str] = None):
        """
        Initialize alternative stats fetchers.

        Args:
            sportsdataio_key: Optional API key for sportsdata.io
        """
        self.nba_api = NBAApiEndpoint()
        self.balldontlie = BallDontLieAPI()
        self.sportsdataio = SportsDataIO(sportsdataio_key)
        self.scraper = BasketballReferenceScraper()
        self.espn = ESPNAPI()

        self.sources_tried: List[str] = []
        self.sources_succeeded: Dict[str, int] = {}

    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """
        Get team stats from best available alternative source.

        Args:
            team_name: Full team name (e.g., "Boston Celtics")

        Returns:
            Dict with stats or None if all sources fail
        """
        self.sources_tried = []

        # Try NBA API endpoint first (same data as NBA.com but different headers)
        self.sources_tried.append("nba_api")
        result = self.nba_api.get_team_stats(team_name)
        if result:
            self._record_success("nba_api")
            return result

        # Try balldontlie (currently requires auth, but may work in some cases)
        self.sources_tried.append("balldontlie")
        result = self.balldontlie.get_team_stats(team_name)
        if result:
            self._record_success("balldontlie")
            return result

        # Try SportsData.io (if key available)
        if self.sportsdataio.is_available():
            self.sources_tried.append("sportsdataio")
            result = self.sportsdataio.get_team_stats(team_name)
            if result:
                self._record_success("sportsdataio")
                return result

        # Try web scraping basketball-reference
        self.sources_tried.append("basketball-reference")
        result = self.scraper.get_team_stats(team_name)
        if result:
            self._record_success("basketball-reference")
            return result

        # Try ESPN API (limited data, but better than nothing)
        self.sources_tried.append("espn")
        result = self.espn.get_team_stats(team_name)
        if result:
            self._record_success("espn")
            return result

        # All sources failed
        logger.warning(f"All alternative sources failed for {team_name}")
        return None

    def _record_success(self, source: str):
        """Record successful fetch from source"""
        if source not in self.sources_succeeded:
            self.sources_succeeded[source] = 0
        self.sources_succeeded[source] += 1

    def get_success_report(self) -> Dict[str, int]:
        """Get report of which sources succeeded"""
        return self.sources_succeeded.copy()

    def is_available(self) -> bool:
        """Check if any alternative sources are available"""
        return True  # At least balldontlie and ESPN should always work


def refresh_all_teams_cache(
    team_names: List[str],
    sportsdataio_key: Optional[str] = None,
    cache_dir: str = "data/cache"
) -> Dict[str, Dict]:
    """
    Refresh cache for all teams using alternative sources.

    Args:
        team_names: List of full team names
        sportsdataio_key: Optional SportsData.io API key
        cache_dir: Directory to cache results

    Returns:
        Dict mapping team_name -> stats
    """
    from pathlib import Path
    import json

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    fetcher = AlternativeStatsFetcher(sportsdataio_key)
    results = {}

    for team_name in team_names:
        logger.info(f"Fetching {team_name} from alternative sources...")
        stats = fetcher.get_team_stats(team_name)

        if stats:
            results[team_name] = stats

            # Save to cache
            cache_file = cache_path / f"alt_{team_name.replace(' ', '_')}.json"
            try:
                with open(cache_file, 'w') as f:
                    json.dump({
                        'stats': stats,
                        'fetch_time': datetime.now().isoformat(),
                        'sources_tried': fetcher.sources_tried,
                    }, f)
            except Exception as e:
                logger.warning(f"Failed to cache stats for {team_name}: {e}")

        else:
            logger.error(f"Failed to fetch stats for {team_name} from all alternative sources")

        # Rate limiting between requests
        time.sleep(0.5)

    # Log summary
    logger.info(f"Alternative sources summary: {fetcher.get_success_report()}")

    return results


if __name__ == "__main__":
    # Test alternative sources
    logging.basicConfig(level=logging.DEBUG)

    fetcher = AlternativeStatsFetcher()

    test_teams = ["Boston Celtics", "Los Angeles Lakers", "Golden State Warriors"]

    for team in test_teams:
        print(f"\n=== Testing {team} ===")
        stats = fetcher.get_team_stats(team)
        if stats:
            print(f"Source: {stats.get('source')}")
            print(f"PPG: {stats.get('points_per_game')}")
            print(f"OPPG: {stats.get('opp_points_per_game')}")
            print(f"Pace: {stats.get('pace')}")
        else:
            print("Failed to fetch stats")
