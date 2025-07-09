"""Tests for the Arena and SeatType models."""

from bb_arena_optimizer.models.arena import Arena, SeatType


def test_seat_type_creation():
    """Test SeatType creation and basic functionality."""
    seat = SeatType(
        name="Test Seats",
        capacity=1000,
        current_price=25.0,
        min_price=10.0,
        max_price=50.0,
    )

    assert seat.name == "Test Seats"
    assert seat.capacity == 1000
    assert seat.current_price == 25.0
    assert seat.is_price_valid(30.0)
    assert not seat.is_price_valid(60.0)
    assert seat.get_max_revenue() == 25000.0


def test_arena_creation():
    """Test Arena creation from API data."""
    arena_data = {
        "seats": {
            "bleachers": 10000,
            "lower_tier": 2000,
            "courtside": 500,
            "luxury_boxes": 50,
        },
        "prices": {
            "bleachers": 10.0,
            "lower_tier": 35.0,
            "courtside": 100.0,
            "luxury_boxes": 800.0,
        },
        "total_capacity": 12550,
    }

    arena = Arena(arena_data)

    assert arena.total_capacity == 12550
    assert arena.bleachers.capacity == 10000
    assert arena.bleachers.current_price == 10.0
    assert arena.luxury_boxes.max_price == 1600.0


def test_revenue_calculations():
    """Test revenue calculation methods."""
    arena_data = {
        "seats": {
            "bleachers": 1000,
            "lower_tier": 500,
            "courtside": 100,
            "luxury_boxes": 10,
        },
        "prices": {
            "bleachers": 10.0,
            "lower_tier": 30.0,
            "courtside": 100.0,
            "luxury_boxes": 500.0,
        },
        "total_capacity": 1610,
    }

    arena = Arena(arena_data)

    # Test max revenue calculation
    expected_max = (1000 * 10) + (500 * 30) + (100 * 100) + (10 * 500)
    assert arena.calculate_max_revenue() == expected_max

    # Test game revenue calculation
    attendance = {
        "bleachers": 800,
        "lower_tier": 400,
        "courtside": 90,
        "luxury_boxes": 8,
    }

    expected_game_revenue = (800 * 10) + (400 * 30) + (90 * 100) + (8 * 500)
    assert arena.calculate_game_revenue(attendance) == expected_game_revenue


def test_capacity_utilization():
    """Test capacity utilization calculations."""
    arena_data = {
        "seats": {
            "bleachers": 1000,
            "lower_tier": 500,
            "courtside": 100,
            "luxury_boxes": 10,
        },
        "prices": {
            "bleachers": 10.0,
            "lower_tier": 30.0,
            "courtside": 100.0,
            "luxury_boxes": 500.0,
        },
        "total_capacity": 1610,
    }

    arena = Arena(arena_data)

    attendance = {
        "bleachers": 800,  # 80% utilization
        "lower_tier": 250,  # 50% utilization
        "courtside": 100,  # 100% utilization
        "luxury_boxes": 5,  # 50% utilization
    }

    utilization = arena.get_capacity_utilization(attendance)

    assert utilization["bleachers"] == 80.0
    assert utilization["lower_tier"] == 50.0
    assert utilization["courtside"] == 100.0
    assert utilization["luxury_boxes"] == 50.0


def test_price_adjustment_suggestions():
    """Test price adjustment suggestion logic."""
    arena_data = {
        "seats": {
            "bleachers": 1000,
            "lower_tier": 500,
            "courtside": 100,
            "luxury_boxes": 10,
        },
        "prices": {
            "bleachers": 10.0,
            "lower_tier": 30.0,
            "courtside": 100.0,
            "luxury_boxes": 500.0,
        },
        "total_capacity": 1610,
    }

    arena = Arena(arena_data)

    # High utilization scenario
    high_attendance = {
        "bleachers": 980,  # 98% - should suggest increase
        "lower_tier": 480,  # 96% - should suggest increase
        "courtside": 65,  # 65% - should suggest decrease
        "luxury_boxes": 8,  # 80% - should maintain
    }

    suggestions = arena.suggest_price_adjustments(
        high_attendance, target_utilization=85.0
    )

    assert suggestions["bleachers"]["recommended_action"] == "increase"
    assert suggestions["lower_tier"]["recommended_action"] == "increase"
    assert suggestions["courtside"]["recommended_action"] == "decrease"
    assert suggestions["luxury_boxes"]["recommended_action"] == "maintain"
