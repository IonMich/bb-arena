"""Basic example of using the BuzzerBeater API integration."""

import os

from dotenv import load_dotenv

from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.models.arena import Arena
from bb_arena_optimizer.models.game import Game
from bb_arena_optimizer.utils.data_helpers import format_currency
from bb_arena_optimizer.utils.logging_config import setup_logging


def main() -> None:
    """Demonstrate basic analysis of stored arena and game data."""
    """Main example function."""
    # Set up logging
    logger = setup_logging()

    # Load environment variables
    load_dotenv()

    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")

    if not username or not security_code:
        logger.error("Please set BB_USERNAME and BB_SECURITY_CODE in your .env file")
        return

    logger.info("Starting BuzzerBeater API integration example")

    try:
        # Use context manager for automatic login/logout
        with BuzzerBeaterAPI(username, security_code) as api:
            logger.info("Successfully connected to BuzzerBeater API")

            # Get arena information
            logger.info("Fetching arena information...")
            arena_data = api.get_arena_info()

            if arena_data:
                arena = Arena(arena_data)

                print("\n" + "=" * 50)
                print("ARENA SUMMARY")
                print("=" * 50)
                print(f"Total Capacity: {arena.total_capacity:,} seats")
                print(
                    f"Maximum Revenue: {format_currency(arena.calculate_max_revenue())}"
                )

                if arena.is_expansion_in_progress():
                    completion_date = arena.get_expansion_completion_date()
                    print(f"Expansion in progress, completion: {completion_date}")

                print("\nCurrent Pricing by Seat Type:")
                print("-" * 40)
                for seat_name, info in arena.get_pricing_summary().items():
                    print(
                        f"{seat_name.replace('_', ' ').title():15} | "
                        f"{info['capacity']:5,} seats | "
                        f"{format_currency(info['current_price']):8} | "
                        f"Range: {info['price_range']:12} | "
                        f"Max Revenue: {format_currency(info['max_revenue'])}"
                    )

            # Get upcoming home games
            logger.info("Fetching schedule information...")
            schedule_data = api.get_schedule()

            if schedule_data:
                upcoming_games = schedule_data["upcoming_home_games"]

                print("\n" + "=" * 50)
                print("UPCOMING HOME GAMES")
                print("=" * 50)

                if upcoming_games:
                    for game_data in upcoming_games[:5]:  # Show next 5 games
                        game = Game.from_api_data(game_data)
                        demand_multiplier = game.game_type.get_demand_multiplier()
                        print(f"{game} | Demand Multiplier: {demand_multiplier:.1f}x")
                else:
                    print("No upcoming home games found")

            # Get economy information
            logger.info("Fetching economy information...")
            economy_data = api.get_economy_info()

            if economy_data:
                print("\n" + "=" * 50)
                print("RECENT FINANCIAL SUMMARY")
                print("=" * 50)
                print(
                    f"Total Revenue (2 weeks): {format_currency(economy_data['total_revenue'])}"
                )
                print(
                    f"Ticket Revenue (2 weeks): {format_currency(economy_data['ticket_revenue'])}"
                )

                # Show recent ticket-related transactions
                ticket_transactions = [
                    t
                    for t in economy_data["transactions"]
                    if any(
                        keyword in t["description"].lower()
                        for keyword in ["ticket", "gate", "attendance"]
                    )
                ]

                if ticket_transactions:
                    print("\nRecent Ticket Sales:")
                    print("-" * 40)
                    for trans in ticket_transactions[-5:]:  # Last 5 transactions
                        print(
                            f"{trans['date']:12} | {format_currency(trans['amount']):10} | {trans['description']}"
                        )

            # Example pricing suggestions based on your historical data
            print("\n" + "=" * 50)
            print("PRICING ANALYSIS EXAMPLE")
            print("=" * 50)

            if arena_data:
                # Use your historical attendance data as example
                example_attendance = {
                    "bleachers": 11000,  # Average from your data
                    "lower_tier": 1500,  # Average from your data
                    "courtside": 475,  # Average from your data
                    "luxury_boxes": 40,  # Average from your data
                }

                utilization = arena.get_capacity_utilization(example_attendance)
                suggestions = arena.suggest_price_adjustments(example_attendance)

                print("Capacity Utilization Analysis:")
                print("-" * 40)
                for seat_type, util in utilization.items():
                    suggestion = suggestions[seat_type]
                    action = suggestion["recommended_action"]

                    print(
                        f"{seat_type.replace('_', ' ').title():15} | "
                        f"{util:5.1f}% | "
                        f"Action: {action:8} | "
                        f"{suggestion.get('reason', 'Optimal pricing')}"
                    )

                    if "suggested_price" in suggestion:
                        current = suggestion["current_price"]
                        suggested = suggestion["suggested_price"]
                        change = ((suggested - current) / current) * 100
                        print(
                            f"                  Current: {format_currency(current):8} → "
                            f"Suggested: {format_currency(suggested):8} "
                            f"({change:+.1f}%)"
                        )

    except Exception as e:
        logger.error(f"Error during API example: {e}")
        return

    logger.info("Example completed successfully")


if __name__ == "__main__":
    main()
