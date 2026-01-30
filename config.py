# config.py
"""
Database configuration supporting both SQLite (local) and MSSQL (production).
Set USE_MSSQL environment variable to switch between databases.
"""
import os
from dotenv import load_dotenv

from pathlib import Path

# Load environment variables from .env file if it exists
load_dotenv()

# Database mode selection
# Set USE_MSSQL=true in production, leave unset or false for local SQLite
USE_MSSQL = os.environ.get('USE_MSSQL', 'false').lower() in ('true', '1', 'yes')

# SQLite Configuration (for local development)
BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = BASE_DIR / "DOH_AMHD_NO_PII.db"

# MSSQL Configuration (for production)
MSSQL_CONFIG = {
    'server': os.environ.get('DB_SERVER', 'your-server.database.windows.net'),
    'database': os.environ.get('DB_NAME', 'your_database_name'),
    'username': os.environ.get('DB_USER', 'your_username'),
    'password': os.environ.get('DB_PASSWORD', 'your_password'),
    'driver': os.environ.get('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
}

def get_mssql_connection_string():
    """
    Build MSSQL connection string from config.
    
    Returns:
        str: ODBC connection string for MSSQL
    """
    return (
        f"DRIVER={MSSQL_CONFIG['driver']};"
        f"SERVER={MSSQL_CONFIG['server']};"
        f"DATABASE={MSSQL_CONFIG['database']};"
        f"UID={MSSQL_CONFIG['username']};"
        f"PWD={MSSQL_CONFIG['password']}"
    )

def get_connection_info():
    """Get connection info for debugging (without password)."""
    db_type = "MSSQL" if USE_MSSQL else "SQLite"
    info = {'type': db_type}
    
    if USE_MSSQL:
        info.update({
            'server': MSSQL_CONFIG['server'],
            'database': MSSQL_CONFIG['database'],
            'username': MSSQL_CONFIG['username'],
            'driver': MSSQL_CONFIG['driver']
        })
    else:
        info['db_path'] = SQLITE_DB_PATH
    
    return info
