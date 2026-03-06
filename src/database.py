"""
DuckDB database connection and query utilities.
"""

from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "saas_data.duckdb"


class Database:
    """Wrapper for DuckDB database operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._connection = None
    
    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get a database connection."""
        if self._connection is None:
            if not self.db_path.exists():
                raise FileNotFoundError(
                    f"Database not found at {self.db_path}. "
                    "Run 'python data/generate_data.py' first."
                )
            self._connection = duckdb.connect(str(self.db_path), read_only=True)
        return self._connection
    
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def query(self, sql: str) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame."""
        con = self.connect()
        try:
            result = con.execute(sql).fetchdf()
            return result
        except Exception as e:
            raise QueryError(f"Query failed: {e}") from e
    
    def get_tables(self) -> list[str]:
        """Get list of all tables in the database."""
        con = self.connect()
        result = con.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        return [row[0] for row in result]
    
    def get_schema(self, table_name: str) -> pd.DataFrame:
        """Get schema information for a table."""
        con = self.connect()
        result = con.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchdf()
        return result
    
    def get_sample(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Get sample rows from a table."""
        return self.query(f"SELECT * FROM {table_name} LIMIT {limit}")
    
    def get_full_schema_info(self) -> str:
        """Get formatted schema information for all tables."""
        tables = self.get_tables()
        schema_info = []
        
        for table in tables:
            schema = self.get_schema(table)
            columns = []
            for _, row in schema.iterrows():
                nullable = "NULL" if row["is_nullable"] == "YES" else "NOT NULL"
                columns.append(f"    {row['column_name']} {row['data_type']} {nullable}")
            
            schema_info.append(f"TABLE {table}:\n" + "\n".join(columns))
        
        return "\n\n".join(schema_info)


class QueryError(Exception):
    """Raised when a database query fails."""
    pass


def get_database() -> Database:
    """Get a database instance."""
    return Database()
