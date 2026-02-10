"""
Data fetchers for odds and stats
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging

from ..utils.retry import retry_on_exception
from ..utils.season import get_season_start_year

logger = logging.getLogger(__name__)


class OddsAPIFetcher:
    """Fetch odds from The Odds API with retry logic"""

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.session = requests.Session()
        self.max_retries = max_retries

    @retry_on_exception((requests.RequestException, ValueError), max_retries=3)
    def get_nba_games(self, days_ahead: int = 1, markets: str = "totals,spreads") -> List[dict]:
        """Get upcoming NBA games with odds"""
        url = f"{self.BASE_URL}/sports/basketball_nba/odds"
        params = {
            "api_key": self.api_key,
            "regions": "us",
            "markets": markets,  # Fetch both totals and spreads
            "oddsFormat": "american",
            "dateFormat": "iso"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Validate response
        if not isinstance(data, list):
            raise ValueError(f"Expected list from API, got {type(data)}")

        return data

    @retry_on_exception((requests.RequestException, ValueError), max_retries=3)
    def get_wnba_games(self, markets: str = "totals,spreads") -> List[dict]:
        """Get upcoming WNBA games with odds"""
        url = f"{self.BASE_URL}/sports/basketball_wnba/odds"
        params = {
            "api_key": self.api_key,
            "regions": "us",
            "markets": markets,  # Fetch both totals and spreads
            "oddsFormat": "american",
            "dateFormat": "iso"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            raise ValueError(f"Expected list from API, got {type(data)}")

        return data

    @retry_on_exception((requests.RequestException, ValueError), max_retries=3)
    def get_ncaa_games(self, markets: str = "totals,spreads") -> List[dict]:
        """Get upcoming NCAA men's basketball games with odds"""
        url = f"{self.BASE_URL}/sports/basketball_ncaab/odds"
        params = {
            "api_key": self.api_key,
            "regions": "us",
            "markets": markets,  # Fetch both totals and spreads
            "oddsFormat": "american",
            "dateFormat": "iso"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            raise ValueError(f"Expected list from API, got {type(data)}")

        return data

    @retry_on_exception((requests.RequestException, ValueError), max_retries=3)
    def fetch_odds(self, sport: str, markets: str = "totals") -> List[dict]:
        """
        Get odds for any sport.

        Args:
            sport: Sport key (e.g., 'basketball_nba', 'americanfootball_nfl')
            markets: Markets to fetch (e.g., 'totals', 'spreads', 'h2h')

        Returns:
            List of games with odds data
        """
        url = f"{self.BASE_URL}/sports/{sport}/odds"
        params = {
            "api_key": self.api_key,
            "regions": "us",
            "markets": markets,
            "oddsFormat": "american",
            "dateFormat": "iso"
        }

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            raise ValueError(f"Expected list from API, got {type(data)}")

        return data


class NBAStatsFetcher:
    """Fetch NBA statistics using API-NBA"""

    def __init__(self, api_key: str = ""):
        # Using the free API-NBA endpoint
        self.base_url = "https://api-nba-v1.p.rapidapi.com"
        self.api_key = api_key
        self.session = requests.Session()
        self.headers = {}

        if api_key:
            self.headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "api-nba-v1.p.rapidapi.com"
            }

    def get_team_stats(self, season: int = None) -> List[dict]:
        """Get team statistics for a season"""
        if season is None:
            season = get_season_start_year()
        # Try free NBA stats API first
        url = f"https://stats.nba.com/stats/leaguedashteamstats"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        params = {
            "LeagueID": "00",
            "Season": f"{season}-{str(season+1)[-2:]}",
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
            "LastNGames": "0"
        }

        try:
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Parse NBA stats response
            if 'resultSets' in data and len(data['resultSets']) > 0:
                headers_list = data['resultSets'][0]['headers']
                rows = data['resultSets'][0]['rowSet']

                teams = []
                for row in rows:
                    team_dict = dict(zip(headers_list, row))
                    teams.append({
                        'team_id': team_dict.get('TEAM_ID'),
                        'team_name': team_dict.get('TEAM_NAME'),
                        'games_played': team_dict.get('GP'),
                        'points_per_game': team_dict.get('PTS'),
                        'opponent_points_per_game': team_dict.get('OPP_PTS'),
                        'offensive_rating': team_dict.get('OFF_RATING'),
                        'defensive_rating': team_dict.get('DEF_RATING'),
                        'pace': team_dict.get('PACE'),
                        ' possessions': team_dict.get('POSS')
                    })

                return teams

        except Exception as e:
            logger.warning(f"Could not fetch NBA stats from official API: {e}")

        # Fallback: return cached/mock data structure
        return self._get_fallback_team_stats()

    def _get_fallback_team_stats(self) -> List[dict]:
        """Fallback team stats when API is unavailable"""
        # This would be replaced with actual cached data
        return [
            {
                'team_id': '1',
                'team_name': 'Atlanta Hawks',
                'games_played': 82,
                'points_per_game': 118.5,
                'opponent_points_per_game': 119.2,
                'offensive_rating': 115.2,
                'defensive_rating': 116.5,
                'pace': 100.5
            },
            # More teams would be here
        ]

    def get_games(self, date: Optional[datetime] = None) -> List[dict]:
        """Get games for a specific date"""
        if date is None:
            date = datetime.now()

        # Use NBA's scoreboard endpoint
        url = f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            games = []
            if 'scoreboard' in data and 'games' in data['scoreboard']:
                for game in data['scoreboard']['games']:
                    games.append({
                        'game_id': game['gameId'],
                        'home_team': game['homeTeam']['teamName'],
                        'away_team': game['awayTeam']['teamName'],
                        'game_time': game['gameTimeUTC'],
                        'home_score': game.get('homeTeam', {}).get('score'),
                        'away_score': game.get('awayTeam', {}).get('score'),
                        'status': game.get('gameStatus')
                    })

            return games

        except Exception as e:
            logger.error(f"Error fetching games: {e}")
            return []


class OddsDataScraper:
    """Fallback scraper for odds data when APIs fail"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_oddsportal_nba(self) -> List[dict]:
        """Scrape NBA odds from OddsPortal"""
        # This is a placeholder - actual scraping would need more work
        logger.info("Odds scraping not implemented - using API data")
        return []

    def scrape_bettingpros_nba(self) -> List[dict]:
        """Scrape NBA odds from BettingPros"""
        # Placeholder
        return []


def get_games_with_odds(api_key: str, sport: str = "nba") -> List[dict]:
    """
    Main function to get games with current odds

    Args:
        api_key: The Odds API key
        sport: Sport to fetch (nba, wnba, ncaab, etc.)

    Returns:
        List of games with odds data
    """
    fetcher = OddsAPIFetcher(api_key)

    if sport == "nba":
        return fetcher.get_nba_games()
    elif sport == "wnba":
        return fetcher.get_wnba_games()
    elif sport == "ncaab":
        return fetcher.get_ncaa_games()
    else:
        logger.warning(f"Sport {sport} not yet implemented")
        return []
