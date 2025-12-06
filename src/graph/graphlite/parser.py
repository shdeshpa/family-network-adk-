"""Parse GraphLite CLI output."""

import re
from src.graph.models import QueryResult


class OutputParser:
    """Parse GraphLite CLI table output."""
    
    @staticmethod
    def parse_table(output: str) -> QueryResult:
        """
        Parse CLI table output into structured data.
        """
        lines = output.strip().split('\n')
        
        columns = []
        rows = []
        header_separator_found = False
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Skip decorative lines
            if line.startswith('┌') or line.startswith('└'):
                continue
            
            # Skip row separators
            if line.startswith('├') and '╌' in line:
                continue
            
            # Header separator - data comes after this
            if line.startswith('╞'):
                header_separator_found = True
                continue
            
            # Only skip INFO lines (not table data)
            # These lines do NOT contain │ or ┆
            if '│' not in line and '┆' not in line:
                continue
            
            # Parse table row
            normalized = line.replace('┆', '│')
            parts = [p.strip() for p in normalized.split('│')]
            parts = [p for p in parts if p != '']
            
            if not parts:
                continue
            
            # Skip status rows like "Created 1 node"
            if len(parts) == 1 and any(kw in parts[0] for kw in ['Created', 'Deleted', 'Updated', 'MATCH INSERT']):
                continue
            
            if not header_separator_found:
                columns = parts
            else:
                if len(parts) == len(columns):
                    row = {}
                    for i, col in enumerate(columns):
                        value = parts[i]
                        row[col] = None if value == 'NULL' else value
                    rows.append(row)
        
        return QueryResult(
            success=True, 
            columns=columns, 
            rows=rows, 
            raw_output=output
        )
    
    @staticmethod
    def parse_rows_affected(output: str) -> int:
        """Extract rows affected from output."""
        for pattern in [r'Created (\d+)', r'Deleted (\d+)', r'Updated (\d+)']:
            match = re.search(pattern, output)
            if match:
                return int(match.group(1))
        return 0
    
    @staticmethod
    def extract_error(output: str) -> str:
        """Extract error message from output."""
        for line in output.split('\n'):
            if 'error' in line.lower() or 'Error' in line:
                return line.strip()
        return "Unknown error"
