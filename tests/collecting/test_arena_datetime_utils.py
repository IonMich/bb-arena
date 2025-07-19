"""
Arena Date/Time Utilities

This module provides utilities for converting BuzzerBeater date strings to UTC time ranges.
Since BuzzerBeater dates don't include specific times, we need to handle timezone conversion
for full date ranges.

Key Components:
- BuzzerBeaterTimezone: Service for detecting and handling BuzzerBeater timezones
- DateRangeConverter: Service for converting date strings to UTC time ranges
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import pytz
from dataclasses import dataclass


@dataclass
class UTCTimeRange:
    """Represents a UTC time range for a given local date."""
    earliest_utc: datetime  # Start of day in UTC
    latest_utc: datetime    # End of day in UTC (23:59:59)
    local_date: str        # Original date string
    local_timezone: str    # Timezone used for conversion


class BuzzerBeaterTimezone:
    """Service for detecting and managing BuzzerBeater timezone information."""
    
    # Default fallback timezone as specified
    DEFAULT_TIMEZONE = "US/Eastern"
    
    @staticmethod
    def detect_timezone_from_html(html_content: Optional[str] = None) -> str:
        """
        Attempt to detect the timezone from BuzzerBeater HTML content.
        
        Args:
            html_content: Optional HTML content to analyze
            
        Returns:
            Timezone string (defaults to US/Eastern if detection fails)
        """
        # TODO: In the future, we could look for timezone hints in the HTML
        # For now, BuzzerBeater appears to use Eastern Time as default
        
        if html_content:
            # Look for potential timezone indicators in HTML
            # This is a placeholder for future enhancement
            pass
        
        # Fallback to Eastern Time as requested
        return BuzzerBeaterTimezone.DEFAULT_TIMEZONE
    
    @staticmethod
    def get_timezone_object(timezone_str: str) -> pytz.BaseTzInfo:
        """
        Get a pytz timezone object from a timezone string.
        
        Args:
            timezone_str: Timezone identifier (e.g., "US/Eastern")
            
        Returns:
            pytz timezone object
        """
        try:
            return pytz.timezone(timezone_str)
        except pytz.UnknownTimeZoneError:
            # Fallback to default if unknown timezone
            return pytz.timezone(BuzzerBeaterTimezone.DEFAULT_TIMEZONE)


class DateRangeConverter:
    """Service for converting date strings to UTC time ranges."""
    
    @staticmethod
    def parse_date_string(date_str: str) -> datetime:
        """
        Parse a BuzzerBeater date string into a date object.
        
        Args:
            date_str: Date string in format "MM/DD/YYYY"
            
        Returns:
            datetime object (time set to midnight)
        """
        try:
            return datetime.strptime(date_str.strip(), '%m/%d/%Y')
        except ValueError as e:
            raise ValueError(f"Invalid date format: {date_str}. Expected MM/DD/YYYY") from e
    
    @staticmethod
    def get_earliest_utc_time(date_str: str, timezone_str: str) -> datetime:
        """
        Get the earliest possible UTC time for a given date in a timezone.
        
        This represents the start of the day (00:00:00) in the local timezone
        converted to UTC.
        
        Args:
            date_str: Date string in format "MM/DD/YYYY"
            timezone_str: Timezone identifier (e.g., "US/Eastern")
            
        Returns:
            Earliest UTC datetime for that date
        """
        # Parse the date
        local_date = DateRangeConverter.parse_date_string(date_str)
        
        # Get timezone object
        tz = BuzzerBeaterTimezone.get_timezone_object(timezone_str)
        
        # Create start of day in local timezone (00:00:00)
        local_start = tz.localize(local_date)
        
        # Convert to UTC
        return local_start.astimezone(timezone.utc)
    
    @staticmethod
    def get_latest_utc_time(date_str: str, timezone_str: str) -> datetime:
        """
        Get the latest possible UTC time for a given date in a timezone.
        
        This represents the end of the day (23:59:59.999999) in the local timezone
        converted to UTC.
        
        Args:
            date_str: Date string in format "MM/DD/YYYY"
            timezone_str: Timezone identifier (e.g., "US/Eastern")
            
        Returns:
            Latest UTC datetime for that date
        """
        # Parse the date
        local_date = DateRangeConverter.parse_date_string(date_str)
        
        # Get timezone object
        tz = BuzzerBeaterTimezone.get_timezone_object(timezone_str)
        
        # Create end of day in local timezone (23:59:59.999999)
        end_of_day = local_date.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        local_end = tz.localize(end_of_day)
        
        # Convert to UTC
        return local_end.astimezone(timezone.utc)
    
    @staticmethod
    def get_utc_time_range(date_str: str, timezone_str: Optional[str] = None) -> UTCTimeRange:
        """
        Get the complete UTC time range for a given date.
        
        Args:
            date_str: Date string in format "MM/DD/YYYY"
            timezone_str: Optional timezone identifier (defaults to detection)
            
        Returns:
            UTCTimeRange object with earliest and latest UTC times
        """
        if timezone_str is None:
            timezone_str = BuzzerBeaterTimezone.detect_timezone_from_html()
        
        earliest = DateRangeConverter.get_earliest_utc_time(date_str, timezone_str)
        latest = DateRangeConverter.get_latest_utc_time(date_str, timezone_str)
        
        return UTCTimeRange(
            earliest_utc=earliest,
            latest_utc=latest,
            local_date=date_str,
            local_timezone=timezone_str
        )


# Convenience functions for easy usage
def get_earliest_utc_for_date(date_str: str, timezone_str: Optional[str] = None) -> datetime:
    """
    Convenience function to get earliest UTC time for a date.
    
    Args:
        date_str: Date string in format "MM/DD/YYYY"
        timezone_str: Optional timezone (defaults to US/Eastern)
        
    Returns:
        Earliest UTC datetime
    """
    if timezone_str is None:
        timezone_str = BuzzerBeaterTimezone.DEFAULT_TIMEZONE
    
    return DateRangeConverter.get_earliest_utc_time(date_str, timezone_str)


def get_latest_utc_for_date(date_str: str, timezone_str: Optional[str] = None) -> datetime:
    """
    Convenience function to get latest UTC time for a date.
    
    Args:
        date_str: Date string in format "MM/DD/YYYY"
        timezone_str: Optional timezone (defaults to US/Eastern)
        
    Returns:
        Latest UTC datetime
    """
    if timezone_str is None:
        timezone_str = BuzzerBeaterTimezone.DEFAULT_TIMEZONE
    
    return DateRangeConverter.get_latest_utc_time(date_str, timezone_str)


def get_bb_timezone_from_html(html_content: Optional[str] = None) -> str:
    """
    Convenience function to detect BuzzerBeater timezone.
    
    Args:
        html_content: Optional HTML content to analyze
        
    Returns:
        Timezone string (US/Eastern as fallback)
    """
    return BuzzerBeaterTimezone.detect_timezone_from_html(html_content)


if __name__ == "__main__":
    # Example usage
    print("🕐 BuzzerBeater Date/Time Utilities")
    print()
    
    # Test with the example from the request
    date_example = "5/17/2025"
    timezone_example = "US/Eastern"
    
    print(f"📅 Example: {date_example} in {timezone_example}")
    
    earliest = get_earliest_utc_for_date(date_example, timezone_example)
    latest = get_latest_utc_for_date(date_example, timezone_example)
    
    print(f"   Earliest UTC: {earliest}")
    print(f"   Latest UTC:   {latest}")
    print()
    
    # Test with full range object
    time_range = DateRangeConverter.get_utc_time_range(date_example, timezone_example)
    print(f"🔍 Full Range Object:")
    print(f"   Local Date: {time_range.local_date}")
    print(f"   Local Timezone: {time_range.local_timezone}")
    print(f"   UTC Range: {time_range.earliest_utc} to {time_range.latest_utc}")
    print()
    
    # Test timezone detection
    detected_tz = get_bb_timezone_from_html()
    print(f"🌍 Detected/Default Timezone: {detected_tz}")


import pytest
from datetime import datetime, timezone
import pytz


class TestBuzzerBeaterTimezone:
    """Test suite for BuzzerBeater timezone detection and handling."""
    
    def test_default_timezone_fallback(self) -> None:
        """Test: Does timezone detection fall back to US/Eastern?"""
        detected = BuzzerBeaterTimezone.detect_timezone_from_html()
        assert detected == "US/Eastern"
        
        # Test with None
        detected_none = BuzzerBeaterTimezone.detect_timezone_from_html(None)
        assert detected_none == "US/Eastern"
        
        # Test with empty HTML
        detected_empty = BuzzerBeaterTimezone.detect_timezone_from_html("")
        assert detected_empty == "US/Eastern"
    
    def test_timezone_object_creation(self) -> None:
        """Test: Can we create valid timezone objects?"""
        # Test valid timezone
        tz = BuzzerBeaterTimezone.get_timezone_object("US/Eastern")
        assert isinstance(tz, pytz.BaseTzInfo)
        assert str(tz) == "US/Eastern"
        
        # Test Pacific timezone
        tz_pacific = BuzzerBeaterTimezone.get_timezone_object("US/Pacific")
        assert isinstance(tz_pacific, pytz.BaseTzInfo)
        assert str(tz_pacific) == "US/Pacific"
    
    def test_invalid_timezone_fallback(self) -> None:
        """Test: Does invalid timezone fall back to default?"""
        tz = BuzzerBeaterTimezone.get_timezone_object("Invalid/Timezone")
        assert str(tz) == "US/Eastern"


class TestDateRangeConverter:
    """Test suite for date string to UTC conversion."""
    
    def test_date_string_parsing(self) -> None:
        """Test: Can we parse BuzzerBeater date strings?"""
        # Test standard format
        parsed = DateRangeConverter.parse_date_string("5/17/2025")
        assert parsed.year == 2025
        assert parsed.month == 5
        assert parsed.day == 17
        assert parsed.hour == 0
        assert parsed.minute == 0
        
        # Test with leading zeros
        parsed_zeros = DateRangeConverter.parse_date_string("05/07/2025")
        assert parsed_zeros.month == 5
        assert parsed_zeros.day == 7
    
    def test_invalid_date_string(self) -> None:
        """Test: Does invalid date string raise proper error?"""
        with pytest.raises(ValueError, match="Invalid date format"):
            DateRangeConverter.parse_date_string("invalid date")
        
        with pytest.raises(ValueError, match="Invalid date format"):
            DateRangeConverter.parse_date_string("2025-05-17")  # Wrong format
    
    def test_earliest_utc_time_eastern(self) -> None:
        """Test: Earliest UTC time calculation for Eastern timezone."""
        # Test during Standard Time (EST = UTC-5)
        earliest = DateRangeConverter.get_earliest_utc_time("1/15/2025", "US/Eastern")
        assert earliest.hour == 5  # EST is UTC-5
        assert earliest.minute == 0
        assert earliest.second == 0
        
        # Test during Daylight Time (EDT = UTC-4)  
        earliest_summer = DateRangeConverter.get_earliest_utc_time("7/15/2025", "US/Eastern")
        assert earliest_summer.hour == 4  # EDT is UTC-4
        assert earliest_summer.minute == 0
        assert earliest_summer.second == 0
    
    def test_latest_utc_time_eastern(self) -> None:
        """Test: Latest UTC time calculation for Eastern timezone."""
        # Test during Standard Time (EST = UTC-5)
        latest = DateRangeConverter.get_latest_utc_time("1/15/2025", "US/Eastern")
        assert latest.day == 16  # Next day in UTC
        assert latest.hour == 4   # 23:59:59 EST + 5 hours = 04:59:59 UTC next day
        assert latest.minute == 59
        assert latest.second == 59
        
        # Test during Daylight Time (EDT = UTC-4)
        latest_summer = DateRangeConverter.get_latest_utc_time("7/15/2025", "US/Eastern")
        assert latest_summer.day == 16  # Next day in UTC
        assert latest_summer.hour == 3   # 23:59:59 EDT + 4 hours = 03:59:59 UTC next day
        assert latest_summer.minute == 59
        assert latest_summer.second == 59
    
    def test_utc_time_range_object(self) -> None:
        """Test: Complete UTC time range object creation."""
        time_range = DateRangeConverter.get_utc_time_range("5/17/2025", "US/Eastern")
        
        assert isinstance(time_range, UTCTimeRange)
        assert time_range.local_date == "5/17/2025"
        assert time_range.local_timezone == "US/Eastern"
        assert time_range.earliest_utc.hour == 4  # EDT = UTC-4
        assert time_range.latest_utc.hour == 3    # Next day
        assert time_range.latest_utc.day == 18    # Next day
    
    def test_timezone_defaults(self) -> None:
        """Test: Does None timezone default to detected timezone?"""
        time_range = DateRangeConverter.get_utc_time_range("5/17/2025")
        assert time_range.local_timezone == "US/Eastern"


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    def test_convenience_function_earliest(self) -> None:
        """Test: Convenience function for earliest UTC time."""
        # With explicit timezone
        earliest = get_earliest_utc_for_date("5/17/2025", "US/Eastern")
        assert earliest.hour == 4
        
        # With default timezone
        earliest_default = get_earliest_utc_for_date("5/17/2025")
        assert earliest_default.hour == 4
    
    def test_convenience_function_latest(self) -> None:
        """Test: Convenience function for latest UTC time."""
        # With explicit timezone
        latest = get_latest_utc_for_date("5/17/2025", "US/Eastern")
        assert latest.day == 18
        assert latest.hour == 3
        
        # With default timezone
        latest_default = get_latest_utc_for_date("5/17/2025")
        assert latest_default.day == 18
        assert latest_default.hour == 3
    
    def test_timezone_detection_function(self) -> None:
        """Test: Convenience function for timezone detection."""
        detected = get_bb_timezone_from_html()
        assert detected == "US/Eastern"
        
        detected_with_html = get_bb_timezone_from_html("<html>some content</html>")
        assert detected_with_html == "US/Eastern"


class TestRealWorldScenarios:
    """Test suite for real-world BuzzerBeater scenarios."""
    
    def test_example_from_request(self) -> None:
        """Test: The exact example from the user request."""
        # Example: 05/17/2025 in ET should give UTC range 05/17/2025 4am to 05/18/2025 3:59am
        earliest = get_earliest_utc_for_date("05/17/2025", "US/Eastern")
        latest = get_latest_utc_for_date("05/17/2025", "US/Eastern")
        
        assert earliest.strftime("%m/%d/%Y %H:%M") == "05/17/2025 04:00"
        assert latest.strftime("%m/%d/%Y %H:%M") == "05/18/2025 03:59"
    
    def test_different_timezones(self) -> None:
        """Test: UTC conversion for different timezones."""
        # Pacific Time (UTC-8 in standard, UTC-7 in daylight)
        earliest_pacific = get_earliest_utc_for_date("5/17/2025", "US/Pacific")
        assert earliest_pacific.hour == 7  # PDT is UTC-7
        
        # Central Time (UTC-6 in standard, UTC-5 in daylight)
        earliest_central = get_earliest_utc_for_date("5/17/2025", "US/Central")
        assert earliest_central.hour == 5  # CDT is UTC-5
    
    def test_winter_vs_summer_time(self) -> None:
        """Test: Daylight saving time handling."""
        # Winter date (Standard Time)
        winter_earliest = get_earliest_utc_for_date("1/15/2025", "US/Eastern")
        assert winter_earliest.hour == 5  # EST = UTC-5
        
        # Summer date (Daylight Time)
        summer_earliest = get_earliest_utc_for_date("7/15/2025", "US/Eastern")
        assert summer_earliest.hour == 4  # EDT = UTC-4


def test_datetime_utils_integration() -> None:
    """Integration test for datetime utilities."""
    print("Testing BuzzerBeater DateTime Utilities...")
    
    # Test the core functionality
    test_date = "5/17/2025"
    timezone_str = "US/Eastern"
    
    # Get the range
    time_range = DateRangeConverter.get_utc_time_range(test_date, timezone_str)
    
    print(f"✅ DateTime Utils Complete:")
    print(f"   Local: {time_range.local_date} ({time_range.local_timezone})")
    print(f"   UTC Range: {time_range.earliest_utc} to {time_range.latest_utc}")
    
    # Verify the range is about 24 hours
    duration = time_range.latest_utc - time_range.earliest_utc
    assert duration.total_seconds() >= 86399  # Almost 24 hours (23:59:59.999999)
    assert duration.total_seconds() < 86400   # Less than exactly 24 hours
