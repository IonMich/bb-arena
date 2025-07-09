"""Arena and seat type data models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SeatType:
    """Represents a type of seat in the arena."""

    name: str
    capacity: int
    current_price: float
    min_price: float
    max_price: float

    def is_price_valid(self, price: float) -> bool:
        """Check if a price is within the allowed range."""
        return self.min_price <= price <= self.max_price

    def get_max_revenue(self) -> float:
        """Calculate maximum revenue for this seat type at current price."""
        return self.capacity * self.current_price

    def calculate_revenue(self, attendance: int, price: float | None = None) -> float:
        """Calculate revenue for given attendance and price."""
        price_used = price if price is not None else self.current_price
        return min(attendance, self.capacity) * price_used


class Arena:
    """Represents the team's arena with all seat types and pricing."""

    def __init__(self, arena_data: dict[str, Any]) -> None:
        """Initialize arena from API data.

        Args:
            arena_data: Dictionary from API containing seats and prices data
        """
        self.bleachers = SeatType(
            name="Bleachers",
            capacity=arena_data["seats"].get("bleachers", 0),
            current_price=arena_data["prices"].get("bleachers", 0),
            min_price=5.0,
            max_price=20.0,
        )

        self.lower_tier = SeatType(
            name="Lower Tier",
            capacity=arena_data["seats"].get("lower_tier", 0),
            current_price=arena_data["prices"].get("lower_tier", 0),
            min_price=18.0,
            max_price=70.0,
        )

        self.courtside = SeatType(
            name="Courtside",
            capacity=arena_data["seats"].get("courtside", 0),
            current_price=arena_data["prices"].get("courtside", 0),
            min_price=50.0,
            max_price=200.0,
        )

        self.luxury_boxes = SeatType(
            name="Luxury Boxes",
            capacity=arena_data["seats"].get("luxury_boxes", 0),
            current_price=arena_data["prices"].get("luxury_boxes", 0),
            min_price=400.0,
            max_price=1600.0,
        )

        self.total_capacity = arena_data.get("total_capacity", 0)
        self.expansion_info = arena_data.get("expansion", {})

    @property
    def seat_types(self) -> dict[str, SeatType]:
        """Get all seat types as a dictionary."""
        return {
            "bleachers": self.bleachers,
            "lower_tier": self.lower_tier,
            "courtside": self.courtside,
            "luxury_boxes": self.luxury_boxes,
        }

    def calculate_max_revenue(self) -> float:
        """Calculate theoretical maximum revenue if all seats sold at current prices."""
        return sum(
            seat.capacity * seat.current_price for seat in self.seat_types.values()
        )

    def calculate_game_revenue(self, attendance_data: dict[str, int]) -> float:
        """Calculate actual revenue for a game given attendance by seat type.

        Args:
            attendance_data: Dictionary with attendance by seat type

        Returns:
            Total revenue for the game
        """
        total_revenue = 0.0

        for seat_name, seat in self.seat_types.items():
            attendance = attendance_data.get(seat_name, 0)
            total_revenue += seat.calculate_revenue(attendance)

        return total_revenue

    def get_pricing_summary(self) -> dict[str, Any]:
        """Get a summary of current pricing for all seat types."""
        return {
            seat_name: {
                "capacity": seat.capacity,
                "current_price": seat.current_price,
                "price_range": f"${seat.min_price}-${seat.max_price}",
                "max_revenue": seat.capacity * seat.current_price,
            }
            for seat_name, seat in self.seat_types.items()
        }

    def get_capacity_utilization(
        self, attendance_data: dict[str, int]
    ) -> dict[str, float]:
        """Calculate capacity utilization percentage by seat type.

        Args:
            attendance_data: Dictionary with attendance by seat type

        Returns:
            Dictionary with utilization percentages
        """
        utilization = {}

        for seat_name, seat in self.seat_types.items():
            attendance = attendance_data.get(seat_name, 0)
            if seat.capacity > 0:
                utilization[seat_name] = (attendance / seat.capacity) * 100
            else:
                utilization[seat_name] = 0.0

        return utilization

    def suggest_price_adjustments(
        self, attendance_data: dict[str, int], target_utilization: float = 85.0
    ) -> dict[str, dict[str, Any]]:
        """Suggest price adjustments based on capacity utilization.

        Args:
            attendance_data: Recent attendance data by seat type
            target_utilization: Target capacity utilization percentage

        Returns:
            Dictionary with pricing suggestions
        """
        suggestions = {}
        utilization = self.get_capacity_utilization(attendance_data)

        for seat_name, seat in self.seat_types.items():
            current_util = utilization[seat_name]
            suggestion = {
                "current_price": seat.current_price,
                "current_utilization": current_util,
                "recommended_action": "maintain",
            }

            if current_util > target_utilization + 10:  # Oversubscribed
                # Suggest price increase
                price_increase = min(
                    seat.current_price * 0.1,  # 10% increase
                    seat.max_price - seat.current_price,
                )
                suggestion["recommended_action"] = "increase"
                suggestion["suggested_price"] = min(
                    seat.current_price + price_increase, seat.max_price
                )
                suggestion["reason"] = f"High demand ({current_util:.1f}% utilization)"

            elif current_util < target_utilization - 15:  # Undersubscribed
                # Suggest price decrease
                price_decrease = min(
                    seat.current_price * 0.1,  # 10% decrease
                    seat.current_price - seat.min_price,
                )
                suggestion["recommended_action"] = "decrease"
                suggestion["suggested_price"] = max(
                    seat.current_price - price_decrease, seat.min_price
                )
                suggestion["reason"] = f"Low demand ({current_util:.1f}% utilization)"

            suggestions[seat_name] = suggestion

        return suggestions

    def is_expansion_in_progress(self) -> bool:
        """Check if arena expansion is currently in progress."""
        return bool(self.expansion_info.get("in_progress", False))

    def get_expansion_completion_date(self) -> datetime | None:
        """Get the estimated completion date for current expansion."""
        completion_str = self.expansion_info.get("completion_date")
        if completion_str:
            try:
                return datetime.fromisoformat(completion_str.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
