from bs4 import BeautifulSoup, Tag
from typing import Optional


class ArenaTableIsolator:
    """Service for isolating the attendance table from arena HTML."""
    
    @staticmethod
    def find_attendance_table(html_content: str) -> Optional[Tag]:
        """
        Find the attendance history table in the arena HTML.
        
        Args:
            html_content: Full HTML content of arena page
            
        Returns:
            BeautifulSoup Tag object of the table, or None if not found
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', id='cphContent_seatingStats')
        return table if isinstance(table, Tag) else None
    
    @staticmethod
    def validate_table_structure(table: Tag) -> bool:
        """
        Validate that the table has expected structure.
        
        Args:
            table: BeautifulSoup table Tag
            
        Returns:
            True if table structure is valid
        """
        # Check for header row
        header_row = table.find('tr', class_='tableHeader')
        if not header_row or not isinstance(header_row, Tag):
            return False
        
        # Check headers
        expected_headers = [
            'Date', 'Opponent', 'Bleachers', 'Lower Tier', 
            'Courtside Seats', 'Luxury Boxes', 'Total Attendance', 'Game Type'
        ]
        
        headers = [th.get_text().strip() for th in header_row.find_all('th')]
        return headers == expected_headers
    
    @staticmethod
    def count_data_rows(table: Tag) -> int:
        """
        Count the number of data rows (excluding header).
        
        Args:
            table: BeautifulSoup table Tag
            
        Returns:
            Number of data rows
        """
        all_rows = table.find_all('tr')
        data_rows = []
        
        for row in all_rows:
            if isinstance(row, Tag):
                row_class = row.get('class')
                # Skip header rows
                if row_class is None or 'tableHeader' not in str(row_class):
                    data_rows.append(row)
        
        return len(data_rows)