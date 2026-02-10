"""
Output formatting for SportsTotalBot
"""

import logging
from datetime import datetime
from typing import List
import csv
import json

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from ..data.models import BetRecommendation, Game, SportType

logger = logging.getLogger(__name__)

# Eastern Timezone
ET = ZoneInfo("America/New_York")


class OutputFormatter:
    """Format and output picks/recommendations"""

    def __init__(self, output_path: str = "data/picks"):
        self.output_path = output_path

    def format_daily_picks(self, recommendations: List[BetRecommendation], games: dict, quality_report=None, compact=False, injury_reports=None) -> str:
        """
        Format daily picks into a readable report

        Args:
            recommendations: List of bet recommendations
            games: Dict mapping game_id to Game info
            quality_report: Optional DataQualityReport for data quality warning
            compact: If True, use compact format showing both totals and spreads per game

        Returns:
            Formatted string report
        """
        if not recommendations:
            return "No +EV bets found today."

        if compact:
            return self._format_compact_picks(recommendations, games, quality_report, injury_reports=injury_reports)
        else:
            return self._format_detailed_picks(recommendations, games, quality_report, injury_reports=injury_reports)

    def _format_compact_picks(self, recommendations: List[BetRecommendation], games: dict, quality_report=None, injury_reports=None) -> str:
        """
        Format picks in compact mode - grouped by game showing both totals and spreads

        Example:
        Celtics @ Rockets - 8:00 PM ET
        TOTAL: OVER 210.5 (EV: 15.5%)
        SPREAD: Celtics -3.5 (EV: 8.2%)
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"SportsTotalBot Daily Picks - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        # Add data quality warning if needed
        if quality_report and not quality_report.should_trust_picks:
            lines.append("\n⚠️  WARNING: Low data quality detected!")
            lines.append(f"   Quality Score: {quality_report.quality_score:.0f}/100")
            lines.append(f"   Only {int((quality_report.excellent_quality + quality_report.good_quality) / max(quality_report.total_teams, 1) * 100)}% of teams have reliable data")
            lines.append("   Picks may not be accurate. Use with caution.")
            lines.append("")

        lines.append("")

        # Group recommendations by game_id
        by_game = {}
        for rec in recommendations:
            if rec.game_id not in by_game:
                by_game[rec.game_id] = {'totals': None, 'spreads': None}
            if rec.bet_type.value == 'totals':
                by_game[rec.game_id]['totals'] = rec
            elif rec.bet_type.value == 'spreads':
                by_game[rec.game_id]['spreads'] = rec

        # Group by sport
        by_sport = {}
        for game_id, recs in by_game.items():
            game = games.get(game_id)
            if game:
                sport = game.sport.value.upper()
                if sport not in by_sport:
                    by_sport[sport] = []
                by_sport[sport].append((game_id, recs))

        for sport, game_recs in by_sport.items():
            lines.append(f"\n--- {sport} ---\n")

            # Sort by game time
            for game_id, recs in sorted(game_recs, key=lambda x: games.get(x[0]).game_time if games.get(x[0]) else datetime.min):
                game = games.get(game_id)
                if not game:
                    continue

                # Format game time
                game_time_str = game.game_time.strftime('%I:%M %p %Z')
                lines.append(f"{game.away_team} @ {game.home_team} - {game_time_str}")

                # Show injury notes if available
                if injury_reports and game_id in injury_reports:
                    injuries = injury_reports[game_id]
                    if injuries:
                        lines.append(f"  Injuries: {injuries}")

                # Show TOTAL pick if available
                if recs['totals']:
                    rec = recs['totals']
                    side_symbol = "🔼" if rec.side.value == "over" else "🔽"
                    lines.append(f"TOTAL: {side_symbol} {rec.side.value.upper()} {round(rec.line, 1)} (EV: {rec.ev:.1%})")

                # Show SPREAD pick if available
                if recs['spreads']:
                    rec = recs['spreads']
                    # Determine which team is favored
                    if rec.side.value == "home":
                        team = game.home_team
                        spread_str = f"-{round(rec.line, 1)}"  # Home favorite
                    else:
                        team = game.away_team
                        spread_str = f"+{round(rec.line, 1)}"  # Away underdog
                    lines.append(f"SPREAD: {team} {spread_str} (EV: {rec.ev:.1%})")

                lines.append("")

        lines.append("=" * 70)
        lines.append(f"Total picks: {len(recommendations)}")

        # Add quality report summary
        if quality_report:
            lines.append("")
            lines.append("Data Quality Summary:")
            lines.append(f"  Excellent (A): {quality_report.excellent_quality}")
            lines.append(f"  Good (B):      {quality_report.good_quality}")
            lines.append(f"  Fair (C):      {quality_report.fair_quality}")
            lines.append(f"  Poor (D):      {quality_report.poor_quality}")
            if quality_report.api_failures:
                lines.append(f"  API Failures:  {len(quality_report.api_failures)}")

        lines.append("")

        return "\n".join(lines)

    def _format_detailed_picks(self, recommendations: List[BetRecommendation], games: dict, quality_report=None, injury_reports=None) -> str:
        """
        Format picks in detailed mode - full information for each pick
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"SportsTotalBot Daily Picks - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        # Add data quality warning if needed
        if quality_report and not quality_report.should_trust_picks:
            lines.append("\n⚠️  WARNING: Low data quality detected!")
            lines.append(f"   Quality Score: {quality_report.quality_score:.0f}/100")
            lines.append(f"   Only {int((quality_report.excellent_quality + quality_report.good_quality) / max(quality_report.total_teams, 1) * 100)}% of teams have reliable data")
            lines.append("   Picks may not be accurate. Use with caution.")
            lines.append("")

        lines.append("")

        # Group by sport and bet type
        by_sport_and_type = {}
        for rec in recommendations:
            sport = rec.sport.value.upper()
            bet_type = rec.bet_type.value.upper()
            key = f"{sport}_{bet_type}"
            if key not in by_sport_and_type:
                by_sport_and_type[key] = []
            by_sport_and_type[key].append(rec)

        # Display in order: TOTALS first, then SPREADS
        for bet_type_label in ['TOTALS', 'SPREADS']:
            for sport_key, recs in sorted(by_sport_and_type.items()):
                if not sport_key.endswith(bet_type_label):
                    continue

                sport = sport_key.split('_')[0]
                lines.append(f"\n--- {sport} {bet_type_label} ---\n")

                for rec in sorted(recs, key=lambda r: r.ev, reverse=True):
                    game = games.get(rec.game_id)
                    if game:
                        teams = f"{game.away_team} @ {game.home_team}"
                    else:
                        teams = "Unknown"

                    # Format based on bet type
                    if rec.bet_type.value == 'totals':
                        # Totals format
                        lines.append(f"🎯 {rec.side.value.upper()} {round(rec.line, 1)}")
                        lines.append(f"   Teams: {teams}")
                        lines.append(f"   Odds: {rec.odds}")
                        lines.append(f"   Projected Total: {round(rec.projected_value, 1)}")
                        lines.append(f"   Win Prob: {rec.win_probability:.1%}")
                        lines.append(f"   EV: {rec.ev:.2%}")
                        lines.append(f"   Confidence: {rec.confidence:.1%}")
                    else:
                        # Spreads format
                        side_label = "HOME" if rec.side.value == "home" else "AWAY"
                        lines.append(f"🎯 {side_label} {rec.line:+.1f}")  # Show + or - for spread
                        lines.append(f"   Teams: {teams}")
                        lines.append(f"   Odds: {rec.odds}")
                        lines.append(f"   Projected Margin: {rec.projected_value:+.1f}")
                        lines.append(f"   Win Prob: {rec.win_probability:.1%}")
                        lines.append(f"   EV: {rec.ev:.2%}")
                        lines.append(f"   Confidence: {rec.confidence:.1%}")

                    # Add units if available (V2 recommendations)
                    if hasattr(rec, 'units'):
                        lines.append(f"   Units: {rec.units}")

                    # Add data quality indicator if available
                    if hasattr(rec, 'data_quality'):
                        dq_symbol = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⚫"}
                        lines.append(f"   Data Quality: {dq_symbol.get(rec.data_quality, '?')} {rec.data_quality}")

                    # Add injury notes if available
                    if injury_reports and rec.game_id in injury_reports:
                        injuries = injury_reports[rec.game_id]
                        if injuries:
                            lines.append(f"   Injuries: {injuries}")

                    lines.append(f"   Reasoning: {rec.reasoning}")
                    lines.append("")

        lines.append("=" * 70)
        lines.append(f"Total picks: {len(recommendations)}")

        # Add quality report summary
        if quality_report:
            lines.append("")
            lines.append("Data Quality Summary:")
            lines.append(f"  Excellent (A): {quality_report.excellent_quality}")
            lines.append(f"  Good (B):      {quality_report.good_quality}")
            lines.append(f"  Fair (C):      {quality_report.fair_quality}")
            lines.append(f"  Poor (D):      {quality_report.poor_quality}")
            if quality_report.api_failures:
                lines.append(f"  API Failures:  {len(quality_report.api_failures)}")

        lines.append("")

        return "\n".join(lines)

    def save_picks_to_csv(self, recommendations: List[BetRecommendation], games: dict):
        """Save picks to CSV file"""
        import os
        os.makedirs(self.output_path, exist_ok=True)

        filename = f"{self.output_path}/daily_picks_{datetime.now().strftime('%Y%m%d')}.csv"

        # Handle potential permission issues with SMB mounts
        # If file exists and can't be opened for writing, remove it first
        if os.path.exists(filename):
            try:
                # Test if we can write to the file
                with open(filename, 'a', newline='') as f:
                    pass
            except (PermissionError, OSError):
                logger.warning(f"Cannot write to existing file {filename}, removing and recreating")
                try:
                    os.remove(filename)
                except Exception as e:
                    logger.error(f"Failed to remove {filename}: {e}")
                    # Try alternative filename
                    filename = f"{self.output_path}/daily_picks_{datetime.now().strftime('%Y%m%d')}_retry.csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Game ID', 'Sport', 'Bet Type', 'Side', 'Line', 'Odds',
                    'Projected Value', 'EV', 'Win Probability', 'Confidence',
                    'Home Team', 'Away Team', 'Game Time', 'Reasoning'
                ])

                for rec in recommendations:
                    game = games.get(rec.game_id)
                    if game:
                        home_team = game.home_team
                        away_team = game.away_team
                        game_time = game.game_time.strftime('%Y-%m-%d %H:%M')
                    else:
                        home_team = away_team = game_time = "Unknown"

                    writer.writerow([
                        rec.game_id,
                        rec.sport.value,
                        rec.bet_type.value,
                        rec.side.value,
                        rec.line,
                        rec.odds,
                        rec.projected_value,
                        f"{rec.ev:.4f}",
                        f"{rec.win_probability:.4f}",
                        f"{rec.confidence:.4f}",
                        home_team,
                        away_team,
                        game_time,
                        rec.reasoning
                    ])
        except Exception as e:
            logger.error(f"Failed to save CSV to {filename}: {e}")
            # Try with absolute path as last resort
            abs_filename = os.path.abspath(filename)
            logger.info(f"Retrying with absolute path: {abs_filename}")
            with open(abs_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Game ID', 'Sport', 'Bet Type', 'Side', 'Line', 'Odds',
                    'Projected Value', 'EV', 'Win Probability', 'Confidence',
                    'Home Team', 'Away Team', 'Game Time', 'Reasoning'
                ])

                for rec in recommendations:
                    game = games.get(rec.game_id)
                    if game:
                        home_team = game.home_team
                        away_team = game.away_team
                        game_time = game.game_time.strftime('%Y-%m-%d %H:%M')
                    else:
                        home_team = away_team = game_time = "Unknown"

                    writer.writerow([
                        rec.game_id,
                        rec.sport.value,
                        rec.bet_type.value,
                        rec.side.value,
                        rec.line,
                        rec.odds,
                        rec.projected_value,
                        f"{rec.ev:.4f}",
                        f"{rec.win_probability:.4f}",
                        f"{rec.confidence:.4f}",
                        home_team,
                        away_team,
                        game_time,
                        rec.reasoning
                    ])
            filename = abs_filename

        logger.info(f"Saved {len(recommendations)} picks to {filename}")
        return filename

    def save_picks_to_json(self, recommendations: List[BetRecommendation], games: dict):
        """Save picks to JSON file for API consumption"""
        import os
        os.makedirs(self.output_path, exist_ok=True)

        filename = f"{self.output_path}/daily_picks_{datetime.now().strftime('%Y%m%d')}.json"

        output_data = []
        for rec in recommendations:
            game = games.get(rec.game_id)
            output_data.append({
                'game_id': rec.game_id,
                'sport': rec.sport.value,
                'bet_type': rec.bet_type.value,
                'side': rec.side.value,
                'line': rec.line,
                'odds': rec.odds,
                'projected_value': rec.projected_value,
                'ev': round(rec.ev, 4),
                'win_probability': round(rec.win_probability, 4),
                'confidence': round(rec.confidence, 4),
                'home_team': game.home_team if game else "Unknown",
                'away_team': game.away_team if game else "Unknown",
                'game_time': game.game_time.isoformat() if game else None,
                'reasoning': rec.reasoning
            })

        # Handle potential permission issues with SMB mounts
        if os.path.exists(filename):
            try:
                # Test if we can write to the file
                with open(filename, 'a') as f:
                    pass
            except (PermissionError, OSError):
                logger.warning(f"Cannot write to existing file {filename}, removing and recreating")
                try:
                    os.remove(filename)
                except Exception as e:
                    logger.error(f"Failed to remove {filename}: {e}")
                    # Try alternative filename
                    filename = f"{self.output_path}/daily_picks_{datetime.now().strftime('%Y%m%d')}_retry.json"

        try:
            with open(filename, 'w') as f:
                json.dump(output_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save JSON to {filename}: {e}")
            # Try with absolute path as last resort
            abs_filename = os.path.abspath(filename)
            logger.info(f"Retrying with absolute path: {abs_filename}")
            with open(abs_filename, 'w') as f:
                json.dump(output_data, f, indent=2)
            filename = abs_filename

        logger.info(f"Saved picks to JSON: {filename}")
        return filename

    def format_performance_report(self, stats: dict) -> str:
        """Format performance statistics report"""
        lines = []
        lines.append("=" * 50)
        lines.append("SportsTotalBot Performance Report")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Total Bets:     {stats['total_bets']}")
        lines.append(f"Wins:           {stats['wins']}")
        lines.append(f"Losses:         {stats['losses']}")
        lines.append(f"Win Rate:       {stats['win_rate']}%")
        lines.append(f"Total P/L:      ${stats['total_profit_loss']:+.2f}")
        lines.append(f"ROI:            {stats['roi']}%")
        lines.append("")

        if stats['total_bets'] > 0:
            if stats['roi'] > 0:
                lines.append("✓ Profitable!")
            else:
                lines.append("✗ Not profitable yet")

        lines.append("=" * 50)

        return "\n".join(lines)


class DiscordNotifier:
    """Send notifications to Discord"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_picks(self, message: str):
        """Send picks to Discord webhook"""
        import requests

        if not self.webhook_url or self.webhook_url == "":
            logger.warning("No Discord webhook configured")
            return

        data = {
            "content": message,
            "username": "SportsTotalBot"
        }

        try:
            response = requests.post(self.webhook_url, json=data, timeout=10)
            response.raise_for_status()
            logger.info("Sent picks to Discord")
        except Exception as e:
            logger.error(f"Failed to send to Discord: {e}")

    def send_simple_pick(self, rec: BetRecommendation, game: Game):
        """Send a single pick notification"""
        emoji = "🔼" if rec.side.value == "over" else "🔽"

        message = (
            f"{emoji} **{rec.side.value.upper()} {rec.line}**\n"
            f"**{game.away_team} @ {game.home_team}**\n"
            f"Odds: {rec.odds} | EV: {rec.ev:.1%} | Win Prob: {rec.win_probability:.0%}"
        )

        self.send_picks(message)


class TelegramNotifier:
    """Send picks to Telegram with team names"""

    def __init__(self, bot_token="", chat_id=""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_picks(self, picks, quality_report=None, games=None):
        """Send daily picks to Telegram in compact format (grouped by game)"""
        if not self.bot_token or not self.chat_id:
            logger.warning("No Telegram credentials configured")
            return

        try:
            import requests

            # Use Eastern Time for all timestamps
            now_et = datetime.now(ET).strftime("%b %d, %Y • %I:%M %p ET")

            # Header - clean and professional
            msg = "*─────── 🏀 SPORTS: DAILY PICKS 🏀 ───────*\n"
            msg += f"📅 {now_et}\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            if not picks:
                msg += "📭 *No +EV picks found today.*\n"
            else:
                # Group by game_id to show both totals and spreads per game
                by_game = {}
                for pick in picks:
                    game_id = getattr(pick, 'game_id', None) or pick.get('game_id', '')
                    if game_id not in by_game:
                        by_game[game_id] = {'totals': None, 'spreads': None}

                    bet_type = getattr(pick, 'bet_type', type('BetType', (), {'value': 'totals'}))
                    if hasattr(bet_type, "value"):
                        bet_type = bet_type.value
                    elif isinstance(bet_type, str):
                        pass
                    else:
                        bet_type = 'totals'

                    if bet_type == 'totals':
                        by_game[game_id]['totals'] = pick
                    elif bet_type == 'spreads':
                        by_game[game_id]['spreads'] = pick

                # Sort by EV and take top games
                game_list = []
                for game_id, recs in by_game.items():
                    total_ev = 0
                    if recs['totals']:
                        ev = getattr(recs['totals'], 'ev', 0) or recs['totals'].get('ev', 0)
                        total_ev += ev
                    if recs['spreads']:
                        ev = getattr(recs['spreads'], 'ev', 0) or recs['spreads'].get('ev', 0)
                        total_ev += ev
                    game_list.append((game_id, recs, total_ev))

                # Sort by total EV and take top 3 games
                for idx, (game_id, recs, total_ev) in enumerate(sorted(game_list, key=lambda x: x[2], reverse=True)[:3], 1):
                    game = games.get(game_id) if games else None

                    # Rank badge with circle
                    rank_emoji = ["🥇", "🥈", "🥉"][idx-1] if idx <= 3 else f"#{idx}"
                    msg += f"\n*{rank_emoji} *"

                    if game:
                        home = game.home_team
                        away = game.away_team
                        # Convert game time to ET
                        game_time_et = game.game_time.astimezone(ET).strftime('%I:%M %p ET')
                        msg += f" *{away}* vs *{home}*\n"
                        msg += f"│ 🕐 `{game_time_et}`\n"
                    else:
                        msg += f"\n*Game {game_id}*\n"

                    # Show TOTAL pick if available
                    if recs['totals']:
                        pick = recs['totals']
                        side = str(getattr(pick, 'side', '')).upper()
                        if hasattr(side, "value"):
                            side = side.value.upper()
                        line = getattr(pick, 'line', 0) or pick.get('line', 0)
                        ev = getattr(pick, 'ev', 0) or pick.get('ev', 0)

                        # Visual indicators for side
                        if side == "OVER":
                            side_emoji = "🔼"
                            side_text = "OVER"
                        else:
                            side_emoji = "🔽"
                            side_text = "UNDER"

                        # EV strength indicator
                        if ev >= 0.12:
                            ev_indicator = "💎💎💎"
                        elif ev >= 0.10:
                            ev_indicator = "💎💎"
                        elif ev >= 0.08:
                            ev_indicator = "💎"
                        else:
                            ev_indicator = "⭐"

                        msg += f"│ {side_emoji} *{side_text}* `{round(line, 1)}`  {ev_indicator}  `{ev:.1%}`\n"

                    # Show SPREAD pick if available
                    if recs['spreads']:
                        pick = recs['spreads']
                        side = getattr(pick, 'side', '') or pick.get('side', '')
                        if hasattr(side, "value"):
                            side = side.value
                        line = getattr(pick, 'line', 0) or pick.get('line', 0)
                        ev = getattr(pick, 'ev', 0) or pick.get('ev', 0)

                        if game:
                            if side == "home":
                                team = game.home_team
                                spread_str = f"-{round(line, 1)}"
                            else:
                                team = game.away_team
                                spread_str = f"+{round(line, 1)}"
                        else:
                            team = side.upper()
                            spread_str = f"{line:+.1f}"

                        # EV strength indicator
                        if ev >= 0.12:
                            ev_indicator = "💎💎💎"
                        elif ev >= 0.10:
                            ev_indicator = "💎💎"
                        elif ev >= 0.08:
                            ev_indicator = "💎"
                        else:
                            ev_indicator = "⭐"

                        msg += f"│ 🏐 *{team}* `{spread_str}`  {ev_indicator}  `{ev:.1%}`\n"

                    msg += "│\n"

            # Data quality footer
            if quality_report:
                try:
                    score = quality_report.quality_score
                    if score >= 95:
                        quality_emoji = "🟢🟢🟢"
                    elif score >= 85:
                        quality_emoji = "🟢🟢"
                    elif score >= 70:
                        quality_emoji = "🟢"
                    elif score >= 50:
                        quality_emoji = "🟡"
                    else:
                        quality_emoji = "🔴"
                    msg += f"{quality_emoji} *Data Quality:* `{round(score, 0)}/100`"
                    if score < 70:
                        msg += " ⚠️ *Use caution*"
                    msg += "\n"
                except:
                    pass

            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += "💰 *Bet responsibly. Good luck!* 💰"

            url = "https://api.telegram.org/bot" + self.bot_token + "/sendMessage"
            payload = {"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"}
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                logger.info("Sent picks to Telegram")
            else:
                logger.error("Telegram failed: " + str(r.status_code))

        except Exception as e:
            logger.error("Telegram error: " + str(e))
