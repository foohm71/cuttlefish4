#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Simple Splunk search test script.
Tests searching logs in Splunk using the same environment variables as ingestion.
"""

import os
import sys
import json
import requests
import time
import urllib3
from datetime import datetime

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, skip loading .env file
    pass

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SplunkSearchTester:
    def __init__(self):
        """Initialize Splunk search tester with environment configuration."""
        self.splunk_host = os.environ.get('SPLUNK_HOST')
        self.splunk_token = os.environ.get('SPLUNK_TOKEN')
        self.search_token = os.environ.get('SPLUNK_SEARCH_TOKEN')
        self.index_name = os.environ.get('SPLUNK_INDEX', 'history')
        
        if not self.splunk_host:
            raise ValueError("SPLUNK_HOST environment variable is required")
        
        # Use search token if available, otherwise fall back to regular token
        if self.search_token:
            self.token_to_use = self.search_token
            print("🔍 Using dedicated search token")
        elif self.splunk_token:
            self.token_to_use = self.splunk_token
            print("⚠️  Using HEC token for search (may have limited permissions)")
        else:
            raise ValueError("Either SPLUNK_TOKEN or SPLUNK_SEARCH_TOKEN environment variable is required")
        
        # Remove :8088 from host if present for search API (uses default HTTPS port)
        self.search_host = self.splunk_host.replace(':8088', '')
        
        # Setup session with headers for search API
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Splunk {self.token_to_use}',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        
        # Try the standard Splunk search endpoint first
        self.search_endpoint = f"{self.search_host}/services/search/jobs"
        
        print(f"✅ Splunk search tester initialized")
        print(f"   Search Host: {self.search_host}")
        print(f"   Index: {self.index_name}")
    
    def run_search(self, search_query, max_results=10):
        """
        Run a search query in Splunk and return results.
        
        Args:
            search_query: SPL search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        try:
            print(f"\n🔍 Running search: {search_query}")
            
            # Try multiple endpoint formats for Splunk Cloud
            endpoints_to_try = [
                f"{self.search_host}/services/search/jobs/export",
                f"{self.search_host}/servicesNS/-/-/search/jobs/export", 
                f"{self.search_host}/servicesNS/sc_admin/-/search/jobs/export",
                f"{self.search_host}/api/search/jobs/export"
            ]
            
            # Create search parameters
            search_params = {
                'search': search_query,
                'earliest_time': '-24h',
                'latest_time': 'now',
                'count': max_results,
                'output_mode': 'json'
            }
            
            response = None
            for i, endpoint in enumerate(endpoints_to_try):
                print(f"🔄 Trying endpoint {i+1}/{len(endpoints_to_try)}: {endpoint.split('/')[-3:]}")
                
                response = self.session.post(endpoint, 
                                           data=search_params, 
                                           timeout=60,
                                           verify=False)
                
                if response.status_code == 200:
                    print(f"✅ Success with endpoint {i+1}")
                    break
                else:
                    print(f"❌ Failed: {response.status_code}")
                    if i == len(endpoints_to_try) - 1:
                        print(f"Response: {response.text[:200]}")
            
            if not response or response.status_code != 200:
                return []
            
            # Parse results (each line is a JSON object)
            results = []
            for line in response.text.strip().split('\n'):
                if line.strip():
                    try:
                        result = json.loads(line)
                        results.append(result)
                    except json.JSONDecodeError:
                        continue
            
            print(f"✅ Found {len(results)} results")
            return results[:max_results]
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []
    
    
    def test_basic_searches(self):
        """Run a series of test searches."""
        
        # Test 1: Basic search for our ingested logs
        print(f"\n{'='*60}")
        print("TEST 1: Search for ingested synthetic logs")
        print(f"{'='*60}")
        
        query1 = f'search index={self.index_name} source="cuttlefish_synthetic_logs.log"'
        results1 = self.run_search(query1, 5)
        
        if results1:
            print(f"\n📊 Sample results:")
            for i, event in enumerate(results1[:3], 1):
                timestamp = event.get('_time', 'No timestamp')
                raw = event.get('_raw', 'No raw data')
                print(f"  {i}. {timestamp}")
                print(f"     {raw[:100]}...")
        
        # Test 2: Search for ERROR level logs
        print(f"\n{'='*60}")
        print("TEST 2: Search for ERROR level logs")  
        print(f"{'='*60}")
        
        query2 = f'search index={self.index_name} source="cuttlefish_synthetic_logs.log" level=ERROR'
        results2 = self.run_search(query2, 5)
        
        if results2:
            print(f"\n📊 ERROR logs found:")
            for i, event in enumerate(results2[:2], 1):
                raw = event.get('_raw', 'No raw data')
                print(f"  {i}. {raw[:150]}...")
        
        # Test 3: Search for specific exceptions
        print(f"\n{'='*60}")
        print("TEST 3: Search for certificate exceptions")
        print(f"{'='*60}")
        
        query3 = f'search index={self.index_name} source="cuttlefish_synthetic_logs.log" "CertificateExpired"'
        results3 = self.run_search(query3, 3)
        
        if results3:
            print(f"\n📊 Certificate exception logs:")
            for i, event in enumerate(results3, 1):
                raw = event.get('_raw', 'No raw data')
                print(f"  {i}. {raw[:150]}...")
        
        # Summary
        print(f"\n{'='*60}")
        print("SEARCH TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Basic log search: {len(results1)} results")
        print(f"✅ ERROR level search: {len(results2)} results") 
        print(f"✅ Certificate exception search: {len(results3)} results")
        
        if any([results1, results2, results3]):
            print(f"\n🎉 Splunk search functionality is working!")
            print(f"💡 You can now use these search patterns in the LogSearch agent")
        else:
            print(f"\n⚠️  No results found. Check if data was ingested correctly.")

def main():
    try:
        tester = SplunkSearchTester()
        tester.test_basic_searches()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    print("🚀 Splunk Search Test")
    print("=" * 50)
    exit(main())