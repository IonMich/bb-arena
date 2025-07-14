"""Team arena page collector for historical pricing data."""

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@dataclass
class GamePricingData:
    """Represents pricing data extracted from a game entry."""
    
    game_id: Optional[str] = None
    date: Optional[datetime] = None
    opponent: Optional[str] = None
    attendance: Optional[int] = None
    bleachers_price: Optional[int] = None
    lower_tier_price: Optional[int] = None
    courtside_price: Optional[int] = None
    luxury_boxes_price: Optional[int] = None
    is_price_change: bool = False
    price_change_note: Optional[str] = None
    table_row_index: Optional[int] = None  # To preserve original table order


@dataclass
class CollectionResult:
    """Result of collecting from a team's arena page."""
    
    team_id: str
    success: bool
    games_data: List[GamePricingData]
    error_message: Optional[str] = None
    last_10_games_found: int = 0
    price_changes_found: int = 0


class TeamArenaCollector:
    """Collector for BuzzerBeater team arena pages to extract historical pricing."""
    
    BASE_URL = "https://www.buzzerbeater.com"
    
    def __init__(self, request_delay: float = 1.0, timeout: int = 30):
        """Initialize the collector.
        
        Args:
            request_delay: Delay between requests in seconds to be respectful
            timeout: Request timeout in seconds
        """
        self.request_delay = request_delay
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set a realistic user agent to appear like a regular user
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def collect_team_arena_data(self, team_id: str) -> CollectionResult:
        """Collect historical game and pricing data from team's arena page.
        
        Args:
            team_id: The BuzzerBeater team ID
            
        Returns:
            CollectionResult with extracted data or error information
        """
        logger.info(f"Starting to collect arena data for team {team_id}")
        
        try:
            # Construct the arena page URL
            url = f"{self.BASE_URL}/team/{team_id}/arena.aspx"
            logger.debug(f"Fetching URL: {url}")
            
            # Add delay to be respectful to the server
            time.sleep(self.request_delay)
            
            # Make the request
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract game and pricing data
            games_data = self._extract_games_and_pricing(soup, team_id)
            
            # Count different types of data found
            last_10_games = len([g for g in games_data if not g.is_price_change])
            price_changes = len([g for g in games_data if g.is_price_change])
            
            logger.info(f"Successfully collected team {team_id}: found {last_10_games} games and {price_changes} price changes")
            
            return CollectionResult(
                team_id=team_id,
                success=True,
                games_data=games_data,
                last_10_games_found=last_10_games,
                price_changes_found=price_changes
            )
            
        except requests.RequestException as e:
            error_msg = f"Network error while collecting team {team_id}: {str(e)}"
            logger.error(error_msg)
            return CollectionResult(
                team_id=team_id,
                success=False,
                games_data=[],
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error while collecting team {team_id}: {str(e)}"
            logger.error(error_msg)
            return CollectionResult(
                team_id=team_id,
                success=False,
                games_data=[],
                error_message=error_msg
            )
    
    def _extract_games_and_pricing(self, soup: BeautifulSoup, team_id: str) -> List[GamePricingData]:
        """Extract game attendance and pricing data from the arena page.
        
        The arena page contains a single table that mixes game attendance records and price updates.
        Price updates have 'Ticket Price Update' as opponent and attendance = -1.
        
        Args:
            soup: Parsed HTML content
            team_id: Team ID for logging/debugging
            
        Returns:
            List of GamePricingData objects (both games and price changes)
        """
        games_data: List[GamePricingData] = []
        
        try:
            # Find the main attendance table (there should be only one)
            table = self._find_games_section(soup)
            if not table:
                logger.warning(f"Could not find attendance table for team {team_id}")
                return games_data
            
            logger.debug(f"Found attendance table for team {team_id}")
            
            # Parse the table rows
            rows = table.find_all('tr')
            if not rows:
                logger.warning(f"No rows found in attendance table for team {team_id}")
                return games_data
            
            # Find header row to understand column structure
            header_row = None
            for row in rows:
                if isinstance(row, Tag):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) > 0:
                        header_texts = [cell.get_text().strip().lower() for cell in cells]
                        if any('date' in text for text in header_texts):
                            header_row = row
                            break
            
            if not header_row:
                logger.warning(f"Could not find header row in attendance table for team {team_id}")
                return games_data
            
            # Map column positions
            column_map = self._parse_column_mapping(header_row)
            logger.debug(f"Column mapping for team {team_id}: {column_map}")
            
            # Parse each data row
            row_index = 0
            for row in rows:
                if row == header_row or not isinstance(row, Tag):
                    continue
                
                cells = row.find_all(['td', 'th'])
                if len(cells) < max(column_map.values()) + 1 if column_map else 0:
                    continue
                
                # Extract data from this row
                cell_tags = [cell for cell in cells if isinstance(cell, Tag)]
                game_data = self._parse_table_row(cell_tags, column_map, row_index)
                if game_data:
                    games_data.append(game_data)
                    if game_data.is_price_change:
                        logger.debug(f"Found price update for team {team_id}: {game_data.date}")
                    else:
                        logger.debug(f"Found game for team {team_id}: {game_data.date} vs {game_data.opponent}")
                
                row_index += 1
        except Exception as e:
            logger.error(f"Error extracting data for team {team_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return games_data
    
    def _find_games_section(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the section containing recent game attendance data."""
        
        # Common patterns to look for
        selectors_to_try = [
            # Look for tables with attendance data
            'table:has(th:contains("Attendance"))',
            'table:has(td:contains("attendance"))',
            'table:has(th:contains("Date"))',
            
            # Look for sections with specific text
            'div:contains("Last 10 official")',
            'div:contains("attendance")',
            'section:contains("Games")',
            
            # Generic table selectors
            'table.gameTable',
            'table.attendanceTable',
            'table.data',
            '.attendance-section',
            '.games-section'
        ]
        
        for selector in selectors_to_try:
            try:
                elements = soup.select(selector)
                if elements:
                    return elements[0]
            except Exception:
                continue
                
        # If specific selectors don't work, look for tables containing game-like data
        tables = soup.find_all('table')
        for table in tables:
            if isinstance(table, Tag):
                text = table.get_text().lower()
                if any(keyword in text for keyword in ['attendance', 'game', 'date', 'opponent']):
                    return table
                
        return None
    
    def _find_price_changes_section(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the section containing price change history."""
        
        selectors_to_try = [
            'table:has(th:contains("Price"))',
            'table:has(td:contains("price"))',
            'div:contains("price change")',
            'div:contains("ticket price")',
            'section:contains("Price")',
            '.price-section',
            '.pricing-history'
        ]
        
        for selector in selectors_to_try:
            try:
                elements = soup.select(selector)
                if elements:
                    return elements[0]
            except Exception:
                continue
                
        # Look for tables with price-related content
        tables = soup.find_all('table')
        for table in tables:
            if isinstance(table, Tag):
                text = table.get_text().lower()
                if any(keyword in text for keyword in ['price', 'pricing', 'ticket']):
                    return table
                
        return None
    
    def _parse_games_section(self, section: Tag) -> List[GamePricingData]:
        """Parse the games attendance section."""
        games_data = []
        
        try:
            # Look for table rows
            rows = section.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                if not isinstance(row, Tag):
                    continue
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:  # Need at least date, opponent, attendance
                    continue
                
                game_data = GamePricingData()
                
                # Try to extract data from cells
                # This will need to be adjusted based on the actual page structure
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text().strip()
                    
                    # Try to identify what each cell contains
                    if self._looks_like_date(cell_text):
                        game_data.date = self._parse_date(cell_text)
                    elif self._looks_like_attendance(cell_text):
                        game_data.attendance = self._parse_attendance(cell_text)
                    elif self._looks_like_opponent(cell_text):
                        game_data.opponent = cell_text
                    elif self._looks_like_price(cell_text):
                        # Try to identify which seat type
                        self._parse_price_into_game_data(cell_text, game_data, i)
                
                if game_data.date or game_data.opponent or game_data.attendance:
                    games_data.append(game_data)
                    
        except Exception as e:
            logger.error(f"Error parsing games section: {e}")
        
        return games_data
    
    def _parse_price_changes_section(self, section: Tag) -> List[GamePricingData]:
        """Parse the price changes section."""
        price_changes = []
        
        try:
            rows = section.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                if not isinstance(row, Tag):
                    continue
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                price_data = GamePricingData(is_price_change=True)
                
                for cell in cells:
                    cell_text = cell.get_text().strip()
                    
                    if self._looks_like_date(cell_text):
                        price_data.date = self._parse_date(cell_text)
                    elif self._looks_like_price(cell_text):
                        self._parse_price_into_game_data(cell_text, price_data, 0)
                    else:
                        # Might be a description of the price change
                        if not price_data.price_change_note:
                            price_data.price_change_note = cell_text
                
                if price_data.date or any([
                    price_data.bleachers_price,
                    price_data.lower_tier_price,
                    price_data.courtside_price,
                    price_data.luxury_boxes_price
                ]):
                    price_changes.append(price_data)
                    
        except Exception as e:
            logger.error(f"Error parsing price changes section: {e}")
        
        return price_changes
    
    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date."""
        # Common date patterns
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY/MM/DD
            r'\w+ \d{1,2}, \d{4}',             # Month DD, YYYY
            r'\d{1,2} \w+ \d{4}',              # DD Month YYYY
        ]
        
        return any(re.search(pattern, text) for pattern in date_patterns)
    
    def _looks_like_attendance(self, text: str) -> bool:
        """Check if text looks like attendance numbers."""
        # Remove commas and check if it's a number
        clean_text = text.replace(',', '').replace('.', '')
        return clean_text.isdigit() and len(clean_text) >= 3
    
    def _looks_like_opponent(self, text: str) -> bool:
        """Check if text looks like an opponent name."""
        # Opponent names are usually text, not numbers or special symbols
        return (len(text) > 2 and 
                not text.replace(',', '').replace('.', '').isdigit() and
                not self._looks_like_date(text) and
                not self._looks_like_price(text))
    
    def _looks_like_price(self, text: str) -> bool:
        """Check if text looks like a price."""
        # Look for currency symbols or price patterns
        price_patterns = [
            r'[$€£¥]\s*\d+',
            r'\d+\s*[$€£¥]',
            r'\d+\.\d{2}',
            r'\b\d{1,3}(?:,\d{3})*\b'  # Numbers with commas
        ]
        
        return any(re.search(pattern, text) for pattern in price_patterns)
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from text."""
        try:
            # Try various date formats
            formats = [
                '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
                '%m-%d-%Y', '%d-%m-%Y', '%Y-%m-%d',
                '%B %d, %Y', '%d %B %Y',
                '%b %d, %Y', '%d %b %Y',
                '%m/%d/%y', '%d/%m/%y',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not parse date '{date_text}': {e}")
        
        return None
    
    def _parse_attendance(self, attendance_text: str) -> Optional[int]:
        """Parse attendance number from text."""
        try:
            # Remove commas and other formatting
            clean_text = attendance_text.replace(',', '').replace('.', '').strip()
            return int(clean_text)
        except (ValueError, TypeError):
            return None
    
    def _parse_price_into_game_data(self, price_text: str, game_data: GamePricingData, cell_index: int):
        """Parse price and assign to appropriate seat type in game data."""
        try:
            # Extract numeric price
            price_match = re.search(r'\d+(?:,\d{3})*(?:\.\d{2})?', price_text.replace('$', ''))
            if not price_match:
                return
            
            price = int(float(price_match.group().replace(',', '')))
            
            # Try to determine seat type from context
            text_lower = price_text.lower()
            
            if any(keyword in text_lower for keyword in ['bleacher', 'general', 'cheap']):
                game_data.bleachers_price = price
            elif any(keyword in text_lower for keyword in ['lower', 'tier', 'lower tier']):
                game_data.lower_tier_price = price
            elif any(keyword in text_lower for keyword in ['courtside', 'court', 'premium']):
                game_data.courtside_price = price
            elif any(keyword in text_lower for keyword in ['luxury', 'box', 'vip']):
                game_data.luxury_boxes_price = price
            else:
                # If we can't determine the type, assign based on cell position
                if cell_index == 0 or 'bleacher' in text_lower:
                    game_data.bleachers_price = price
                elif cell_index == 1:
                    game_data.lower_tier_price = price
                elif cell_index == 2:
                    game_data.courtside_price = price
                elif cell_index == 3:
                    game_data.luxury_boxes_price = price
                    
        except Exception as e:
            logger.debug(f"Could not parse price '{price_text}': {e}")
    
    def _parse_column_mapping(self, header_row: Tag) -> Dict[str, int]:
        """Parse header row to create column mapping.
        
        Args:
            header_row: The header row containing column names
            
        Returns:
            Dictionary mapping column names to indices
        """
        column_map = {}
        headers = header_row.find_all(['th', 'td'])
        
        for i, header in enumerate(headers):
            header_text = header.get_text().strip().lower()
            
            if 'date' in header_text:
                column_map['date'] = i
            elif 'opponent' in header_text:
                column_map['opponent'] = i
            elif 'bleacher' in header_text:
                column_map['bleachers'] = i
            elif 'lower tier' in header_text or 'lower' in header_text:
                column_map['lower_tier'] = i
            elif 'courtside' in header_text:
                column_map['courtside'] = i
            elif 'luxury' in header_text:
                column_map['luxury_boxes'] = i
            elif 'total attendance' in header_text or 'attendance' in header_text:
                column_map['attendance'] = i
            elif 'game type' in header_text or 'type' in header_text:
                column_map['game_type'] = i
        
        return column_map
    
    def _parse_table_row(self, cells: List[Tag], column_map: Dict[str, int], row_index: int) -> Optional[GamePricingData]:
        """Parse a single table row into GamePricingData.
        
        Args:
            cells: List of table cells
            column_map: Mapping of column names to indices
            
        Returns:
            GamePricingData object or None if parsing fails
        """
        try:
            # Extract data from cells based on column mapping
            row_data = {}
            for col_name, col_index in column_map.items():
                if col_index < len(cells):
                    cell_text = cells[col_index].get_text().strip()
                    row_data[col_name] = cell_text
            
            # Check if this is a price update or game
            opponent = row_data.get('opponent', '')
            attendance_str = row_data.get('attendance', '')
            
            is_price_update = (
                'ticket price update' in opponent.lower() or
                attendance_str == '-1' or
                (attendance_str.isdigit() and int(attendance_str) == -1)
            )
            
            # Create GamePricingData object
            game_data = GamePricingData(is_price_change=is_price_update, table_row_index=row_index)
            
            # Parse date
            if 'date' in row_data:
                game_data.date = self._parse_date(row_data['date'])
            
            # Parse based on whether it's a price update or game
            if is_price_update:
                # This is a price update - the seat columns contain the NEW PRICES
                game_data.price_change_note = "Ticket Price Update"
                
                # For price updates, the seat columns contain prices (in dollars)
                if 'bleachers' in row_data:
                    game_data.bleachers_price = self._parse_price(row_data['bleachers'])
                if 'lower_tier' in row_data:
                    game_data.lower_tier_price = self._parse_price(row_data['lower_tier'])
                if 'courtside' in row_data:
                    game_data.courtside_price = self._parse_price(row_data['courtside'])
                if 'luxury_boxes' in row_data:
                    game_data.luxury_boxes_price = self._parse_price(row_data['luxury_boxes'])
            else:
                # This is a game attendance record - seat columns contain ATTENDANCE by section
                game_data.opponent = row_data.get('opponent', '')
                
                # Parse total attendance
                if 'attendance' in row_data:
                    attendance = self._parse_attendance(row_data['attendance'])
                    if attendance is not None:
                        game_data.attendance = attendance
                
                # For games, the seat columns contain attendance numbers, NOT prices
                # The actual prices that were charged for this game are not directly available
                # in this table - they need to be inferred from price updates or arena snapshots
            
            # Only return if we have meaningful data
            if game_data.date or game_data.opponent or game_data.attendance is not None:
                return game_data
            
        except Exception as e:
            logger.debug(f"Error parsing table row: {e}")
        
        return None
    
    def _parse_price(self, price_text: str) -> Optional[int]:
        """Parse price text to integer.
        
        Args:
            price_text: Text containing price
            
        Returns:
            Price as integer or None if parsing fails
        """
        try:
            if not price_text or price_text.strip() == '-':
                return None
            
            # Extract numeric value, removing currency symbols and commas
            price_match = re.search(r'\d+(?:,\d{3})*(?:\.\d{2})?', price_text.replace('$', ''))
            if price_match:
                price_str = price_match.group().replace(',', '')
                return int(float(price_str))
        except (ValueError, AttributeError):
            pass
        
        return None

    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
