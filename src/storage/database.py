"""
Database handling for SportsTotalBot
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from contextlib import contextmanager

from ..data.models import (
    Game, OddsLine, Projection,
    BetRecommendation, PickResult,
    SportType, BetType
)


class Database:
    """SQLite database for storing games, picks, and results"""

    def __init__(self, db_path: str = "data/sportstotalbot.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            # Games table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    game_id TEXT PRIMARY KEY,
                    sport TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    game_time TEXT NOT NULL,
                    home_score INTEGER,
                    away_score INTEGER,
                    is_completed BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Odds table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS odds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    bet_type TEXT NOT NULL,
                    total_line REAL,
                    over_odds INTEGER,
                    under_odds INTEGER,
                    home_spread REAL,
                    home_spread_odds INTEGER,
                    away_spread REAL,
                    away_spread_odds INTEGER,
                    home_moneyline INTEGER,
                    away_moneyline INTEGER,
                    book_name TEXT,
                    update_time TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games (game_id)
                )
            """)

            # Projections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    projected_home_score REAL NOT NULL,
                    projected_away_score REAL NOT NULL,
                    projected_total REAL NOT NULL,
                    confidence REAL NOT NULL,
                    model_version TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games (game_id)
                )
            """)

            # Recommendations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    bet_type TEXT NOT NULL,
                    side TEXT NOT NULL,
                    line REAL NOT NULL,
                    odds INTEGER NOT NULL,
                    projected_value REAL NOT NULL,
                    ev REAL NOT NULL,
                    win_probability REAL NOT NULL,
                    confidence REAL NOT NULL,
                    reasoning TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games (game_id)
                )
            """)

            # Results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    won BOOLEAN NOT NULL,
                    actual_result REAL NOT NULL,
                    line REAL NOT NULL,
                    profit_loss REAL NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (recommendation_id) REFERENCES recommendations (id),
                    FOREIGN KEY (game_id) REFERENCES games (game_id)
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_sport ON games(sport)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_odds_game ON odds(game_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recs_game ON recommendations(game_id)")

    def save_game(self, game: Game) -> str:
        """Save or update a game"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO games
                (game_id, sport, home_team, away_team, game_time, home_score, away_score, is_completed, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game.game_id, game.sport.value, game.home_team, game.away_team,
                game.game_time.isoformat(), game.home_team_score, game.away_team_score,
                game.is_completed, datetime.now().isoformat()
            ))
        return game.game_id

    def save_odds(self, odds: OddsLine):
        """Save odds data"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO odds
                (game_id, sport, bet_type, total_line, over_odds, under_odds,
                 home_spread, home_spread_odds, away_spread, away_spread_odds,
                 home_moneyline, away_moneyline, book_name, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                odds.game_id, odds.sport.value, odds.bet_type.value,
                odds.total_line, odds.over_odds, odds.under_odds,
                odds.home_spread, odds.home_spread_odds, odds.away_spread, odds.away_spread_odds,
                odds.home_moneyline, odds.away_moneyline, odds.book_name,
                odds.update_time.isoformat() if odds.update_time else None
            ))

    def save_recommendation(self, rec: BetRecommendation) -> int:
        """Save a bet recommendation"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO recommendations
                (game_id, sport, bet_type, side, line, odds, projected_value, ev,
                 win_probability, confidence, reasoning, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.game_id, rec.sport.value, rec.bet_type.value, rec.side.value,
                rec.line, rec.odds, rec.projected_value, rec.ev,
                rec.win_probability, rec.confidence, rec.reasoning,
                rec.generated_at.isoformat() if rec.generated_at else datetime.now().isoformat()
            ))
            return cursor.lastrowid

    def get_pending_recommendations(self) -> List[dict]:
        """Get all recommendations that haven't been resolved"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT r.*, g.home_score, g.away_score, g.is_completed
                FROM recommendations r
                JOIN games g ON r.game_id = g.game_id
                WHERE r.id NOT IN (SELECT recommendation_id FROM results)
                ORDER BY r.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_results_for_completed_games(self):
        """Check completed games and update results for recommendations"""
        pending = self.get_pending_recommendations()
        results_updated = []

        for rec in pending:
            if rec['is_completed'] and rec['home_score'] is not None:
                # Calculate if the bet won
                won = self._calculate_bet_result(rec)

                # Save result
                profit_loss = self._calculate_profit_loss(rec, won)

                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO results
                        (recommendation_id, game_id, won, actual_result, line, profit_loss, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rec['id'], rec['game_id'], won,
                        rec['home_score'] + rec['away_score'] if rec['bet_type'] == 'totals' else None,
                        rec['line'], profit_loss, datetime.now().isoformat()
                    ))
                results_updated.append(rec['id'])

        return results_updated

    def _calculate_bet_result(self, rec: dict) -> bool:
        """Calculate if a bet won based on game results"""
        total_score = rec['home_score'] + rec['away_score']

        if rec['bet_type'] == 'totals':
            if rec['side'] == 'over':
                return total_score > rec['line']
            else:  # under
                return total_score < rec['line']
        # Add spread/moneyline logic later
        return False

    def _calculate_profit_loss(self, rec: dict, won: bool) -> float:
        """Calculate profit/loss for a bet (assuming $100 unit)"""
        unit = 100.0

        if won:
            # Calculate profit based on American odds
            if rec['odds'] > 0:
                return unit * (rec['odds'] / 100)
            else:
                return unit * (100 / abs(rec['odds']))
        else:
            return -unit  # Lost the bet

    def get_performance_stats(self) -> dict:
        """Get overall performance statistics"""
        with self._get_connection() as conn:
            # Total bets
            total = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]

            # Wins
            wins = conn.execute("SELECT COUNT(*) FROM results WHERE won = 1").fetchone()[0]

            # Win rate
            win_rate = wins / total if total > 0 else 0

            # Total profit/loss
            profit = conn.execute("SELECT SUM(profit_loss) FROM results").fetchone()[0] or 0

            # ROI
            total_invested = total * 100  # Assuming $100 per bet
            roi = (profit / total_invested * 100) if total_invested > 0 else 0

            return {
                'total_bets': total,
                'wins': wins,
                'losses': total - wins,
                'win_rate': round(win_rate * 100, 2),
                'total_profit_loss': round(profit, 2),
                'roi': round(roi, 2)
            }
