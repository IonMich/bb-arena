"""Comprehensive example of data collection, storage, and analysis."""

import os

from dotenv import load_dotenv

from bb_arena_optimizer.analysis import StoredDataAnalyzer
from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.storage import DatabaseManager, DataCollectionService
from bb_arena_optimizer.utils.logging_config import setup_logging


def main() -> None:
    """Demonstrate the full data workflow: collect, store, and analyze."""
    logger = setup_logging()
    load_dotenv()

    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")

    if not username or not security_code:
        print("Error: BB_USERNAME and BB_SECURITY_CODE must be set in .env file")
        return

    print("🏀 BuzzerBeater Arena Optimizer - Data Workflow Demo")
    print("=" * 60)

    # Initialize components
    db_manager = DatabaseManager("bb_arena_data.db")
    collector = DataCollectionService(db_manager)
    analyzer = StoredDataAnalyzer(db_manager)

    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            print("\n📊 Step 1: Collecting Data from API...")
            print("-" * 40)

            # Get team info first
            team_info = api.get_team_info()
            if not team_info:
                print("❌ Failed to get team information")
                return

            team_id = str(team_info["id"])
            print(f"Team: {team_info.get('name', 'Unknown')} (ID: {team_id})")
            print(f"Owner: {team_info.get('owner', 'Unknown')}")

            # Collect all data
            results = collector.collect_full_data_snapshot(api)

            success_count = sum(results.values())
            print(f"\nData Collection Results: {success_count}/3 successful")
            for data_type, success in results.items():
                status = "✅" if success else "❌"
                print(f"  {status} {data_type.capitalize()}")

            if success_count == 0:
                print("❌ No data was collected successfully")
                return

            print("\n💾 Step 2: Database Storage Status...")
            print("-" * 40)

            stats = db_manager.get_database_stats()
            print(f"Arena Snapshots: {stats['arena_snapshots']}")
            print(f"Price Snapshots: {stats['price_snapshots']}")
            print(f"Game Records: {stats['total_games']}")
            print(f"Unique Teams: {stats['unique_teams']}")

            if stats["earliest_game"] and stats["latest_game"]:
                print(
                    f"Game Date Range: {stats['earliest_game']} to {stats['latest_game']}"
                )

            print("\n📈 Step 3: Data Analysis...")
            print("-" * 40)

            # Revenue Analysis
            print("\n💰 Revenue Analysis:")
            revenue_analysis = analyzer.get_revenue_analysis(team_id, days_back=90)
            if "error" not in revenue_analysis:
                print(f"  Total Games: {revenue_analysis['total_games']}")
                if revenue_analysis["total_games"] > 0:
                    print(f"  Total Revenue: ${revenue_analysis['total_revenue']:,.2f}")
                    print(
                        f"  Average Revenue: ${revenue_analysis['average_revenue']:,.2f}"
                    )
                    print(
                        f"  Revenue Range: ${revenue_analysis['min_revenue']:,.2f} - ${revenue_analysis['max_revenue']:,.2f}"
                    )

                    if revenue_analysis.get(
                        "home_average_revenue"
                    ) and revenue_analysis.get("away_average_revenue"):
                        home_avg = revenue_analysis["home_average_revenue"]
                        away_avg = revenue_analysis["away_average_revenue"]
                        print(f"  Home Game Average: ${home_avg:,.2f}")
                        print(f"  Away Game Average: ${away_avg:,.2f}")
                        print(
                            f"  Home vs Away Difference: ${home_avg - away_avg:+,.2f}"
                        )
            else:
                print(f"  {revenue_analysis['error']}")

            # Pricing Trends
            print("\n🎫 Pricing Trends:")
            pricing_trends = analyzer.get_pricing_trends(team_id, days_back=90)
            if "error" not in pricing_trends:
                print(f"  Price Snapshots: {pricing_trends['total_snapshots']}")

                for seat_type, trend in pricing_trends.get(
                    "seat_type_trends", {}
                ).items():
                    seat_name = seat_type.replace("_", " ").title()
                    current = trend["current_price"]
                    change = trend["percent_change"]
                    change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"

                    print(
                        f"  {seat_name}: ${current:.2f} ({change:+.1f}%) {change_symbol}"
                    )
            else:
                print(f"  {pricing_trends['error']}")

            # Attendance Patterns
            print("\n👥 Attendance Patterns:")
            attendance_patterns = analyzer.get_attendance_patterns(team_id)
            if "error" not in attendance_patterns:
                print(
                    f"  Games with Attendance Data: {attendance_patterns['total_games_with_attendance']}"
                )
                if attendance_patterns["total_games_with_attendance"] > 0:
                    print(
                        f"  Overall Average: {attendance_patterns['overall_average']:.0f}"
                    )

                    if attendance_patterns["home_average_attendance"] > 0:
                        print(
                            f"  Home Average: {attendance_patterns['home_average_attendance']:.0f}"
                        )
                    if attendance_patterns["away_average_attendance"] > 0:
                        print(
                            f"  Away Average: {attendance_patterns['away_average_attendance']:.0f}"
                        )

                    # Show seat type breakdown
                    seat_patterns = attendance_patterns.get("seat_type_patterns", {})
                    if seat_patterns:
                        print("  Seat Type Averages:")
                        for seat_type, pattern in seat_patterns.items():
                            seat_name = seat_type.replace("_", " ").title()
                            avg = pattern["average_attendance"]
                            print(f"    {seat_name}: {avg:.0f}")
            else:
                print(f"  {attendance_patterns['error']}")

            # Price-Performance Correlation
            print("\n🔗 Price-Performance Correlation:")
            correlation_analysis = analyzer.get_price_performance_correlation(team_id)
            if "error" not in correlation_analysis:
                correlations = correlation_analysis.get("seat_type_correlations", {})
                if correlations:
                    print("  Price vs Attendance Correlations:")
                    for seat_type, corr_data in correlations.items():
                        seat_name = seat_type.replace("_", " ").title()
                        correlation = corr_data["price_attendance_correlation"]

                        if correlation > 0.3:
                            trend = "📈 Positive (higher prices, higher attendance)"
                        elif correlation < -0.3:
                            trend = "📉 Negative (higher prices, lower attendance)"
                        else:
                            trend = "➡️ Weak correlation"

                        print(f"    {seat_name}: {correlation:.3f} - {trend}")
                        print(f"      Data points: {corr_data['data_points']}")
                else:
                    print("  Not enough data for correlation analysis")
            else:
                print(f"  {correlation_analysis['error']}")

            print("\n📄 Step 4: Export Summary...")
            print("-" * 40)

            # Export summary
            analyzer.export_data_summary(team_id, "team_summary.txt")
            print("Summary exported to: team_summary.txt")

            print("\n✅ Workflow Complete!")
            print("=" * 60)
            print("📁 Database: bb_arena_data.db")
            print("📄 Summary: team_summary.txt")
            print("\n💡 You can now:")
            print("  • Run analysis without API calls using stored data")
            print("  • Track pricing changes over time")
            print("  • Analyze attendance and revenue patterns")
            print("  • Optimize ticket prices based on historical data")
            print("\n🔄 Run this script regularly to build a comprehensive dataset!")

    except Exception as e:
        logger.error(f"Error during workflow: {e}")
        print(f"❌ Error: {e}")

        # Show what data we do have
        print("\n📊 Current Database Status:")
        stats = db_manager.get_database_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
