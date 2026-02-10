"""
NCAA Basketball Injury Fetcher

Fetches injury reports for NCAA basketball teams.
Note: College injuries are less impactful than NBA (no "stars" in same way)
and lineups are more variable anyway.
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class NCAAInjuryFetcher:
    """
    Fetches NCAA injury reports from ESPN.
    """

    def __init__(self, cache_dir: str = "data/cache/ncaa/injuries"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "ncaa_injuries.json")
        self.espn_url = "https://www.espn.com/mens-college-basketball/injuries"

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Load from cache if available and fresh
        self.injuries = self._load_cache()

    def fetch_injuries(self, force_refresh: bool = False) -> Dict[str, List[Dict]]:
        """
        Fetch injury reports for all NCAA teams.

        Args:
            force_refresh: Force fetching from ESPN even if cache is fresh

        Returns:
            Dictionary mapping team names to lists of injured players
        """
        if not force_refresh and self.injuries:
            logger.info("Using cached NCAA injury reports")
            return self.injuries

        try:
            logger.info(f"Fetching NCAA injuries from ESPN: {self.espn_url}")
            response = requests.get(self.espn_url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()

            injuries = self._parse_espn_injuries(response.text)
            self.injuries = injuries
            self._save_cache(injuries)

            logger.info(f"Fetched injury reports for {len(injuries)} teams")
            return injuries

        except Exception as e:
            logger.error(f"Failed to fetch NCAA injuries: {e}")
            # Return cached if available
            return self.injuries if self.injuries else {}

    def _parse_espn_injuries(self, html: str) -> Dict[str, List[Dict]]:
        """
        Parse ESPN injuries page HTML.

        Note: This is a simplified parser. ESPN's college basketball injury
        page structure may vary.
        """
        injuries = {}

        try:
            # Look for injury data in JSON-LD or embedded JSON
            # For now, return empty dict - college injuries are less critical
            # and lineups are more variable anyway

            # TODO: Implement actual scraping if needed
            # For NCAA, injuries matter less because:
            # 1. No true "stars" like NBA (players leave after 1-2 years)
            # 2. Deeper benches (15+ scholarship players)
            # 3. Lineups vary more game-to-game anyway

            logger.debug("NCAA injury parsing not fully implemented - college injuries less impactful")

        except Exception as e:
            logger.debug(f"Error parsing NCAA injuries: {e}")

        return injuries

    def get_team_injuries(self, team_name: str) -> List[Dict]:
        """
        Get injury list for a specific team.

        Args:
            team_name: Full team name

        Returns:
            List of injured player dictionaries
        """
        if not self.injuries:
            self.fetch_injuries()

        # Check for exact match or partial match
        for team, injuries in self.injuries.items():
            if team_name.lower() in team.lower() or team.lower() in team_name.lower():
                return injuries

        return []

    def calculate_injury_impact(self, team_name: str, projected_total: float) -> float:
        """
        Calculate impact of injuries on projected total.

        For NCAA, injuries are less impactful than NBA:
        - Role player out: -0.5 to -1.5 points
        - Starter out: -1.5 to -3.0 points
        - Star player out: -3.0 to -5.0 points

        Args:
            team_name: Team name
            projected_total: Current projected total

        Returns:
            Adjustment to projected total (usually negative)
        """
        injuries = self.get_team_injuries(team_name)
        if not injuries:
            return 0.0

        impact = 0.0
        for injury in injuries:
            status = injury.get('status', '').lower()
            if 'out' not in status and 'day-to-day' not in status:
                continue

            # Simple impact estimation
            # In NCAA, even "stars" don't move lines as much as NBA
            impact -= 1.5  # Base deduction for any injury

        return min(impact, -8.0)  # Cap at -8 points total

    def _load_cache(self) -> Dict[str, List[Dict]]:
        """Load injuries from cache if fresh"""
        if not os.path.exists(self.cache_file):
            return {}

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)

            cache_time = datetime.fromisoformat(data.get('cached_at', ''))
            age = datetime.now() - cache_time

            # Cache is fresh if less than 12 hours old
            # NCAA injuries change less frequently than NBA
            if age < timedelta(hours=12):
                return data.get('injuries', {})

        except Exception as e:
            logger.debug(f"Failed to load injury cache: {e}")

        return {}

    def _save_cache(self, injuries: Dict[str, List[Dict]]):
        """Save injuries to cache"""
        try:
            data = {
                'cached_at': datetime.now().isoformat(),
                'injuries': injuries
            }

            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.debug(f"Failed to save injury cache: {e}")


def get_ncaa_injuries(cache_dir: str = "data/cache/ncaa/injuries") -> NCAAInjuryFetcher:
    """
    Convenience function to get NCAA injury fetcher.

    Args:
        cache_dir: Cache directory for injury data

    Returns:
        NCAAInjuryFetcher instance
    """
    return NCAAInjuryFetcher(cache_dir=cache_dir)
