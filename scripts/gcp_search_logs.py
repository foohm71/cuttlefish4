#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
GCP Cloud Logging search script for Cuttlefish4.
Search and retrieve log entries from Google Cloud Logging using the Cloud Logging API.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add the app directory to the path so we can import our tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from google.cloud import logging
    from google.cloud.logging import DESCENDING, ASCENDING
    from app.tools.gcp_auth import get_gcp_client, test_gcp_auth, get_deployment_info
except ImportError as e:
    print(f"❌ Error: Required packages not installed. Run: pip install google-cloud-logging")
    print(f"   Import error: {e}")
    sys.exit(1)

DEFAULT_LOG_NAME = "cuttlefish_synthetic_logs"
DEFAULT_MAX_RESULTS = 10

class GCPLogSearcher:
    def __init__(self, project_id: str = None):
        """Initialize GCP Log searcher with project configuration."""
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project_id required")
        
        # Initialize the logging client using cloud-ready authentication
        try:
            self.client = get_gcp_client(self.project_id)
            
            # Get deployment info
            deployment_info = get_deployment_info()
            
            print(f"✅ GCP Log searcher initialized")
            print(f"   Project: {self.project_id}")
            if deployment_info.get("is_gcp"):
                print(f"   Running on GCP: {deployment_info.get('gcp_service', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Failed to initialize GCP Logging client: {e}")
            print(f"💡 Deployment info: {get_deployment_info()}")
            raise ValueError(f"Failed to initialize GCP Logging client: {e}")
    
    def search_logs(self, filter_query: str = "", max_results: int = DEFAULT_MAX_RESULTS, 
                   order_by: str = "timestamp desc") -> List[Dict[str, Any]]:
        """
        Search log entries in Google Cloud Logging.
        
        Args:
            filter_query: GCP Logging filter query
            max_results: Maximum number of results to return
            order_by: Sort order for results ('timestamp desc' or 'timestamp asc')
            
        Returns:
            List of log entries
        """
        try:
            print(f"🔍 Searching logs with filter: {filter_query}")
            print(f"   Max results: {max_results}")
            print(f"   Order: {order_by}")
            
            # Set order direction
            order = DESCENDING if "desc" in order_by.lower() else ASCENDING
            
            # Search log entries
            entries = self.client.list_entries(
                filter_=filter_query,
                order_by=order,
                max_results=max_results
            )
            
            results = []
            for entry in entries:
                # Extract structured data
                result = {
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                    'severity': entry.severity,
                    'log_name': entry.log_name,
                    'resource_type': entry.resource.type if entry.resource else None,
                    'labels': dict(entry.labels) if entry.labels else {},
                    'insert_id': entry.insert_id,
                    'http_request': entry.http_request,
                    'operation': entry.operation,
                    'trace': entry.trace,
                    'span_id': entry.span_id,
                    'source_location': entry.source_location
                }
                
                # Handle different payload types
                if hasattr(entry, 'payload') and entry.payload:
                    if hasattr(entry.payload, 'json_payload'):
                        result['payload'] = dict(entry.payload.json_payload)
                        result['payload_type'] = 'json'
                    elif hasattr(entry.payload, 'proto_payload'):
                        result['payload'] = str(entry.payload.proto_payload)
                        result['payload_type'] = 'proto'
                    else:
                        result['payload'] = str(entry.payload)
                        result['payload_type'] = 'text'
                else:
                    result['payload'] = None
                    result['payload_type'] = 'none'
                
                results.append(result)
            
            print(f"✅ Found {len(results)} log entries")
            return results
            
        except Exception as e:
            print(f"❌ Error searching logs: {e}")
            return []
    
    def search_by_log_name(self, log_name: str = DEFAULT_LOG_NAME, 
                          max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
        """Search logs by log name."""
        filter_query = f'logName="projects/{self.project_id}/logs/{log_name}"'
        return self.search_logs(filter_query, max_results)
    
    def search_by_severity(self, severity: str, log_name: str = DEFAULT_LOG_NAME, 
                          max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
        """Search logs by severity level."""
        filter_query = f'logName="projects/{self.project_id}/logs/{log_name}" AND severity="{severity.upper()}"'
        return self.search_logs(filter_query, max_results)
    
    def search_by_message_content(self, search_text: str, log_name: str = DEFAULT_LOG_NAME, 
                                 max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
        """Search logs by message content."""
        filter_query = f'logName="projects/{self.project_id}/logs/{log_name}" AND jsonPayload.message:"{search_text}"'
        return self.search_logs(filter_query, max_results)
    
    def search_by_time_range(self, start_time: str, end_time: str = None, 
                            log_name: str = DEFAULT_LOG_NAME, 
                            max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
        """
        Search logs within a time range.
        
        Args:
            start_time: Start time in ISO format (e.g., '2025-08-19T10:00:00Z')
            end_time: End time in ISO format (default: now)
            log_name: Log name to search
            max_results: Maximum number of results
        """
        if end_time is None:
            end_time = datetime.now().isoformat() + 'Z'
        
        filter_query = f'logName="projects/{self.project_id}/logs/{log_name}" AND timestamp>="{start_time}" AND timestamp<="{end_time}"'
        return self.search_logs(filter_query, max_results)
    
    def search_recent_logs(self, hours: int = 1, log_name: str = DEFAULT_LOG_NAME, 
                          max_results: int = DEFAULT_MAX_RESULTS) -> List[Dict[str, Any]]:
        """Search logs from the last N hours."""
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + 'Z'
        return self.search_by_time_range(start_time, log_name=log_name, max_results=max_results)
    
    def test_basic_searches(self, log_name: str = DEFAULT_LOG_NAME):
        """Run basic search tests similar to Splunk tests."""
        
        print(f"\\n{'='*60}")
        print("GCP LOGGING SEARCH TESTS")
        print(f"{'='*60}")
        
        # Test 1: Search for logs by name
        print(f"\\n📋 TEST 1: Search for logs by name ({log_name})")
        results1 = self.search_by_log_name(log_name, 5)
        
        if results1:
            print(f"📊 Sample results:")
            for i, entry in enumerate(results1[:3], 1):
                timestamp = entry.get('timestamp', 'No timestamp')
                payload = entry.get('payload', {})
                
                if isinstance(payload, dict):
                    message = payload.get('message', 'No message')
                    logger = payload.get('logger', 'No logger')
                    print(f"  {i}. {timestamp} [{logger}]")
                    print(f"     {message[:100]}...")
                else:
                    print(f"  {i}. {timestamp}")
                    print(f"     {str(payload)[:100]}...")
        
        # Test 2: Search for ERROR level logs
        print(f"\\n📋 TEST 2: Search for ERROR level logs")
        results2 = self.search_by_severity('ERROR', log_name, 5)
        
        if results2:
            print(f"📊 ERROR logs found:")
            for i, entry in enumerate(results2[:2], 1):
                payload = entry.get('payload', {})
                severity = entry.get('severity', 'UNKNOWN')
                
                if isinstance(payload, dict):
                    message = payload.get('message', 'No message')
                    print(f"  {i}. [{severity}] {message[:150]}...")
                else:
                    print(f"  {i}. [{severity}] {str(payload)[:150]}...")
        
        # Test 3: Search for specific content
        print(f"\\n📋 TEST 3: Search for certificate exceptions")
        results3 = self.search_by_message_content('CertificateExpired', log_name, 3)
        
        if results3:
            print(f"📊 Certificate exception logs:")
            for i, entry in enumerate(results3, 1):
                payload = entry.get('payload', {})
                
                if isinstance(payload, dict):
                    message = payload.get('message', 'No message')
                    print(f"  {i}. {message[:150]}...")
                else:
                    print(f"  {i}. {str(payload)[:150]}...")
        
        # Test 4: Search recent logs (last hour)
        print(f"\\n📋 TEST 4: Search recent logs (last hour)")
        results4 = self.search_recent_logs(1, log_name, 5)
        
        if results4:
            print(f"📊 Recent logs:")
            for i, entry in enumerate(results4[:2], 1):
                timestamp = entry.get('timestamp', 'No timestamp')
                payload = entry.get('payload', {})
                
                if isinstance(payload, dict):
                    level = payload.get('level', 'INFO')
                    message = payload.get('message', 'No message')
                    print(f"  {i}. {timestamp} [{level}] {message[:100]}...")
                else:
                    print(f"  {i}. {timestamp} {str(payload)[:100]}...")
        
        # Summary
        print(f"\\n{'='*60}")
        print("GCP LOGGING SEARCH SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Basic log search: {len(results1)} results")
        print(f"✅ ERROR level search: {len(results2)} results")
        print(f"✅ Certificate exception search: {len(results3)} results")
        print(f"✅ Recent logs search: {len(results4)} results")
        
        if any([results1, results2, results3, results4]):
            print(f"\\n🎉 GCP Logging search functionality is working!")
            print(f"💡 Ready to integrate with LogSearch agent")
        else:
            print(f"\\n⚠️  No results found. Check if data was ingested correctly.")
            print(f"💡 Try ingesting some logs first with: python gcp_ingest_logs.py")
        
        return {
            'basic_search': len(results1),
            'error_search': len(results2),
            'content_search': len(results3),
            'recent_search': len(results4)
        }
    
    def export_logs_to_json(self, filter_query: str, output_file: str, 
                           max_results: int = 1000) -> bool:
        """Export search results to JSON file."""
        try:
            print(f"📤 Exporting logs to {output_file}")
            results = self.search_logs(filter_query, max_results)
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"✅ Exported {len(results)} log entries to {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export logs: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Search log entries in Google Cloud Logging')
    parser.add_argument('--project-id', '-p', help='GCP Project ID (default: from GOOGLE_CLOUD_PROJECT env var)')
    parser.add_argument('--log-name', '-l', default=DEFAULT_LOG_NAME,
                      help=f'GCP log name (default: {DEFAULT_LOG_NAME})')
    parser.add_argument('--filter', '-f', help='GCP Logging filter query')
    parser.add_argument('--severity', '-s', help='Search by severity level (ERROR, WARNING, INFO, DEBUG)')
    parser.add_argument('--message', '-m', help='Search by message content')
    parser.add_argument('--recent-hours', '-r', type=int, help='Search logs from last N hours')
    parser.add_argument('--max-results', '-n', type=int, default=DEFAULT_MAX_RESULTS,
                      help=f'Maximum number of results (default: {DEFAULT_MAX_RESULTS})')
    parser.add_argument('--order', '-o', choices=['asc', 'desc'], default='desc',
                      help='Sort order (default: desc)')
    parser.add_argument('--export', '-e', help='Export results to JSON file')
    parser.add_argument('--test', '-t', action='store_true',
                      help='Run basic search tests')
    
    args = parser.parse_args()
    
    try:
        # Initialize searcher
        searcher = GCPLogSearcher(project_id=args.project_id)
        
        # Run tests if requested
        if args.test:
            searcher.test_basic_searches(args.log_name)
            return 0
        
        # Determine search type
        results = []
        
        if args.filter:
            # Custom filter query
            results = searcher.search_logs(
                filter_query=args.filter,
                max_results=args.max_results,
                order_by=f"timestamp {args.order}"
            )
            
        elif args.severity:
            # Search by severity
            results = searcher.search_by_severity(
                severity=args.severity,
                log_name=args.log_name,
                max_results=args.max_results
            )
            
        elif args.message:
            # Search by message content
            results = searcher.search_by_message_content(
                search_text=args.message,
                log_name=args.log_name,
                max_results=args.max_results
            )
            
        elif args.recent_hours:
            # Search recent logs
            results = searcher.search_recent_logs(
                hours=args.recent_hours,
                log_name=args.log_name,
                max_results=args.max_results
            )
            
        else:
            # Default: search by log name
            results = searcher.search_by_log_name(
                log_name=args.log_name,
                max_results=args.max_results
            )
        
        # Export if requested
        if args.export and results:
            searcher.export_logs_to_json("", args.export, len(results))
        
        # Display results
        if results:
            print(f"\\n📊 Found {len(results)} results:")
            for i, entry in enumerate(results[:5], 1):
                timestamp = entry.get('timestamp', 'No timestamp')
                severity = entry.get('severity', 'UNKNOWN')
                payload = entry.get('payload', {})
                
                if isinstance(payload, dict):
                    message = payload.get('message', 'No message')
                    logger = payload.get('logger', 'No logger')
                    print(f"\\n{i}. [{severity}] {timestamp}")
                    print(f"   Logger: {logger}")
                    print(f"   Message: {message[:200]}...")
                else:
                    print(f"\\n{i}. [{severity}] {timestamp}")
                    print(f"   Payload: {str(payload)[:200]}...")
        else:
            print("\\n⚠️  No results found")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())