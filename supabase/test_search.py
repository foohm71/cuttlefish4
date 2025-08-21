#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Simple script to test the unified Supabase search interface.
Demonstrates how to use the new search() method with different parameters.
"""

import sys
from pathlib import Path

# Add the supabase directory to the path
sys.path.append(str(Path(__file__).parent))

from supabase_client import SupabaseVectorClient

def main():
    """Test the unified search interface."""
    
    print("🔍 Testing Unified Supabase Search Interface")
    print("=" * 50)
    
    try:
        # Initialize client
        client = SupabaseVectorClient()
        print("✅ Client initialized successfully")
        
        # Test different search scenarios
        test_queries = [
            # (query, table, search_type, description)
            ("authentication error", "bugs", "vector", "Vector search for authentication issues"),
            ("login failed", "bugs", "keyword", "Keyword search for login failures"),
            ("database connection timeout", "bugs", "hybrid", "Hybrid search for DB issues"),
            ("feature enhancement", "pcr", "keyword", "PCR search for features"),
            ("new user interface", "pcr", "vector", "Vector search for UI features"),
        ]
        
        for query, table, search_type, description in test_queries:
            print(f"\n🧪 {description}")
            print(f"   Query: '{query}' | Table: {table} | Type: {search_type}")
            
            try:
                results = client.search(
                    query=query,
                    table=table,
                    search_type=search_type,
                    k=3  # Get top 3 results
                )
                
                print(f"   ✅ Found {len(results)} results")
                
                # Show first result if available
                if results:
                    first_result = results[0]
                    title = first_result.get('title', 'No title')
                    key = first_result.get('key', 'No key')
                    
                    # Get appropriate score based on search type
                    if search_type == 'vector':
                        score = first_result.get('similarity', 0)
                    elif search_type == 'hybrid':
                        score = first_result.get('combined_score', 0)
                    else:
                        score = 0  # Keyword search doesn't return scores
                    
                    print(f"   📄 Top result: [{key}] {title[:60]}... (score: {score:.3f})")
                else:
                    print("   📄 No results found")
                
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        # Test document counts
        print(f"\n📊 Document Counts:")
        for table in ['bugs', 'pcr']:
            try:
                count = client.count_documents(table)
                print(f"   {table}: {count} documents")
            except Exception as e:
                print(f"   {table}: Error counting - {e}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        print("\nMake sure you have:")
        print("1. Set up your .env file with SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY")
        print("2. Created the bugs and pcr tables in Supabase")
        print("3. Uploaded some data to test with")


def interactive_search():
    """Interactive search mode for testing."""
    
    print("\n🔬 Interactive Search Mode")
    print("Type 'quit' to exit")
    
    try:
        client = SupabaseVectorClient()
        
        while True:
            print("\n" + "-" * 30)
            query = input("Enter search query (or 'quit'): ").strip()
            
            if query.lower() == 'quit':
                break
            
            if not query:
                print("Please enter a valid query")
                continue
            
            # Get search parameters
            table = input("Table (bugs/pcr) [bugs]: ").strip() or "bugs"
            search_type = input("Search type (vector/keyword/hybrid) [vector]: ").strip() or "vector"
            
            try:
                results = client.search(
                    query=query,
                    table=table,
                    search_type=search_type,
                    k=5
                )
                
                print(f"\n📋 Found {len(results)} results:")
                
                for i, result in enumerate(results[:3], 1):
                    title = result.get('title', 'No title')
                    jira_key = result.get('key', 'No key')
                    
                    # Get appropriate score based on search type
                    if search_type == 'vector':
                        score = result.get('similarity', 0)
                    elif search_type == 'hybrid':
                        score = result.get('combined_score', 0)
                    else:
                        score = 0  # Keyword search doesn't return scores
                    
                    print(f"{i}. [{jira_key}] {title[:80]}...")
                    if score > 0:
                        print(f"   Score: {score:.3f}")
                
            except Exception as e:
                print(f"❌ Search failed: {e}")
    
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Supabase unified search interface")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_search()
    else:
        main()