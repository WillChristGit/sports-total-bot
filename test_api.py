import requests
import sys
sys.path.insert(0, '/root/SportsTotalBot')
from src.utils.season import get_current_nba_season

season = get_current_nba_season()
print("Season:", season)

url = "https://stats.nba.com/stats/leaguedashteamstats"
params = {
    "LeagueID": "00",
    "Season": season,
    "SeasonType": "Regular Season",
    "MeasureType": "Base",
    "PerMode": "PerGame",
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers, params=params, timeout=30)
data = response.json()
headers_list = data["resultSets"][0]["headers"]
print("Available fields:")
for i, h in enumerate(headers_list):
    print(str(i) + ": " + h)

# Check one team
rows = data["resultSets"][0]["rowSet"]
for row in rows[:1]:
    team_dict = dict(zip(headers_list, row))
    print("\n--- Sample Team Data ---")
    field = "TEAM_NAME"
    print(field + ": " + str(team_dict.get(field)))
    for f in ["PTS", "OPP_PTS", "OFF_RATING", "DEF_RATING", "PACE", "MIN", "GP"]:
        print(f + ": " + str(team_dict.get(f)))
