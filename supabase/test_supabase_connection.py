#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Test Supabase connection to diagnose SSL issues.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection."""
    
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    print("🔧 Testing Supabase Connection...")
    print(f"URL: {supabase_url}")
    print(f"Key: {'*' * 20 if supabase_key else 'NOT SET'}")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY in environment")
        print("Please check your .env file")
        return False
    
    try:
        # Test 1: Basic import
        print("\n1. Testing Supabase import...")
        from supabase import create_client, Client
        print("✅ Supabase import successful")
        
        # Test 2: Client creation
        print("\n2. Testing client creation...")
        client: Client = create_client(supabase_url, supabase_key)
        print("✅ Client creation successful")
        
        # Test 3: Simple connection test
        print("\n3. Testing basic connection...")
        
        # Try to list tables (this will test the connection)
        result = client.table('bugs').select('id').limit(1).execute()
        print("✅ Connection test successful")
        print(f"Response: {len(result.data)} rows (this is expected to be 0 initially)")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Provide specific troubleshooting based on error type
        if "SSL" in str(e) or "ssl" in str(e).lower():
            print("\n🔧 SSL Troubleshooting:")
            print("1. Check if your Supabase project is active")
            print("2. Verify your SUPABASE_URL is correct")
            print("3. Make sure you're using the service role key, not anon key")
            print("4. Try accessing your Supabase dashboard to confirm it's working")
            
        elif "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
            print("\n🔧 Authentication Troubleshooting:")
            print("1. Check if your SUPABASE_KEY is the service role key")
            print("2. Verify the key hasn't expired")
            print("3. Check RLS policies if enabled")
            
        elif "timeout" in str(e).lower():
            print("\n🔧 Network Troubleshooting:")
            print("1. Check your internet connection")
            print("2. Try again in a few minutes")
            print("3. Check if there are firewall issues")
        
        return False

def test_with_different_settings():
    """Test connection with different SSL settings."""
    print("\n🔧 Testing with different SSL settings...")
    
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing credentials")
        return
    
    try:
        import httpx
        
        # Test with custom HTTP client settings
        print("Testing with relaxed SSL verification...")
        
        # Create a custom HTTP client with more lenient SSL
        custom_client = httpx.Client(
            verify=True,  # Keep SSL verification on for security
            timeout=30.0  # Longer timeout
        )
        
        # Test direct HTTP request to Supabase
        response = custom_client.get(f"{supabase_url}/rest/v1/", headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}"
        })
        
        print(f"✅ Direct HTTP test successful: {response.status_code}")
        
    except Exception as e:
        print(f"❌ Custom client test failed: {e}")

if __name__ == "__main__":
    print("🚀 Supabase Connection Diagnostics")
    print("=" * 50)
    
    success = test_supabase_connection()
    
    if not success:
        test_with_different_settings()
        
        print("\n💡 Next Steps:")
        print("1. Double-check your Supabase credentials")
        print("2. Verify your project is active in Supabase dashboard")
        print("3. Try the upload again with smaller batch size:")
        print("   BATCH_SIZE=10 python supabase/upload_jira_csv_to_supabase.py your_data.csv")
    else:
        print("\n🎉 Connection successful! You can proceed with data upload.")