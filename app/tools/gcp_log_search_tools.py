# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Google Cloud Platform log search tools for LogSearch agent.
Provides search functionality for GCP Cloud Logging with cloud-ready authentication.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google.cloud import logging as cloud_logging
    from google.cloud.logging import DESCENDING, ASCENDING
    
    # Handle both relative and absolute imports
    try:
        from .gcp_auth import get_gcp_client, test_gcp_auth, get_deployment_info
    except ImportError:
        # Fallback for standalone execution
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from gcp_auth import get_gcp_client, test_gcp_auth, get_deployment_info
        
except ImportError as e:
    print(f"❌ Error: Required packages not installed: {e}")
    raise ImportError("google-cloud-logging and gcp_auth module required")

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Structured search result from GCP Logging."""
    timestamp: str
    severity: str
    message: str
    logger: str
    thread: str
    level: str
    raw_log: str
    log_name: str
    source_file: str
    line_number: Optional[int] = None
    labels: Optional[Dict[str, str]] = None
    resource_type: Optional[str] = None

@dataclass
class SearchQuery:
    """Structured search query for GCP Logging."""
    text: Optional[str] = None
    severity: Optional[str] = None
    logger: Optional[str] = None
    time_range: Optional[tuple] = None  # (start_time, end_time)
    max_results: int = 10
    log_name: Optional[str] = None

class GCPLogSearchTools:
    """GCP Cloud Logging search tools for LogSearch agent."""
    
    def __init__(self, project_id: Optional[str] = None, default_log_name: str = "cuttlefish_synthetic_logs"):
        """Initialize GCP log search tools."""
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project_id required")
        
        self.default_log_name = default_log_name
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the GCP logging client with cloud-ready authentication."""
        try:
            self.client = get_gcp_client(self.project_id)
            logger.info(f"GCP Log Search Tools initialized for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize GCP Logging client: {e}")
            raise
    
    def search_logs(self, query: Union[str, SearchQuery], **kwargs) -> List[SearchResult]:
        """
        Search logs using text query or structured SearchQuery.
        
        Args:
            query: Text string or SearchQuery object
            **kwargs: Additional parameters (max_results, log_name, etc.)
            
        Returns:
            List of SearchResult objects
        """
        # Handle different query types
        if isinstance(query, str):
            search_query = SearchQuery(text=query, **kwargs)
        elif isinstance(query, SearchQuery):
            # Override with any additional kwargs
            for key, value in kwargs.items():
                if hasattr(search_query, key):
                    setattr(search_query, key, value)
            search_query = query
        else:
            raise ValueError("Query must be string or SearchQuery object")
        
        # Build GCP Logging filter
        filter_parts = []
        
        # Log name filter
        log_name = search_query.log_name or self.default_log_name
        filter_parts.append(f'logName="projects/{self.project_id}/logs/{log_name}"')
        
        # Text search
        if search_query.text:
            # Search in message content
            filter_parts.append(f'jsonPayload.message:"{search_query.text}"')
        
        # Severity filter
        if search_query.severity:
            filter_parts.append(f'severity="{search_query.severity.upper()}"')
        
        # Logger filter
        if search_query.logger:
            filter_parts.append(f'jsonPayload.logger:"{search_query.logger}"')
        
        # Time range filter
        if search_query.time_range:
            start_time, end_time = search_query.time_range
            if isinstance(start_time, datetime):
                start_time = start_time.isoformat() + 'Z'
            if isinstance(end_time, datetime):
                end_time = end_time.isoformat() + 'Z'
            filter_parts.append(f'timestamp>="{start_time}"')
            filter_parts.append(f'timestamp<="{end_time}"')
        
        # Combine filters
        filter_query = ' AND '.join(filter_parts)
        
        return self._execute_search(filter_query, search_query.max_results)
    
    def search_by_error_type(self, error_type: str, max_results: int = 10) -> List[SearchResult]:
        """Search for logs containing specific error types."""
        query = SearchQuery(
            text=error_type,
            severity="ERROR",
            max_results=max_results
        )
        return self.search_logs(query)
    
    def search_recent_errors(self, hours: int = 72, max_results: int = 20) -> List[SearchResult]:
        """Search for recent error logs."""
        # Search for ERROR in message content instead of severity
        # Use expanded time range to handle timezone issues and cover more days
        start_time = datetime.now() - timedelta(hours=hours*2)  
        end_time = datetime.now() + timedelta(hours=12)  # Include future timestamps
        
        query = SearchQuery(
            text="ERROR",  # Search for ERROR in message content
            time_range=(start_time, end_time),
            max_results=max_results
        )
        return self.search_logs(query)
    
    def search_by_logger(self, logger_name: str, max_results: int = 10) -> List[SearchResult]:
        """Search for logs from specific logger."""
        query = SearchQuery(
            logger=logger_name,
            max_results=max_results
        )
        return self.search_logs(query)
    
    def search_time_range(self, start_time: datetime, end_time: datetime, 
                         severity: Optional[str] = None, max_results: int = 50) -> List[SearchResult]:
        """Search logs within a specific time range."""
        query = SearchQuery(
            time_range=(start_time, end_time),
            severity=severity,
            max_results=max_results
        )
        return self.search_logs(query)
    
    def get_log_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics for logs in the last N hours."""
        try:
            # Use a more inclusive time range to handle timezone issues
            start_time = datetime.now() - timedelta(hours=hours*2)  # Double the range
            end_time = datetime.now() + timedelta(hours=12)  # Include future timestamps
            
            # Get all logs first (without severity filtering)
            all_results = self.search_time_range(
                start_time, end_time, 
                severity=None, max_results=200
            )
            
            summary = {
                'time_range': f"Last {hours} hours (expanded for timezone tolerance)", 
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'by_level': {},  # Changed from severity to level
                'total_logs': len(all_results),
                'top_loggers': {},
                'top_errors': []
            }
            
            # Count by log level (from our parsed data, not GCP severity)
            for result in all_results:
                level = result.level or 'UNKNOWN'
                summary['by_level'][level] = summary['by_level'].get(level, 0) + 1
                
                # Count loggers
                logger_name = result.logger or 'unknown'
                summary['top_loggers'][logger_name] = summary['top_loggers'].get(logger_name, 0) + 1
            
            # Get error messages (search by text content)
            error_results = [r for r in all_results if 'ERROR' in (r.message or '') or r.level == 'ERROR']
            error_messages = {}
            for result in error_results:
                msg_key = (result.message or '')[:100]  # First 100 chars as key
                if msg_key:  # Only add non-empty messages
                    error_messages[msg_key] = error_messages.get(msg_key, 0) + 1
            
            summary['top_errors'] = sorted(
                error_messages.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get log summary: {e}")
            return {'error': str(e)}
    
    def _execute_search(self, filter_query: str, max_results: int) -> List[SearchResult]:
        """Execute the actual search and return structured results."""
        try:
            logger.debug(f"Executing search with filter: {filter_query}")
            
            entries = self.client.list_entries(
                filter_=filter_query,
                order_by=DESCENDING,
                max_results=max_results
            )
            
            results = []
            for entry in entries:
                try:
                    # Extract structured data
                    result_data = {
                        'timestamp': entry.timestamp.isoformat() if entry.timestamp else datetime.now().isoformat(),
                        'severity': entry.severity or 'INFO',
                        'log_name': entry.log_name or '',
                        'resource_type': entry.resource.type if entry.resource else None,
                        'labels': dict(entry.labels) if entry.labels else {}
                    }
                    
                    # Extract payload information
                    if hasattr(entry, 'payload') and hasattr(entry.payload, 'json_payload'):
                        payload = dict(entry.payload.json_payload)
                        result_data.update({
                            'message': payload.get('message', ''),
                            'logger': payload.get('logger', ''),
                            'thread': payload.get('thread', ''),
                            'level': payload.get('level', ''),
                            'raw_log': payload.get('raw_log', ''),
                            'source_file': payload.get('source_file', ''),
                            'line_number': payload.get('line_number')
                        })
                    else:
                        # Handle non-JSON payloads
                        payload_str = str(entry.payload) if entry.payload else ''
                        result_data.update({
                            'message': payload_str,
                            'logger': 'unknown',
                            'thread': 'unknown',
                            'level': entry.severity or 'INFO',
                            'raw_log': payload_str,
                            'source_file': 'unknown'
                        })
                    
                    # Create SearchResult object
                    search_result = SearchResult(**result_data)
                    results.append(search_result)
                    
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue
            
            logger.info(f"Search completed: {len(results)} results found")
            return results
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the GCP log search tools."""
        try:
            # Test authentication
            auth_result = test_gcp_auth(self.project_id)
            
            # Test simple search
            test_results = self.search_logs("test", max_results=1)
            
            # Get deployment info
            deployment_info = get_deployment_info()
            
            return {
                'status': 'healthy' if auth_result['status'] == 'success' else 'unhealthy',
                'project_id': self.project_id,
                'default_log_name': self.default_log_name,
                'authentication': auth_result,
                'deployment_info': deployment_info,
                'test_search_results': len(test_results),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Convenience functions for direct use
def search_logs(query: str, project_id: Optional[str] = None, max_results: int = 10) -> List[SearchResult]:
    """Quick search function."""
    tools = GCPLogSearchTools(project_id)
    return tools.search_logs(query, max_results=max_results)

def search_errors(error_text: str = "", hours: int = 24, project_id: Optional[str] = None) -> List[SearchResult]:
    """Quick error search function."""
    tools = GCPLogSearchTools(project_id)
    if error_text:
        return tools.search_by_error_type(error_text)
    else:
        return tools.search_recent_errors(hours=hours)

def get_log_health() -> Dict[str, Any]:
    """Quick health check function."""
    try:
        tools = GCPLogSearchTools()
        return tools.health_check()
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}

