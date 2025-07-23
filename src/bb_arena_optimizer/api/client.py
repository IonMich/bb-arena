"""BuzzerBeater API client for arena and team data."""

import logging
import datetime
from typing import Any, TypedDict
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)


class BoxscoreData(TypedDict):
    """Typed structure for boxscore data from BB API."""
    match_id: int
    bleachers_attendance: int
    lower_tier_attendance: int
    courtside_attendance: int
    luxury_box_attendance: int
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    game_type: str
    neutral: bool
    start_date: str


class ScheduleMatchData(TypedDict):
    """Typed structure for a single match from schedule API."""
    match_id: int
    home_team_id: int
    away_team_id: int
    home_score: int | None  # Optional - None for upcoming games
    away_score: int | None  # Optional - None for upcoming games
    game_type: str
    start_date: str


class ScheduleData(TypedDict):
    """Typed structure for schedule data from BB API."""
    team_id: int
    season: int
    matches: list[ScheduleMatchData]


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

    def get_schedule(
        self, team_id: int | None = None, season: int | None = None
    ) -> ScheduleData | None:
        """Get team schedule with typed return structure.
        
        Args:
            team_id: Optional team ID (defaults to current user's team)
            season: Optional season number (defaults to current season)
            
        Returns:
            ScheduleData with typed matches or None if error
        """
        params = {}
        if team_id:
            params["teamid"] = team_id
        if season:
            params["season"] = season

        root = self._make_request("schedule.aspx", params)

        if root is None:
            return None

        return self._parse_schedule_data(root, season or 0)

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

    def get_boxscore(self, game_id: str) -> BoxscoreData | None:
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

    def get_seasons(self) -> dict[str, Any]:
        """Get all seasons from the BuzzerBeater API.

        Returns:
            dict: Seasons data with list of seasons including start/end dates

        Raises:
            Exception: If not authenticated or request fails
        """
        if not self._authenticated:
            raise Exception("Not authenticated. Call login() first.")

        try:
            url = f"{self.BASE_URL}/seasons.aspx"
            response = self.session.get(url)
            response.raise_for_status()

            # Log the raw response for debugging
            logger.info(f"Raw seasons response: {response.text[:500]}...")

            # Parse XML response
            root = ET.fromstring(response.content)

            # Check for errors
            error = root.find(".//error")
            if error is not None:
                raise Exception(f"API Error: {error.get('message')}")

            seasons_data: dict[str, Any] = {"seasons": []}

            # Parse season elements - try different possible paths
            season_elements = root.findall(".//season")
            if not season_elements:
                # Try alternative paths
                season_elements = root.findall("season")
            if not season_elements:
                season_elements = root.findall(".//bbapi/season")
            
            logger.info(f"Found {len(season_elements)} season elements in XML")

            # Parse season elements
            for season_elem in season_elements:
                # The XML uses 'id' for season number, not 'number'
                season_number = season_elem.get("id")
                
                # The XML uses child elements for dates, not attributes
                start_elem = season_elem.find("./start")
                finish_elem = season_elem.find("./finish")
                
                start_date = start_elem.text if start_elem is not None else None
                end_date = finish_elem.text if finish_elem is not None else None
                
                # Log what we're parsing
                logger.info(f"Parsing season: id={season_number}, start={start_date}, end={end_date}")
                
                season_number_int = int(season_number) if season_number and season_number.isdigit() else None
                
                season_info = {
                    "number": season_number_int,
                    "start": start_date,
                    "end": end_date,
                }
                
                # Only add valid seasons
                if season_number_int is not None and season_number_int > 0:
                    seasons_data["seasons"].append(season_info)

            logger.info(f"Retrieved {len(seasons_data['seasons'])} valid seasons")
            return seasons_data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch seasons: {e}")
            raise Exception(f"Failed to fetch seasons: {e}")
        except ET.ParseError as e:
            logger.error(f"Failed to parse seasons XML: {e}")
            raise Exception(f"Failed to parse seasons XML: {e}")

    def get_country_level_1_league(self, country_id: int) -> dict[str, Any] | None:
        """Get level 1 league for a specific country.

        Args:
            country_id: The country ID to get level 1 league for

        Returns:
            Dictionary with level 1 league data or None if error
        """
        params = {"countryid": country_id, "level": 1}
        root = self._make_request("leagues.aspx", params)

        if root is None:
            return None

        return self._parse_leagues_data(root, country_id)

    def get_all_country_level_1_leagues(self, max_country_id: int = 150) -> list[dict[str, Any]]:
        """Get level 1 leagues for all countries (1 to max_country_id).

        Args:
            max_country_id: Maximum country ID to check (default 150)

        Returns:
            List of dictionaries with country and league data
        """
        level_1_leagues = []
        
        for country_id in range(1, max_country_id + 1):
            try:
                logger.info(f"Fetching level 1 league for country {country_id}")
                league_data = self.get_country_level_1_league(country_id)
                
                if league_data:
                    level_1_leagues.append({
                        "country_id": country_id,
                        "country_name": league_data.get("country_name"),
                        "league_data": league_data
                    })
                    logger.info(f"Found level 1 league for country {country_id}: {league_data.get('league_name')}")
                else:
                    logger.debug(f"No level 1 league found for country {country_id}")
                    
            except Exception as e:
                logger.warning(f"Error fetching level 1 league for country {country_id}: {e}")
                continue
        
        logger.info(f"Successfully fetched level 1 leagues for {len(level_1_leagues)} countries")
        return level_1_leagues

    def get_countries(self) -> list[dict[str, Any]]:
        """Get all countries from the BuzzerBeater API.
        
        Returns:
            List of dictionaries with country data
        """
        root = self._make_request("countries.aspx", {})
        
        if root is None:
            return []
        
        countries = []
        country_elements = root.findall(".//country")
        
        for country_elem in country_elements:
            country_id = country_elem.get("id")
            country_name = country_elem.text.strip() if country_elem.text else None
            divisions = country_elem.get("divisions")
            first_season = country_elem.get("firstSeason")
            users = country_elem.get("users")
            
            if country_id and country_name:
                countries.append({
                    "id": int(country_id),
                    "name": country_name,
                    "divisions": int(divisions) if divisions and divisions.isdigit() else 0,
                    "first_season": int(first_season) if first_season else 0,
                    "users": int(users) if users else 0
                })
        
        logger.info(f"Found {len(countries)} countries")
        return countries

    def get_leagues(self, country_id: int, max_level: int = 3) -> list[dict[str, Any]]:
        """Get all leagues for a specific country across multiple levels.
        
        Args:
            country_id: The country ID to get leagues for
            max_level: Maximum league level to check
            
        Returns:
            List of dictionaries with league data
        """
        leagues = []
        
        for level in range(1, max_level + 1):
            try:
                params = {"countryid": country_id, "level": level}
                root = self._make_request("leagues.aspx", params)
                
                if root is None:
                    continue
                
                # Parse league data
                league_elements = root.findall(".//league")
                
                if not league_elements:
                    # No more leagues at this level
                    break
                
                for league_elem in league_elements:
                    league_id_str = league_elem.get("id")
                    league_id = int(league_id_str) if league_id_str and league_id_str.isdigit() else None
                    
                    league_data = {
                        "id": league_id,
                        "name": league_elem.text.strip() if league_elem.text else None,
                        "level": level
                    }
                    
                    if league_data["id"] and league_data["name"]:
                        leagues.append(league_data)
                
            except Exception as e:
                logger.debug(f"Error fetching level {level} leagues for country {country_id}: {e}")
                continue
        
        logger.debug(f"Found {len(leagues)} leagues for country {country_id}")
        return leagues

    def _parse_leagues_data(self, root: ET.Element, country_id: int) -> dict[str, Any] | None:
        """Parse leagues XML data for level 1 league information."""
        
        # Look for league elements
        league_elements = root.findall(".//league")
        
        if not league_elements:
            return None
        
        # Get country name from the response
        country_name = f"Country {country_id}"  # default
        country_elem = root.find(".//country")
        if country_elem is not None and country_elem.text:
            country_name = country_elem.text.strip()
        
        # Build leagues list
        leagues = []
        for league_elem in league_elements:
            league_id = league_elem.get("id")
            league_name = league_elem.text.strip() if league_elem.text else None
            
            if league_id and league_name:
                leagues.append({
                    "id": league_id,
                    "name": league_name,
                    "country": country_name
                })
        
        return {
            "leagues": leagues,
            "country_id": country_id,
            "country_name": country_name
        }

    def get_team_history_from_webpage(self, team_id: int) -> list[dict[str, Any]]:
        """Get team history by parsing the team history webpage.

        Args:
            team_id: The team ID to get history for

        Returns:
            List of dictionaries with team history data
        """
        import re
        from bs4 import BeautifulSoup, Tag
        
        try:
            url = f"https://buzzerbeater.com/team/{team_id}/history.aspx"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the main container div
            container_div = soup.find('div', id='containerDiv')
            if not container_div:
                logger.error("Could not find containerDiv")
                return []
            
            # Find the div with class 'boxcontent' that contains the season history
            history_div = None
            boxcontent_divs = container_div.find_all('div', class_='boxcontent')
            for div in boxcontent_divs:
                if not isinstance(div, Tag):
                    continue
                div_text = div.get_text()
                if 'season' in div_text.lower() and 'league' in div_text.lower():
                    # Count season references to find the main history div
                    season_count = len(re.findall(r'season \d+', div_text, re.IGNORECASE))
                    if season_count > 10:  # The main history div should have many seasons
                        history_div = div
                        break
            
            if not history_div:
                logger.error("Could not find history div with season content")
                return []
            
            logger.info("Found history div with season content")
            
            history_entries = []
            
            # Use raw text parsing approach
            container_text = history_div.get_text()
            lines = container_text.split('\n')
            
            # Pattern to match season entries with league information
            # Improved pattern that handles team names with commas and allows periods in league names
            season_league_pattern = re.compile(
                r'In season (\d+), (.+?)\s+(?:were|was|made|won|lost|played|finished).*?(?:in|from|of)\s+league\s+([^,]+?)(?:,|$)',
                re.IGNORECASE
            )
            
            # Get league IDs from the links
            league_links = history_div.find_all('a', href=re.compile(r'/league/(\d+)'))
            league_id_map = {}
            
            for link in league_links:
                href = link.get('href')
                league_name = link.get_text().strip()
                league_id_match = re.search(r'/league/(\d+)', href)
                if league_id_match:
                    league_id = int(league_id_match.group(1))
                    league_id_map[league_name] = league_id
            
            logger.info(f"Found {len(league_id_map)} league ID mappings")
            
            for line in lines:
                line = line.strip()
                match = season_league_pattern.search(line)
                
                if match:
                    season = int(match.group(1))
                    team_name = match.group(2).strip()
                    league_name = match.group(3).strip()
                    
                    # Get league ID from our mapping - try exact match first, then partial match
                    league_id: int | None = league_id_map.get(league_name)
                    
                    # If no exact match, try to find a partial match
                    if league_id is None:
                        for link_league_name, link_league_id in league_id_map.items():
                            # Check if the parsed league name is a substring of the link text
                            # or if the link text starts with the parsed league name
                            if (league_name in link_league_name or 
                                link_league_name.startswith(league_name) or
                                # Also check the reverse - link text might be shorter
                                league_name.startswith(link_league_name)):
                                league_id = link_league_id
                                logger.debug(f"Found partial match: '{league_name}' -> '{link_league_name}' (ID: {league_id})")
                                break
                    
                    # Calculate league level using both league name and ID
                    league_level = self._calculate_league_level(league_name, league_id)
                    
                    # Extract achievement from the text
                    achievement = ""
                    if "crowned champions" in line:
                        achievement = "Champions"
                    elif "semifinals of the playoffs" in line:
                        achievement = "Semifinals"
                    elif "made the playoffs" in line and "semifinals" not in line:
                        achievement = "Playoffs"
                    elif "relegation series to stay" in line:
                        achievement = "Survived relegation"
                    elif "relegated from" in line:
                        achievement = "Relegated"
                    elif "final" in line and "teams" in line:
                        # Extract tournament achievement like "final 512 teams"
                        final_match = re.search(r'final (\d+) teams', line)
                        if final_match:
                            achievement = f"Tournament Round of {final_match.group(1)}"
                    
                    entry = {
                        'season': season,
                        'team_name': team_name,
                        'league_name': league_name,
                        'league_id': league_id,
                        'league_level': league_level,
                        'achievement': achievement,
                        'is_active_team': True,  # Will be determined later
                    }
                    
                    history_entries.append(entry)
            
            # Sort by season (descending - most recent first)
            history_entries.sort(key=lambda x: x['season'], reverse=True)
            
            # Determine active vs inactive teams
            if history_entries:
                current_team_name = history_entries[0]['team_name']
                for entry in history_entries:
                    entry['is_active_team'] = entry['team_name'] == current_team_name
            
            logger.info(f"Parsed {len(history_entries)} history entries for team {team_id}")
            return history_entries
            
        except Exception as e:
            logger.error(f"Error parsing team history for team {team_id}: {e}")
            return []

    def _calculate_league_level(self, league_name: str, league_id: int | None = None) -> int:
        """
        Calculate league level using three-tier approach:
        1. First try database lookup if league_id exists (for any level)
        2. Check if the league_id is in the level 1 league table
        3. Finally try Roman numeral parsing
        """
        if not league_name:
            return 0
        
        # Tier 1: Database lookup by league_id if available (for any level)
        if league_id:
            try:
                import sqlite3
                from pathlib import Path
                
                # Get database path
                project_root = Path(__file__).parent.parent.parent.parent
                db_path = project_root / "bb_arena_data.db"
                
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Direct lookup by league_id (if we somehow have league levels for other leagues)
                    cursor.execute(
                        "SELECT league_level FROM league_hierarchy WHERE league_id = ?", 
                        (league_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        logger.debug(f"Found league level {result[0]} for league_id {league_id} in database")
                        return int(result[0])
                    
                    logger.debug(f"No database match found for league_id {league_id}")
                    
            except Exception as e:
                logger.debug(f"Database lookup failed: {e}")
        
        # Tier 2: Check if this is a level 1 league using our authoritative level 1 database
        if league_id:
            try:
                import sqlite3
                from pathlib import Path
                
                # Get database path
                project_root = Path(__file__).parent.parent.parent.parent
                db_path = project_root / "bb_arena_data.db"
                
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if this league_id is a level 1 league
                    cursor.execute(
                        "SELECT 1 FROM league_hierarchy WHERE league_id = ? AND league_level = 1", 
                        (league_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        logger.debug(f"Confirmed league_id {league_id} is level 1 from authoritative database")
                        return 1
                    
                    logger.debug(f"League_id {league_id} is not in level 1 database")
                    
            except Exception as e:
                logger.debug(f"Level 1 database lookup failed: {e}")
        
        # Tier 3: Roman numeral parsing (fallback for non-level-1 leagues)
        logger.debug(f"Falling back to Roman numeral parsing for '{league_name}'")
        
        # Roman numeral parsing
        roman_to_int = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
        }
        
        # Look for Roman numerals in the league name
        for roman, level in roman_to_int.items():
            if f' {roman}.' in league_name:
                logger.debug(f"Parsed Roman numeral '{roman}' from '{league_name}' -> level {level}")
                return level
        
        # If no pattern matches, assume level 1 (first division)
        logger.debug(f"No pattern matched for '{league_name}', defaulting to level 1")
        return 1

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
                        # Convert to integer (BuzzerBeater ticket prices are always whole dollars)
                        arena_data["prices"][internal_name] = int(float(price_str))

        # Parse expansion information if available
        expansion_elem = root.find(".//expansion")
        if expansion_elem is not None:
            arena_data["expansion"] = {
                "in_progress": expansion_elem.get("in_progress") == "true",
                "completion_date": expansion_elem.get("completion_date"),
                "cost": float(expansion_elem.get("cost", 0)),
            }

        return arena_data


    def _parse_schedule_data(self, root: ET.Element, season: int) -> ScheduleData:
        """Parse schedule XML data into typed structure."""
        matches: list[ScheduleMatchData] = []
        
        # Get team ID from schedule element
        schedule_elem = root.find(".//schedule")
        current_team_id = (
            schedule_elem.get("teamid") if schedule_elem is not None else None
        )
        
        if current_team_id is None:
            raise ValueError("Could not determine team ID from schedule data")
            
        team_id = int(current_team_id)

        for match in root.findall(".//match"):
            # Get basic match info
            match_id_str = match.get("id")
            start_time = match.get("start") 
            match_type = match.get("type")
            
            if not match_id_str or not start_time or not match_type:
                continue

            # Get team info
            home_team_elem = match.find("./homeTeam")
            away_team_elem = match.find("./awayTeam")

            if home_team_elem is None or away_team_elem is None:
                continue

            home_team_id_str = home_team_elem.get("id")
            away_team_id_str = away_team_elem.get("id")
            
            if not home_team_id_str or not away_team_id_str:
                continue
                
            try:
                match_id = int(match_id_str)
                home_team_id = int(home_team_id_str)
                away_team_id = int(away_team_id_str)
            except ValueError:
                continue

            # Extract scores from the XML (if available)
            home_score = None
            away_score = None
            
            # Try to get home team score
            home_score_elem = home_team_elem.find("./score")
            if home_score_elem is not None and home_score_elem.text:
                try:
                    home_score = int(home_score_elem.text.strip())
                except ValueError:
                    pass
            
            # Try to get away team score  
            away_score_elem = away_team_elem.find("./score")
            if away_score_elem is not None and away_score_elem.text:
                try:
                    away_score = int(away_score_elem.text.strip())
                except ValueError:
                    pass

            match_data: ScheduleMatchData = {
                "match_id": match_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": home_score,
                "away_score": away_score,
                "game_type": match_type,
                "start_date": start_time
            }

            matches.append(match_data)

        return ScheduleData(
            team_id=team_id,
            season=season,
            matches=matches
        )

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
        
        # Get creation date
        create_date_elem = team_elem.find("./createDate")
        if create_date_elem is not None and create_date_elem.text:
            team_data["create_date"] = create_date_elem.text.strip()

        return team_data

    def _get_required_element(self, parent: ET.Element, xpath: str, field_name: str) -> ET.Element:
        """Get a required XML element or raise ValueError."""
        elem = parent.find(xpath)
        if elem is None:
            logger.error(f"No {field_name} element found in XML")
            raise ValueError(f"No {field_name} element found in XML")
        return elem
    
    def _get_required_attribute(self, elem: ET.Element, attr: str, field_name: str) -> str:
        """Get a required XML attribute or raise ValueError."""
        value = elem.get(attr)
        if not value or not value.strip():
            logger.error(f"No {field_name} attribute found")
            raise ValueError(f"No {field_name} attribute found")
        return value.strip()
    
    def _get_required_text(self, elem: ET.Element, field_name: str) -> str:
        """Get required text content from XML element or raise ValueError."""
        if not elem.text or not elem.text.strip():
            logger.error(f"No {field_name} text found")
            raise ValueError(f"No {field_name} text found")
        return elem.text.strip()
    
    def _get_required_int_text(self, elem: ET.Element, field_name: str) -> int:
        """Get required integer text content from XML element or raise ValueError."""
        text = self._get_required_text(elem, field_name)
        try:
            return int(text)
        except ValueError:
            logger.error(f"Invalid {field_name} value: {text}")
            raise ValueError(f"Invalid {field_name} value: {text}")

    def _parse_boxscore_data(self, root: ET.Element) -> BoxscoreData:
        """Parse boxscore XML data including attendance, type, and date."""
        
        # Extract match info
        match_elem = self._get_required_element(root, ".//match", "match")
        match_id = int(self._get_required_attribute(match_elem, "id", "match ID"))
        game_type = self._get_required_attribute(match_elem, "type", "game type")
        
        # Extract neutral flag
        neutral_elem = self._get_required_element(match_elem, "./neutral", "neutral")
        neutral_text = self._get_required_text(neutral_elem, "neutral value")
        if neutral_text not in ["0", "1"]:
            logger.error(f"Invalid neutral value: {neutral_text}")
            raise ValueError(f"Invalid neutral value: {neutral_text}, must be 0 or 1")
        neutral = neutral_text == "1"
        
        # Extract start time
        start_time_elem = self._get_required_element(root, ".//startTime", "startTime")
        start_time = self._get_required_text(start_time_elem, "start time")
        
        # Extract attendance data
        attendance_elem = self._get_required_element(root, ".//attendance", "attendance")
        bleachers_attendance = self._get_required_int_text(
            self._get_required_element(attendance_elem, "./bleachers", "bleachers attendance"), 
            "bleachers attendance"
        )
        lower_tier_attendance = self._get_required_int_text(
            self._get_required_element(attendance_elem, "./lowerTier", "lower tier attendance"), 
            "lower tier attendance"
        )
        courtside_attendance = self._get_required_int_text(
            self._get_required_element(attendance_elem, "./courtside", "courtside attendance"), 
            "courtside attendance"
        )
        luxury_box_attendance = self._get_required_int_text(
            self._get_required_element(attendance_elem, "./luxury", "luxury box attendance"), 
            "luxury box attendance"
        )

        # Extract team data
        home_team = self._get_required_element(root, ".//homeTeam", "home team")
        home_team_id = int(self._get_required_attribute(home_team, "id", "home team ID"))
        home_score = self._get_required_int_text(
            self._get_required_element(home_team, ".//score", "home team score"),
            "home team score"
        )

        away_team = self._get_required_element(root, ".//awayTeam", "away team")
        away_team_id = int(self._get_required_attribute(away_team, "id", "away team ID"))
        away_score = self._get_required_int_text(
            self._get_required_element(away_team, ".//score", "away team score"),
            "away team score"
        )

        # Construct and return BoxscoreData
        return BoxscoreData(
            match_id=match_id,
            bleachers_attendance=bleachers_attendance,
            lower_tier_attendance=lower_tier_attendance,
            courtside_attendance=courtside_attendance,
            luxury_box_attendance=luxury_box_attendance,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            game_type=game_type,
            neutral=neutral,
            start_date=start_time
        )

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
        # Parameters are required by the context manager protocol but not used
        _ = exc_type, exc_val, exc_tb
        self.logout()
