"""
NCAA Basketball Statistics Fetcher

Fetches team stats for NCAA D1 basketball teams using multiple scraping sources with fallbacks.

Sources (in priority order):
1. Sports Reference (cbb) - Scrapes sports-reference.com/cbb/ (most reliable)
2. NCAA.com official stats - Parses their JSON endpoints
3. ESPN NCAA Team Stats - Scrapes ESPN.com team pages
4. RealGM API - Uses RealGM.com for advanced stats
5. Bart Torvik - Scrapes barttorvik.com for advanced stats
6. Cached data - Previously cached successful fetches
7. League averages - Final fallback
"""

import requests
import json
import os
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logging.warning("BeautifulSoup4 not available. Web scraping features limited.")

logger = logging.getLogger(__name__)


# NCAA League Averages (when no data available)
NCAA_LEAGUE_AVERAGES = {
    'points_per_game': 75.5,
    'opponent_points_per_game': 75.5,
    'pace': 70.5,
    'offensive_rating': 105.0,
    'defensive_rating': 105.0,
    'field_goal_pct': 0.450,
    'three_point_pct': 0.345,
    'free_throw_pct': 0.715,
    'source': 'league_averages'
}

# User-Agent headers to avoid being blocked
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


def get_random_headers() -> Dict:
    """Get random headers to avoid blocking"""
    import random
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


class SourceResult:
    """Track result from each data source"""
    def __init__(self, source_name: str, success: bool, data: Optional[Dict] = None,
                 error: Optional[str] = None):
        self.source_name = source_name
        self.success = success
        self.data = data
        self.error = error

    def __repr__(self):
        if self.success:
            return f"SourceResult({self.source_name}: SUCCESS)"
        return f"SourceResult({self.source_name}: FAILED - {self.error})"


