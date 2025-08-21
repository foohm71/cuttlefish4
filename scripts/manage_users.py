#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
User management CLI script for Cuttlefish4.
Allows admins to add, remove, update, and list users.
"""

import os
import sys
import argparse
import sqlite3
from datetime import datetime, date
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database.init_db import get_database_path, initialize_database, check_database_exists

def get_db_connection():
    """Get database connection."""
    db_path = get_database_path()
    if not check_database_exists(db_path):
        print(f"Database not found. Initializing at {db_path}...")
        if not initialize_database(db_path):
            print("❌ Failed to initialize database")
            sys.exit(1)
    
    return sqlite3.connect(db_path)

def list_users():
    """List all users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT email, display_name, daily_limit, requests_used, 
               unlimited_access, is_active, is_admin, created_at
        FROM users 
        ORDER BY created_at DESC
    """)
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print("No users found.")
        return
    
    print(f"\n{'Email':<30} {'Name':<20} {'Limit':<8} {'Used':<6} {'Unlimited':<10} {'Active':<8} {'Admin':<7} {'Created'}")
    print("-" * 120)
    
    for user in users:
        email, name, limit, used, unlimited, active, admin, created = user
        name = name or "N/A"
        created_date = created.split()[0] if created else "N/A"
        
        print(f"{email:<30} {name:<20} {limit:<8} {used:<6} {str(unlimited):<10} {str(active):<8} {str(admin):<7} {created_date}")

def add_user(email: str, google_id: str = None, daily_limit: int = 50, 
             unlimited: bool = False, admin: bool = False, name: str = None):
    """Add a new user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        print(f"❌ User {email} already exists")
        conn.close()
        return
    
    # Use temporary google_id if not provided
    if not google_id:
        google_id = f"temp_{email.replace('@', '_').replace('.', '_')}"
    
    try:
        cursor.execute("""
            INSERT INTO users (
                email, google_id, display_name, daily_limit, 
                unlimited_access, is_admin
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (email, google_id, name, daily_limit, unlimited, admin))
        
        conn.commit()
        print(f"✅ User {email} added successfully")
        
        if unlimited:
            print(f"   - Unlimited access: YES")
        else:
            print(f"   - Daily limit: {daily_limit}")
        
        if admin:
            print(f"   - Admin privileges: YES")
            
    except sqlite3.Error as e:
        print(f"❌ Failed to add user: {e}")
    
    conn.close()

def update_user(email: str, daily_limit: int = None, unlimited: bool = None, 
                active: bool = None, admin: bool = None):
    """Update user settings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if not cursor.fetchone():
        print(f"❌ User {email} not found")
        conn.close()
        return
    
    updates = []
    values = []
    
    if daily_limit is not None:
        updates.append("daily_limit = ?")
        values.append(daily_limit)
    
    if unlimited is not None:
        updates.append("unlimited_access = ?")
        values.append(unlimited)
    
    if active is not None:
        updates.append("is_active = ?")
        values.append(active)
    
    if admin is not None:
        updates.append("is_admin = ?")
        values.append(admin)
    
    if not updates:
        print("❌ No updates specified")
        conn.close()
        return
    
    updates.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(email)
    
    try:
        query = f"UPDATE users SET {', '.join(updates)} WHERE email = ?"
        cursor.execute(query, values)
        conn.commit()
        
        print(f"✅ User {email} updated successfully")
        
        # Show what was updated
        if daily_limit is not None:
            print(f"   - Daily limit: {daily_limit}")
        if unlimited is not None:
            print(f"   - Unlimited access: {unlimited}")
        if active is not None:
            print(f"   - Active status: {active}")
        if admin is not None:
            print(f"   - Admin privileges: {admin}")
            
    except sqlite3.Error as e:
        print(f"❌ Failed to update user: {e}")
    
    conn.close()

def remove_user(email: str, confirm: bool = False):
    """Remove a user."""
    if not confirm:
        response = input(f"Are you sure you want to remove user {email}? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if not cursor.fetchone():
        print(f"❌ User {email} not found")
        conn.close()
        return
    
    try:
        # Remove user (cascade will remove related api_requests)
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        
        print(f"✅ User {email} removed successfully")
        
    except sqlite3.Error as e:
        print(f"❌ Failed to remove user: {e}")
    
    conn.close()

def reset_usage(email: str = None):
    """Reset usage counters for user(s)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if email:
            # Reset specific user
            cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
            if not cursor.fetchone():
                print(f"❌ User {email} not found")
                conn.close()
                return
            
            cursor.execute("""
                UPDATE users 
                SET requests_used = 0, last_reset_date = ? 
                WHERE email = ?
            """, (date.today().isoformat(), email))
            
            print(f"✅ Usage reset for {email}")
        else:
            # Reset all users
            cursor.execute("""
                UPDATE users 
                SET requests_used = 0, last_reset_date = ?
            """, (date.today().isoformat(),))
            
            affected = cursor.rowcount
            print(f"✅ Usage reset for {affected} users")
        
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"❌ Failed to reset usage: {e}")
    
    conn.close()

def show_usage_stats():
    """Show system usage statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    active_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE unlimited_access = 1")
    unlimited_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_users = cursor.fetchone()[0]
    
    # Get today's usage
    today = date.today().isoformat()
    cursor.execute("""
        SELECT SUM(requests_used) FROM users 
        WHERE last_reset_date = ?
    """, (today,))
    
    today_requests = cursor.fetchone()[0] or 0
    
    # Get top users today
    cursor.execute("""
        SELECT email, requests_used, daily_limit 
        FROM users 
        WHERE last_reset_date = ? AND requests_used > 0
        ORDER BY requests_used DESC 
        LIMIT 5
    """, (today,))
    
    top_users = cursor.fetchall()
    
    conn.close()
    
    print("\n📊 Usage Statistics")
    print("=" * 50)
    print(f"Total Users:      {total_users}")
    print(f"Active Users:     {active_users}")
    print(f"Unlimited Users:  {unlimited_users}")
    print(f"Admin Users:      {admin_users}")
    print(f"Today's Requests: {today_requests}")
    
    if top_users:
        print(f"\n🔥 Top Users Today:")
        for email, used, limit in top_users:
            percentage = (used / limit * 100) if limit > 0 else 0
            print(f"   {email}: {used}/{limit} ({percentage:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="Cuttlefish4 User Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List users
    subparsers.add_parser('list', help='List all users')
    
    # Add user
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('email', help='User email address')
    add_parser.add_argument('--name', help='Display name')
    add_parser.add_argument('--limit', type=int, default=50, help='Daily request limit')
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