"""Analysis utilities for stored BuzzerBeater data."""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..storage import DatabaseManager

logger = logging.getLogger(__name__)


class StoredDataAnalyzer:
    """Analyzer for stored BuzzerBeater data."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize analyzer with database manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def get_revenue_analysis(self, team_id: str, days_back: int = 30) -> dict[str, Any]:
        """Analyze revenue trends for a team.

        Args:
            team_id: Team ID to analyze
            days_back: Number of days to look back

        Returns:
            Dictionary with revenue analysis
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get games with revenue data
            cursor = conn.execute(
                """
                SELECT date, opponent, is_home, ticket_revenue, total_attendance,
                       bleachers_price, lower_tier_price, courtside_price, luxury_boxes_price
                FROM games 
                WHERE team_id = ? AND date >= ? AND ticket_revenue IS NOT NULL
                ORDER BY date DESC
            """,
                (team_id, cutoff_date),
            )

            games = cursor.fetchall()

            if not games:
                return {"error": "No revenue data found for the specified period"}

            # Calculate statistics
            revenues = [game["ticket_revenue"] for game in games]
            attendances = [
                game["total_attendance"] for game in games if game["total_attendance"]
            ]

            home_games = [g for g in games if g["is_home"]]
            away_games = [g for g in games if not g["is_home"]]

            analysis = {
                "total_games": len(games),
                "home_games": len(home_games),
                "away_games": len(away_games),
                "total_revenue": sum(revenues),
                "average_revenue": sum(revenues) / len(revenues),
                "max_revenue": max(revenues),
                "min_revenue": min(revenues),
                "date_range": {
                    "start": games[-1]["date"] if games else None,
                    "end": games[0]["date"] if games else None,
                },
            }

            if attendances:
                analysis["average_attendance"] = sum(attendances) / len(attendances)
                analysis["max_attendance"] = max(attendances)
                analysis["min_attendance"] = min(attendances)

            # Revenue per game type
            if home_games:
                home_revenues = [g["ticket_revenue"] for g in home_games]
                analysis["home_average_revenue"] = sum(home_revenues) / len(
                    home_revenues
                )

            if away_games:
                away_revenues = [g["ticket_revenue"] for g in away_games]
                analysis["away_average_revenue"] = sum(away_revenues) / len(
                    away_revenues
                )

            return analysis

    def get_pricing_trends(self, team_id: str, days_back: int = 90) -> dict[str, Any]:
        """Analyze pricing trends for a team.

        Args:
            team_id: Team ID to analyze
            days_back: Number of days to look back

        Returns:
            Dictionary with pricing trend analysis
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get price snapshots
            cursor = conn.execute(
                """
                SELECT created_at, bleachers_price, lower_tier_price, 
                       courtside_price, luxury_boxes_price, game_id
                FROM price_snapshots 
                WHERE team_id = ? AND created_at >= ?
                ORDER BY created_at ASC
            """,
                (team_id, cutoff_date),
            )

            prices = cursor.fetchall()

            if not prices:
                return {"error": "No pricing data found for the specified period"}

            # Calculate trends for each seat type
            seat_types = ["bleachers", "lower_tier", "courtside", "luxury_boxes"]
            trends = {}

            for seat_type in seat_types:
                price_column = f"{seat_type}_price"
                price_values = [
                    p[price_column] for p in prices if p[price_column] is not None
                ]

                if price_values:
                    trends[seat_type] = {
                        "current_price": price_values[-1],
                        "starting_price": price_values[0],
                        "average_price": sum(price_values) / len(price_values),
                        "max_price": max(price_values),
                        "min_price": min(price_values),
                        "price_changes": len(set(price_values)),
                        "total_change": price_values[-1] - price_values[0],
                        "percent_change": (
                            (price_values[-1] - price_values[0]) / price_values[0]
                        )
                        * 100
                        if price_values[0] > 0
                        else 0,
                    }

            return {
                "total_snapshots": len(prices),
                "date_range": {
                    "start": prices[0]["created_at"],
                    "end": prices[-1]["created_at"],
                },
                "seat_type_trends": trends,
            }

    def get_attendance_patterns(self, team_id: str) -> dict[str, Any]:
        """Analyze attendance patterns by seat type.

        Args:
            team_id: Team ID to analyze

        Returns:
            Dictionary with attendance pattern analysis
        """
        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get games with attendance data
            cursor = conn.execute(
                """
                SELECT date, opponent, is_home, game_type,
                       bleachers_attendance, lower_tier_attendance,
                       courtside_attendance, luxury_boxes_attendance, total_attendance
                FROM games 
                WHERE team_id = ? AND total_attendance IS NOT NULL
                ORDER BY date DESC
            """,
                (team_id,),
            )

            games = cursor.fetchall()

            if not games:
                return {"error": "No attendance data found"}

            # Calculate patterns
            seat_types = ["bleachers", "lower_tier", "courtside", "luxury_boxes"]
            attendance_patterns = {}

            for seat_type in seat_types:
                attendance_column = f"{seat_type}_attendance"
                attendance_values = [
                    g[attendance_column]
                    for g in games
                    if g[attendance_column] is not None
                ]

                if attendance_values:
                    attendance_patterns[seat_type] = {
                        "average_attendance": sum(attendance_values)
                        / len(attendance_values),
                        "max_attendance": max(attendance_values),
                        "min_attendance": min(attendance_values),
                        "games_with_data": len(attendance_values),
                    }

            # Home vs Away patterns
            home_games = [g for g in games if g["is_home"]]
            away_games = [g for g in games if not g["is_home"]]

            home_avg = (
                sum(g["total_attendance"] for g in home_games) / len(home_games)
                if home_games
                else 0
            )
            away_avg = (
                sum(g["total_attendance"] for g in away_games) / len(away_games)
                if away_games
                else 0
            )

            return {
                "total_games_with_attendance": len(games),
                "home_games": len(home_games),
                "away_games": len(away_games),
                "home_average_attendance": home_avg,
                "away_average_attendance": away_avg,
                "seat_type_patterns": attendance_patterns,
                "overall_average": sum(g["total_attendance"] for g in games)
                / len(games),
            }

    def get_price_performance_correlation(self, team_id: str) -> dict[str, Any]:
        """Analyze correlation between prices and attendance/revenue.

        Args:
            team_id: Team ID to analyze

        Returns:
            Dictionary with price-performance correlation analysis
        """
        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get games with both pricing and performance data
            cursor = conn.execute(
                """
                SELECT date, ticket_revenue, total_attendance,
                       bleachers_price, lower_tier_price, courtside_price, luxury_boxes_price,
                       bleachers_attendance, lower_tier_attendance, 
                       courtside_attendance, luxury_boxes_attendance
                FROM games 
                WHERE team_id = ? 
                AND ticket_revenue IS NOT NULL 
                AND total_attendance IS NOT NULL
                AND (bleachers_price IS NOT NULL OR lower_tier_price IS NOT NULL 
                     OR courtside_price IS NOT NULL OR luxury_boxes_price IS NOT NULL)
                ORDER BY date DESC
            """,
                (team_id,),
            )

            games = cursor.fetchall()

            if len(games) < 2:
                return {
                    "error": "Insufficient data for correlation analysis (need at least 2 games)"
                }

            # Calculate correlations for each seat type
            correlations = {}
            seat_types = ["bleachers", "lower_tier", "courtside", "luxury_boxes"]

            for seat_type in seat_types:
                price_column = f"{seat_type}_price"
                attendance_column = f"{seat_type}_attendance"

                # Get data points where both price and attendance are available
                data_points = []
                for game in games:
                    if (
                        game[price_column] is not None
                        and game[attendance_column] is not None
                    ):
                        data_points.append(
                            {
                                "price": game[price_column],
                                "attendance": game[attendance_column],
                                "revenue": game["ticket_revenue"],
                            }
                        )

                if len(data_points) >= 2:
                    prices = [dp["price"] for dp in data_points]
                    attendances = [dp["attendance"] for dp in data_points]

                    # Simple correlation calculation
                    price_avg = sum(prices) / len(prices)
                    attendance_avg = sum(attendances) / len(attendances)

                    numerator = sum(
                        (p - price_avg) * (a - attendance_avg)
                        for p, a in zip(prices, attendances, strict=False)
                    )
                    price_variance = sum((p - price_avg) ** 2 for p in prices)
                    attendance_variance = sum(
                        (a - attendance_avg) ** 2 for a in attendances
                    )

                    if price_variance > 0 and attendance_variance > 0:
                        correlation = (
                            numerator / (price_variance * attendance_variance) ** 0.5
                        )

                        correlations[seat_type] = {
                            "price_attendance_correlation": correlation,
                            "average_price": price_avg,
                            "average_attendance": attendance_avg,
                            "data_points": len(data_points),
                        }

            return {
                "total_games_analyzed": len(games),
                "seat_type_correlations": correlations,
                "note": "Negative correlation means higher prices lead to lower attendance",
            }

    def export_data_summary(
        self, team_id: str, output_file: str | Path | None = None
    ) -> str:
        """Export a comprehensive data summary for a team.

        Args:
            team_id: Team ID to analyze
            output_file: Optional output file path

        Returns:
            Summary text
        """
        summary_lines = [
            f"BuzzerBeater Data Summary for Team {team_id}",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Revenue analysis
        revenue_analysis = self.get_revenue_analysis(team_id, days_back=90)
        if "error" not in revenue_analysis:
            summary_lines.extend(
                [
                    "REVENUE ANALYSIS (Last 90 Days):",
                    f"  Total Games: {revenue_analysis['total_games']}",
                    f"  Total Revenue: ${revenue_analysis['total_revenue']:,.2f}",
                    f"  Average Revenue: ${revenue_analysis['average_revenue']:,.2f}",
                    f"  Max Revenue: ${revenue_analysis['max_revenue']:,.2f}",
                    f"  Min Revenue: ${revenue_analysis['min_revenue']:,.2f}",
                    "",
                ]
            )

        # Pricing trends
        pricing_trends = self.get_pricing_trends(team_id, days_back=90)
        if "error" not in pricing_trends:
            summary_lines.append("PRICING TRENDS (Last 90 Days):")
            for seat_type, trend in pricing_trends["seat_type_trends"].items():
                summary_lines.extend(
                    [
                        f"  {seat_type.replace('_', ' ').title()}:",
                        f"    Current: ${trend['current_price']:.2f}",
                        f"    Average: ${trend['average_price']:.2f}",
                        f"    Change: {trend['percent_change']:+.1f}%",
                    ]
                )
            summary_lines.append("")

        # Attendance patterns
        attendance_patterns = self.get_attendance_patterns(team_id)
        if "error" not in attendance_patterns:
            summary_lines.extend(
                [
                    "ATTENDANCE PATTERNS:",
                    f"  Games with data: {attendance_patterns['total_games_with_attendance']}",
                    f"  Overall average: {attendance_patterns['overall_average']:.0f}",
                    f"  Home average: {attendance_patterns['home_average_attendance']:.0f}",
                    f"  Away average: {attendance_patterns['away_average_attendance']:.0f}",
                    "",
                ]
            )

        summary_text = "\n".join(summary_lines)

        if output_file:
            Path(output_file).write_text(summary_text)
            logger.info(f"Data summary exported to {output_file}")

        return summary_text
