#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Simple test script to verify Tavily web search functionality.
Run this script to test if the WebSearch tools are working correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_web_search_tools():
    """Simple test for web search tools."""
    print("🧪 Testing Tavily Web Search Tools")
    print("=" * 50)
    
    # Check if TAVILY_API_KEY is set
    tavily_key = os.environ.get('TAVILY_API_KEY')
    if not tavily_key:
        print("❌ TAVILY_API_KEY environment variable not found")
        print("   Please set your Tavily API key:")
        print("   export TAVILY_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ TAVILY_API_KEY found: {tavily_key[:8]}...")
    
    try:
        # Import the web search tools
        sys.path.append('/Users/foohm/github/cuttlefish4')
        from app.tools.web_search_tools import WebSearchTools
        
        print("✅ WebSearchTools imported successfully")
        
        # Initialize tools
        tools = WebSearchTools()
        
        # Test connection
        print("\n🔗 Testing connection...")
        if tools.test_connection():
            print("✅ Connection test successful")
        else:
            print("❌ Connection test failed")
            return False
        
        # Test basic web search
        print("\n🔍 Testing basic web search...")
        test_query = "GitHub status"
        results = tools.web_search(test_query, max_results=2)
        
        if results:
            print(f"✅ Retrieved {len(results)} results for '{test_query}'")
            
            # Show first result details
            first_result = results[0]
            print(f"   Title: {first_result.get('title', 'No title')[:50]}...")
            print(f"   URL: {first_result.get('url', 'No URL')}")
            print(f"   Content length: {len(first_result.get('content', ''))} chars")
            
            return True
        else:
            print("❌ No results returned from web search")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running from the correct directory")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_web_search_tools()
    
    if success:
        print("\n🎉 Web Search Tools are working correctly!")
        print("   You can now use the WebSearch agent in Cuttlefish4")
    else:
        print("\n❌ Web Search Tools test failed")
        print("   Fix the issues above before using WebSearch agent")
    
    print("\n" + "=" * 50)