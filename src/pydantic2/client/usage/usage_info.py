from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from peewee import (
    Model, SqliteDatabase, CharField, IntegerField,
    FloatField, DateTimeField, TextField, AutoField, fn
)
import sqlite3
from ...utils.logger import logger

# Database configuration
THIS_DIR = Path(__file__).parent.parent.parent
DB_DIR = THIS_DIR / 'db'
DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = DB_DIR / "usage.db"

# Singleton database instance
_db = None


def get_db():
    """Get or create database connection singleton"""
    global _db
    if _db is None:
        _db = SqliteDatabase(DEFAULT_DB_PATH)
    return _db


class UsageLog(Model):
    """Model for tracking API usage."""
    id = AutoField()
    client_id = CharField(null=True)
    user_id = CharField(null=True)
    request_id = CharField(null=True)
    model_name = CharField()
    raw_request = TextField()
    raw_response = TextField(null=True)
    error_message = TextField(null=True)
    prompt_tokens = IntegerField(null=True)
    completion_tokens = IntegerField(null=True)
    total_tokens = IntegerField(null=True)
    total_cost = FloatField(null=True)
    response_time = FloatField(null=True)
    status = CharField(null=True)  # Added status field
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = get_db()


class UsageInfo:
    """Class for tracking API usage information."""

    def __init__(self, client_id: Optional[str] = None, user_id: Optional[str] = None):
        """Initialize the usage info tracker.

        Args:
            client_id: Optional client identifier
            user_id: Optional user identifier
        """
        self.client_id = client_id
        self.user_id = user_id
        self.db = get_db()
        try:
            if self.db.is_closed():
                self.db.connect()
            self.db.create_tables([UsageLog], safe=True)
            logger.debug("Usage info initialized with database")
        except Exception as e:
            logger.error(f"Database error: {e}")
            self.db = None

    def log_request(self, model_name: str, raw_request: str, request_id: str) -> None:
        """Log a request to the API.

        Args:
            model_name: The name of the model being used
            raw_request: The raw request sent to the API
            request_id: Unique identifier for the request

        Returns:
            None
        """
        if not self.db:
            return

        try:
            if self.db.is_closed:
                self.db = get_db()

            UsageLog.create(
                request_id=request_id,
                client_id=self.client_id,
                user_id=self.user_id,
                model_name=model_name,
                raw_request=raw_request
            )
        except Exception as e:
            logger.error(f"Error logging request: {e}")

    def log_response(self, raw_response: str, usage_info: Dict[str, Any],
                     response_time: Optional[float] = None, request_id: Optional[str] = None) -> None:
        """Log a successful response from the API.

        Args:
            raw_response: The raw response from the API
            usage_info: Dictionary containing token usage information
            response_time: Time taken to get the response in seconds
            request_id: Unique identifier for the request

        Returns:
            None
        """
        if not self.db or not request_id:
            return

        try:
            if self.db.is_closed:
                self.db = get_db()

            prompt_tokens = usage_info.get('prompt_tokens', 0)
            completion_tokens = usage_info.get('completion_tokens', 0)
            total_tokens = usage_info.get('total_tokens', 0)
            total_cost = usage_info.get('total_cost', 0.0)

            UsageLog.update(
                raw_response=raw_response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                total_cost=total_cost,
                response_time=response_time,
                status='completed'
            ).where(UsageLog.request_id == request_id).execute()
        except Exception as e:
            logger.error(f"Error logging response: {e}")

    def log_error(self, error_message: str, response_time: Optional[float] = None,
                  request_id: Optional[str] = None) -> None:
        """Log an error response from the API.

        Args:
            error_message: The error message
            response_time: Time taken before the error occurred
            request_id: Unique identifier for the request

        Returns:
            None
        """
        if not self.db or not request_id:
            return

        try:
            if self.db.is_closed:
                self.db = get_db()

            UsageLog.update(
                error_message=error_message,
                response_time=response_time,
                status='error'
            ).where(UsageLog.request_id == request_id).execute()
        except Exception as e:
            logger.error(f"Error logging error: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics.

        Returns:
            Dictionary containing usage statistics
        """
        if not self.db:
            return {
                'total_requests': 0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'models': []
            }

        try:
            if self.db.is_closed:
                self.db = get_db()

            overall_stats = UsageLog.select(
                fn.COUNT(UsageLog.id).alias('total_requests'),
                fn.SUM(UsageLog.total_tokens).alias('total_tokens'),
                fn.SUM(UsageLog.total_cost).alias('total_cost')
            ).where(UsageLog.client_id == self.client_id, UsageLog.user_id == self.user_id).dicts().get()

            per_model_stats = UsageLog.select(
                UsageLog.model_name,
                fn.COUNT(UsageLog.id).alias('requests'),
                fn.SUM(UsageLog.total_tokens).alias('tokens'),
                fn.SUM(UsageLog.total_cost).alias('cost')
            ).where(UsageLog.client_id == self.client_id, UsageLog.user_id == self.user_id).group_by(UsageLog.model_name).dicts()

            return {
                'total_requests': overall_stats['total_requests'] or 0,
                'total_tokens': overall_stats['total_tokens'] or 0,
                'total_cost': overall_stats['total_cost'] or 0.0,
                'models': per_model_stats
            }

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                'total_requests': 0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'models': []
            }

    def print_usage_info(self):
        """Print usage information to the console."""
        stats = self.get_usage_stats()
        print("\nUsage Statistics:")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Total Tokens: {stats['total_tokens']}")
        print(f"Total Cost: ${stats['total_cost']:.4f}")

        if stats['models']:
            print("\nPer-Model Statistics:")
            for model in stats['models']:
                print(f"  {model['model_name']}:")
                print(f"    Requests: {model['requests']}")
                print(f"    Tokens: {model['tokens']}")
                print(f"    Cost: ${model['cost']:.4f}")

    def close(self):
        """Close the database connection."""
        if self.db and not self.db.is_closed():
            try:
                self.db.close()
            except sqlite3.Error:
                pass
