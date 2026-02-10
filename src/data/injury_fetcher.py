"""
NBA Injury Data Fetcher

Fetches injury data from multiple sources with caching and fallback support.
Injury impact is calculated based on player importance (usage rate) and status.

Data Sources (in order of preference):
1. ESPN NBA Injuries - Web scraping
2. RotoWire NBA Injury Report - Web scraping
3. Cached data - Up to 6 hours old
4. League averages - No injury impact

Author: SportsTotalBot
Date: 2026-02-06
"""

import logging
import re
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib

import requests
from bs4 import BeautifulSoup

from ..utils.retry import retry_on_exception

logger = logging.getLogger(__name__)


class InjuryStatus(str, Enum):
    """Injury status classifications"""
    OUT = "Out"
    DAY_TO_DAY = "Day-To-Day"
    DOUBTFUL = "Doubtful"
    QUESTIONABLE = "Questionable"
    PROBABLE = "Probable"
    AVAILABLE = "Available"


class PlayerImportance(str, Enum):
    """Player importance based on usage rate and role"""
    STAR = "star"           # Top option, 25%+ usage, All-Star level
    STARTER = "starter"     # Regular starter, 15-25% usage
    ROLE_PLAYER = "role"    # Rotation player, 10-15% usage
    BENCH = "bench"         # Bench player, <10% usage


@dataclass
class PlayerInjury:
    """Represents a single player's injury status"""
    player_name: str
    team: str
    position: str
    status: InjuryStatus
    injury_type: str = ""
    return_date: Optional[str] = None
    comment: str = ""
    importance: PlayerImportance = PlayerImportance.ROLE_PLAYER

    @property
    def impact_score(self) -> float:
        """Calculate impact score for betting adjustments"""
        # Base impact by importance
        base_impacts = {
            PlayerImportance.STAR: 7.0,
            PlayerImportance.STARTER: 4.0,
            PlayerImportance.ROLE_PLAYER: 1.5,
            PlayerImportance.BENCH: 0.5
        }

        base = base_impacts.get(self.importance, 1.0)

        # Adjust by status
        status_multipliers = {
            InjuryStatus.OUT: 1.0,
            InjuryStatus.DAY_TO_DAY: 0.5,
            InjuryStatus.DOUBTFUL: 0.7,
            InjuryStatus.QUESTIONABLE: 0.3,
            InjuryStatus.PROBABLE: 0.1,
            InjuryStatus.AVAILABLE: 0.0
        }

        multiplier = status_multipliers.get(self.status, 0.0)

        return base * multiplier


@dataclass
class TeamInjuryReport:
    """Aggregated injury report for a single team"""
    team_name: str
    injuries: List[PlayerInjury] = field(default_factory=list)
    total_offensive_impact: float = 0.0
    total_defensive_impact: float = 0.0
    pace_impact: float = 0.0

    def add_injury(self, injury: PlayerInjury) -> None:
        """Add an injury and recalculate impacts"""
        self.injuries.append(injury)

        # Calculate impacts
        impact = injury.impact_score

        # Offensive impact is direct (scoring)
        self.total_offensive_impact += impact

        # Defensive impact depends on position
        # Guards/Forwards affect perimeter defense, Centers affect rim protection
        if injury.position in ['C', 'PF']:
            self.total_defensive_impact += impact * 0.8
        else:
            self.total_defensive_impact += impact * 0.5

        # Pace impact: stars slow down game when out
        if injury.importance == PlayerImportance.STAR:
            self.pace_impact -= impact * 0.15

    def get_significant_injuries(self, min_impact: float = 2.0) -> List[PlayerInjury]:
        """Get injuries with significant betting impact"""
        return [i for i in self.injuries if i.impact_score >= min_impact]

    def get_summary(self) -> str:
        """Get a text summary of injuries"""
        if not self.injuries:
            return "No significant injuries"

        significant = self.get_significant_injuries()
        if not significant:
            return "Minor injuries only"

        parts = []
        for injury in significant[:3]:  # Top 3 most significant
            status_sym = "OUT" if injury.status == InjuryStatus.OUT else "Q"
            parts.append(f"{injury.player_name} ({status_sym})")

        return ", ".join(parts)


