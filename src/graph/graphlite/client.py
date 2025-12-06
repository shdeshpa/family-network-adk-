"""GraphLite CLI client via stdin pipe."""

import subprocess
from typing import Optional

from src.graph.models import QueryResult
from src.graph.graphlite.config import GraphLiteConfig
from src.graph.graphlite.parser import OutputParser


class GraphLiteClient:
    """Python client for GraphLite-AI database."""
    
    def __init__(self, config: GraphLiteConfig = None):
        self.config = config or GraphLiteConfig()
        self.parser = OutputParser()
    
    def _run_gql(self, queries: list[str]) -> tuple[bool, str, str]:
        """Run GQL queries via stdin pipe."""
        lines = [f"SESSION SET GRAPH {self.config.graph_path};"]
        lines.extend([q.strip().rstrip(';') + ';' for q in queries])
        lines.append("exit")
        
        input_text = '\n'.join(lines)
        
        cmd = [
            "graphlite", "gql",
            "--path", self.config.db_path,
            "-u", self.config.user,
            "-p", self.config.password
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Query timeout"
        except FileNotFoundError:
            return False, "", "graphlite CLI not found"
    
    def execute(self, query: str) -> QueryResult:
        """Execute a write statement (INSERT, DELETE, SET)."""
        success, stdout, stderr = self._run_gql([query])
        
        if not success or "Error:" in stderr:
            return QueryResult(
                success=False,
                error=stderr or self.parser.extract_error(stdout),
                raw_output=stdout + stderr
            )
        
        return QueryResult(
            success=True,
            rows_affected=self.parser.parse_rows_affected(stdout),
            raw_output=stdout
        )
    
    def query(self, query: str) -> QueryResult:
        """Execute a read query (MATCH ... RETURN)."""
        success, stdout, stderr = self._run_gql([query])
        
        if not success or "Error:" in stderr:
            return QueryResult(
                success=False,
                error=stderr or self.parser.extract_error(stdout),
                raw_output=stdout + stderr
            )
        
        return self.parser.parse_table(stdout)
    
    def init_schema(self) -> bool:
        """Initialize schema and graph."""
        cmd = [
            "graphlite", "gql",
            "--path", self.config.db_path,
            "-u", self.config.user,
            "-p", self.config.password
        ]
        
        queries = f"""CREATE SCHEMA /{self.config.schema};
CREATE GRAPH /{self.config.schema}/{self.config.graph};
exit
"""
        try:
            subprocess.run(cmd, input=queries, capture_output=True, text=True, timeout=30)
            return True
        except:
            return False
