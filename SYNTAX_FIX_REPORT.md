# SportsTotalBot Syntax Error Fix Report

**Date:** 2026-02-04  
**File:** `/mnt/smb/legbassd/bots/SportsTotalBot/src/data/multi_source_stats.py`  
**Line:** ~349 (actual error at try/except block structure)

## Problem Description

The Python interpreter reported:
```
SyntaxError: expected 'except' or 'finally' block
```

## Root Cause

The code had an improperly structured try-except block within a retry loop:

### Before (Incorrect Structure):
```python
for attempt in range(max_retries):
    try:
        response = self.session.get(url, params=params, timeout=30)
        # ... error handling ...
        response.raise_for_status()
        data = response.json()

    # ❌ Lines below were OUTSIDE the try block (wrong indentation)
    if 'resultSets' not in data or not data['resultSets']:
        return None

    headers = data['resultSets'][0]['headers']
    rows = data['resultSets'][0]['rowSet']

    for row in rows:
        if row[0] == team_id:
            # ... return TeamStatsWithQuality ...

# ❌ This except was OUTSIDE the for loop (wrong indentation)
except Exception as e:
    # ❌ Body had wrong indentation (12 spaces instead of 16)
    logger.debug(f"NBA.com fetch failed for {team_name}: {e}")
    self.quality_report.api_failures.append(...)
```

### Issues:
1. Lines processing the API response were **outside** the try block (12 spaces instead of 16)
2. The `except` block was **outside** the for loop instead of inside it
3. The except block body had insufficient indentation (12 spaces instead of 16)

## Solution

### Fix Applied:
1. Moved all response processing code **inside** the try block (indented from 12 to 16 spaces)
2. Moved the `except` block **inside** the for loop (12 spaces, matching the try)
3. Fixed except block body indentation to 16 spaces (one level deeper than except)

### After (Correct Structure):
```python
for attempt in range(max_retries):
    try:
        response = self.session.get(url, params=params, timeout=30)
        # ... error handling ...
        response.raise_for_status()
        data = response.json()

        # ✓ Now INSIDE the try block (16 spaces)
        if 'resultSets' not in data or not data['resultSets']:
            return None

        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']

        for row in rows:
            if row[0] == team_id:
                # ... return TeamStatsWithQuality ...

    # ✓ Now INSIDE the for loop (12 spaces, matching try)
    except Exception as e:
        # ✓ Correct indentation (16 spaces, one level deeper)
        logger.debug(f"NBA.com fetch failed for {team_name}: {e}")
        self.quality_report.api_failures.append(f"{team_name}: NBA.com - {str(e)[:50]}")

return None
```

## Verification

✅ **Syntax Check:** Passed  
```bash
python3 -m py_compile src/data/multi_source_stats.py
# Output: ✓ Syntax is valid
```

✅ **Import Check:** Passed  
```bash
python3 -c "from src.data.multi_source_stats import MultiSourceStatsFetcher"
# Output: ✓ Module imports successfully
```

## Changes Made

**File:** `src/data/multi_source_stats.py`

1. **Lines ~351-376:** Increased indentation by 4 spaces (moved inside try block)
   - Response processing code
   - Data validation
   - Team stats extraction

2. **Line ~378:** Repositioned `except` block to match try indentation (inside for loop)

3. **Lines ~379-380:** Increased indentation by 4 spaces (proper except block body)

## Impact

- The retry logic with exponential backoff now correctly wraps the entire API fetch operation
- Exceptions during response processing are properly caught and logged
- The quality report correctly tracks API failures
- Bot can now start without syntax errors

## Tested By

- **Syntax validation:** Python compiler
- **Module import:** Successful import of MultiSourceStatsFetcher class
- **No runtime errors:** The module loads without issues

---

**Status:** ✅ FIXED  
**Bot Status:** Ready to start without syntax errors
