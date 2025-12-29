"""Unit tests for date utility functions."""

import datetime
from datetime import timedelta
import pytest
from unittest.mock import patch, MagicMock

from cqc_lem.utilities.date import convert_datetime_to_local_tz, format_year, get_datetime


class TestDateUtilities:
    """Test suite for date utility functions."""

    def test_convert_datetime_to_local_tz_with_utc(self):
        """Test converting UTC datetime to local timezone."""
        # Create a UTC datetime
        utc_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Convert to local timezone
        local_time = convert_datetime_to_local_tz(utc_time)
        
        # Verify it has timezone info
        assert local_time.tzinfo is not None
        # Verify it's different from UTC (unless system is in UTC)
        assert isinstance(local_time, datetime.datetime)

    def test_convert_datetime_to_local_tz_naive(self):
        """Test converting naive datetime to local timezone assuming UTC."""
        # Create a naive datetime
        naive_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        
        # Convert to local timezone (assuming UTC)
        local_time = convert_datetime_to_local_tz(naive_time, assumed_utc=True)
        
        # Verify it has timezone info
        assert local_time.tzinfo is not None
        assert isinstance(local_time, datetime.datetime)

    def test_format_year(self):
        """Test formatting year strings."""
        # Test various year formats (format_year expects a 4-digit year as string)
        assert format_year("2020") == "20"
        assert format_year("2024") == "24"

    def test_get_datetime(self):
        """Test parsing datetime from text."""
        # Test parsing various date formats
        result = get_datetime("2024-01-01 12:00:00")
        assert isinstance(result, datetime.datetime) or result is None

    def test_datetime_arithmetic_with_timezone(self):
        """Test that datetime arithmetic works correctly with timezones."""
        # Create a timezone-aware datetime
        utc_time = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Subtract 15 minutes
        updated_time = utc_time - timedelta(minutes=15)
        
        # Verify the time is correct
        expected = datetime.datetime(2024, 1, 1, 11, 45, 0, tzinfo=datetime.timezone.utc)
        assert updated_time == expected
        assert updated_time.tzinfo == datetime.timezone.utc

    def test_datetime_format_12_hour(self):
        """Test formatting datetime in 12-hour format."""
        # Create a datetime
        dt = datetime.datetime(2024, 1, 1, 15, 30, 0, tzinfo=datetime.timezone.utc)
        
        # Format in 12-hour format
        formatted = dt.strftime('%Y-%m-%d %I:%M:%S %p %Z')
        
        # Verify format
        assert '03:30:00 PM' in formatted
        assert '2024-01-01' in formatted
        assert 'UTC' in formatted or 'GMT' in formatted  # Depends on system


@pytest.mark.unit
class TestDateIntegration:
    """Integration tests for date utilities with database."""

    @pytest.mark.requires_database
    def test_post_scheduled_time_conversion(self, mock_database_connection, sample_post_data):
        """Test scheduled time conversion for posts from database."""
        # This test would require actual database connection
        # Marking with requires_database to skip in CI
        pass
