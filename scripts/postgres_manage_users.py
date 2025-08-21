#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
PostgreSQL User management CLI script for Cuttlefish4.
Allows admins to add, remove, update, and list users.
"""

import os
import sys
import argparse
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.models import DatabaseManager, User, ApiRequest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session():
    """Get database session."""
    db_manager = DatabaseManager()
    return db_manager.SessionLocal()

def list_users():
    """List all users."""
    with get_db_session() as session:
        users = session.query(User).order_by(User.created_at.desc()).all()
        
        if not users:
            print("No users found.")
            return
        
        print(f"\n{'Email':<30} {'Name':<20} {'Limit':<8} {'Used':<6} {'Unlimited':<10} {'Active':<8} {'Admin':<7} {'Created'}")
        print("-" * 120)
        
        for user in users:
            name = user.display_name or "N/A"
            created_date = user.created_at.strftime('%Y-%m-%d') if user.created_at else "N/A"
            
            print(f"{user.email:<30} {name:<20} {user.daily_limit:<8} {user.requests_used:<6} {str(user.unlimited_access):<10} {str(user.is_active):<8} {str(user.is_admin):<7} {created_date}")

def add_user(email: str, google_id: str = None, daily_limit: int = 20, 
             unlimited: bool = False, admin: bool = False, name: str = None):
    """Add a new user."""
    with get_db_session() as session:
        # Check if user exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            print(f"❌ User {email} already exists")
            return
        
        # Use temporary google_id if not provided
        if not google_id:
            google_id = f"temp_{email.replace('@', '_').replace('.', '_')}"
        
        try:
            new_user = User(
                email=email,
                google_id=google_id,
                display_name=name,
                daily_limit=daily_limit,
                unlimited_access=unlimited,
                is_admin=admin,
                is_active=True,
                requests_used=0
            )
            
            session.add(new_user)
            session.commit()
            
            print(f"✅ User {email} added successfully")
            
            if unlimited:
                print(f"   - Unlimited access: YES")
            else:
                print(f"   - Daily limit: {daily_limit}")
            
            if admin:
                print(f"   - Admin privileges: YES")
                
        except Exception as e:
            print(f"❌ Failed to add user: {e}")
            session.rollback()

def update_user(email: str, daily_limit: int = None, unlimited: bool = None, 
                active: bool = None, admin: bool = None):
    """Update user settings."""
    with get_db_session() as session:
        # Check if user exists
        user = session.query(User).filter_by(email=email).first()
        if not user:
            print(f"❌ User {email} not found")
            return
        
        changes = []
        
        if daily_limit is not None:
            user.daily_limit = daily_limit
            changes.append(f"Daily limit: {daily_limit}")
        
        if unlimited is not None:
            user.unlimited_access = unlimited
            changes.append(f"Unlimited access: {unlimited}")
        
        if active is not None:
            user.is_active = active
            changes.append(f"Active status: {active}")
        
        if admin is not None:
            user.is_admin = admin
            changes.append(f"Admin privileges: {admin}")
        
        if not changes:
            print("❌ No updates specified")
            return
        
        user.updated_at = datetime.utcnow()
        
        try:
            session.commit()
            print(f"✅ User {email} updated successfully")
            for change in changes:
                print(f"   - {change}")
                
        except Exception as e:
            print(f"❌ Failed to update user: {e}")
            session.rollback()

def remove_user(email: str, confirm: bool = False):
    """Remove a user."""
    if not confirm:
        response = input(f"Are you sure you want to remove user {email}? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            return
    
    with get_db_session() as session:
        # Check if user exists
        user = session.query(User).filter_by(email=email).first()
        if not user:
            print(f"❌ User {email} not found")
            return
        
        try:
            # Remove associated API requests first (due to foreign key)
            api_requests = session.query(ApiRequest).filter_by(user_email=email).all()
            for req in api_requests:
                session.delete(req)
            
            # Remove user
            session.delete(user)
            session.commit()
            
            print(f"✅ User {email} removed successfully")
            
        except Exception as e:
            print(f"❌ Failed to remove user: {e}")
            session.rollback()

def reset_usage(email: str = None):
    """Reset usage counters for user(s)."""
    with get_db_session() as session:
        try:
            today = date.today()
            
            if email:
                # Reset specific user
                user = session.query(User).filter_by(email=email).first()
                if not user:
                    print(f"❌ User {email} not found")
                    return
                
                user.requests_used = 0
                user.last_reset_date = today
                user.updated_at = datetime.utcnow()
                
                session.commit()
                print(f"✅ Usage reset for {email}")
            else:
                # Reset all users
                users = session.query(User).all()
                count = 0
                
                for user in users:
                    user.requests_used = 0
                    user.last_reset_date = today
                    user.updated_at = datetime.utcnow()
                    count += 1
                
                session.commit()
                print(f"✅ Usage reset for {count} users")
            
        except Exception as e:
            print(f"❌ Failed to reset usage: {e}")
            session.rollback()

def show_usage_stats():
    """Show system usage statistics."""
    with get_db_session() as session:
        # Get basic stats
        total_users = session.query(User).count()
        active_users = session.query(User).filter_by(is_active=True).count()
        unlimited_users = session.query(User).filter_by(unlimited_access=True).count()
        admin_users = session.query(User).filter_by(is_admin=True).count()
        
        # Get today's usage
        today = date.today()
        today_requests = session.query(User).filter_by(last_reset_date=today).with_entities(
            User.requests_used
        ).all()
        
        total_today = sum(req[0] for req in today_requests if req[0])
        
        # Get top users today
        top_users = session.query(User).filter(
            User.last_reset_date == today,
            User.requests_used > 0
        ).order_by(User.requests_used.desc()).limit(5).all()
        
        print("\n📊 Usage Statistics")
        print("=" * 50)
        print(f"Total Users:      {total_users}")
        print(f"Active Users:     {active_users}")
        print(f"Unlimited Users:  {unlimited_users}")
        print(f"Admin Users:      {admin_users}")
        print(f"Today's Requests: {total_today}")
        
        if top_users:
            print(f"\n🔥 Top Users Today:")
            for user in top_users:
                percentage = (user.requests_used / user.daily_limit * 100) if user.daily_limit > 0 else 0
                print(f"   {user.email}: {user.requests_used}/{user.daily_limit} ({percentage:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="Cuttlefish4 PostgreSQL User Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List users
    subparsers.add_parser('list', help='List all users')
    
    # Add user
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('email', help='User email address')
    add_parser.add_argument('--name', help='Display name')
    add_parser.add_argument('--limit', type=int, default=20, help='Daily request limit (default: 20)')
    add_parser.add_argument('--unlimited', action='store_true', help='Give unlimited access')
    add_parser.add_argument('--admin', action='store_true', help='Give admin privileges')
    add_parser.add_argument('--google-id', help='Google user ID (optional)')
    
    # Update user
    update_parser = subparsers.add_parser('update', help='Update user settings')
    update_parser.add_argument('email', help='User email address')
    update_parser.add_argument('--limit', type=int, help='New daily request limit')
    update_parser.add_argument('--unlimited', action='store_true', help='Give unlimited access')
    update_parser.add_argument('--no-unlimited', action='store_true', help='Remove unlimited access')
    update_parser.add_argument('--activate', action='store_true', help='Activate user')
    update_parser.add_argument('--deactivate', action='store_true', help='Deactivate user')
    update_parser.add_argument('--admin', action='store_true', help='Give admin privileges')
    update_parser.add_argument('--no-admin', action='store_true', help='Remove admin privileges')
    
    # Remove user
    remove_parser = subparsers.add_parser('remove', help='Remove a user')
    remove_parser.add_argument('email', help='User email address')
    remove_parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    
    # Reset usage
    reset_parser = subparsers.add_parser('reset-usage', help='Reset usage counters')
    reset_parser.add_argument('--email', help='Specific user email (optional)')
    
    # Usage stats
    subparsers.add_parser('stats', help='Show usage statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'list':
        list_users()
    
    elif args.command == 'add':
        add_user(
            email=args.email,
            google_id=args.google_id,
            daily_limit=args.limit,
            unlimited=args.unlimited,
            admin=args.admin,
            name=args.name
        )
    
    elif args.command == 'update':
        unlimited = None
        if args.unlimited:
            unlimited = True
        elif args.no_unlimited:
            unlimited = False
        
        active = None
        if args.activate:
            active = True
        elif args.deactivate:
            active = False
        
        admin = None
        if args.admin:
            admin = True
        elif args.no_admin:
            admin = False
        
        update_user(
            email=args.email,
            daily_limit=args.limit,
            unlimited=unlimited,
            active=active,
            admin=admin
        )
    
    elif args.command == 'remove':
        remove_user(args.email, confirm=args.yes)
    
    elif args.command == 'reset-usage':
        reset_usage(args.email)
    
    elif args.command == 'stats':
        show_usage_stats()

if __name__ == "__main__":
    main()