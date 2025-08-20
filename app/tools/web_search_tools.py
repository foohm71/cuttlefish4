#!/usr/bin/env python3
"""
Web search tools for Cuttlefish4 multi-agent system.
Provides Tavily-powered web search capabilities for production incident research.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSearchTools:
    """Web search tools using Tavily API for real-time information retrieval."""
    
    def __init__(self):
        """Initialize web search tools."""
        self.tavily_api_key = os.environ.get('TAVILY_API_KEY')
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not found in environment variables")
            self.tavily_tool = None
        else:
            try:
                from langchain_community.tools.tavily_search import TavilySearchResults
                self.tavily_tool = TavilySearchResults(
                    max_results=5,
                    api_key=self.tavily_api_key
                )
                logger.info("✅ Tavily web search tool initialized")
            except ImportError as e:
                logger.error(f"Failed to import TavilySearchResults: {e}")
                self.tavily_tool = None
    
    def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform web search using Tavily API.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with content, URL, and metadata
        """
        if not self.tavily_tool:
            logger.error("Tavily tool not available - check TAVILY_API_KEY")
            return []
        
        try:
            logger.info(f"Web search for: '{query[:50]}...' (max_results={max_results})")
            
            # Use Tavily tool to perform search
            results = self.tavily_tool.invoke(query)
            
            # Format results consistently
            formatted_results = []
            if isinstance(results, list):
                for result in results[:max_results]:
                    if isinstance(result, dict):
                        formatted_results.append({
                            'content': result.get('content', ''),
                            'url': result.get('url', ''),
                            'title': result.get('title', ''),
                            'score': result.get('score', 0.5),
                            'search_type': 'web_search',
                            'source': 'tavily',
                            'timestamp': datetime.now().isoformat()
                        })
            
            logger.info(f"Web search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def search_status_pages(self, service_name: str) -> List[Dict[str, Any]]:
        """
        Search for service status pages and downtime information.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            List of status page results
        """
        status_queries = [
            f"{service_name} status page",
            f"{service_name} downdetector",
            f"{service_name} outage status",
            f"is {service_name} down"
        ]
        
        all_results = []
        for query in status_queries:
            results = self.web_search(query, max_results=3)
            for result in results:
                result['search_type'] = 'status_check'
                result['service'] = service_name
            all_results.extend(results)
        
        return all_results
    
    def search_production_issues(self, error_message: str, technology: str = None) -> List[Dict[str, Any]]:
        """
        Search for production issues and solutions.
        
        Args:
            error_message: Error message or symptom
            technology: Specific technology (e.g., "Java", "Spring", "HBase")
            
        Returns:
            List of search results related to production issues
        """
        search_queries = [
            f'"{error_message}" production issue solution',
            f"{error_message} fix troubleshooting"
        ]
        
        if technology:
            search_queries.extend([
                f"{technology} {error_message} solution",
                f"{technology} production issue {error_message}"
            ])
        
        all_results = []
        for query in search_queries[:3]:  # Limit to 3 queries to avoid rate limits
            results = self.web_search(query, max_results=2)
            for result in results:
                result['search_type'] = 'production_issue'
                result['error_context'] = error_message
                if technology:
                    result['technology'] = technology
            all_results.extend(results)
        
        return all_results
    
    def test_connection(self) -> bool:
        """Test if web search is working."""
        try:
            if not self.tavily_tool:
                return False
            
            # Perform a simple test search
            results = self.web_search("test", max_results=1)
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Web search connection test failed: {e}")
            return False

# Convenience function for creating tools instance
def get_web_search_tools() -> WebSearchTools:
    """Get web search tools instance."""
    return WebSearchTools()

# For testing
if __name__ == "__main__":
    # Test web search tools
    print("🧪 Testing Web Search Tools")
    print("=" * 40)
    
    # Check API key
    tavily_key = os.environ.get('TAVILY_API_KEY')
    if not tavily_key:
        print("❌ TAVILY_API_KEY not found in environment variables")
        print("   Set it with: export TAVILY_API_KEY=your_key_here")
        exit(1)
    
    print(f"✅ TAVILY_API_KEY found: {tavily_key[:8]}...")
    
    tools = get_web_search_tools()
    
    # Test connection
    print("\n🔗 Testing connection...")
    if tools.test_connection():
        print("✅ Web search connection successful")
        
        # Test different search types
        test_cases = [
            ("GitHub status", "Basic search test"),
            ("AWS outage", "Status page search"),
            ("Docker Hub down", "Service status check")
        ]
        
        for query, description in test_cases:
            print(f"\n🔍 {description}: '{query}'")
            results = tools.web_search(query, max_results=2)
            
            if results:
                print(f"   ✅ {len(results)} results retrieved")
                for i, result in enumerate(results, 1):
                    title = result.get('title', 'No title')[:40]
                    url = result.get('url', 'No URL')[:50]
                    content_len = len(result.get('content', ''))
                    print(f"   {i}. {title}...")
                    print(f"      URL: {url}...")
                    print(f"      Content: {content_len} chars")
            else:
                print(f"   ❌ No results for '{query}'")
        
        print(f"\n🎉 Web search tools are working!")
        
    else:
        print("❌ Web search connection failed")
        print("   Check your TAVILY_API_KEY and internet connection")
    
    print("=" * 40)