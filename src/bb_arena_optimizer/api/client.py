"""BuzzerBeater API client for arena and team data."""

import logging
from typing import Any
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)


class BuzzerBeaterAPI:
    """BuzzerBeater API client for arena and team data."""

    BASE_URL = "http://bbapi.buzzerbeater.com"

    def __init__(self, username: str, security_code: str):
        """Initialize the API client.

        Args:
            username: BuzzerBeater username
            security_code: BuzzerBeater security code (read-only password)
        """
        self.username = username
        self.security_code = security_code
        self.session = requests.Session()
        self._authenticated = False

    def login(self) -> bool:
        """Authenticate with the BuzzerBeater API.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            url = f"{self.BASE_URL}/login.aspx"
            params = {"login": self.username, "code": self.security_code}

            response = self.session.get(url, params=params)
            response.raise_for_status()

            # Parse XML response to check for errors
            root = ET.fromstring(response.content)
            error = root.find(".//error")

            if error is not None:
                logger.error(f"Login failed: {error.get('message')}")
                return False

            self._authenticated = True
            logger.info("Successfully authenticated with BuzzerBeater API")
            return True

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def logout(self) -> bool:
        """End the current session.

        Returns:
            bool: True if logout successful, False otherwise
        """
        try:
            url = f"{self.BASE_URL}/logout.aspx"
            response = self.session.get(url)
            response.raise_for_status()
            self._authenticated = False
            logger.info("Successfully logged out")
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> ET.Element | None:
        """Make an authenticated request to the API.

        Args:
            endpoint: API endpoint to call
            params: Optional parameters for the request

        Returns:
            XML root element or None if error
        """
        if not self._authenticated:
            logger.error("Not authenticated. Please login first.")
            return None

        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = self.session.get(url, params=params or {})
            response.raise_for_status()

            root = ET.fromstring(response.content)

            # Check for API errors
            error = root.find(".//error")
            if error is not None:
                logger.error(f"API error: {error.get('message')}")
                return None

            return root

        except Exception as e:
            logger.error(f"Request error for {endpoint}: {e}")
            return None

    def get_arena_info(self, team_id: int | None = None) -> dict[str, Any] | None:
        """Get arena information for a team.

        Args:
            team_id: Optional team ID (defaults to current user's team)

        Returns:
            Dictionary with arena data or None if error
        """
        params = {"teamid": team_id} if team_id else {}
        root = self._make_request("arena.aspx", params)

        if root is None:
            return None

        return self._parse_arena_data(root)

    def get_economy_info(self) -> dict[str, Any] | None:
        """Get economy information including ticket revenues.

        Returns:
            Dictionary with economy data or None if error
        """
        root = self._make_request("economy.aspx")

        if root is None:
            return None

        return self._parse_economy_data(root)

    def get_schedule(
        self, team_id: int | None = None, season: int | None = None
    ) -> dict[str, Any] | None:
        """Get team schedule.

        Args:
            team_id: Optional team ID (defaults to current user's team)
            season: Optional season number (defaults to current season)

        Returns:
            Dictionary with schedule data or None if error
        """
        params = {}
        if team_id:
            params["teamid"] = team_id
        if season:
            params["season"] = season

        root = self._make_request("schedule.aspx", params)

        if root is None:
            return None

        return self._parse_schedule_data(root)

    def get_team_info(self, team_id: int | None = None) -> dict[str, Any] | None:
        """Get basic team information.

        Args:
            team_id: Optional team ID (defaults to current user's team)

        Returns:
            Dictionary with team data or None if error
        """
        params = {"teamid": team_id} if team_id else {}
        root = self._make_request("teaminfo.aspx", params)

        if root is None:
            return None

        return self._parse_team_data(root)

    def get_boxscore(self, game_id: str) -> dict[str, Any] | None:
        """Get detailed boxscore for a specific game including attendance.

        Args:
            game_id: The game ID to get boxscore for

        Returns:
            Dictionary with boxscore data including attendance or None if error
        """
        params = {"matchid": game_id}
        root = self._make_request("boxscore.aspx", params)

        if root is None:
            return None

        return self._parse_boxscore_data(root)

    def get_league_standings(
        self, league_id: int, season: int | None = None
    ) -> dict[str, Any] | None:
        """Get league standings which includes all teams in the league.

        Args:
            league_id: The league ID to get standings for
            season: Optional season number (defaults to current season)

        Returns:
            Dictionary with standings data including team IDs or None if error
        """
        params = {"leagueid": league_id}
        if season:
            params["season"] = season

        root = self._make_request("standings.aspx", params)

        if root is None:
            return None

        return self._parse_standings_data(root)

    def _parse_arena_data(self, root: ET.Element) -> dict[str, Any]:
        """Parse arena XML data into a structured format."""
        arena_data: dict[str, Any] = {
            "seats": {},
            "prices": {},
            "expansion": {},
            "total_capacity": 0,
        }

        # Get arena info
        arena_elem = root.find(".//arena")
        if arena_elem is not None:
            arena_data["team_id"] = arena_elem.get("teamid")

            # Get arena name
            name_elem = arena_elem.find("./name")
            if name_elem is not None:
                arena_data["name"] = name_elem.text

        # Parse seats section
        seats_elem = root.find(".//seats")
        if seats_elem is not None:
            # Map XML element names to our internal names
            seat_mapping = {
                "bleachers": "bleachers",
                "lowerTier": "lower_tier",
                "courtside": "courtside",
                "luxury": "luxury_boxes",
            }

            for xml_name, internal_name in seat_mapping.items():
                seat_elem = seats_elem.find(f"./{xml_name}")
                if seat_elem is not None:
                    # Capacity is the text content
                    if seat_elem.text:
                        capacity = int(seat_elem.text.strip())
                        arena_data["seats"][internal_name] = capacity
                        arena_data["total_capacity"] += capacity

                    # Current price is in the 'price' attribute
                    price_str = seat_elem.get("price")
                    if price_str:
                        arena_data["prices"][internal_name] = float(price_str)

        # Parse expansion information if available
        expansion_elem = root.find(".//expansion")
        if expansion_elem is not None:
            arena_data["expansion"] = {
                "in_progress": expansion_elem.get("in_progress") == "true",
                "completion_date": expansion_elem.get("completion_date"),
                "cost": float(expansion_elem.get("cost", 0)),
            }

        return arena_data

    def _parse_economy_data(self, root: ET.Element) -> dict[str, Any]:
        """Parse economy XML data."""
        economy_data: dict[str, Any] = {
            "transactions": [],
            "total_revenue": 0.0,
            "ticket_revenue": 0.0,
        }

        # Parse last week and this week transactions
        for week_elem in root.findall(".//lastWeek") + root.findall(".//thisWeek"):
            # Parse all transaction types
            for child in week_elem:
                if child.tag in ["initial", "final", "current"]:
                    continue  # Skip balance entries

                amount_text = child.text
                if amount_text:
                    try:
                        amount = float(amount_text.strip())
                    except ValueError:
                        continue

                    trans_data = {
                        "date": child.get("date", ""),
                        "type": child.tag,
                        "amount": amount,
                        "description": child.tag,
                    }

                    # Add additional info for transfers
                    if child.tag == "transfer":
                        player_id = child.get("playerid")
                        if player_id:
                            trans_data["description"] = f"Transfer (Player {player_id})"
                    elif child.tag == "matchRevenue":
                        match_id = child.get("matchid")
                        if match_id:
                            trans_data["description"] = (
                                f"Match Revenue (Match {match_id})"
                            )
                            economy_data["ticket_revenue"] += amount

                    economy_data["transactions"].append(trans_data)

                    # Only positive amounts count as revenue
                    if amount > 0:
                        economy_data["total_revenue"] += amount

        return economy_data

    def _parse_schedule_data(self, root: ET.Element) -> dict[str, Any]:
        """Parse schedule XML data."""
        schedule_data: dict[str, Any] = {"games": [], "upcoming_home_games": []}
        
        # Get team ID from schedule element
        schedule_elem = root.find(".//schedule")
        current_team_id = (
            schedule_elem.get("teamid") if schedule_elem is not None else None
        )
        schedule_data["team_id"] = current_team_id

        for match in root.findall(".//match"):
            # Get basic match info
            match_id = match.get("id")
            start_time = match.get("start")
            match_type = match.get("type", "league.rs")

            # Get team info
            home_team_elem = match.find("./homeTeam")
            away_team_elem = match.find("./awayTeam")

            if home_team_elem is None or away_team_elem is None:
                continue

            home_team_id = home_team_elem.get("id")

            home_team_name_elem = home_team_elem.find("./teamName")
            away_team_name_elem = away_team_elem.find("./teamName")

            home_team_name = (
                home_team_name_elem.text
                if home_team_name_elem is not None
                else "Unknown"
            )
            away_team_name = (
                away_team_name_elem.text
                if away_team_name_elem is not None
                else "Unknown"
            )

            # Determine if this is a home game for the current team
            is_home = home_team_id == current_team_id
            opponent = away_team_name if is_home else home_team_name

            game_data = {
                "id": match_id,
                "date": start_time,
                "opponent": opponent,
                "home": is_home,
                "type": match_type,
                "attendance": None,  # Not available in schedule
                "score_home": None,  # Not available in schedule
                "score_away": None,  # Not available in schedule
            }

            schedule_data["games"].append(game_data)

            # Check if it's an upcoming home game
            if is_home:
                schedule_data["upcoming_home_games"].append(game_data)

        return schedule_data

    def _parse_team_data(self, root: ET.Element) -> dict[str, Any]:
        """Parse team XML data."""
        team_elem = root.find(".//team")
        if team_elem is None:
            return {}
            
        team_data = {
            "id": team_elem.get("id"),
        }
        
        # Get team name
        team_name_elem = team_elem.find("./teamName")
        if team_name_elem is not None and team_name_elem.text:
            team_data["name"] = team_name_elem.text.strip()
        
        # Get short name
        short_name_elem = team_elem.find("./shortName")
        if short_name_elem is not None and short_name_elem.text:
            team_data["short_name"] = short_name_elem.text.strip()
            
        # Get owner
        owner_elem = team_elem.find("./owner")
        if owner_elem is not None and owner_elem.text:
            team_data["owner"] = owner_elem.text.strip()
            
        # Get league info
        league_elem = team_elem.find("./league")
        if league_elem is not None:
            team_data["league_id"] = league_elem.get("id")
            team_data["league_level"] = league_elem.get("level")
            if league_elem.text:
                team_data["league"] = league_elem.text.strip()
        
        # Get country info
        country_elem = team_elem.find("./country")
        if country_elem is not None:
            team_data["country_id"] = country_elem.get("id")
            if country_elem.text:
                team_data["country"] = country_elem.text.strip()
        
        # Get rival info
        rival_elem = team_elem.find("./rival")
        if rival_elem is not None:
            team_data["rival_id"] = rival_elem.get("id")
            if rival_elem.text:
                team_data["rival"] = rival_elem.text.strip()

        return team_data

    def _parse_boxscore_data(self, root: ET.Element) -> dict[str, Any]:
        """Parse boxscore XML data including attendance."""
        boxscore_data: dict[str, Any] = {
            "game_id": None,
            "attendance": {},
            "revenue": None,
            "scores": {},
            "teams": {},
        }

        # Get basic game info
        match_elem = root.find(".//match")
        if match_elem is not None:
            boxscore_data["game_id"] = match_elem.get("id")

        # Look for attendance data
        attendance_elem = root.find(".//attendance")
        if attendance_elem is not None:
            # Parse different seat types
            seat_mapping = {
                "bleachers": "bleachers",
                "lowerTier": "lower_tier", 
                "courtside": "courtside",
                "luxury": "luxury_boxes",
            }
            
            for xml_name, internal_name in seat_mapping.items():
                seat_elem = attendance_elem.find(f"./{xml_name}")
                if seat_elem is not None and seat_elem.text:
                    try:
                        boxscore_data["attendance"][internal_name] = int(seat_elem.text.strip())
                    except ValueError:
                        pass

        # Look for revenue data
        revenue_elem = root.find(".//revenue") or root.find(".//ticketRevenue")
        if revenue_elem is not None and revenue_elem.text:
            try:
                boxscore_data["revenue"] = float(revenue_elem.text.strip())
            except ValueError:
                pass

        # Get team scores
        home_team = root.find(".//homeTeam")
        away_team = root.find(".//awayTeam")
        
        if home_team is not None:
            score_elem = home_team.find(".//score")
            if score_elem is not None and score_elem.text:
                try:
                    boxscore_data["scores"]["home"] = int(score_elem.text.strip())
                except ValueError:
                    pass

        if away_team is not None:
            score_elem = away_team.find(".//score")
            if score_elem is not None and score_elem.text:
                try:
                    boxscore_data["scores"]["away"] = int(score_elem.text.strip())
                except ValueError:
                    pass

        return boxscore_data

    def _parse_standings_data(self, root: ET.Element) -> dict[str, Any]:
        """Parse standings XML data to extract team information."""
        standings_data: dict[str, Any] = {"teams": [], "league_info": {}}
        
        # Get league info from standings element
        standings_elem = root.find(".//standings")
        if standings_elem is not None:
            standings_data["league_info"] = {
                "league_id": standings_elem.get("leagueid"),
                "season": standings_elem.get("season"),
                "league_name": standings_elem.get("leaguename")
            }

        # Extract team information from standings
        for team_elem in root.findall(".//team"):
            team_id = team_elem.get("id")
            team_name_elem = team_elem.find("./teamName")
            team_name = team_name_elem.text if team_name_elem is not None else "Unknown"
            
            # Get additional team info if available
            team_info = {
                "id": team_id,
                "name": team_name,
                "wins": team_elem.get("wins"),
                "losses": team_elem.get("losses"),
                "position": team_elem.get("position")
            }
            
            standings_data["teams"].append(team_info)

        return standings_data

    def __enter__(self) -> "BuzzerBeaterAPI":
        """Context manager entry."""
        if self.login():
            return self
        else:
            raise Exception("Failed to authenticate with BuzzerBeater API")

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.logout()
