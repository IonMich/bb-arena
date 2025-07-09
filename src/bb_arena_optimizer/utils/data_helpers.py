"""Helper functions for data processing and analysis."""

import re
from datetime import datetime


def calculate_moving_average(values: list[float], window: int = 5) -> list[float]:
    """Calculate moving average of a list of values.

    Args:
        values: List of numerical values
        window: Size of the moving window

    Returns:
        List of moving averages
    """
    if len(values) < window:
        return values

    moving_averages = []
    for i in range(len(values)):
        if i < window - 1:
            # Not enough data points for full window
            moving_averages.append(values[i])
        else:
            # Calculate average of current window
            window_values = values[i - window + 1 : i + 1]
            avg = sum(window_values) / len(window_values)
            moving_averages.append(avg)

    return moving_averages


def parse_bb_date(date_string: str) -> datetime | None:
    """Parse BuzzerBeater date string to datetime object.

    Args:
        date_string: Date string from BuzzerBeater API

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Handle ISO format with Z timezone
        if date_string.endswith("Z"):
            return datetime.fromisoformat(date_string.replace("Z", "+00:00"))

        # Handle other common formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue

        return None

    except Exception:
        return None


def format_currency(amount: float, currency: str = "$") -> str:
    """Format a monetary amount for display.

    Args:
        amount: Monetary amount
        currency: Currency symbol

    Returns:
        Formatted currency string
    """
    return f"{currency}{amount:,.2f}"


def calculate_price_elasticity(
    price_changes: list[float], demand_changes: list[float]
) -> float | None:
    """Calculate price elasticity of demand.

    Args:
        price_changes: List of percentage price changes
        demand_changes: List of percentage demand changes

    Returns:
        Price elasticity coefficient or None if calculation fails
    """
    if len(price_changes) != len(demand_changes) or len(price_changes) == 0:
        return None

    try:
        # Calculate average elasticity
        elasticities = []
        for price_change, demand_change in zip(
            price_changes, demand_changes, strict=False
        ):
            if price_change != 0:
                elasticity = demand_change / price_change
                elasticities.append(elasticity)

        if elasticities:
            return sum(elasticities) / len(elasticities)

        return None

    except Exception:
        return None


def normalize_team_name(team_name: str) -> str:
    """Normalize team name for consistent comparison.

    Args:
        team_name: Raw team name

    Returns:
        Normalized team name
    """
    if not team_name:
        return ""

    # Remove extra whitespace and convert to title case
    normalized = re.sub(r"\s+", " ", team_name.strip()).title()

    # Handle common abbreviations
    abbreviations = {"Fc": "FC", "Bc": "BC", "Cc": "CC", "Ac": "AC"}

    for old, new in abbreviations.items():
        normalized = normalized.replace(old, new)

    return normalized


def calculate_revenue_per_seat(total_revenue: float, total_attendance: int) -> float:
    """Calculate average revenue per seat sold.

    Args:
        total_revenue: Total revenue from ticket sales
        total_attendance: Total number of tickets sold

    Returns:
        Average revenue per seat
    """
    if total_attendance == 0:
        return 0.0

    return total_revenue / total_attendance


def find_optimal_price_point(
    price_points: list[float], revenues: list[float]
) -> float | None:
    """Find the price point that maximizes revenue.

    Args:
        price_points: List of price points tested
        revenues: Corresponding revenue amounts

    Returns:
        Optimal price point or None if no data
    """
    if len(price_points) != len(revenues) or len(price_points) == 0:
        return None

    max_revenue = max(revenues)
    max_index = revenues.index(max_revenue)

    return price_points[max_index]


def validate_price_within_bounds(
    price: float, min_price: float, max_price: float
) -> float:
    """Ensure price is within allowed bounds.

    Args:
        price: Proposed price
        min_price: Minimum allowed price
        max_price: Maximum allowed price

    Returns:
        Price clamped to bounds
    """
    return max(min_price, min(price, max_price))


def calculate_capacity_utilization_trend(
    utilization_history: list[float], window: int = 5
) -> str:
    """Determine trend in capacity utilization.

    Args:
        utilization_history: List of utilization percentages over time
        window: Number of recent periods to consider

    Returns:
        Trend description: 'increasing', 'decreasing', 'stable'
    """
    if len(utilization_history) < 2:
        return "stable"

    # Use only recent data if available
    recent_data = (
        utilization_history[-window:]
        if len(utilization_history) >= window
        else utilization_history
    )

    if len(recent_data) < 2:
        return "stable"

    # Calculate trend using simple linear regression slope
    n = len(recent_data)
    x_values = list(range(n))
    y_values = recent_data

    # Calculate slope (trend)
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n

    numerator = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=False)
    )
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Classify trend based on slope
    if slope > 2.0:  # Increasing by more than 2% per period
        return "increasing"
    elif slope < -2.0:  # Decreasing by more than 2% per period
        return "decreasing"
    else:
        return "stable"
