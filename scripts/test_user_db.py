#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Test script to verify user database functionality with PostgreSQL.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.models import DatabaseManager, User, ApiRequest
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test PostgreSQL connection and create tables."""
    
    logger.info("Testing database connection...")
    
    # Debug environment variables
    logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    logger.info(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'Not set')}")
    logger.info(f"SUPABASE_DB_PASSWORD: {os.getenv('SUPABASE_DB_PASSWORD', 'Not set')}")
    
    try:
        # Initialize database manager (will auto-detect PostgreSQL from env)
        db_manager = DatabaseManager()
        logger.info(f"Database URL: {db_manager.database_url}")
        
        # Test connection
        with db_manager.SessionLocal() as session:
            result = session.execute(text("SELECT 1")).scalar()
            logger.info("✅ Database connection successful")
        
        # Create tables
        logger.info("Creating user tables...")
        db_manager.create_tables()
        logger.info("✅ Tables created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def test_user_operations():
    """Test basic user operations."""
    
    logger.info("Testing user operations...")
    
    try:
        db_manager = DatabaseManager()
        
        with db_manager.SessionLocal() as session:
            # Create a test user
            test_user = User(
                email="test@example.com",
                google_id="12345",
                display_name="Test User",
                daily_limit=50,
                requests_used=0
            )
            
            session.add(test_user)
            session.commit()
            logger.info("✅ Test user created")
            
            # Query the user
            found_user = session.query(User).filter_by(email="test@example.com").first()
            if found_user:
                logger.info(f"✅ User found: {found_user.email} - {found_user.display_name}")
            
            # Test user methods
            can_make_request = found_user.can_make_request()
            logger.info(f"✅ Can make request: {can_make_request}")
            
            # Clean up test user
            session.delete(found_user)
            session.commit()
            logger.info("✅ Test user cleaned up")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ User operations test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🧪 Testing User Database with PostgreSQL")
    logger.info("=" * 50)
    
    # Test connection and table creation
    if test_database_connection():
        # Test user operations
        if test_user_operations():
            logger.info("🎉 All tests passed! Database is ready.")
        else:
            logger.error("❌ User operations test failed")
            sys.exit(1)
    else:
        logger.error("❌ Database connection test failed")
        logger.error("Make sure:")
        logger.error("1. SUPABASE_DB_PASSWORD is set in .env")
        logger.error("2. psycopg2-binary is installed")
        logger.error("3. Your Supabase database is accessible")
        sys.exit(1)