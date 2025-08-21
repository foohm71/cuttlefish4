#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Database initialization script for Cuttlefish4 authentication system.
Creates SQLite database with user management schema.
"""

import os
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_database_path() -> str:
    """Get the database file path."""
    db_path = os.environ.get('DATABASE_PATH', './users.db')
    return db_path

def read_schema() -> str:
    """Read the SQL schema file."""
    schema_path = Path(__file__).parent / 'schema.sql'
    with open(schema_path, 'r') as f:
        return f.read()

def initialize_database(db_path: str = None) -> bool:
    """
    Initialize the SQLite database with the required schema.
    
    Args:
        db_path: Optional database path override
    
    Returns:
        True if successful, False otherwise
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        # Ensure database directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Connect and execute schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        schema_sql = read_schema()
        cursor.executescript(schema_sql)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Database initialized successfully at: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False

def check_database_exists(db_path: str = None) -> bool:
    """
    Check if the database file exists and has the required tables.
    
    Args:
        db_path: Optional database path override
    
    Returns:
        True if database exists and is valid, False otherwise
    """
    if db_path is None:
        db_path = get_database_path()
    
    if not os.path.exists(db_path):
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if required tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('users', 'api_requests')
        """)
        tables = cursor.fetchall()
        
        conn.close()
        
        # Should have both tables
        return len(tables) == 2
        
    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        return False

def get_user_count(db_path: str = None) -> int:
    """
    Get the number of users in the database.
    
    Args:
        db_path: Optional database path override
    
    Returns:
        Number of users, -1 if error
    """
    if db_path is None:
        db_path = get_database_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed to get user count: {e}")
        return -1

if __name__ == "__main__":
    # Initialize database when run directly
    logging.basicConfig(level=logging.INFO)
    
    db_path = get_database_path()
    print(f"Initializing database at: {db_path}")
    
    if initialize_database(db_path):
        user_count = get_user_count(db_path)
        print(f"✅ Database ready with {user_count} users")
    else:
        print("❌ Database initialization failed")
        exit(1)