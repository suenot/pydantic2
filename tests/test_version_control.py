import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from src.pydantic2.utils.version_control.check import VersionControl
from src.pydantic2.utils.logger import logger


class TestVersionControl(unittest.TestCase):
    def setUp(self):
        self.version_control = VersionControl()
        # Mock the current version for consistent testing
        self.version_control.current_version = "1.0.3"

    @patch.object(VersionControl, '_save_cache')
    @patch.object(VersionControl, '_fetch_latest_version')
    @patch.object(VersionControl, '_load_cache')
    def test_check_for_update_new_version_available(
        self, mock_load_cache, mock_fetch_latest_version, mock_save_cache
    ):
        # Mock the cache to be outdated
        outdated_time = datetime.now() - timedelta(days=2)
        mock_load_cache.return_value = ("1.0.0", outdated_time)
        # Set the cached values directly to ensure they're outdated
        self.version_control.cached_version = "1.0.0"
        self.version_control.cache_time = outdated_time
        # Mock the latest version to be greater than the current version
        mock_fetch_latest_version.return_value = "1.0.4"

        with patch.object(logger, 'debug') as mock_debug, \
                patch.object(logger, 'warning') as mock_warning:
            self.version_control.check_for_update()
            # Verify that we fetched and saved the new version
            mock_fetch_latest_version.assert_called_once()
            mock_save_cache.assert_called_once_with("1.0.4")
            # Verify debug messages
            mock_debug.assert_any_call("[DEBUG] Fetched latest version: 1.0.4")
            mock_debug.assert_any_call("[DEBUG] Current version: 1.0.3")
            mock_warning.assert_called_with(
                "🚀 A new version 1.0.4 is available! "
                "You are using 1.0.3. Consider updating."
            )

    @patch.object(VersionControl, '_fetch_latest_version')
    @patch.object(VersionControl, '_load_cache')
    def test_check_for_update_no_new_version(
        self, mock_load_cache, mock_fetch_latest_version
    ):
        # Mock the cache to be up-to-date
        current_time = datetime.now()
        mock_load_cache.return_value = ("1.0.3", current_time)
        # Set the cached values directly
        self.version_control.cached_version = "1.0.3"
        self.version_control.cache_time = current_time
        # Mock the latest version to be the same as the current version
        mock_fetch_latest_version.return_value = "1.0.3"

        with patch.object(logger, 'debug') as mock_debug:
            self.version_control.check_for_update()
            mock_debug.assert_any_call("[DEBUG] Using cached version: 1.0.3")
            mock_debug.assert_any_call("[DEBUG] Current version: 1.0.3")
            mock_debug.assert_any_call(
                "✅ You are using the latest version: 1.0.3."
            )


if __name__ == '__main__':
    unittest.main()
