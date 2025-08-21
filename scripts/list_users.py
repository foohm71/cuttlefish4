#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Simple script to list and manage users in PostgreSQL database.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.models import DatabaseManager, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_users():
    """List all users in the database."""
    db_manager = DatabaseManager()
    
    with db_manager.SessionLocal() as session:
        users = session.query(User).all()
        
        if not users:
            print("📝 No users found in database")
            return
        
        print(f"\n👥 Found {len(users)} user(s):")
        print("=" * 120)
        
        for user in users:
            admin_flag = "🔐 ADMIN" if user.is_admin else ""
            active_flag = "✅" if user.is_active else "❌"
            unlimited_flag = "♾️ UNLIMITED" if user.unlimited_access else f"({user.requests_used}/{user.daily_limit})"
            
            print(f"{active_flag} {user.email}")
            print(f"    Name: {user.display_name}")
            print(f"    Google ID: {user.google_id}")
            print(f"    Usage: {unlimited_flag}")
            print(f"    Created: {user.created_at}")
            print(f"    {admin_flag}")
            print()

def create_admin_user(email: str, google_id: str, display_name: str = None):
    """Create an admin user."""
    db_manager = DatabaseManager()
    
    with db_manager.SessionLocal() as session:
        # Check if user already exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            print(f"⚠️  User {email} already exists!")
            return
        
        # Create new admin user
        admin_user = User(
            email=email,
            google_id=google_id,
            display_name=display_name or email,
            daily_limit=1000,  # High limit for admin
            unlimited_access=True,
            is_admin=True,
            is_active=True
        )
        
        session.add(admin_user)
        session.commit()
        
        print(f"🎉 Admin user created: {email}")
        print(f"    Google ID: {google_id}")
        print(f"    Display Name: {admin_user.display_name}")
        print(f"    Admin: {admin_user.is_admin}")
        print(f"    Unlimited Access: {admin_user.unlimited_access}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='List and manage Cuttlefish users')
    parser.add_argument('--list', action='store_true', help='List all users')
    parser.add_argument('--create-admin', help='Create admin user (email)')
    parser.add_argument('--google-id', help='Google ID for new admin user')
    parser.add_argument('--display-name', help='Display name for new user')
    
    args = parser.parse_args()
    
    if args.create_admin:
        if not args.google_id:
            print("Error: --google-id is required when creating admin user")
            print("To find your Google ID, go to https://myaccount.google.com/profile")
            sys.exit(1)
        create_admin_user(args.create_admin, args.google_id, args.display_name)
    else:
        list_users()  # Default action