# db_utils.py
"""
Database utility functions supporting both SQLite and MSSQL connections.
Automatically selects the appropriate database based on configuration.
"""
import sqlite3
import pandas as pd
from config import USE_MSSQL, SQLITE_DB_PATH, get_mssql_connection_string, get_connection_info

# Only import pyodbc if we're using MSSQL
if USE_MSSQL:
    import pyodbc

def get_connection():
    """
    Get database connection (SQLite or MSSQL based on config).
    
    Returns:
        Connection object (sqlite3.Connection or pyodbc.Connection)
    """
    try:
        if USE_MSSQL:
            conn_str = get_mssql_connection_string()
            conn = pyodbc.connect(conn_str)
            print("[db_utils] Successfully connected to MSSQL database")
        else:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            print(f"[db_utils] Successfully connected to SQLite database: {SQLITE_DB_PATH}")
        return conn
    except Exception as e:
        print(f"[db_utils] Error connecting to database: {e}")
        info = get_connection_info()
        print(f"[db_utils] Connection info: {info}")
        raise

def execute_query(query):
    """
    Execute a SQL query and return results as DataFrame.
    Works with both SQLite and MSSQL.
    
    Args:
        query (str): SQL query to execute
        
    Returns:
        pd.DataFrame: Query results as DataFrame
    """
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(query, conn)
            db_type = "MSSQL" if USE_MSSQL else "SQLite"
            print(f"[db_utils] Query returned {len(df):,} rows from {db_type}")
            return df
    except Exception as e:
        print(f"[db_utils] Error executing query: {e}")
        print(f"[db_utils] Query: {query[:200]}...")  # Print first 200 chars
        raise

def execute_non_query(query):
    """
    Execute a non-query SQL command (INSERT, UPDATE, DELETE, CREATE, etc.).
    Works with both SQLite and MSSQL.
    
    Args:
        query (str): SQL command to execute
        
    Returns:
        int: Number of rows affected
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            rows_affected = cursor.rowcount
            db_type = "MSSQL" if USE_MSSQL else "SQLite"
            print(f"[db_utils] Command executed on {db_type}, {rows_affected} rows affected")
            return rows_affected
    except Exception as e:
        print(f"[db_utils] Error executing command: {e}")
        print(f"[db_utils] Command: {query[:200]}...")
        raise

def test_connection():
    """Test database connection and print connection details."""
    try:
        info = get_connection_info()
        print(f"[db_utils] Testing {info['type']} connection...")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if USE_MSSQL:
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                print(f"[db_utils] Connected successfully!")
                print(f"[db_utils] SQL Server version: {version[:100]}...")
            else:
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()[0]
                print(f"[db_utils] Connected successfully!")
                print(f"[db_utils] SQLite version: {version}")
            
            return True
    except Exception as e:
        print(f"[db_utils] Connection test failed: {e}")
        return False
