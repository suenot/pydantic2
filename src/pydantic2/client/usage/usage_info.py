from typing import Dict, Any, Optional
import sqlite3
from datetime import datetime


class UsageInfo:
    """Class for tracking and storing usage information in SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the usage tracking system.

        Args:
            db_path: Path to SQLite database file. If None, usage tracking is disabled.
        """
        self.db_path = db_path
        if db_path:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        if not self.db_path:
            return

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    prompt_price REAL NOT NULL,
                    completion_price REAL NOT NULL,
                    total_price REAL NOT NULL
                )
            """)
            conn.commit()

    def add_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        prompt_price: float,
        completion_price: float
    ) -> None:
        """Add a usage record to the database.

        Args:
            model: Name of the model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            prompt_price: Cost of prompt tokens in USD
            completion_price: Cost of completion tokens in USD
        """
        if not self.db_path:
            return

        total_price = prompt_price + completion_price
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO usage_log (
                    timestamp, model, prompt_tokens, completion_tokens,
                    prompt_price, completion_price, total_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp, model, prompt_tokens, completion_tokens,
                    prompt_price, completion_price, total_price
                )
            )
            conn.commit()

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics from the database.

        Returns:
            Dictionary containing usage statistics
        """
        if not self.db_path:
            return {}

        with sqlite3.connect(str(self.db_path)) as conn:
            # Get total usage
            total = conn.execute("""
                SELECT
                    COUNT(*) as requests,
                    SUM(prompt_tokens) as total_prompt_tokens,
                    SUM(completion_tokens) as total_completion_tokens,
                    SUM(prompt_price) as total_prompt_price,
                    SUM(completion_price) as total_completion_price,
                    SUM(total_price) as total_price
                FROM usage_log
            """).fetchone()

            # Get per-model breakdown
            models = conn.execute("""
                SELECT
                    model,
                    COUNT(*) as requests,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_price) as total_price
                FROM usage_log
                GROUP BY model
            """).fetchall()

            return {
                "total_requests": total[0] or 0,
                "total_prompt_tokens": total[1] or 0,
                "total_completion_tokens": total[2] or 0,
                "total_prompt_price": total[3] or 0,
                "total_completion_price": total[4] or 0,
                "total_price": total[5] or 0,
                "models": [
                    {
                        "name": row[0],
                        "requests": row[1],
                        "prompt_tokens": row[2],
                        "completion_tokens": row[3],
                        "total_price": row[4]
                    }
                    for row in models
                ]
            }
