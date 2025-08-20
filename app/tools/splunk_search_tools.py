#!/usr/bin/env python3
"""
Splunk search tools for Cuttlefish4 multi-agent system.
Provides Splunk Cloud REST API capabilities for log analysis and search.
"""

import os
import json
import logging
import requests
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, skip loading .env file
    pass

logger = logging.getLogger(__name__)

class SplunkSearchTools:
    """Splunk search tools using Splunk Cloud REST API for log analysis."""
    
    def __init__(self):
        """Initialize Splunk search tools."""
        self.splunk_host = os.environ.get('SPLUNK_HOST')  # e.g., https://your-instance.splunkcloud.com
        self.splunk_token = os.environ.get('SPLUNK_TOKEN')  # Authentication token
        self.splunk_username = os.environ.get('SPLUNK_USERNAME')  # Alternative: username/password
        self.splunk_password = os.environ.get('SPLUNK_PASSWORD')
        self.index_name = os.environ.get('SPLUNK_INDEX', 'cuttlefish')
        
        # Validate configuration
        if not self.splunk_host:
            logger.warning("SPLUNK_HOST not found in environment variables")
            
        if not (self.splunk_token or (self.splunk_username and self.splunk_password)):
            logger.warning("Neither SPLUNK_TOKEN nor SPLUNK_USERNAME/SPLUNK_PASSWORD found")
            
        # Setup session
        self.session = requests.Session()
        self._setup_auth()
        
        # API endpoints
        self.search_endpoint = f"{self.splunk_host}/services/search/jobs"
        self.results_endpoint_template = f"{self.splunk_host}/services/search/jobs/{{}}/results"
        
        logger.info("✅ Splunk search tools initialized")
    
    def _setup_auth(self):
        """Setup authentication for Splunk API."""
        if self.splunk_token:
            # Token-based authentication
            self.session.headers.update({
                'Authorization': f'Bearer {self.splunk_token}',
                'Content-Type': 'application/json'
            })
        elif self.splunk_username and self.splunk_password:
            # Basic authentication
            credentials = f"{self.splunk_username}:{self.splunk_password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.session.headers.update({
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            })
        else:
            logger.error("No valid authentication method configured")
    
    def test_connection(self) -> bool:
        """Test connection to Splunk and ingest a single test log entry."""
        try:
            if not self.splunk_host:
                logger.error("No Splunk host configured")
                return False
            
            # Test with a simple search query
            test_query = f'search index={self.index_name} | head 1'
            
            logger.info("Testing Splunk connection with simple query...")
            
            # Create search job
            search_data = {
                'search': test_query,
                'earliest_time': '-24h',
                'latest_time': 'now'
            }
            
            response = self.session.post(self.search_endpoint, data=search_data, timeout=30)
            
            if response.status_code == 201:
                logger.info("✅ Splunk connection test successful")
                
                # Test log ingestion
                return self._test_log_ingestion()
            else:
                logger.error(f"Splunk connection test failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Splunk connection test failed: {e}")
            return False
    
    def _test_log_ingestion(self) -> bool:
        """Test ingesting a single log entry."""
        try:
            # Create test log entry
            test_log = {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'logger': 'com.cuttlefish.test.ConnectionTest',
                'message': 'Splunk connection test successful',
                'thread': 'main',
                'source': 'cuttlefish_connection_test'
            }
            
            # Format as Log4j-style entry
            log_entry = self._format_log4j_entry(test_log)
            
            # Send to Splunk HTTP Event Collector endpoint
            hec_endpoint = f"{self.splunk_host}/services/collector"
            
            hec_data = {
                'time': int(datetime.now().timestamp()),
                'index': self.index_name,
                'source': 'cuttlefish_test',
                'sourcetype': 'java_log4j',
                'event': log_entry
            }
            
            # Use different headers for HEC
            hec_headers = {
                'Authorization': f'Splunk {self.splunk_token}' if self.splunk_token else self.session.headers['Authorization'],
                'Content-Type': 'application/json'
            }
            
            response = requests.post(hec_endpoint, 
                                   headers=hec_headers,
                                   data=json.dumps(hec_data),
                                   timeout=30)
            
            if response.status_code == 200:
                logger.info("✅ Test log ingestion successful")
                return True
            else:
                logger.error(f"Test log ingestion failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Test log ingestion failed: {e}")
            return False
    
    def _format_log4j_entry(self, log_data: Dict[str, Any]) -> str:
        """Format log data as Log4j entry."""
        timestamp = log_data.get('timestamp', datetime.now().isoformat())
        level = log_data.get('level', 'INFO')
        logger_name = log_data.get('logger', 'com.cuttlefish.Application')
        message = log_data.get('message', '')
        thread = log_data.get('thread', 'main')
        
        # Log4j format: timestamp [thread] level logger - message
        return f"{timestamp} [{thread}] {level} {logger_name} - {message}"
    
    def search_logs(self, query: str, time_range: str = '-1h', max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search Splunk logs using SPL (Search Processing Language).
        
        Args:
            query: SPL search query
            time_range: Time range for search (e.g., '-1h', '-24h', '-7d')
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        if not self.splunk_host:
            logger.error("Splunk not configured - check SPLUNK_HOST")
            return []
        
        try:
            logger.info(f"Searching Splunk logs: '{query[:50]}...' (time_range={time_range})")
            
            # Prepare full search query
            if not query.startswith('search'):
                full_query = f'search index={self.index_name} {query} | head {max_results}'
            else:
                full_query = f'{query} | head {max_results}'
            
            # Create search job
            search_data = {
                'search': full_query,
                'earliest_time': time_range,
                'latest_time': 'now',
                'output_mode': 'json'
            }
            
            response = self.session.post(self.search_endpoint, data=search_data, timeout=30)
            
            if response.status_code != 201:
                logger.error(f"Failed to create search job: {response.status_code} - {response.text}")
                return []
            
            # Extract job ID from response
            job_id = self._extract_job_id(response.text)
            if not job_id:
                logger.error("Failed to extract job ID from search response")
                return []
            
            # Wait for job completion and get results
            results = self._get_search_results(job_id)
            
            logger.info(f"Splunk search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Splunk search failed: {e}")
            return []
    
    def search_exceptions(self, exception_types: List[str] = None, time_range: str = '-1h') -> List[Dict[str, Any]]:
        """
        Search for specific exception types in logs.
        
        Args:
            exception_types: List of exception types to search for
            time_range: Time range for search
            
        Returns:
            List of exception log entries
        """
        if exception_types is None:
            exception_types = [
                'CertificateExpiredException',
                'HttpServerErrorException',
                'DiskSpaceExceededException', 
                'DeadLetterQueueException'
            ]
        
        # Build search query for exceptions
        exception_filter = ' OR '.join([f'"{exc}"' for exc in exception_types])
        query = f'level=ERROR AND ({exception_filter})'
        
        return self.search_logs(query, time_range, max_results=50)
    
    def search_production_issues(self, error_context: str, time_range: str = '-1h') -> List[Dict[str, Any]]:
        """
        Search for production issues based on error context.
        
        Args:
            error_context: Error message or context to search for
            time_range: Time range for search
            
        Returns:
            List of related log entries
        """
        # Search for ERROR level logs with the error context
        query = f'level=ERROR "{error_context}"'
        error_logs = self.search_logs(query, time_range, max_results=20)
        
        # Also search for WARN level logs that might be related
        warn_query = f'level=WARN "{error_context}"'
        warn_logs = self.search_logs(warn_query, time_range, max_results=10)
        
        # Combine results
        all_logs = error_logs + warn_logs
        
        # Sort by timestamp if available
        try:
            all_logs.sort(key=lambda x: x.get('_time', ''), reverse=True)
        except:
            pass  # If sorting fails, just return unsorted
            
        return all_logs[:30]  # Limit to 30 total results
    
    def _extract_job_id(self, response_text: str) -> Optional[str]:
        """Extract job ID from Splunk search response."""
        try:
            # Response is typically XML, extract job ID
            import re
            match = re.search(r'<sid>([^<]+)</sid>', response_text)
            if match:
                return match.group(1)
            
            # Alternative: look for job ID in different format
            match = re.search(r'"sid":\s*"([^"]+)"', response_text)
            if match:
                return match.group(1)
                
        except Exception as e:
            logger.error(f"Failed to extract job ID: {e}")
        
        return None
    
    def _get_search_results(self, job_id: str, timeout: int = 30) -> List[Dict[str, Any]]:
        """Get results from a Splunk search job."""
        try:
            # Wait for job completion
            status_url = f"{self.splunk_host}/services/search/jobs/{job_id}"
            
            for _ in range(timeout):  # Wait up to timeout seconds
                status_response = self.session.get(status_url + "?output_mode=json")
                
                if status_response.status_code == 200:
                    # Check if job is done (this part may need adjustment based on actual Splunk API response)
                    break
                
                import time
                time.sleep(1)
            
            # Get results
            results_url = self.results_endpoint_template.format(job_id)
            results_response = self.session.get(results_url + "?output_mode=json")
            
            if results_response.status_code == 200:
                results_data = results_response.json()
                
                # Extract results (format may vary based on Splunk version)
                if 'results' in results_data:
                    return results_data['results']
                elif isinstance(results_data, list):
                    return results_data
                else:
                    logger.warning(f"Unexpected results format: {type(results_data)}")
                    return []
            else:
                logger.error(f"Failed to get search results: {results_response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get search results: {e}")
            return []


# Convenience function for creating tools instance
def get_splunk_search_tools() -> SplunkSearchTools:
    """Get Splunk search tools instance."""
    return SplunkSearchTools()


# For testing
if __name__ == "__main__":
    # Test Splunk search tools
    print("🧪 Testing Splunk Search Tools")
    print("=" * 40)
    
    # Check environment variables
    splunk_host = os.environ.get('SPLUNK_HOST')
    splunk_token = os.environ.get('SPLUNK_TOKEN')
    
    if not splunk_host:
        print("❌ SPLUNK_HOST not found in environment variables")
        print("   Set it with: export SPLUNK_HOST=https://your-instance.splunkcloud.com")
        exit(1)
    
    if not splunk_token:
        print("❌ SPLUNK_TOKEN not found in environment variables")
        print("   Set it with: export SPLUNK_TOKEN=your_token_here")
        exit(1)
    
    print(f"✅ SPLUNK_HOST found: {splunk_host}")
    print(f"✅ SPLUNK_TOKEN found: {splunk_token[:8]}...")
    
    tools = get_splunk_search_tools()
    
    # Test connection and ingestion
    print("\n🔗 Testing connection and log ingestion...")
    if tools.test_connection():
        print("✅ Splunk connection and test ingestion successful")
        
        # Test search functionality
        print("\n🔍 Testing search functionality...")
        results = tools.search_logs("level=INFO", time_range="-1h", max_results=5)
        
        if results:
            print(f"   ✅ {len(results)} search results retrieved")
            for i, result in enumerate(results, 1):
                timestamp = result.get('_time', 'No timestamp')
                raw = result.get('_raw', 'No raw data')[:100]
                print(f"   {i}. {timestamp}: {raw}...")
        else:
            print(f"   ⚠️ No search results found (this may be normal if index is empty)")
        
        print(f"\n🎉 Splunk search tools are working!")
        
    else:
        print("❌ Splunk connection or test ingestion failed")
        print("   Check your SPLUNK_HOST, SPLUNK_TOKEN, and network connectivity")
    
    print("=" * 40)