# Known star players with their teams and positions (2025-26 season)
# This helps classify players when scraping doesn't provide usage rate
STAR_PLAYERS = {
    # Eastern Conference
    "Giannis Antetokounmpo": ("Milwaukee Bucks", "PF"),
    "Jayson Tatum": ("Boston Celtics", "SF"),
    "Joel Embiid": ("Philadelphia 76ers", "C"),
    "Damian Lillard": ("Milwaukee Bucks", "PG"),
    "Jalen Brunson": ("New York Knicks", "PG"),
    "Donovan Mitchell": ("Cleveland Cavaliers", "SG"),
    "Darius Garland": ("Cleveland Cavaliers", "PG"),
    "Paolo Banchero": ("Orlando Magic", "PF"),
    "Franz Wagner": ("Orlando Magic", "SF"),
    "Tyrese Haliburton": ("Indiana Pacers", "PG"),
    "Domantas Sabonis": ("Sacramento Kings", "C"),  # Traded to Kings
    "Trae Young": ("Atlanta Hawks", "PG"),
    "LaMelo Ball": ("Charlotte Hornets", "PG"),
    "Jimmy Butler": ("Miami Heat", "SF"),
    "Karl-Anthony Towns": ("New York Knicks", "C"),
    "Victor Wembanyama": ("San Antonio Spurs", "C"),
    "Cade Cunningham": ("Detroit Pistons", "PG"),
    "Scottie Barnes": ("Toronto Raptors", "SF"),
    "Jaylen Brown": ("Boston Celtics", "SG"),
    "Devin Booker": ("Phoenix Suns", "SG"),
    "Kyrie Irving": ("Dallas Mavericks", "PG"),

    # Western Conference
    "Nikola Jokic": ("Denver Nuggets", "C"),
    "Luka Doncic": ("Dallas Mavericks", "PG"),
    "Shai Gilgeous-Alexander": ("Oklahoma City Thunder", "PG"),
    "Stephen Curry": ("Golden State Warriors", "PG"),
    "Kevin Durant": ("Phoenix Suns", "PF"),
    "Anthony Edwards": ("Minnesota Timberwolves", "SG"),
    "LeBron James": ("Los Angeles Lakers", "SF"),
    "Anthony Davis": ("Los Angeles Lakers", "PF"),
    "Kawhi Leonard": ("LA Clippers", "SF"),
    "James Harden": ("LA Clippers", "PG"),
    "Ja Morant": ("Memphis Grizzlies", "PG"),
    "De'Aaron Fox": ("Sacramento Kings", "PG"),
    "Zion Williamson": ("New Orleans Pelicans", "PF"),
    "Chet Holmgren": ("Oklahoma City Thunder", "C"),
    "Jalen Williams": ("Oklahoma City Thunder", "SF"),
    "Alperen Sengun": ("Houston Rockets", "C"),
}


