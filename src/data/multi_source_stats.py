"""
Multi-source NBA stats fetcher with data quality scoring
Fetches from multiple sources and grades data quality

Priority order:
1. NBA.com API (official)
2. Alternative APIs (balldontlie, SportsData.io, ESPN, scraping)
3. Cache (if recent)
4. League averages (fallback)
"""

import requests
import json
import logging
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field

from .nba_stats_cache import NBAStatsFetcher as NBAStatsCache
from .alternative_sources import AlternativeStatsFetcher
from src.utils.season import get_current_nba_season

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source priority"""
    NBA_COM = "nba_com"              # Official NBA.com stats
    ALTERNATIVE = "alternative_api"  # Alternative APIs (balldontlie, ESPN, etc.)
    CACHED = "cached"                # Cached data
    LEAGUE_AVG = "league_avg"        # League averages (fallback)


class DataQuality(Enum):
    """Data quality grades"""
    EXCELLENT = "A"      # Fresh data from official source
    GOOD = "B"           # Cached but recent (< 6 hours)
    FAIR = "C"           # Cached but stale (> 6 hours)
    POOR = "D"           # League averages/estimates
    UNRELIABLE = "F"     # No data available


@dataclass
class TeamStatsWithQuality:
    """Team stats with data quality metadata"""
    team_name: str
    points_per_game: float
    opp_points_per_game: float
    offensive_rating: float
    defensive_rating: float
    pace: float
    efg_pct: float = 0.520
    tov_pct: float = 0.135
    orb_pct: float = 0.260
    ft_rate: float = 0.210

    # Quality metadata
    data_source: DataSource = DataSource.LEAGUE_AVG
    data_quality: DataQuality = DataQuality.POOR
    fetch_time: Optional[datetime] = None
    cache_age_hours: float = 0.0
    is_fallback: bool = True


@dataclass
class DataQualityReport:
    """Report on overall data quality for a run"""
    total_teams: int = 0
    excellent_quality: int = 0
    good_quality: int = 0
    fair_quality: int = 0
    poor_quality: int = 0
    unreliable_quality: int = 0
    api_failures: List[str] = field(default_factory=list)

    @property
    def quality_score(self) -> float:
        """Overall quality score (0-100)"""
        if self.total_teams == 0:
            return 0.0

        weighted = (
            self.excellent_quality * 100 +
            self.good_quality * 80 +
            self.fair_quality * 60 +
            self.poor_quality * 40 +
            self.unreliable_quality * 20
        )
        return weighted / self.total_teams

    @property
    def should_trust_picks(self) -> bool:
        """Whether picks should be trusted based on data quality"""
        # Need at least 70% of teams with good or better data
        good_plus = self.excellent_quality + self.good_quality
        return (good_plus / max(self.total_teams, 1)) >= 0.7


class MultiSourceStatsFetcher:
    """
    Fetch NBA stats from multiple sources with fallback
    Tracks data quality and provides warnings
    """

    # Current Season League Averages (dynamically calculated) (updated periodically)
    LEAGUE_AVERAGES = {
        "points_per_game": 112.5,
        "opp_points_per_game": 112.5,
        "offensive_rating": 114.0,
        "defensive_rating": 114.0,
        "pace": 99.5,
        "efg_pct": 0.520,
        "tov_pct": 0.135,
        "orb_pct": 0.260,
        "ft_rate": 0.210,
    }

    def __init__(self, cache_dir: str = "data/cache", odds_api_key: str = "",
                 sportsdataio_key: Optional[str] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.odds_api_key = odds_api_key

        # Get SportsData.io key from env if not provided
        if sportsdataio_key is None:
            sportsdataio_key = os.getenv("SPORTSDATAIO_KEY")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.nba.com/',
        })

        # Team mappings
        self.team_name_to_id = self._build_team_mappings()

        # Track quality
        self.quality_report = DataQualityReport()

        # Initialize alternative stats fetcher
        self.alternative_fetcher = AlternativeStatsFetcher(
            sportsdataio_key=sportsdataio_key
        )

    def _build_team_mappings(self) -> Dict[str, int]:
        """Build team name to ID mappings"""
        mappings = {
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
            "Orlando Magic": 1610612753,
            "Philadelphia 76ers": 1610612755,
            "Phoenix Suns": 1610612756,
            "Portland Trail Blazers": 1610612757,
            "Sacramento Kings": 1610612758,
            "San Antonio Spurs": 1610612759,
            "Toronto Raptors": 1610612761,
            "Utah Jazz": 1610612762,
            "Washington Wizards": 1610612764,
            "Oklahoma City Thunder": 1610612760,
        }

        # Add common abbreviations
        abbrev_map = {
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

        # Add both full names and abbreviations
        full_map = {}
        full_map.update(mappings)
        for abbrev, full in abbrev_map.items():
            if full in mappings:
                full_map[abbrev] = mappings[full]

        return full_map

    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to full format"""
        # Direct match
        if team_name in self.team_name_to_id:
            return team_name

        # Try to find partial match
        for full_name in self.team_name_to_id.keys():
            if team_name.lower() in full_name.lower() or full_name.lower() in team_name.lower():
                return full_name

        return team_name

    def get_team_stats(self, team_name: str) -> TeamStatsWithQuality:
        """
        Get team stats from best available source with quality grading

        Priority:
        1. NBA.com API (fresh, official)
        2. Alternative APIs (balldontlie, SportsData.io, ESPN, scraping)
        3. Cache (if recent)
        4. League averages (fallback)
        """
        self.quality_report.total_teams += 1
        normalized_name = self.normalize_team_name(team_name)

        # Try NBA.com API first
        stats = self._try_nba_com_stats(normalized_name)
        if stats:
            return stats

        # Try alternative sources (when NBA.com is blocked)
        stats = self._try_alternative_sources(normalized_name)
        if stats:
            return stats

        # Try NBAStatsCache (uses cached data with calculated metrics)
        try:
            nba_cache = NBAStatsCache(cache_dir=str(self.cache_dir))
            cached_stats = nba_cache.get_team_stats(normalized_name)
            if cached_stats and cached_stats.get('pace', 0) > 0:
                # Check cache age for quality grading
                cache_file = self.cache_dir / f"team_{normalized_name.replace(' ', '_')}.json"
                if cache_file.exists():
                    cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    age_hours = (datetime.now() - cache_time).total_seconds() / 3600

                    if age_hours < 6:
                        quality = DataQuality.GOOD
                        self.quality_report.good_quality += 1
                    elif age_hours < 24:
                        quality = DataQuality.FAIR
                        self.quality_report.fair_quality += 1
                    else:
                        quality = DataQuality.POOR
                        self.quality_report.poor_quality += 1
                else:
                    quality = DataQuality.GOOD
                    self.quality_report.good_quality += 1

                return TeamStatsWithQuality(
                    team_name=normalized_name,
                    points_per_game=cached_stats.get('avg_points_scored', self.LEAGUE_AVERAGES['points_per_game']),
                    opp_points_per_game=cached_stats.get('avg_points_allowed', self.LEAGUE_AVERAGES['opp_points_per_game']),
                    offensive_rating=cached_stats.get('offensive_rating', self.LEAGUE_AVERAGES['offensive_rating']),
                    defensive_rating=cached_stats.get('defensive_rating', self.LEAGUE_AVERAGES['defensive_rating']),
                    pace=cached_stats.get('pace', self.LEAGUE_AVERAGES['pace']),
                    efg_pct=cached_stats.get('efg_pct', self.LEAGUE_AVERAGES['efg_pct']),
                    tov_pct=cached_stats.get('tov_pct', self.LEAGUE_AVERAGES['tov_pct']),
                    orb_pct=cached_stats.get('orb_pct', self.LEAGUE_AVERAGES['orb_pct']),
                    ft_rate=cached_stats.get('ft_rate', self.LEAGUE_AVERAGES['ft_rate']),
                    data_source=DataSource.CACHED,
                    data_quality=quality,
                    fetch_time=datetime.now(),
                    is_fallback=(age_hours >= 24 if 'age_hours' in locals() else False)
                )
        except Exception as e:
            logger.debug(f"NBAStatsCache failed for {team_name}: {e}")

        # Try legacy cache
        stats = self._try_cached_stats(normalized_name)
        if stats:
            return stats

        # Fall back to league averages
        logger.warning(f"Using league averages for {team_name} (no data available)")
        self.quality_report.poor_quality += 1
        self.quality_report.api_failures.append(f"{team_name}: All sources failed")

        return TeamStatsWithQuality(
            team_name=team_name,
            **self.LEAGUE_AVERAGES,
            data_source=DataSource.LEAGUE_AVG,
            data_quality=DataQuality.POOR,
            fetch_time=datetime.now(),
            is_fallback=True
        )

    def _try_nba_com_stats(self, team_name: str) -> Optional[TeamStatsWithQuality]:
        """Try fetching from NBA.com with retry logic"""
        import time
        team_id = self.team_name_to_id.get(team_name)
        if not team_id:
            return None

        # Get current season (using utility function)
        season = get_current_nba_season()  # Dynamic!

        url = "https://stats.nba.com/stats/leaguedashteamstats"
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

        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle server errors with retry
                if response.status_code == 500:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Got 500 error for {team_name}, retrying in {delay}s... (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {team_name} due to 500 errors")
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

                        self.quality_report.excellent_quality += 1

                        return TeamStatsWithQuality(
                            team_name=team_name,
                            points_per_game=team_dict.get('PTS', self.LEAGUE_AVERAGES['points_per_game']),
                            opp_points_per_game=team_dict.get('OPP_PTS', self.LEAGUE_AVERAGES['opp_points_per_game']),
                            offensive_rating=team_dict.get('OFF_RATING', self.LEAGUE_AVERAGES['offensive_rating']),
                            defensive_rating=team_dict.get('DEF_RATING', self.LEAGUE_AVERAGES['defensive_rating']),
                            pace=team_dict.get('PACE', self.LEAGUE_AVERAGES['pace']),
                            efg_pct=team_dict.get('EFG_PCT', self.LEAGUE_AVERAGES['efg_pct']),
                            tov_pct=team_dict.get('TOV_PCT', self.LEAGUE_AVERAGES['tov_pct']),
                            orb_pct=team_dict.get('OREB_PCT', self.LEAGUE_AVERAGES['orb_pct']),
                            ft_rate=team_dict.get('FTA_RATE', self.LEAGUE_AVERAGES['ft_rate']),
                            data_source=DataSource.NBA_COM,
                            data_quality=DataQuality.EXCELLENT,
                            fetch_time=datetime.now(),
                            is_fallback=False
                        )

            except Exception as e:
                logger.debug(f"NBA.com fetch failed for {team_name}: {e}")
                self.quality_report.api_failures.append(f"{team_name}: NBA.com - {str(e)[:50]}")

        return None

    def _try_alternative_sources(self, team_name: str) -> Optional[TeamStatsWithQuality]:
        """
        Try fetching from alternative APIs when NBA.com is blocked.

        Tries sources in order:
        1. balldontlie.io (free, no key)
        2. SportsData.io (free tier, needs key)
        3. ESPN API (free, no key)
        4. basketball-reference.com scraping (free, no key)
        """
        try:
            alt_stats = self.alternative_fetcher.get_team_stats(team_name)

            if alt_stats:
                # Get the source name for logging
                source_name = alt_stats.get('source', 'unknown')

                # Map alternative source to quality grade
                # balldontlie and ESPN are reliable sources (B grade)
                # scraping is less reliable (C grade)
                if source_name in ['balldontlie', 'sportsdataio']:
                    quality = DataQuality.GOOD
                    self.quality_report.good_quality += 1
                elif source_name == 'espn':
                    quality = DataQuality.FAIR
                    self.quality_report.fair_quality += 1
                elif source_name == 'basketball-reference':
                    quality = DataQuality.FAIR
                    self.quality_report.fair_quality += 1
                else:
                    quality = DataQuality.POOR
                    self.quality_report.poor_quality += 1

                logger.info(f"Fetched {team_name} from alternative source: {source_name}")

                return TeamStatsWithQuality(
                    team_name=team_name,
                    points_per_game=alt_stats.get('points_per_game', self.LEAGUE_AVERAGES['points_per_game']),
                    opp_points_per_game=alt_stats.get('opp_points_per_game', self.LEAGUE_AVERAGES['opp_points_per_game']),
                    offensive_rating=alt_stats.get('offensive_rating', self.LEAGUE_AVERAGES['offensive_rating']),
                    defensive_rating=alt_stats.get('defensive_rating', self.LEAGUE_AVERAGES['defensive_rating']),
                    pace=alt_stats.get('pace', self.LEAGUE_AVERAGES['pace']),
                    efg_pct=alt_stats.get('efg_pct', self.LEAGUE_AVERAGES['efg_pct']),
                    tov_pct=alt_stats.get('tov_pct', self.LEAGUE_AVERAGES['tov_pct']),
                    orb_pct=alt_stats.get('orb_pct', self.LEAGUE_AVERAGES['orb_pct']),
                    ft_rate=alt_stats.get('ft_rate', self.LEAGUE_AVERAGES['ft_rate']),
                    data_source=DataSource.ALTERNATIVE,
                    data_quality=quality,
                    fetch_time=datetime.now(),
                    is_fallback=True
                )

        except Exception as e:
            logger.debug(f"Alternative sources failed for {team_name}: {e}")
            self.quality_report.api_failures.append(f"{team_name}: Alternative - {str(e)[:50]}")

        return None

    def _try_cached_stats(self, team_name: str) -> Optional[TeamStatsWithQuality]:
        """Try loading from cache"""
        cache_file = self.cache_dir / f"team_stats_{team_name.replace(' ', '_')}.json"

        if not cache_file.exists():
            return None

        try:
            # Check cache age
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age_hours = (datetime.now() - cache_time).total_seconds() / 3600

            with open(cache_file) as f:
                data = json.load(f)

            # Grade based on age
            if age_hours < 6:
                quality = DataQuality.GOOD
                self.quality_report.good_quality += 1
            elif age_hours < 24:
                quality = DataQuality.FAIR
                self.quality_report.fair_quality += 1
            else:
                quality = DataQuality.POOR
                self.quality_report.poor_quality += 1

            return TeamStatsWithQuality(
                team_name=team_name,
                **data,
                data_source=DataSource.CACHED,
                data_quality=quality,
                fetch_time=cache_time,
                cache_age_hours=age_hours,
                is_fallback=(age_hours >= 6)
            )

        except Exception as e:
            logger.warning(f"Failed to load cache for {team_name}: {e}")

        return None

    def save_to_cache(self, stats: TeamStatsWithQuality):
        """Save stats to cache for future use"""
        if stats.data_source == DataSource.LEAGUE_AVG:
            return  # Don't cache league averages

        cache_file = self.cache_dir / f"team_stats_{stats.team_name.replace(' ', '_')}.json"

        try:
            data = {
                "points_per_game": stats.points_per_game,
                "opp_points_per_game": stats.opp_points_per_game,
                "offensive_rating": stats.offensive_rating,
                "defensive_rating": stats.defensive_rating,
                "pace": stats.pace,
                "efg_pct": stats.efg_pct,
                "tov_pct": stats.tov_pct,
                "orb_pct": stats.orb_pct,
                "ft_rate": stats.ft_rate,
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f)

        except Exception as e:
            logger.warning(f"Failed to save cache for {stats.team_name}: {e}")

    def get_quality_report(self) -> DataQualityReport:
        """Get the data quality report for this run"""
        return self.quality_report

    def reset_quality_report(self):
        """Reset for new run"""
        self.quality_report = DataQualityReport()
