import sys
sys.path.insert(0, ".")
from src.data.nba_stats_cache import NBAStatsFetcher

f = NBAStatsFetcher()

teams = ["Celtics", "Rockets", "Thunder", "Spurs", "Grizzlies", "Kings"]
for team in teams:
    stats = f.get_team_stats(team)
    if stats:
        print(team + ":")
        print("  PPG:", str(stats["avg_points_scored"]), "OPP:", str(stats["avg_points_allowed"]))
        print("  ORtg:", str(stats["offensive_rating"]), "DRtg:", str(stats["defensive_rating"]))
        print("  Pace:", str(stats["pace"]))
        print()
