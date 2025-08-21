#!/usr/bin/env python3
"""
Debug script to test database connectivity from Render to Supabase.
Run this to diagnose connection issues.
"""

import os
import sys
import socket
import psycopg2

def test_network_connectivity():
    """Test if we can reach Supabase database host."""
    host = "db.jzstozvrjjhmwigycjtj.supabase.co"
    port = 5432
    
    print(f"Testing network connectivity to {host}:{port}")
    
    try:
        # Test socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ Network connectivity: SUCCESS")
            return True
        else:
            print(f"❌ Network connectivity: FAILED (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Network connectivity: FAILED ({e})")
        return False

def test_database_connection():
    """Test PostgreSQL connection with credentials."""
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    database_url = os.getenv("DATABASE_URL")
    
    print(f"\nEnvironment Variables:")
    print(f"SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Not set'}")
    print(f"SUPABASE_DB_PASSWORD: {'✅ Set' if db_password else '❌ Not set'}")
    print(f"DATABASE_URL: {'✅ Set' if database_url else '❌ Not set'}")
    
    if database_url:
        print(f"\nTesting DATABASE_URL connection...")
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            print("✅ DATABASE_URL connection: SUCCESS")
            return True
        except Exception as e:
            print(f"❌ DATABASE_URL connection: FAILED ({e})")
    
    if supabase_url and db_password:
        # Construct URL like the app does
        project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")
        constructed_url = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"
        
        print(f"\nTesting constructed Supabase URL...")
        print(f"Project ref: {project_ref}")
        print(f"URL: postgresql://postgres:***@db.{project_ref}.supabase.co:5432/postgres")
        
        try:
            conn = psycopg2.connect(constructed_url)
            conn.close()
            print("✅ Supabase connection: SUCCESS")
            return True
        except Exception as e:
            print(f"❌ Supabase connection: FAILED ({e})")
    
    return False

def main():
    print("🔍 Database Connectivity Diagnostic")
    print("=" * 50)
    
    # Test network first
    network_ok = test_network_connectivity()
    
    # Test database connection
    db_ok = test_database_connection()
    
    print(f"\n📊 Summary:")
    print(f"Network: {'✅' if network_ok else '❌'}")
    print(f"Database: {'✅' if db_ok else '❌'}")
    
    if not network_ok:
        print("\n💡 Network issue detected:")
        print("- Render may not be able to reach Supabase")
        print("- Check Render's networking configuration")
        print("- Verify Supabase allows connections from Render IPs")
    
    if network_ok and not db_ok:
        print("\n💡 Database authentication issue:")
        print("- Network is reachable but connection failed")
        print("- Check SUPABASE_DB_PASSWORD is correct")
        print("- Verify Supabase database credentials")
        print("- Check if database URL is properly constructed")
    
    sys.exit(0 if (network_ok and db_ok) else 1)

if __name__ == "__main__":
    main()