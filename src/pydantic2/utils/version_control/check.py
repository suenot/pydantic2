import requests
import semver
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

from ...__pack__ import __version__, __name__
from ..logger import logger


class VersionControl:
    """Class to manage version control and caching for the library."""

    CACHE_DURATION = timedelta(days=1)

    def __init__(self):
        self.current_version = __version__
        self.package_name = __name__
        # Store cache in the same directory as the module
        module_dir = Path(__file__).parent
        self.cache_file = module_dir / "cache.json"
        self._load_initial_cache()

    def _load_initial_cache(self):
        """Load initial cache values."""
        self.cached_version, self.cache_time = self._load_cache()

    def _fetch_latest_version(self) -> str:
        """Fetch the latest version from PyPI."""
        url = f"https://pypi.org/pypi/{self.package_name}/json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['info']['version']
        return "0.0.0"

    def _load_cache(self) -> tuple[str, datetime]:
        """Load the cached version and timestamp from JSON."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Verify cache data is valid
                    if (not isinstance(cache_data, dict) or
                        'version' not in cache_data or
                            'timestamp' not in cache_data):
                        return "0.0.0", datetime.min
                    return (
                        cache_data['version'],
                        datetime.fromtimestamp(cache_data['timestamp'])
                    )
            except (json.JSONDecodeError, KeyError, ValueError):
                # If cache file is corrupted or invalid, return default values
                return "0.0.0", datetime.min
        return "0.0.0", datetime.min

    def _save_cache(self, version: str):
        """Save the version and current timestamp to JSON cache."""
        cache_data = {
            'version': version,
            'timestamp': time.time(),
            'package': self.package_name,
            'last_checked': datetime.now().isoformat()
        }
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        # Update instance variables after saving
        self.cached_version = version
        self.cache_time = datetime.fromtimestamp(cache_data['timestamp'])

    def check_for_update(self):
        """Check if there is a newer version available."""
        current_time = datetime.now()
        cache_age = current_time - self.cache_time

        if cache_age > self.CACHE_DURATION:
            latest_version = self._fetch_latest_version()
            self._save_cache(latest_version)
            logger.debug(f"[DEBUG] Fetched latest version: {latest_version}")
        else:
            latest_version = self.cached_version
            logger.debug(f"[DEBUG] Using cached version: {latest_version}")

        logger.debug(f"[DEBUG] Current version: {self.current_version}")

        if semver.compare(latest_version, self.current_version) > 0:
            logger.warning(
                f"🚀 A new version {latest_version} is available! "
                f"You are using {self.current_version}. Consider updating."
            )
        else:
            logger.debug(
                f"✅ You are using the latest version: {self.current_version}."
            )
