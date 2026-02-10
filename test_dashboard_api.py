#!/usr/bin/env python3
"""
Quick test script to verify dashboard API endpoints work correctly.
Run this while the dashboard server is running.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"

def test_endpoint(endpoint, name):
    """Test a single API endpoint."""
    print(f"\n{name}")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            print(f"✓ Status: {response.status_code}")
            print(f"✓ Success: {data.get('success')}")

            # Show relevant fields based on endpoint
            if 'total_picks' in data:
                print(f"✓ Total Picks: {data['total_picks']}")
            if 'date' in data:
                print(f"✓ Date: {data['date']}")
            if 'period' in data:
                print(f"✓ Period: {data['period']}")
            if 'stats' in data:
                stats = data['stats']
                print(f"✓ Stats: {stats['total_picks']} picks, {stats['avg_ev']}% avg EV")
            if 'status' in data:
                print(f"✓ Status: {data['status']}")
            if 'version' in data:
                print(f"✓ Version: {data['version']}")

            return True
        else:
            print(f"✗ Status: {response.status_code}")
            print(f"✗ Error: {data.get('error', 'Unknown error')}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to server")
        print("  Make sure the dashboard is running: ./run_dashboard.sh")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("SportsTotalBot Dashboard API Test")
    print("=" * 60)
    print(f"Testing endpoints at: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("/api/health", "Health Check"),
        ("/api/picks", "Today's Picks"),
        ("/api/picks?refresh=true", "Today's Picks (Force Refresh)"),
        ("/api/history", "Historical Performance (30 days)"),
        ("/api/history?days=7", "Historical Performance (7 days)"),
        ("/api/stats", "Today's Statistics"),
        ("/api/stats?period=history&days=14", "Historical Statistics (14 days)"),
    ]

    results = []
    for endpoint, name in tests:
        results.append(test_endpoint(endpoint, name))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ {total - passed} test(s) failed")

    print("=" * 60)

if __name__ == "__main__":
    main()
