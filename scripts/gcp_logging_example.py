#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Google Cloud Logging example for Cuttlefish4 LogSearch system.
Demonstrates log ingestion and searching using GCP Logging API.
"""

from google.cloud import logging
from google.cloud.logging import DESCENDING, ASCENDING
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class GCPLogManager:
    def __init__(self, project_id: str = None):
        """Initialize GCP Logging client."""
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project_id required")
        
        # Initialize the logging client
        self.client = logging.Client(project=self.project_id)
        
        print(f"✅ GCP Logging client initialized for project: {self.project_id}")
    
    def ingest_log_entries(self, log_entries: List[Dict[str, Any]], log_name: str = "cuttlefish_synthetic_logs") -> bool:
        """
        Ingest log entries into Google Cloud Logging.
        
        Args:
            log_entries: List of log entry dictionaries
            log_name: Name of the log (default: cuttlefish_synthetic_logs)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get logger for the specified log name
            logger = self.client.logger(log_name)
            
            print(f"📤 Ingesting {len(log_entries)} log entries to log: {log_name}")
            
            for entry in log_entries:
                # Structure the log entry
                structured_entry = {
                    'level': entry.get('level', 'INFO'),
                    'logger': entry.get('logger', 'unknown'),
                    'thread': entry.get('thread', 'main'),
                    'message': entry.get('message', ''),
                    'raw_log': entry.get('raw', ''),
                    'timestamp': entry.get('timestamp', datetime.now().isoformat())
                }
                
                # Log with appropriate severity
                severity = entry.get('level', 'INFO')
                if severity == 'ERROR':
                    logger.log_struct(structured_entry, severity='ERROR')
                elif severity == 'WARN':
                    logger.log_struct(structured_entry, severity='WARNING')
                elif severity == 'DEBUG':
                    logger.log_struct(structured_entry, severity='DEBUG')
                else:
                    logger.log_struct(structured_entry, severity='INFO')
            
            print(f"✅ Successfully ingested {len(log_entries)} log entries")
            return True
            
        except Exception as e:
            print(f"❌ Error ingesting log entries: {e}")
            return False
    
    def search_logs(self, filter_query: str = "", max_results: int = 10, order_by: str = "timestamp desc") -> List[Dict[str, Any]]:
        """
        Search log entries in Google Cloud Logging.
        
        Args:
            filter_query: GCP Logging filter query
            max_results: Maximum number of results to return
            order_by: Sort order for results
            
        Returns:
            List of log entries
        """
        try:
            print(f"🔍 Searching logs with filter: {filter_query}")
            
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
                result = {
                    'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                    'severity': entry.severity,
                    'log_name': entry.log_name,
                    'payload': entry.payload,
                    'resource': entry.resource.type if entry.resource else None,
                    'labels': dict(entry.labels) if entry.labels else {}
                }
                results.append(result)
            
            print(f"✅ Found {len(results)} log entries")
            return results
            
        except Exception as e:
            print(f"❌ Error searching logs: {e}")
            return []
    
    def test_basic_searches(self):
        """Run basic search tests similar to Splunk tests."""
        
        print(f"\n{'='*60}")
        print("GCP LOGGING SEARCH TESTS")
        print(f"{'='*60}")
        
        # Test 1: Search for synthetic logs
        print(f"\n📋 TEST 1: Search for synthetic logs")
        results1 = self.search_logs(
            filter_query='logName="projects/{}/logs/cuttlefish_synthetic_logs"'.format(self.project_id),
            max_results=5
        )
        
        if results1:
            print(f"📊 Sample results:")
            for i, entry in enumerate(results1[:3], 1):
                timestamp = entry.get('timestamp', 'No timestamp')
                payload = entry.get('payload', {})
                message = payload.get('message', 'No message') if isinstance(payload, dict) else str(payload)
                print(f"  {i}. {timestamp}")
                print(f"     {message[:100]}...")
        
        # Test 2: Search for ERROR level logs
        print(f"\n📋 TEST 2: Search for ERROR level logs")
        results2 = self.search_logs(
            filter_query=f'logName="projects/{self.project_id}/logs/cuttlefish_synthetic_logs" AND severity="ERROR"',
            max_results=5
        )
        
        if results2:
            print(f"📊 ERROR logs found:")
            for i, entry in enumerate(results2[:2], 1):
                payload = entry.get('payload', {})
                message = payload.get('message', 'No message') if isinstance(payload, dict) else str(payload)
                print(f"  {i}. {message[:150]}...")
        
        # Test 3: Search for specific exceptions
        print(f"\n📋 TEST 3: Search for certificate exceptions")
        results3 = self.search_logs(
            filter_query=f'logName="projects/{self.project_id}/logs/cuttlefish_synthetic_logs" AND jsonPayload.message:"CertificateExpired"',
            max_results=3
        )
        
        if results3:
            print(f"📊 Certificate exception logs:")
            for i, entry in enumerate(results3, 1):
                payload = entry.get('payload', {})
                message = payload.get('message', 'No message') if isinstance(payload, dict) else str(payload)
                print(f"  {i}. {message[:150]}...")
        
        # Summary
        print(f"\n{'='*60}")
        print("GCP LOGGING TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Basic log search: {len(results1)} results")
        print(f"✅ ERROR level search: {len(results2)} results")
        print(f"✅ Certificate exception search: {len(results3)} results")
        
        if any([results1, results2, results3]):
            print(f"\n🎉 GCP Logging functionality is working!")
            print(f"💡 Ready to integrate with LogSearch agent")
        else:
            print(f"\n⚠️  No results found. Check if data was ingested correctly.")

def main():
    """Main function to demonstrate GCP Logging capabilities."""
    try:
        # Initialize GCP Log Manager
        log_manager = GCPLogManager()
        
        # Example log entries (similar to your synthetic logs)
        sample_logs = [
            {
                'level': 'INFO',
                'logger': 'com.cuttlefish.Application',
                'thread': 'main',
                'message': 'Application started successfully',
                'raw': '2025-08-19 10:30:00.123 [main] INFO com.cuttlefish.Application - Application started successfully',
                'timestamp': '2025-08-19T10:30:00.123Z'
            },
            {
                'level': 'ERROR',
                'logger': 'com.cuttlefish.ssl.CertificateManager',
                'thread': 'worker-1',
                'message': 'CertificateExpired: SSL certificate expired for domain example.com',
                'raw': '2025-08-19 10:30:01.456 [worker-1] ERROR com.cuttlefish.ssl.CertificateManager - CertificateExpired: SSL certificate expired for domain example.com',
                'timestamp': '2025-08-19T10:30:01.456Z'
            },
            {
                'level': 'WARN',
                'logger': 'com.cuttlefish.network.ConnectionPool',
                'thread': 'pool-1',
                'message': 'Connection pool size: 85 active, 15 idle',
                'raw': '2025-08-19 10:30:02.789 [pool-1] WARN com.cuttlefish.network.ConnectionPool - Connection pool size: 85 active, 15 idle',
                'timestamp': '2025-08-19T10:30:02.789Z'
            }
        ]
        
        # Ingest sample logs
        success = log_manager.ingest_log_entries(sample_logs)
        
        if success:
            print(f"\n⏳ Waiting a moment for logs to be indexed...")
            import time
            time.sleep(5)  # Wait for logs to be indexed
            
            # Run search tests
            log_manager.test_basic_searches()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    print("🚀 GCP Logging Test")
    print("=" * 50)
    exit(main())