class NCAAStatsFetcher:
    """
    Fetches NCAA team statistics from multiple sources.

    Priority:
    1. Sports Reference scraping (best data)
    2. NCAA.com JSON API
    3. ESPN.com scraping
    4. RealGM scraping
    5. Bart Torvik scraping
    6. Cached data
    7. League averages
    """

    # Team name mappings for common variations
    TEAM_MAPPINGS = {
        # ACC
        'duke': 'Duke Blue Devils', 'duke blue devils': 'Duke Blue Devils',
        'north carolina': 'North Carolina Tar Heels', 'north carolina tar heels': 'North Carolina Tar Heels', 'unc': 'North Carolina Tar Heels',
        'virginia': 'Virginia Cavaliers', 'virginia cavaliers': 'Virginia Cavaliers',
        'florida state': 'Florida State Seminoles', 'florida state seminoles': 'Florida State Seminoles',
        'miami': 'Miami Hurricanes', 'miami hurricanes': 'Miami Hurricanes',
        'clemson': 'Clemson Tigers', 'clemson tigers': 'Clemson Tigers',
        'nc state': 'North Carolina State Wolfpack', 'north carolina state': 'North Carolina State Wolfpack', 'nc state wolfpack': 'North Carolina State Wolfpack',
        'wake forest': 'Wake Forest Demon Deacons', 'wake forest demon deacons': 'Wake Forest Demon Deacons',
        'georgia tech': 'Georgia Tech Yellow Jackets', 'georgia tech yellow jackets': 'Georgia Tech Yellow Jackets',
        'louisville': 'Louisville Cardinals', 'louisville cardinals': 'Louisville Cardinals',
        'notre dame': 'Notre Dame Fighting Irish', 'notre dame fighting irish': 'Notre Dame Fighting Irish',
        'pittsburgh': 'Pittsburgh Panthers', 'pittsburgh panthers': 'Pittsburgh Panthers',
        'syracuse': 'Syracuse Orange', 'syracuse orange': 'Syracuse Orange',
        'virginia tech': 'Virginia Tech Hokies', 'virginia tech hokies': 'Virginia Tech Hokies',
        'boston college': 'Boston College Eagles', 'boston college eagles': 'Boston College Eagles',
        # Big 12
        'kansas': 'Kansas Jayhawks', 'kansas jayhawks': 'Kansas Jayhawks',
        'kansas state': 'Kansas State Wildcats', 'kansas state wildcats': 'Kansas State Wildcats',
        'baylor': 'Baylor Bears', 'baylor bears': 'Baylor Bears',
        'texas': 'Texas Longhorns', 'texas longhorns': 'Texas Longhorns',
        'texas tech': 'Texas Tech Red Raiders', 'texas tech red raiders': 'Texas Tech Red Raiders',
        'tcu': 'TCU Horned Frogs', 'tcu horned frogs': 'TCU Horned Frogs',
        'west virginia': 'West Virginia Mountaineers', 'west virginia mountaineers': 'West Virginia Mountaineers',
        'iowa state': 'Iowa State Cyclones', 'iowa state cyclones': 'Iowa State Cyclones',
        'oklahoma': 'Oklahoma Sooners', 'oklahoma sooners': 'Oklahoma Sooners',
        'oklahoma state': 'Oklahoma State Cowboys', 'oklahoma state cowboys': 'Oklahoma State Cowboys',
        ' BYU': 'BYU Cougars', 'byu': 'BYU Cougars', 'byu cougars': 'BYU Cougars',
        'ucf': 'UCF Knights', 'ucf knights': 'UCF Knights',
        'houston': 'Houston Cougars', 'houston cougars': 'Houston Cougars',
        'cincinnati': 'Cincinnati Bearcats', 'cincinnati bearcats': 'Cincinnati Bearcats',
        # Big East
        'villanova': 'Villanova Wildcats', 'villanova wildcats': 'Villanova Wildcats',
        'uconn': 'UConn Huskies', 'uconn huskies': 'UConn Huskies', 'connecticut': 'UConn Huskies',
        'xavier': 'Xavier Musketeers', 'xavier musketeers': 'Xavier Musketeers',
        'creighton': 'Creighton Bluejays', 'creighton bluejays': 'Creighton Bluejays',
        'providence': 'Providence Friars', 'providence friars': 'Providence Friars',
        'seton hall': 'Seton Hall Pirates', 'seton hall pirates': 'Seton Hall Pirates',
        'st john': 'St. John\'s Red Storm', 'st johns': 'St. John\'s Red Storm', 'st. john\'s': 'St. John\'s Red Storm',
        'georgetown': 'Georgetown Hoyas', 'georgetown hoyas': 'Georgetown Hoyas',
        'depaul': 'DePaul Blue Demons', 'depaul blue demons': 'DePaul Blue Demons',
        'butler': 'Butler Bulldogs', 'butler bulldogs': 'Butler Bulldogs',
        'marquette': 'Marquette Golden Eagles', 'marquette golden eagles': 'Marquette Golden Eagles',
        # Big Ten
        'purdue': 'Purdue Boilermakers', 'purdue boilermakers': 'Purdue Boilermakers',
        'indiana': 'Indiana Hoosiers', 'indiana hoosiers': 'Indiana Hoosiers',
        'michigan state': 'Michigan State Spartans', 'michigan state spartans': 'Michigan State Spartans',
        'michigan': 'Michigan Wolverines', 'michigan wolverines': 'Michigan Wolverines',
        'ohio state': 'Ohio State Buckeyes', 'ohio state buckeyes': 'Ohio State Buckeyes',
        'illinois': 'Illinois Fighting Illini', 'illinois fighting illini': 'Illinois Fighting Illini',
        'iowa': 'Iowa Hawkeyes', 'iowa hawkeyes': 'Iowa Hawkeyes',
        'wisconsin': 'Wisconsin Badgers', 'wisconsin badgers': 'Wisconsin Badgers',
        'maryland': 'Maryland Terrapins', 'maryland terrapins': 'Maryland Terrapins',
        'rutgers': 'Rutgers Scarlet Knights', 'rutgers scarlet knights': 'Rutgers Scarlet Knights',
        'minnesota': 'Minnesota Golden Gophers', 'minnesota golden gophers': 'Minnesota Golden Gophers',
        'penn state': 'Penn State Nittany Lions', 'penn state nittany lions': 'Penn State Nittany Lions',
        'northwestern': 'Northwestern Wildcats', 'northwestern wildcats': 'Northwestern Wildcats',
        'nebraska': 'Nebraska Cornhuskers', 'nebraska cornhuskers': 'Nebraska Cornhuskers',
        # SEC
        'kentucky': 'Kentucky Wildcats', 'kentucky wildcats': 'Kentucky Wildcats',
        'tennessee': 'Tennessee Volunteers', 'tennessee volunteers': 'Tennessee Volunteers',
        'alabama': 'Alabama Crimson Tide', 'alabama crimson tide': 'Alabama Crimson Tide',
        'auburn': 'Auburn Tigers', 'auburn tigers': 'Auburn Tigers',
        'florida': 'Florida Gators', 'florida gators': 'Florida Gators',
        'lsu': 'LSU Tigers', 'lsu tigers': 'LSU Tigers',
        'georgia': 'Georgia Bulldogs', 'georgia bulldogs': 'Georgia Bulldogs',
        'south carolina': 'South Carolina Gamecocks', 'south carolina gamecocks': 'South Carolina Gamecocks',
        'mississippi state': 'Mississippi State Bulldogs', 'mississippi state bulldogs': 'Mississippi State Bulldogs',
        'ole miss': 'Ole Miss Rebels', 'ole miss rebels': 'Ole Miss Rebels',
        'arkansas': 'Arkansas Razorbacks', 'arkansas razorbacks': 'Arkansas Razorbacks',
        'missouri': 'Missouri Tigers', 'missouri tigers': 'Missouri Tigers',
        'texas a&m': 'Texas A&M Aggies', 'texas a&m aggies': 'Texas A&M Aggies',
        'vanderbilt': 'Vanderbilt Commodores', 'vanderbilt commodores': 'Vanderbilt Commodores',
        # Pac-12
        'ucla': 'UCLA Bruins', 'ucla bruins': 'UCLA Bruins',
        'arizona': 'Arizona Wildcats', 'arizona wildcats': 'Arizona Wildcats',
        'oregon': 'Oregon Ducks', 'oregon ducks': 'Oregon Ducks',
        'usc': 'USC Trojans', 'usc trojans': 'USC Trojans',
        'washington': 'Washington Huskies', 'washington huskies': 'Washington Huskies',
        'colorado': 'Colorado Buffaloes', 'colorado buffaloes': 'Colorado Buffaloes',
        'arizona state': 'Arizona State Sun Devils', 'asu': 'Arizona State Sun Devils',
        'stanford': 'Stanford Cardinal', 'stanford cardinal': 'Stanford Cardinal',
        'oregon state': 'Oregon State Beavers', 'oregon state beavers': 'Oregon State Beavers',
        'washington state': 'Washington State Cougars', 'washington state cougars': 'Washington State Cougars',
        'cal': 'California Golden Bears', 'california': 'California Golden Bears',
        'utah': 'Utah Utes', 'utah utes': 'Utah Utes',
        # Other major programs
        'gonzaga': 'Gonzaga Bulldogs', 'gonzaga bulldogs': 'Gonzaga Bulldogs',
        'san diego state': 'San Diego State Aztecs', 'san diego state aztecs': 'San Diego State Aztecs',
        'memphis': 'Memphis Tigers', 'memphis tigers': 'Memphis Tigers',
        'dayton': 'Dayton Flyers', 'dayton flyers': 'Dayton Flyers',
        'smu': 'SMU Mustangs', 'smu mustangs': 'SMU Mustangs',
        'temple': 'Temple Owls', 'temple owls': 'Temple Owls',
        'wichita state': 'Wichita State Shockers', 'wichita state shockers': 'Wichita State Shockers',
        'unlv': 'UNLV Runnin\' Rebels', 'unlv runnin\' rebels': 'UNLV Runnin\' Rebels',
        'new mexico': 'New Mexico Lobos', 'new mexico lobos': 'New Mexico Lobos',
    }

    # Sports Reference slug mappings
    SLUG_MAPPINGS = {
        'Duke Blue Devils': 'duke',
        'Kansas Jayhawks': 'kansas',
        'Kentucky Wildcats': 'kentucky',
        'North Carolina Tar Heels': 'north-carolina',
        'UCLA Bruins': 'ucla',
        'Gonzaga Bulldogs': 'gonzaga',
        'Villanova Wildcats': 'villanova',
        'Arizona Wildcats': 'arizona',
        'Texas Longhorns': 'texas',
        'Tennessee Volunteers': 'tennessee',
        'Houston Cougars': 'houston',
        'Alabama Crimson Tide': 'alabama',
        'Purdue Boilermakers': 'purdue',
        'Indiana Hoosiers': 'indiana',
        'Michigan State Spartans': 'michigan-state',
        'Michigan Wolverines': 'michigan',
        'Virginia Cavaliers': 'virginia',
        'Florida Gators': 'florida',
        'Arizona State Sun Devils': 'arizona-state',
        'Ohio State Buckeyes': 'ohio-state',
        'Oregon Ducks': 'oregon',
        'Iowa Hawkeyes': 'iowa',
        'Wisconsin Badgers': 'wisconsin',
        'Xavier Musketeers': 'xavier',
        'Creighton Bluejays': 'creighton',
        'Butler Bulldogs': 'butler',
        'Marquette Golden Eagles': 'marquette',
        'Providence Friars': 'providence',
        'St. John\'s Red Storm': 'st-johns',
        'Seton Hall Pirates': 'seton-hall',
        'Georgetown Hoyas': 'georgetown',
        'DePaul Blue Demons': 'depaul',
        'Baylor Bears': 'baylor',
        'Iowa State Cyclones': 'iowa-state',
        'Kansas State Wildcats': 'kansas-state',
        'Oklahoma Sooners': 'oklahoma',
        'Texas A&M Aggies': 'texas-am',
        'Texas Tech Red Raiders': 'texas-tech',
        'West Virginia Mountaineers': 'west-virginia',
        'Auburn Tigers': 'auburn',
        'LSU Tigers': 'louisiana-state',
        'Mississippi State Bulldogs': 'mississippi-state',
        'Ole Miss Rebels': 'mississippi',
        'South Carolina Gamecocks': 'south-carolina',
        'Arkansas Razorbacks': 'arkansas',
        'Georgia Bulldogs': 'georgia',
        'Missouri Tigers': 'missouri',
        'Florida State Seminoles': 'florida-state',
        'Clemson Tigers': 'clemson',
        'Miami Hurricanes': 'miami-fl',
        'North Carolina State Wolfpack': 'nc-state',
        'Wake Forest Demon Deacons': 'wake-forest',
        'Georgia Tech Yellow Jackets': 'georgia-tech',
        'Notre Dame Fighting Irish': 'notre-dame',
        'Pittsburgh Panthers': 'pittsburgh',
        'Syracuse Orange': 'syracuse',
        'Virginia Tech Hokies': 'virginia-tech',
        'Boston College Eagles': 'boston-college',
        'Louisville Cardinals': 'louisville',
        'UConn Huskies': 'connecticut',
        'San Diego State Aztecs': 'san-diego-state',
        'Memphis Tigers': 'memphis',
        'Dayton Flyers': 'dayton',
        'SMU Mustangs': 'smu',
        'Temple Owls': 'temple',
        'Wichita State Shockers': 'wichita-state',
        'UNLV Runnin\' Rebels': 'unlv',
        'New Mexico Lobos': 'new-mexico',
        'Colorado Buffaloes': 'colorado',
        'USC Trojans': 'southern-california',
        'Washington Huskies': 'washington',
        'Stanford Cardinal': 'stanford',
        'California Golden Bears': 'california',
        'Utah Utes': 'utah',
        'Oregon State Beavers': 'oregon-state',
        'Washington State Cougars': 'washington-state',
        'Arizona State Sun Devils': 'arizona-state',
        'Rutgers Scarlet Knights': 'rutgers',
        'Maryland Terrapins': 'maryland',
        'Minnesota Golden Gophers': 'minnesota',
        'Penn State Nittany Lions': 'penn-state',
        'Northwestern Wildcats': 'northwestern',
        'Nebraska Cornhuskers': 'nebraska',
        'Illinois Fighting Illini': 'illinois',
        'TCU Horned Frogs': 'tcu',
        'BYU Cougars': 'brigham-young',
        'UCF Knights': 'ucf',
        'Cincinnati Bearcats': 'cincinnati',
        'Vanderbilt Commodores': 'vanderbilt',
    }

    def __init__(self, cache_dir: str = "data/cache/ncaa", sportsdataio_key: str = None):
        self.cache_dir = cache_dir
        self.sportsdataio_key = sportsdataio_key
        self.session = requests.Session()
        self.session.headers.update(get_random_headers())

        # Track source success rates
        self.source_stats = {
            'sports_reference': {'attempts': 0, 'successes': 0},
            'ncaa_com': {'attempts': 0, 'successes': 0},
            'espn': {'attempts': 0, 'successes': 0},
            'realgm': {'attempts': 0, 'successes': 0},
            'bart_torvik': {'attempts': 0, 'successes': 0},
            'cache': {'attempts': 0, 'successes': 0},
            'league_averages': {'attempts': 0, 'successes': 0},
        }

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team name using mappings"""
        normalized = team_name.strip().lower()
        return self.TEAM_MAPPINGS.get(normalized, team_name)

    def get_team_stats(self, team_name: str) -> Tuple[Dict, List[SourceResult]]:
        """
        Get statistics for a specific NCAA team.

        Args:
            team_name: Full team name (e.g., "Duke Blue Devils", "Kansas Jayhawks")

        Returns:
            Tuple of (stats_dict, list of SourceResult objects)
        """
        results = []
        normalized_name = self.normalize_team_name(team_name)

        # Try cache first
        cached = self._get_cached_stats(normalized_name)
        if cached and self._is_cache_fresh(cached):
            self.source_stats['cache']['attempts'] += 1
            self.source_stats['cache']['successes'] += 1
            logger.debug(f"Using cached stats for {normalized_name}")
            results.append(SourceResult('cache', True, cached['stats']))
            return cached['stats'], results

        # Try multiple sources in order
        sources = [
            ('sports_reference', self._try_sports_reference),
            ('ncaa_com', self._try_ncaa_com_json),
            ('espn', self._try_espn),
            ('realgm', self._try_realgm),
            ('bart_torvik', self._try_bart_torvik),
        ]

        stats = None
        for source_name, source_func in sources:
            self.source_stats[source_name]['attempts'] += 1
            result = source_func(normalized_name)
            results.append(result)

            if result.success and result.data:
                self.source_stats[source_name]['successes'] += 1
                stats = result.data
                break

            # Polite delay between sources
            time.sleep(0.5)

        # Use cached if all sources fail
        if not stats and cached:
            logger.warning(f"Using stale cache for {normalized_name}")
            results.append(SourceResult('stale_cache', True, cached['stats']))
            return cached['stats'], results

        # Fall back to league averages
        if not stats:
            self.source_stats['league_averages']['attempts'] += 1
            self.source_stats['league_averages']['successes'] += 1
            logger.warning(f"No stats found for {normalized_name}, using league averages")
            stats = NCAA_LEAGUE_AVERAGES.copy()
            results.append(SourceResult('league_averages', True, stats))

        # Cache the results
        self._save_to_cache(normalized_name, stats)

        return stats, results

    def _try_sports_reference(self, team_name: str) -> SourceResult:
        """
        Scrape Sports Reference CBB team stats.

        URL format: https://www.sports-reference.com/cbb/schools/{school_slug}/{year}.html
        """
        if not HAS_BS4:
            return SourceResult('sports_reference', False, error='BeautifulSoup4 not installed')

        try:
            # Get slug from mappings
            slug = self.SLUG_MAPPINGS.get(team_name)
            if not slug:
                # Try to generate slug
                slug = team_name.lower().replace(' ', '-').replace("'", '')
                # Remove common suffixes
                for suffix in ['-blue-devils', '-jayhawks', '-wildcats', '-tar-heels', '-bruins',
                               '-bulldogs', '-eagles', '-tigers', '-longhorns', '-volunteers',
                               '-cougars', '-crimson-tide', '-boilermakers', '-hoosiers', '-spartans',
                               '-cavaliers', '-gators', '-sun-devils', '-buckeyes', '-ducks',
                               '-hawkeyes', '-badgers', '-musketeers', '-bluejays', '-golden-eagles',
                               '-friars', '-red-storm', '-pirates', 'hoyas', '-fighting-irish',
                               '-panthers', '-orange', '-hokies', '-sem-noles', '-hurricanes',
                               '-wolfpack', '-demon-deacons', '-yellow-jackets', '-gamecocks',
                               '-razorbacks', '-mountaineers', '-cyclones', '-aggies', '-red-raiders',
                               '-sooners', '-bears', '-huskies', '-trojans', '-cardinal',
                               '-buffaloes', '-beavers', '-utes', 'flying-dutchmen']:
                    if slug.endswith(suffix):
                        slug = slug[:-len(suffix)]
                        break

            # Current season year (Sports Reference uses ending year)
            from src.utils.ncaa_season import get_ncaa_season_start_year
            season_year = get_ncaa_season_start_year() + 1

            url = f"https://www.sports-reference.com/cbb/schools/{slug}/{season_year}.html"
            response = self.session.get(url, headers=get_random_headers(), timeout=15)

            if response.status_code == 404:
                return SourceResult('sports_reference', False, error='Team not found (404)')
            if response.status_code != 200:
                return SourceResult('sports_reference', False, error=f'HTTP {response.status_code}')

            soup = BeautifulSoup(response.text, 'html.parser')

            stats = NCAA_LEAGUE_AVERAGES.copy()

            # Parse the season-total_per_game table for team stats
            stats_table = soup.find('table', {'id': 'season-total_per_game'})
            if stats_table:
                # Get all headers
                headers = []
                thead = stats_table.find('thead')
                if thead:
                    for th in thead.find_all('th'):
                        htext = th.get_text(strip=True)
                        headers.append(htext)

                # Get the "Team" row (aggregate stats)
                tbody = stats_table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if not cells:
                            continue

                        row_label = cells[0].get_text(strip=True)
                        if 'Team' in row_label:
                            # Map headers to values
                            for i, cell in enumerate(cells[1:]):  # Skip label
                                header = headers[i + 1] if i + 1 < len(headers) else ''
                                try:
                                    value = float(cell.get_text(strip=True))

                                    if header == 'PTS':
                                        stats['points_per_game'] = value
                                    elif header == 'FG%':
                                        stats['field_goal_pct'] = value
                                    elif header == '3P%':
                                        stats['three_point_pct'] = value
                                    elif header == 'FT%':
                                        stats['free_throw_pct'] = value
                                except (ValueError, IndexError):
                                    pass
                            break

            # Calculate offensive/defensive rating if we have points
            if stats['points_per_game'] != NCAA_LEAGUE_AVERAGES['points_per_game']:
                # Estimate offensive rating from points
                # Default pace if not found
                if stats['pace'] == NCAA_LEAGUE_AVERAGES['pace']:
                    stats['pace'] = 70.0  # Reasonable default
                stats['offensive_rating'] = (stats['points_per_game'] / stats['pace']) * 100
                # Assume average opponent stats for now
                stats['opponent_points_per_game'] = 75.0
                stats['defensive_rating'] = (stats['opponent_points_per_game'] / stats['pace']) * 100

            # Check if we got actual data
            if stats['points_per_game'] != NCAA_LEAGUE_AVERAGES['points_per_game']:
                stats['source'] = 'sports_reference'
                return SourceResult('sports_reference', True, stats)

            return SourceResult('sports_reference', False, error='No valid stats found')

        except Exception as e:
            logger.debug(f"Sports Reference scraping failed for {team_name}: {e}")
            return SourceResult('sports_reference', False, error=str(e))

    def _try_ncaa_com_json(self, team_name: str) -> SourceResult:
        """
        Try to get stats from NCAA.com JSON endpoints.

        NCAA.com has stats at: https://data.ncaa.com/casablanca/scoreboard/basketball-men/d1/{year}/team-stats.json
        """
        try:
            from src.utils.ncaa_season import get_ncaa_season_start_year
            season_year = get_ncaa_season_start_year()

            # Try the team stats JSON endpoint
            url = f"https://data.ncaa.com/casablanca/scoreboard/basketball-men/d1/{season_year}/team-stats.json"

            response = self.session.get(url, headers=get_random_headers(), timeout=15)

            if response.status_code != 200:
                return SourceResult('ncaa_com', False, error=f'HTTP {response.status_code}')

            try:
                data = response.json()
            except json.JSONDecodeError:
                return SourceResult('ncaa_com', False, error='Invalid JSON response')

            stats = self._parse_ncaa_com_json(data, team_name)
            if stats and stats['points_per_game'] != NCAA_LEAGUE_AVERAGES['points_per_game']:
                stats['source'] = 'ncaa_com'
                return SourceResult('ncaa_com', True, stats)

            return SourceResult('ncaa_com', False, error='Team not found in response')

        except Exception as e:
            logger.debug(f"NCAA.com JSON failed for {team_name}: {e}")
            return SourceResult('ncaa_com', False, error=str(e))

    def _parse_ncaa_com_json(self, data: Dict, team_name: str) -> Optional[Dict]:
        """Parse NCAA.com JSON response for team stats"""
        try:
            stats = NCAA_LEAGUE_AVERAGES.copy()

            # NCAA.com JSON structure varies, try to find teams
            if isinstance(data, dict):
                teams = data.get('teams', data.get('teamStats', data.get('teamsList', [])))
            else:
                teams = data if isinstance(data, list) else []

            team_lower = team_name.lower()

            for team in teams:
                if isinstance(team, dict):
                    team_data = team.get('team', team)
                    name = team_data.get('name', team_data.get('teamName', '')).lower()

                    # Match by name
                    if team_lower in name or name in team_lower:
                        # Extract stats
                        stats_obj = team.get('stats', team.get('statAverage', {}))

                        stats['points_per_game'] = float(stats_obj.get('ppg', stats_obj.get('pointsPerGame', 75.5)))
                        stats['opponent_points_per_game'] = float(stats_obj.get('oppPpg', stats_obj.get('opponentPointsPerGame', 75.5)))
                        stats['pace'] = float(stats_obj.get('tempo', stats_obj.get('pace', 70.5)))
                        stats['field_goal_pct'] = float(stats_obj.get('fgPct', stats_obj.get('fieldGoalPercentage', 45.0))) / 100
                        stats['three_point_pct'] = float(stats_obj.get('threePointPct', stats_obj.get('threePointPercentage', 34.5))) / 100
                        stats['free_throw_pct'] = float(stats_obj.get('ftPct', stats_obj.get('freeThrowPercentage', 71.5))) / 100

                        # Calculate offensive/defensive ratings if not provided
                        if 'offRtg' in stats_obj:
                            stats['offensive_rating'] = float(stats_obj['offRtg'])
                        if 'defRtg' in stats_obj:
                            stats['defensive_rating'] = float(stats_obj['defRtg'])

                        return stats

            return None

        except Exception as e:
            logger.debug(f"Error parsing NCAA.com JSON: {e}")
            return None

    def _try_espn(self, team_name: str) -> SourceResult:
        """
        Scrape ESPN NCAA team stats page.

        ESPN URL format: https://www.espn.com/mens-college-basketball/team/stats/_/id/{team_id}
        """
        if not HAS_BS4:
            return SourceResult('espn', False, error='BeautifulSoup4 not installed')

        try:
            # Get ESPN team ID
            team_id = self._espn_get_team_id(team_name)
            if not team_id:
                return SourceResult('espn', False, error='Could not find team ID')

            # Fetch team stats page
            url = f"https://www.espn.com/mens-college-basketball/team/stats/_/id/{team_id}"
            response = self.session.get(url, headers=get_random_headers(), timeout=15)

            if response.status_code != 200:
                return SourceResult('espn', False, error=f'HTTP {response.status_code}')

            soup = BeautifulSoup(response.text, 'html.parser')

            stats = NCAA_LEAGUE_AVERAGES.copy()

            # ESPN uses div-based layout, look for stats in different ways
            # Try to find text patterns
            page_text = soup.get_text()

            # Look for "Points per game" pattern
            ppg_match = re.search(r'Points\s+per\s+game[\s:]+(\d+\.?\d*)', page_text, re.IGNORECASE)
            if ppg_match:
                stats['points_per_game'] = float(ppg_match.group(1))

            # Look for field goal percentage
            fg_match = re.search(r'Field\s+goal[\s%]+(\d+\.?\d*)', page_text, re.IGNORECASE)
            if fg_match:
                stats['field_goal_pct'] = float(fg_match.group(1)) / 100

            # Look for 3-point percentage
            tp_match = re.search(r'3.?point[\s%]+(\d+\.?\d*)', page_text, re.IGNORECASE)
            if tp_match:
                stats['three_point_pct'] = float(tp_match.group(1)) / 100

            # Look for free throw percentage
            ft_match = re.search(r'Free\s+throw[\s%]+(\d+\.?\d*)', page_text, re.IGNORECASE)
            if ft_match:
                stats['free_throw_pct'] = float(ft_match.group(1)) / 100

            # Check if we got actual data
            if stats['points_per_game'] != NCAA_LEAGUE_AVERAGES['points_per_game']:
                # Calculate other stats
                if stats['pace'] == NCAA_LEAGUE_AVERAGES['pace']:
                    stats['pace'] = 70.0
                stats['offensive_rating'] = (stats['points_per_game'] / stats['pace']) * 100
                stats['opponent_points_per_game'] = 75.0
                stats['defensive_rating'] = (stats['opponent_points_per_game'] / stats['pace']) * 100

                stats['source'] = 'espn'
                stats['team_id'] = team_id
                return SourceResult('espn', True, stats)

            return SourceResult('espn', False, error='No valid stats found')

        except Exception as e:
            logger.debug(f"ESPN scraping failed for {team_name}: {e}")
            return SourceResult('espn', False, error=str(e))

    def _espn_get_team_id(self, team_name: str) -> Optional[str]:
        """Get ESPN team ID from mappings"""
        espn_ids = {
            'Duke Blue Devils': '150',
            'Kansas Jayhawks': '2308',
            'Kentucky Wildcats': '2309',
            'North Carolina Tar Heels': '150',
            'UCLA Bruins': '2416',
            'Gonzaga Bulldogs': '274',
            'Villanova Wildcats': '2515',
            'Arizona Wildcats': '12',
            'Texas Longhorns': '251',
            'Tennessee Volunteers': '253',
            'Houston Cougars': '2390',
            'Alabama Crimson Tide': '336',
            'Purdue Boilermakers': '2290',
            'Indiana Hoosiers': '71',
            'Michigan State Spartans': '123',
            'Virginia Cavaliers': '254',
            'Florida Gators': '239',
            'Arizona State Sun Devils': '8',
            'Ohio State Buckeyes': '194',
            'Oregon Ducks': '2486',
            'Iowa Hawkeyes': '2294',
            'Wisconsin Badgers': '132',
            'Xavier Musketeers': '2519',
            'Creighton Bluejays': '2293',
            'Butler Bulldogs': '207',
            'Marquette Golden Eagles': '2306',
            'Providence Friars': '2508',
            'St. John\'s Red Storm': '2511',
            'Seton Hall Pirates': '2510',
            'Georgetown Hoyas': '238',
            'UConn Huskies': '223',
            'Baylor Bears': '250',
            'Iowa State Cyclones': '2295',
            'Kansas State Wildcats': '2307',
            'Oklahoma Sooners': '2462',
            'Texas A&M Aggies': '251',
            'Texas Tech Red Raiders': '252',
            'West Virginia Mountaineers': '2538',
            'Auburn Tigers': '5',
            'LSU Tigers': '2260',
            'Mississippi State Bulldogs': '2430',
            'Ole Miss Rebels': '2463',
            'South Carolina Gamecocks': '2514',
            'Arkansas Razorbacks': '1999',
            'Georgia Bulldogs': '335',
            'Missouri Tigers': '2431',
            'Florida State Seminoles': '2389',
            'Clemson Tigers': '229',
            'Miami Hurricanes': '2410',
            'North Carolina State Wolfpack': '247',
            'Wake Forest Demon Deacons': '2539',
            'Georgia Tech Yellow Jackets': '335',
            'Notre Dame Fighting Irish': '2441',
            'Pittsburgh Panthers': '2484',
            'Syracuse Orange': '2517',
            'Virginia Tech Hokies': '254',
            'Boston College Eagles': '192',
            'Louisville Cardinals': '2241',
            'Michigan Wolverines': '130',
            'Illinois Fighting Illini': '349',
            'Maryland Terrapins': '248',
            'Rutgers Scarlet Knights': '2512',
            'Minnesota Golden Gophers': '2288',
            'Penn State Nittany Lions': '2513',
            'Northwestern Wildcats': '2440',
            'Nebraska Cornhuskers': '2472',
            'USC Trojans': '2477',
            'Washington Huskies': '2541',
            'Colorado Buffaloes': '239',
            'Stanford Cardinal': '2516',
            'California Golden Bears': '197',
            'Arizona State Sun Devils': '8',
            'Oregon State Beavers': '2487',
            'Washington State Cougars': '2542',
            'Utah Utes': '2540',
            'San Diego State Aztecs': '2479',
            'Memphis Tigers': '2396',
            'Wichita State Shockers': '2550',
            'Dayton Flyers': '2393',
            'SMU Mustangs': '2509',
            'Temple Owls': '2518',
            'UNLV Runnin\' Rebels': '2468',
            'New Mexico Lobos': '2445',
            'Vanderbilt Commodores': '2537',
            'TCU Horned Frogs': '2478',
            'BYU Cougars': '244',
            'Cincinnati Bearcats': '2388',
            'UCF Knights': '2520',
        }

        normalized = team_name.strip()
        if normalized in espn_ids:
            return espn_ids[normalized]

        # Try case-insensitive search
        for name, team_id in espn_ids.items():
            if name.lower() in normalized.lower() or normalized.lower() in name.lower():
                return team_id

        return None

    def _try_realgm(self, team_name: str) -> SourceResult:
        """
        Scrape RealGM for NCAA team stats.

        RealGM has advanced stats and is more reliable than some sources.
        """
        if not HAS_BS4:
            return SourceResult('realgm', False, error='BeautifulSoup4 not installed')

        try:
            # RealGM uses a different URL structure
            # We'll need to map team names to their IDs
            realgm_urls = {
                'Duke Blue Devils': 'https://basketball.realgm.com/ncaa/teams/Duke-Blue-Devils/326/stats',
                'Kansas Jayhawks': 'https://basketball.realgm.com/ncaa/teams/Kansas-Jayhawks/327/stats',
                'Kentucky Wildcats': 'https://basketball.realgm.com/ncaa/teams/Kentucky-Wildcats/328/stats',
                'North Carolina Tar Heels': 'https://basketball.realgm.com/ncaa/teams/North-Carolina-Tar-Heels/329/stats',
                'UCLA Bruins': 'https://basketball.realgm.com/ncaa/teams/UCLA-Bruins/330/stats',
            }

            url = realgm_urls.get(team_name)
            if not url:
                return SourceResult('realgm', False, error='Team not in RealGM mapping')

            response = self.session.get(url, headers=get_random_headers(), timeout=15)

            if response.status_code != 200:
                return SourceResult('realgm', False, error=f'HTTP {response.status_code}')

            soup = BeautifulSoup(response.text, 'html.parser')
            stats = NCAA_LEAGUE_AVERAGES.copy()

            # Look for stats in tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if not cells or len(cells) < 2:
                        continue

                    label = cells[0].get_text(strip=True).lower()

                    try:
                        value = float(cells[1].get_text(strip=True))

                        if 'points' in label and 'game' in label:
                            stats['points_per_game'] = value
                        elif 'offensive' in label and 'rating' in label:
                            stats['offensive_rating'] = value
                        elif 'defensive' in label and 'rating' in label:
                            stats['defensive_rating'] = value
                        elif 'pace' in label or 'tempo' in label:
                            stats['pace'] = value
                    except (ValueError, IndexError):
                        pass

            if stats['points_per_game'] != NCAA_LEAGUE_AVERAGES['points_per_game']:
                stats['source'] = 'realgm'
                return SourceResult('realgm', True, stats)

            return SourceResult('realgm', False, error='No valid stats found')

        except Exception as e:
            logger.debug(f"RealGM scraping failed for {team_name}: {e}")
            return SourceResult('realgm', False, error=str(e))

    def _try_bart_torvik(self, team_name: str) -> SourceResult:
        """
        Scrape Bart Torvik for advanced team stats.

        Bart Torvik has excellent advanced stats including offensive/defensive efficiency.
        Site: https://barttorvik.com/
        """
        if not HAS_BS4:
            return SourceResult('bart_torvik', False, error='BeautifulSoup4 not installed')

        try:
            # Bart Torvik search endpoint
            search_url = f"https://barttorvik.com/search.php?search={team_name}"

            response = self.session.get(search_url, headers=get_random_headers(), timeout=15)

            if response.status_code != 200:
                return SourceResult('bart_torvik', False, error=f'HTTP {response.status_code}')

            soup = BeautifulSoup(response.text, 'html.parser')
            stats = NCAA_LEAGUE_AVERAGES.copy()

            # Bart Torvik uses data attributes or specific table structures
            # Try to find stats in page text as fallback
            page_text = soup.get_text()

            # Look for AdjO (Adjusted Offensive Efficiency)
            off_match = re.search(r'AdjO[^\d]+(\d+\.?\d*)', page_text)
            if off_match:
                stats['offensive_rating'] = float(off_match.group(1))

            # Look for AdjD (Adjusted Defensive Efficiency)
            def_match = re.search(r'AdjD[^\d]+(\d+\.?\d*)', page_text)
            if def_match:
                stats['defensive_rating'] = float(def_match.group(1))

            # Look for Tempo/Pace
            tempo_match = re.search(r'Tempo[^\d]+(\d+\.?\d*)', page_text)
            if tempo_match:
                stats['pace'] = float(tempo_match.group(1))

            # Look for PPG
            ppg_match = re.search(r'PPG[^\d]+(\d+\.?\d*)', page_text)
            if ppg_match:
                stats['points_per_game'] = float(ppg_match.group(1))

            # If we got at least offensive/defensive ratings, consider it a success
            if stats['offensive_rating'] != NCAA_LEAGUE_AVERAGES['offensive_rating']:
                # Fill in missing values
                if stats['points_per_game'] == NCAA_LEAGUE_AVERAGES['points_per_game']:
                    # Estimate from offensive rating and pace
                    stats['points_per_game'] = (stats['offensive_rating'] / 100) * stats['pace']
                if stats['opponent_points_per_game'] == NCAA_LEAGUE_AVERAGES['opponent_points_per_game']:
                    stats['opponent_points_per_game'] = (stats['defensive_rating'] / 100) * stats['pace']

                stats['source'] = 'bart_torvik'
                return SourceResult('bart_torvik', True, stats)

            return SourceResult('bart_torvik', False, error='No valid stats found')

        except Exception as e:
            logger.debug(f"Bart Torvik scraping failed for {team_name}: {e}")
            return SourceResult('bart_torvik', False, error=str(e))

    def _get_cached_stats(self, team_name: str) -> Optional[Dict]:
        """Get cached stats for a team"""
        cache_file = os.path.join(self.cache_dir, f"{team_name.replace(' ', '_').replace('/', '_').lower()}.json")

        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _is_cache_fresh(self, cached_data: Dict) -> bool:
        """Check if cached data is still fresh (24 hours)"""
        cache_time = cached_data.get('cached_at')
        if not cache_time:
            return False

        try:
            cached_dt = datetime.fromisoformat(cache_time)
            age = datetime.now() - cached_dt
            return age < timedelta(hours=24)
        except Exception:
            return False

    def _save_to_cache(self, team_name: str, stats: Dict):
        """Save stats to cache"""
        cache_file = os.path.join(self.cache_dir, f"{team_name.replace(' ', '_').replace('/', '_').lower()}.json")

        try:
            data = {
                'team': team_name,
                'cached_at': datetime.now().isoformat(),
                'stats': stats
            }

            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.debug(f"Failed to cache stats for {team_name}: {e}")

    def get_source_stats(self) -> Dict:
        """Get statistics about source success rates"""
        total_attempts = sum(s['attempts'] for s in self.source_stats.values())
        total_successes = sum(s['successes'] for s in self.source_stats.values())

        report = {
            'total_attempts': total_attempts,
            'total_successes': total_successes,
            'overall_success_rate': round(total_successes / total_attempts * 100, 1) if total_attempts > 0 else 0,
            'sources': {}
        }

        for source, stats in self.source_stats.items():
            if stats['attempts'] > 0:
                report['sources'][source] = {
                    'attempts': stats['attempts'],
                    'successes': stats['successes'],
                    'success_rate': round(stats['successes'] / stats['attempts'] * 100, 1)
                }
            else:
                report['sources'][source] = {
                    'attempts': 0,
                    'successes': 0,
                    'success_rate': 0
                }

        return report


def get_ncaa_team_stats(team_name: str, cache_dir: str = "data/cache/ncaa",
                        sportsdataio_key: str = None) -> Dict:
    """
    Convenience function to get NCAA team stats.

    Args:
        team_name: Full team name
        cache_dir: Cache directory
        sportsdataio_key: Optional SportsData.io API key

    Returns:
        Dictionary with team statistics
    """
    fetcher = NCAAStatsFetcher(cache_dir=cache_dir, sportsdataio_key=sportsdataio_key)
    stats, _ = fetcher.get_team_stats(team_name)
    return stats


def test_ncaa_sources(team_names: List[str] = None) -> Dict:
    """
    Test NCAA stats sources and report success rates.

    Args:
        team_names: List of team names to test (defaults to common teams)

    Returns:
        Dictionary with test results
    """
    if team_names is None:
        team_names = [
            'Duke Blue Devils',
            'Kansas Jayhawks',
            'Kentucky Wildcats',
            'North Carolina Tar Heels',
            'UCLA Bruins',
            'Gonzaga Bulldogs',
        ]

    fetcher = NCAAStatsFetcher(cache_dir="data/cache/ncaa_test")

    results = {
        'teams_tested': len(team_names),
        'successful_fetches': 0,
        'league_average_fallbacks': 0,
        'team_results': {},
        'source_stats': {}
    }

    for team_name in team_names:
        stats, source_results = fetcher.get_team_stats(team_name)

        source_names = [r.source_name for r in source_results if r.success]
        successful_source = source_names[0] if source_names else 'none'

        results['team_results'][team_name] = {
            'source': successful_source,
            'points_per_game': stats.get('points_per_game'),
            'offensive_rating': stats.get('offensive_rating'),
            'defensive_rating': stats.get('defensive_rating'),
            'pace': stats.get('pace'),
            'is_league_average': stats.get('source') == 'league_averages'
        }

        if stats.get('source') != 'league_averages':
            results['successful_fetches'] += 1
        else:
            results['league_average_fallbacks'] += 1

    results['source_stats'] = fetcher.get_source_stats()

    return results


if __name__ == "__main__":
    # Test the fetcher with common teams
    import sys

    teams_to_test = [
        'Duke Blue Devils',
        'Kansas Jayhawks',
        'Kentucky Wildcats',
        'North Carolina Tar Heels',
        'UCLA Bruins',
    ]

    if len(sys.argv) > 1:
        teams_to_test = sys.argv[1:]

    print("=" * 60)
    print("NCAA Stats Fetcher Test")
    print("=" * 60)

    test_results = test_ncaa_sources(teams_to_test)

    print(f"\nTeams tested: {test_results['teams_tested']}")
    print(f"Successful fetches: {test_results['successful_fetches']}")
    print(f"League average fallbacks: {test_results['league_average_fallbacks']}")
    print(f"Success rate: {test_results['successful_fetches'] / test_results['teams_tested'] * 100:.1f}%")

    print("\nTeam Results:")
    print("-" * 60)
    for team, result in test_results['team_results'].items():
        print(f"{team}:")
        print(f"  Source: {result['source']}")
        print(f"  PPG: {result['points_per_game']}")
        print(f"  Off Rtg: {result['offensive_rating']}")
        print(f"  Def Rtg: {result['defensive_rating']}")
        print(f"  Pace: {result['pace']}")
        print(f"  Is League Avg: {result['is_league_average']}")

    print("\nSource Statistics:")
    print("-" * 60)
    for source, stats in test_results['source_stats']['sources'].items():
        if stats['attempts'] > 0:
            print(f"{source}: {stats['successes']}/{stats['attempts']} ({stats['success_rate']}%)")
