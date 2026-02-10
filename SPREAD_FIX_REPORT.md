# Spread Odds Parsing Fix - Report

## Issue Summary
The spread EV calculator was not working because spread odds were not being parsed correctly from The Odds API response.

## Root Cause
The `normalize_team_name()` function was being applied to `home_team` and `away_team` from the API response, but **NOT** to the team names in the spread outcomes. This caused a mismatch when trying to match spread outcomes to home/away teams.

### Example of the Bug:
- API returns: `home_team='New York Knicks'`, `away_team='Denver Nuggets'`
- After normalization: `home_team='Knicks'`, `away_team='Denver Nuggets'`
- Spread outcomes from API: `'New York Knicks'`, `'Denver Nuggets'` (NOT normalized)
- Comparison fails: `'Knicks' != 'New York Knicks'`
- Result: Only `away_spreads` gets populated, `home_spreads` remains empty

### Evidence from Debug Logs:
```
Game 9c5539dbfdce420a92a829805150949a: home_team='Knicks', away_team='Denver Nuggets'
  Spread outcome: Denver Nuggets, line: 4.5, price: -106
    ✓ Added to away_spreads: 4.5 @ -106
  Spread outcome: New York Knicks, line: -4.5, price: -114
    ✗ Team name mismatch: 'New York Knicks' not home or away
Spread data check - home_spreads: 0, away_spreads: 9, home_spread_odds: 0, away_spread_odds: 9
✗ Incomplete spread data for game 9c5539dbfdce420a92a829805150949a
```

## The Fix
Applied `normalize_team_name()` to the outcome names in the spread parsing logic:

### Before (line 209):
```python
name = outcome.get('name')
```

### After (line 209):
```python
name = normalize_team_name(outcome.get('name', ''))  # Normalize the outcome name too!
```

## File Modified
- `/Volumes/LegbaSSD/bots/SportsTotalBot/main_v2.py` (line 209)

## Verification
After the fix, all 7 games now have complete spread data:

```
✓ Created spread odds for game 9c5539dbfdce420a92a829805150949a
✓ Created spread odds for game 09a1c85451c2450418f5bcba90e220b9
✓ Created spread odds for game 8b816f6d79780a1772852263e815b070
✓ Created spread odds for game 720fb0aa5ec9b76d0ba6782d87da5d6e
✓ Created spread odds for game 7eb233edb6e9e03622d300ca7dd2c1df
✓ Created spread odds for game 4336bce3a2a2e0e4ab7b6bd8f79693d8
✓ Created spread odds for game 1fabd57d36993380babdef3c224d2992

Parsed 7 games with odds
Total odds entries: 14 (totals + spreads)
  Totals odds: 7
  Spreads odds: 7  ← FIXED! (was 0 before)
```

## Results
The spread EV calculator is now working correctly and generating +EV spread bets:

```
Oklahoma City Thunder @ San Antonio Spurs - 02:40 AM UTC
TOTAL: 🔼 OVER 219.7 (EV: 13.8%)
SPREAD: Oklahoma City Thunder +8.7 (EV: 7.0%)  ← NEW! Spread bet detected
```

## Additional Changes
Added debug logging to track spread parsing:
- Log normalized team names for each game
- Log each spread outcome being processed
- Log successful additions to home_spreads/away_spreads
- Log team name mismatches
- Log final spread data check results
- Log when spread odds are created or incomplete

## Testing
Created test script `/Volumes/LegbaSSD/bots/SportsTotalBot/test_spread_fix.py` to verify the fix with mock data.

Test result: ✅ SUCCESS - Spread data is complete!

## Impact
- Spread betting functionality is now fully operational
- The bot can now identify +EV opportunities in spread bets
- All 7 games analyzed now have both totals and spreads odds
- Enhanced the overall value of the betting analysis system

---
*Fix Date: February 4, 2026*
*Fixed by: Claude Code*
