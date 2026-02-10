#!/usr/bin/env python3
"""
Run the pick tracker and show dashboard
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.pick_tracker import PickTracker


def main():
    import argparse

    parser = argparse.ArgumentParser(description='View SportsTotalBot performance')
    parser.add_argument('--days', type=int, default=30, help='Days to show (default: 30)')
    parser.add_argument('--export', action='store_true', help='Export to files')
    parser.add_argument('--web', action='store_true', help='Launch web dashboard')

    args = parser.parse_args()

    tracker = PickTracker()

    # Show text dashboard
    print("\n" + tracker.generate_dashboard(args.days))

    # Export if requested
    if args.export:
        csv_file = tracker.export_to_csv(args.days)
        json_file = tracker.export_to_json(args.days)
        print(f"\n✅ Exported:")
        print(f"   CSV:  {csv_file}")
        print(f"   JSON: {json_file}")

    # Web dashboard
    if args.web:
        print("\n🌐 Launching web dashboard...")
        print("   Open: http://localhost:5000")
        print("   Press Ctrl+C to stop\n")
        from dashboard_web import app
        app.run(debug=False, port=5000)


if __name__ == '__main__':
    main()
