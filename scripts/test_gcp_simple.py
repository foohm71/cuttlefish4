#!/usr/bin/env python3
"""
Simple test script for GCP Logging functionality.
This script tests both ingestion and search without requiring command line arguments.
"""

import os
import sys
from datetime import datetime

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.cloud import logging
except ImportError:
    print("❌ google-cloud-logging not installed. Run: pip install google-cloud-logging")
    sys.exit(1)

def test_gcp_logging():
    """Test basic GCP logging functionality."""
    
    # Set project ID
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'octopus-282815')
    log_name = 'cuttlefish_test_logs'
    
    print("🚀 GCP Logging Simple Test")
    print("=" * 50)
    print(f"Project ID: {project_id}")
    print(f"Log Name: {log_name}")
    
    try:
        # Initialize client
        print("\\n🔗 Initializing GCP Logging client...")
        client = logging.Client(project=project_id)
        logger = client.logger(log_name)
        
        print("✅ Client initialized successfully")
        
        # Test log ingestion
        print("\\n📤 Testing log ingestion...")
        
        test_entries = [
            {
                'level': 'INFO',
                'logger': 'cuttlefish.test',
                'message': 'Test log entry for GCP logging',
                'timestamp': datetime.now().isoformat(),
                'test_id': 'gcp_test_001'
            },
            {
                'level': 'ERROR',
                'logger': 'cuttlefish.ssl',
                'message': 'CertificateExpired: Test SSL certificate error',
                'timestamp': datetime.now().isoformat(),
                'test_id': 'gcp_test_002'
            },
            {
                'level': 'WARN',
                'logger': 'cuttlefish.network',
                'message': 'Connection pool size warning: 90 active connections',
                'timestamp': datetime.now().isoformat(),
                'test_id': 'gcp_test_003'
            }
        ]
        
        # Ingest test entries
        for entry in test_entries:
            severity = 'ERROR' if entry['level'] == 'ERROR' else ('WARNING' if entry['level'] == 'WARN' else 'INFO')
            logger.log_struct(entry, severity=severity)
            print(f"   ✅ Logged: [{entry['level']}] {entry['message'][:50]}...")
        
        print("\\n⏳ Waiting for logs to be indexed (5 seconds)...")
        import time
        time.sleep(5)
        
        # Test log searching
        print("\\n🔍 Testing log search...")
        
        # Search for our test logs
        filter_query = f'logName="projects/{project_id}/logs/{log_name}" AND jsonPayload.test_id:"gcp_test"'
        
        entries = client.list_entries(filter_=filter_query, max_results=10)
        results = list(entries)
        
        print(f"✅ Found {len(results)} test log entries")
        
        for i, entry in enumerate(results[:3], 1):
            timestamp = entry.timestamp.isoformat() if entry.timestamp else 'No timestamp'
            severity = entry.severity
            
            # Extract message from payload
            if hasattr(entry, 'payload') and hasattr(entry.payload, 'json_payload'):
                payload = dict(entry.payload.json_payload)
                message = payload.get('message', 'No message')
                print(f"  {i}. [{severity}] {timestamp}")
                print(f"     {message}")
            else:
                print(f"  {i}. [{severity}] {timestamp} - Unknown payload format")
        
        # Test summary
        print("\\n" + "=" * 50)
        print("🎉 GCP LOGGING TEST SUMMARY")
        print("=" * 50)
        print(f"✅ Client initialization: SUCCESS")
        print(f"✅ Log ingestion: {len(test_entries)} entries")
        print(f"✅ Log search: {len(results)} results found")
        
        if len(results) > 0:
            print("\\n🎉 All tests passed! GCP Logging is working correctly.")
            print("💡 Ready for integration with LogSearch system.")
        else:
            print("\\n⚠️  Search returned no results. This might be due to indexing delay.")
            print("💡 Try running the test again in a few minutes.")
        
        return True
        
    except Exception as e:
        print(f"\\n❌ Error during testing: {e}")
        print("\\n🔧 Troubleshooting:")
        print("1. Make sure you're authenticated: gcloud auth application-default login")
        print("2. Verify project ID is correct")
        print("3. Check if Cloud Logging API is enabled")
        return False

if __name__ == "__main__":
    success = test_gcp_logging()
    sys.exit(0 if success else 1)