class InjuryFetcher:
    """
    Fetches and caches NBA injury data from multiple sources

    Usage:
        fetcher = InjuryFetcher(cache_dir="data/cache/injuries")
        report = fetcher.get_team_injury_report("Los Angeles Lakers")
        impact = fetcher.calculate_team_impact("Los Angeles Lakers")
    """

    CACHE_EXPIRY_HOURS = 6
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    # Team name normalization mappings
    TEAM_ALIASES = {
        "LAL": "Los Angeles Lakers",
        "LAC": "LA Clippers",
        "Lakers": "Los Angeles Lakers",
        "Clippers": "LA Clippers",
        "Celtics": "Boston Celtics",
        "Warriors": "Golden State Warriors",
        "Nets": "Brooklyn Nets",
        "Knicks": "New York Knicks",
        "Sixers": "Philadelphia 76ers",
        "76ers": "Philadelphia 76ers",
        "Heat": "Miami Heat",
        "Bucks": "Milwaukee Bucks",
        "Bulls": "Chicago Bulls",
        "Cavaliers": "Cleveland Cavaliers",
        "Pistons": "Detroit Pistons",
        "Pacers": "Indiana Pacers",
        "Magic": "Orlando Magic",
        "Hawks": "Atlanta Hawks",
        "Hornets": "Charlotte Hornets",
        "Wizards": "Washington Wizards",
        "Raptors": "Toronto Raptors",

        # Western
        "Mavericks": "Dallas Mavericks",
        "Mavs": "Dallas Mavericks",
        "Rockets": "Houston Rockets",
        "Grizzlies": "Memphis Grizzlies",
        "Spurs": "San Antonio Spurs",
        "Pelicans": "New Orleans Pelicans",
        "Thunder": "Oklahoma City Thunder",
        "Timberwolves": "Minnesota Timberwolves",
        "Nuggets": "Denver Nuggets",
        "Trail Blazers": "Portland Trail Blazers",
        "Blazers": "Portland Trail Blazers",
        "Jazz": "Utah Jazz",
        "Kings": "Sacramento Kings",
        "Suns": "Phoenix Suns",
    }

    def __init__(self, cache_dir: str = "data/cache/injuries"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})

        self._injury_cache: Dict[str, TeamInjuryReport] = {}
        self._cache_timestamp: Optional[datetime] = None

    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to standard format"""
        return self.TEAM_ALIASES.get(team_name, team_name)

    def classify_player_importance(
        self,
        player_name: str,
        team: str,
        position: str = ""
    ) -> PlayerImportance:
        """Classify player importance based on known star list"""
        # Check if known star
        if player_name in STAR_PLAYERS:
            return PlayerImportance.STAR

        # Check for common star indicators in name/comments
        # (This would be enhanced with actual usage rate data)

        # Default to starter-level for named players in injury reports
        # (Injury reports typically list relevant players)
        return PlayerImportance.STARTER

    def parse_position(self, pos_str: str) -> str:
        """Normalize position string"""
        pos_mapping = {
            "G": "PG",
            "SG": "SG",
            "F": "SF",
            "SF": "SF",
            "PF": "PF",
            "C": "C",
            "PG": "PG",
            "Guard": "PG",
            "Forward": "SF",
            "Center": "C"
        }
        return pos_mapping.get(pos_str.upper(), "SF")

    @retry_on_exception((requests.RequestException, Exception), max_retries=2)
    def fetch_from_espn(self) -> Dict[str, TeamInjuryReport]:
        """
        Scrape injury data from ESPN NBA Injuries page

        URL: https://www.espn.com/nba/injuries

        Returns:
            Dict mapping team names to TeamInjuryReport objects
        """
        url = "https://www.espn.com/nba/injuries"
        logger.info(f"Fetching injuries from ESPN: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            reports = {}

            # ESPN structure: The page has multiple tables, each preceded by team name
            # Looking for pattern: Team Name header followed by table
            # Based on actual ESPN structure, we need to look for divs containing team name
            # then find the following table

            # All NBA teams for matching
            all_teams = [
                "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
                "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
                "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
                "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
                "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans",
                "New York Knicks", "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers",
                "Phoenix Suns", "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs",
                "Toronto Raptors", "Utah Jazz", "Washington Wizards"
            ]

            # Find all div elements that might contain team names
            # ESPN structure varies, so we look for text content matching team names
            all_divs = soup.find_all('div')
            team_divs = []

            for div in all_divs:
                text = div.get_text(strip=True)
                # Check if this div contains primarily a team name
                for team in all_teams:
                    if text == team:
                        team_divs.append((div, team))
                        break

            logger.info(f"ESPN: Found {len(team_divs)} team sections")

            # For each team div, find the following table
            for div, team_name in team_divs:
                if team_name in reports:
                    continue

                # Find the next table after this div
                table = div.find_next('table')
                if not table:
                    continue

                team_report = TeamInjuryReport(team_name=team_name)

                # Parse table rows
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header row
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 5:
                        continue

                    try:
                        name_col = cols[0].get_text(strip=True)
                        pos_col = cols[1].get_text(strip=True)
                        date_col = cols[2].get_text(strip=True)
                        status_col = cols[3].get_text(strip=True)
                        comment_col = cols[4].get_text(strip=True) if len(cols) > 4 else ""

                        if not name_col or name_col.lower() in ['name', 'player']:
                            continue

                        # Parse status
                        status_str = status_col.lower()
                        if 'out' in status_str:
                            status = InjuryStatus.OUT
                        elif 'day' in status_str:
                            status = InjuryStatus.DAY_TO_DAY
                        elif 'doubtful' in status_str:
                            status = InjuryStatus.DOUBTFUL
                        elif 'questionable' in status_str:
                            status = InjuryStatus.QUESTIONABLE
                        elif 'probable' in status_str:
                            status = InjuryStatus.PROBABLE
                        else:
                            status = InjuryStatus.AVAILABLE

                        # Create injury
                        position = self.parse_position(pos_col)
                        importance = self.classify_player_importance(name_col, team_name, position)

                        injury = PlayerInjury(
                            player_name=name_col,
                            team=team_name,
                            position=position,
                            status=status,
                            comment=comment_col,
                            return_date=date_col if date_col and date_col != '-' else None,
                            importance=importance
                        )

                        # Only add if not available
                        if status != InjuryStatus.AVAILABLE:
                            team_report.add_injury(injury)

                    except Exception as e:
                        logger.debug(f"Error parsing injury row: {e}")
                        continue

                if team_report.injuries:
                    reports[team_name] = team_report

            logger.info(f"ESPN: Found injury reports for {len(reports)} teams")
            return reports

        except Exception as e:
            logger.warning(f"Failed to fetch from ESPN: {e}")
            return {}

    @retry_on_exception((requests.RequestException, Exception), max_retries=2)
    def fetch_from_rotowire(self) -> Dict[str, TeamInjuryReport]:
        """
        Scrape injury data from RotoWire

        URL: https://www.rotowire.com/basketball/injury-report.php

        Returns:
            Dict mapping team names to TeamInjuryReport objects
        """
        url = "https://www.rotowire.com/basketball/injury-report.php"
        logger.info(f"Fetching injuries from RotoWire: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            reports = {}

            # RotoWire uses a specific structure for injury reports
            # Look for divs with injury information
            injury_sections = soup.find_all(['div', 'section'],
                                           class_=re.compile(r'injury|player|status', re.I))

            # This is a simplified parser - RotoWire's actual structure
            # may require more specific selectors

            logger.info("RotoWire: Parsing completed (implementation may need updates)")
            return reports

        except Exception as e:
            logger.warning(f"Failed to fetch from RotoWire: {e}")
            return {}

    def get_cache_path(self) -> str:
        """Get path to injury cache file"""
        # Use date-based cache file
        date_str = datetime.now().strftime('%Y%m%d')
        hash_val = hashlib.md5(date_str.encode()).hexdigest()[:8]
        return os.path.join(self.cache_dir, f"injuries_{date_str}_{hash_val}.json")

    def load_from_cache(self) -> Optional[Dict[str, TeamInjuryReport]]:
        """Load injury data from cache if available and fresh"""
        cache_path = self.get_cache_path()

        if not os.path.exists(cache_path):
            return None

        # Check file age
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - file_time

        if age > timedelta(hours=self.CACHE_EXPIRY_HOURS):
            logger.info(f"Cache expired ({age.hours:.1f} hours old)")
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            reports = {}
            for team_name, team_data in data.items():
                report = TeamInjuryReport(team_name=team_name)

                for injury_data in team_data.get('injuries', []):
                    injury = PlayerInjury(
                        player_name=injury_data['player_name'],
                        team=injury_data['team'],
                        position=injury_data['position'],
                        status=InjuryStatus(injury_data['status']),
                        injury_type=injury_data.get('injury_type', ''),
                        return_date=injury_data.get('return_date'),
                        comment=injury_data.get('comment', ''),
                        importance=PlayerImportance(injury_data['importance'])
                    )
                    report.injuries.append(injury)

                    # Recalculate impacts
                    report.total_offensive_impact += injury_data.get('offensive_impact', 0)
                    report.total_defensive_impact += injury_data.get('defensive_impact', 0)
                    report.pace_impact += injury_data.get('pace_impact', 0)

                reports[team_name] = report

            logger.info(f"Loaded {len(reports)} team injury reports from cache")
            return reports

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return None

    def save_to_cache(self, reports: Dict[str, TeamInjuryReport]) -> None:
        """Save injury data to cache"""
        cache_path = self.get_cache_path()

        try:
            data = {}
            for team_name, report in reports.items():
                team_data = {
                    'injuries': [],
                    'total_offensive_impact': report.total_offensive_impact,
                    'total_defensive_impact': report.total_defensive_impact,
                    'pace_impact': report.pace_impact
                }

                for injury in report.injuries:
                    injury_data = {
                        'player_name': injury.player_name,
                        'team': injury.team,
                        'position': injury.position,
                        'status': injury.status.value,
                        'injury_type': injury.injury_type,
                        'return_date': injury.return_date,
                        'comment': injury.comment,
                        'importance': injury.importance.value,
                        'offensive_impact': injury.impact_score,
                        'defensive_impact': injury.impact_score * 0.8 if injury.position in ['C', 'PF'] else injury.impact_score * 0.5,
                        'pace_impact': -injury.impact_score * 0.15 if injury.importance == PlayerImportance.STAR else 0
                    }
                    team_data['injuries'].append(injury_data)

                data[team_name] = team_data

            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(reports)} team injury reports to cache")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def fetch_all_injuries(self, force_refresh: bool = False) -> Dict[str, TeamInjuryReport]:
        """
        Fetch all injury reports from available sources

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict mapping team names to TeamInjuryReport objects
        """
        # Try cache first
        if not force_refresh:
            cached = self.load_from_cache()
            if cached:
                self._injury_cache = cached
                self._cache_timestamp = datetime.now()
                return cached

        reports = {}

        # Try ESPN first
        espn_reports = self.fetch_from_espn()
        reports.update(espn_reports)

        # Try RotoWire as backup
        if len(reports) < 15:  # If less than half the teams
            rotowire_reports = self.fetch_from_rotowire()
            for team, report in rotowire_reports.items():
                if team not in reports:
                    reports[team] = report

        # Save to cache
        if reports:
            self.save_to_cache(reports)

        self._injury_cache = reports
        self._cache_timestamp = datetime.now()

        logger.info(f"Total injury reports fetched: {len(reports)} teams")
        return reports

    def get_team_injury_report(self, team_name: str) -> TeamInjuryReport:
        """
        Get injury report for a specific team

        Args:
            team_name: Team name (will be normalized)

        Returns:
            TeamInjuryReport object (empty if no injuries)
        """
        # Ensure cache is loaded
        if not self._injury_cache:
            self.fetch_all_injuries()

        normalized_name = self.normalize_team_name(team_name)
        return self._injury_cache.get(normalized_name,
                                       TeamInjuryReport(team_name=normalized_name))

    def calculate_team_impact(self, team_name: str) -> Tuple[float, float, float]:
        """
        Calculate total injury impact for a team

        Args:
            team_name: Team name

        Returns:
            (offensive_impact, defensive_impact, pace_impact) in points
        """
        report = self.get_team_injury_report(team_name)

        return (
            report.total_offensive_impact,
            report.total_defensive_impact,
            report.pace_impact
        )

    def get_game_injury_impact(
        self,
        home_team: str,
        away_team: str
    ) -> Dict[str, float]:
        """
        Get combined injury impact for a game

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Dict with keys:
                - home_offensive_impact
                - home_defensive_impact
                - away_offensive_impact
                - away_defensive_impact
                - total_impact
                - significant_injuries: list of injury descriptions
        """
        home_report = self.get_team_injury_report(home_team)
        away_report = self.get_team_injury_report(away_team)

        significant_injuries = []

        for injury in home_report.get_significant_injuries():
            significant_injuries.append(f"{home_team}: {injury.player_name} ({injury.status.value})")

        for injury in away_report.get_significant_injuries():
            significant_injuries.append(f"{away_team}: {injury.player_name} ({injury.status.value})")

        return {
            'home_offensive_impact': home_report.total_offensive_impact,
            'home_defensive_impact': home_report.total_defensive_impact,
            'away_offensive_impact': away_report.total_offensive_impact,
            'away_defensive_impact': away_report.total_defensive_impact,
            'pace_impact': home_report.pace_impact + away_report.pace_impact,
            'total_impact': (home_report.total_offensive_impact +
                           away_report.total_offensive_impact +
                           home_report.total_defensive_impact +
                           away_report.total_defensive_impact),
            'significant_injuries': significant_injuries
        }

    def log_injury_summary(self) -> str:
        """Get a summary of all injuries for logging"""
        if not self._injury_cache:
            self.fetch_all_injuries()

        lines = ["Injury Summary:"]
        lines.append("=" * 60)

        for team_name in sorted(self._injury_cache.keys()):
            report = self._injury_cache[team_name]
            significant = report.get_significant_injuries()

            if significant:
                injury_list = ", ".join([
                    f"{i.player_name} ({i.status.value})" for i in significant
                ])
                lines.append(f"{team_name}: {injury_list}")

        lines.append("=" * 60)
        return "\n".join(lines)


# Convenience function for quick injury impact lookup
def get_injury_impact_for_game(
    home_team: str,
    away_team: str,
    cache_dir: str = "data/cache/injuries"
) -> Dict[str, float]:
    """
    Quick lookup for game injury impact

    Args:
        home_team: Home team name
        away_team: Away team name
        cache_dir: Path to cache directory

    Returns:
        Impact dictionary
    """
    fetcher = InjuryFetcher(cache_dir=cache_dir)
    return fetcher.get_game_injury_impact(home_team, away_team)