# Test functions
def test_search_functionality():
    """Test all search functionality."""
    print("🚀 Testing GCP Log Search Tools")
    print("=" * 60)
    
    try:
        # Initialize tools
        tools = GCPLogSearchTools()
        print(f"✅ Tools initialized for project: {tools.project_id}")
        
        # Test 1: Health check
        print(f"\n📋 TEST 1: Health Check")
        health = tools.health_check()
        print(f"Status: {health['status']}")
        if health['status'] == 'healthy':
            print(f"✅ Health check passed")
        else:
            print(f"❌ Health check failed: {health.get('error', 'Unknown error')}")
        
        # Test 2: Basic search
        print(f"\n📋 TEST 2: Basic Text Search")
        results = tools.search_logs("cache", max_results=5)
        print(f"Found {len(results)} results for 'cache'")
        if results:
            print(f"Sample result: {results[0].message[:100]}...")
        
        # Test 3: Error search
        print(f"\n📋 TEST 3: Error Search")
        error_results = tools.search_recent_errors(hours=24, max_results=5)
        print(f"Found {len(error_results)} error logs in last 24 hours")
        if error_results:
            print(f"Latest error: {error_results[0].message[:100]}...")
        
        # Test 4: Logger search
        print(f"\n📋 TEST 4: Logger Search")
        logger_results = tools.search_by_logger("com.cuttlefish", max_results=3)
        print(f"Found {len(logger_results)} results for 'com.cuttlefish' logger")
        
        # Test 5: Log summary
        print(f"\n📋 TEST 5: Log Summary")
        summary = tools.get_log_summary(hours=24)
        if 'error' not in summary:
            print(f"Total logs (24h): {summary['total_logs']}")
            print(f"By level: {summary['by_level']}")
            print(f"Top loggers: {list(summary['top_loggers'].keys())[:3]}")
            print(f"Error count: {len(summary['top_errors'])}")
        else:
            print(f"❌ Summary failed: {summary['error']}")
        
        print(f"\n🎉 All tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main function for testing the GCP log search tools."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            success = test_search_functionality()
            sys.exit(0 if success else 1)
        
        elif command == "health":
            health = get_log_health()
            print(json.dumps(health, indent=2))
            sys.exit(0 if health['status'] == 'healthy' else 1)
        
        elif command == "search":
            if len(sys.argv) < 3:
                print("Usage: python gcp_log_search_tools.py search <query>")
                sys.exit(1)
            
            query = sys.argv[2]
            results = search_logs(query, max_results=10)
            
            print(f"Found {len(results)} results for '{query}':")
            for i, result in enumerate(results[:5], 1):
                print(f"{i}. [{result.severity}] {result.timestamp}")
                print(f"   {result.message[:100]}...")
                print()
            
        elif command == "errors":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            results = search_errors(hours=hours)
            
            print(f"Found {len(results)} errors in last {hours} hours:")
            for i, result in enumerate(results[:5], 1):
                print(f"{i}. [{result.level}] {result.timestamp}")
                print(f"   Logger: {result.logger}")
                print(f"   {result.message[:100]}...")
                print()
        
        else:
            print(f"Unknown command: {command}")
            print("Available commands: test, health, search <query>, errors [hours]")
            sys.exit(1)
    
    else:
        print("GCP Log Search Tools")
        print("Usage:")
        print("  python gcp_log_search_tools.py test        # Run all tests")
        print("  python gcp_log_search_tools.py health      # Check health")
        print("  python gcp_log_search_tools.py search <query>  # Search logs")
        print("  python gcp_log_search_tools.py errors [hours]  # Get recent errors")

if __name__ == "__main__":
    main()