#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
LogSearch Agent for Cuttlefish4 multi-agent system.
Handles log searches for production incident analysis and troubleshooting.
Supports both Splunk and Google Cloud Logging backends.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from langchain_openai import ChatOpenAI
    from .common import AgentState, measure_performance, format_sources
except ImportError:
    from langchain_openai import ChatOpenAI
    from common import AgentState, measure_performance, format_sources

# Import GCP backend tools only
try:
    from ..tools.gcp_log_search_tools import GCPLogSearchTools, SearchQuery, SearchResult
except ImportError:
    from app.tools.gcp_log_search_tools import GCPLogSearchTools, SearchQuery, SearchResult

logger = logging.getLogger(__name__)

class LogSearchAgent:
    """
    LogSearch Agent that performs intelligent log searches for production incidents.
    Uses GPT-4o-mini model to assess queries and perform multiple refined searches.
    Uses Google Cloud Logging backend for log analysis.
    """
    
    def __init__(self, llm: ChatOpenAI, max_searches: int = 5):
        """
        Initialize LogSearch agent with GCP backend.
        
        Args:
            llm: Language model (should be GPT-4o-mini for cost efficiency)
            max_searches: Maximum number of search refinements to perform
        """
        self.llm = llm
        self.max_searches = max_searches
        self.backend = 'gcp'
        
        # Initialize GCP search tools
        try:
            self.search_tools = GCPLogSearchTools()
            logger.info(f"✅ LogSearch Agent initialized with GCP backend (max_searches={max_searches})")
        except Exception as e:
            logger.warning(f"⚠️  GCP LogSearch not available: {e}")
            logger.info("LogSearch will be disabled until GCP credentials are configured")
            self.search_tools = None
    
    
    def process(self, state: AgentState) -> AgentState:
        """
        Process query through LogSearch agent.
        
        Args:
            state: Current agent state with query and metadata
            
        Returns:
            Updated state with log search results
        """
        start_time = datetime.now()
        query = state['query']
        production_incident = state.get('production_incident', False)
        
        logger.info(f"LogSearch Agent processing: '{query[:50]}...'")
        
        # Check if LogSearch is available
        if self.search_tools is None:
            logger.warning("LogSearch not available - GCP credentials not configured")
            state['retrieval_results'] = []
            state['retrieval_method'] = 'logsearch_unavailable'
            state['retrieval_metadata'] = {
                'total_results': 0,
                'search_time': 0,
                'message': 'LogSearch unavailable - GCP authentication required'
            }
            return state
        
        try:
            # Step 1: Assess query and determine search strategy
            search_strategy = self._assess_query(query, production_incident)
            
            logger.info(f"Search strategy: {search_strategy['strategy']} with {len(search_strategy['searches'])} queries")
            
            # Step 2: Execute searches
            all_results = []
            searches_performed = 0
            
            for i, search_query in enumerate(search_strategy['searches'][:self.max_searches], 1):
                logger.info(f"Executing search {i}/{len(search_strategy['searches'])}: '{search_query['query'][:50]}...'")
                
                try:
                    # Execute GCP search
                    results = self._execute_gcp_search(search_query)
                    
                    # Format results for consistency
                    formatted_results = self._format_search_results(results, search_query['type'])
                    all_results.extend(formatted_results)
                    searches_performed += 1
                    
                except Exception as e:
                    logger.error(f"Search {i} failed: {e}")
                    continue
            
            logger.info(f"Total log search results: {len(all_results)}")
            
            # Step 3: Remove duplicates and limit results
            unique_results = self._deduplicate_results(all_results)
            limited_results = unique_results[:10]  # Limit to top 10 results
            
            logger.info(f"LogSearch Agent completed: {len(limited_results)} results")
            
            # Update state
            state['retrieved_contexts'] = limited_results
            state['retrieval_method'] = 'LogSearch'
            state['retrieval_metadata'] = {
                'agent': 'LogSearch',
                'num_results': len(limited_results),
                'processing_time': measure_performance(start_time),
                'method_type': 'log_search',
                'searches_performed': searches_performed,
                'search_strategy': search_strategy['strategy'],
                'production_incident': production_incident,
                'backend': 'gcp',
                'source': 'gcp_logging'
            }
            
            return state
            
        except Exception as e:
            logger.error(f"LogSearch Agent error: {e}")
            
            # Return state with error information
            state['retrieved_contexts'] = []
            state['retrieval_method'] = 'LogSearch_Failed'
            state['retrieval_metadata'] = {
                'agent': 'LogSearch',
                'num_results': 0,
                'processing_time': measure_performance(start_time),
                'method_type': 'log_search_error',
                'error': str(e)
            }
            
            return state
    
    def _execute_gcp_search(self, search_query: Dict[str, Any]) -> List[SearchResult]:
        """Execute search using GCP Cloud Logging backend."""
        query_type = search_query['type']
        query_text = search_query['query']
        max_results = search_query.get('max_results', 50)
        time_range = search_query.get('time_range', '-1h')
        
        # Convert time range to datetime objects
        start_time, end_time = self._parse_time_range(time_range)
        
        if query_type == 'exception_search':
            # Search for exceptions by looking for ERROR level logs and exception types
            exception_types = search_query.get('exception_types', [])
            if exception_types:
                # Search for specific exception types
                results = []
                for exc_type in exception_types:
                    exc_results = self.search_tools.search_by_error_type(exc_type, max_results=max_results//len(exception_types))
                    results.extend(exc_results)
                return results[:max_results]
            else:
                # General error search
                return self.search_tools.search_recent_errors(hours=self._time_range_to_hours(time_range), max_results=max_results)
        
        elif query_type == 'production_issue':
            # Search for production issues in recent time range
            search_query_obj = SearchQuery(
                text=query_text,
                time_range=(start_time, end_time) if start_time and end_time else None,
                max_results=max_results
            )
            return self.search_tools.search_logs(search_query_obj)
        
        else:
            # General search
            search_query_obj = SearchQuery(
                text=query_text,
                time_range=(start_time, end_time) if start_time and end_time else None,
                max_results=max_results
            )
            return self.search_tools.search_logs(search_query_obj)
    
    
    def _parse_time_range(self, time_range: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse time range string into datetime objects."""
        try:
            if time_range.startswith('-'):
                # Relative time (e.g., '-1h', '-24h')
                if time_range.endswith('h'):
                    hours = int(time_range[1:-1])
                    start_time = datetime.now() - timedelta(hours=hours*2)  # Expand for timezone tolerance
                    end_time = datetime.now() + timedelta(hours=12)  # Include future timestamps
                    return start_time, end_time
                elif time_range.endswith('d'):
                    days = int(time_range[1:-1])
                    start_time = datetime.now() - timedelta(days=days*2)
                    end_time = datetime.now() + timedelta(hours=12)
                    return start_time, end_time
            
            # If we can't parse, return None to search all time
            return None, None
        except:
            return None, None
    
    def _time_range_to_hours(self, time_range: str) -> int:
        """Convert time range string to hours for GCP search."""
        try:
            if time_range.startswith('-') and time_range.endswith('h'):
                return int(time_range[1:-1])
            elif time_range.startswith('-') and time_range.endswith('d'):
                return int(time_range[1:-1]) * 24
            else:
                return 24  # Default
        except:
            return 24
    
    def _assess_query(self, query: str, production_incident: bool) -> Dict[str, Any]:
        """
        Use LLM to assess the query and determine optimal log search strategy.
        
        Args:
            query: User query
            production_incident: Whether this is a production incident
            
        Returns:
            Dictionary with search strategy and refined queries
        """
        assessment_prompt = f"""You are a log analysis expert. Analyze the following query and determine the best log search strategy.

Query: "{query}"
Production Incident: {production_incident}

Available log search strategies:
1. "exception_search" - Search for specific Java exceptions (CertificateExpiredException, HttpServerErrorException, DiskSpaceExceededException, DeadLetterQueueException)
2. "production_issue" - Search for production issues based on error context
3. "general_search" - General log search with specific terms
4. "time_range_analysis" - Focus on specific time ranges for incident analysis

For production incidents, prioritize exception searches and recent time ranges.
Generate 1-3 specific log search queries based on the user's request.

Respond with JSON in this format:
{{
    "strategy": "strategy_name",
    "reasoning": "explanation of why this strategy was chosen",
    "searches": [
        {{
            "query": "specific search query or terms",
            "type": "search_type",
            "time_range": "-1h",
            "exception_types": ["ExceptionType1", "ExceptionType2"] (only for exception_search),
            "max_results": 50
        }}
    ]
}}"""

        try:
            response = self.llm.invoke(assessment_prompt)
            
            # Parse the response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                strategy_data = json.loads(json_match.group())
                
                # Validate and set defaults
                if 'searches' not in strategy_data:
                    strategy_data['searches'] = []
                
                # Ensure each search has required fields
                for search in strategy_data['searches']:
                    search.setdefault('time_range', '-72h' if production_incident else '-168h')  # 3 days for prod, 7 days for non-prod
                    search.setdefault('max_results', 30 if production_incident else 50)
                    search.setdefault('type', 'general_search')
                
                return strategy_data
            
            # Fallback if JSON parsing fails
            logger.warning("Failed to parse LLM response, using fallback strategy")
            
        except Exception as e:
            logger.error(f"Error in query assessment: {e}")
        
        # Fallback strategy
        return self._create_fallback_strategy(query, production_incident)
    
    def _create_fallback_strategy(self, query: str, production_incident: bool) -> Dict[str, Any]:
        """Create a fallback search strategy when LLM assessment fails."""
        
        # Check for common error indicators in query
        error_indicators = [
            'error', 'exception', 'failed', 'timeout', 'connection', 'certificate',
            'disk space', 'memory', 'dead letter', '500', '502', '503', '504'
        ]
        
        has_error_indicators = any(indicator in query.lower() for indicator in error_indicators)
        
        if production_incident and has_error_indicators:
            # Production incident with error indicators - search for exceptions
            return {
                'strategy': 'production_exception_search',
                'reasoning': 'Production incident with error indicators detected',
                'searches': [
                    {
                        'query': query,
                        'type': 'exception_search',
                        'time_range': '-72h',  # 3 days for production incidents
                        'max_results': 30
                    },
                    {
                        'query': f'ERROR {query}',
                        'type': 'production_issue',
                        'time_range': '-72h',  # 3 days for production incidents
                        'max_results': 20
                    }
                ]
            }
        elif production_incident:
            # Production incident without clear error indicators
            return {
                'strategy': 'production_general_search',
                'reasoning': 'Production incident requiring broad log analysis',
                'searches': [
                    {
                        'query': f'ERROR OR WARN {query}',
                        'type': 'general_search',
                        'time_range': '-72h',  # 3 days for production incidents
                        'max_results': 30
                    }
                ]
            }
        else:
            # Non-production query
            return {
                'strategy': 'general_analysis',
                'reasoning': 'General log analysis query',
                'searches': [
                    {
                        'query': query,
                        'type': 'general_search',
                        'time_range': '-168h',  # 7 days for non-production queries
                        'max_results': 50
                    }
                ]
            }
    
    def _format_search_results(self, results, search_type: str) -> List[Dict[str, Any]]:
        """
        Format GCP search results into consistent format for the agent system.
        
        Args:
            results: GCP SearchResult objects
            search_type: Type of search that was performed
            
        Returns:
            List of formatted results
        """
        formatted_results = []
        
        for result in results:
            # GCP SearchResult object
            raw_log = result.raw_log or result.message or str(result)
            timestamp = result.timestamp
            source = result.source_file or 'gcp_logging'
            level = result.level or 'UNKNOWN'
            logger_name = result.logger or 'unknown'
            
            formatted_result = {
                'content': raw_log,
                'metadata': {
                    'timestamp': timestamp,
                    'source': source,
                    'level': level,
                    'logger': logger_name,
                    'thread': result.thread or 'unknown',
                    'search_type': search_type,
                    'backend': 'gcp_logging',
                    'severity': result.severity,
                    'log_name': result.log_name,
                    'resource_type': result.resource_type
                },
                'source': 'log_gcp',
                'score': self._calculate_relevance_score(raw_log, search_type, level)
            }
            
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _extract_log_level(self, log_line: str) -> str:
        """Extract log level from raw log line."""
        import re
        
        # Look for common log levels
        level_pattern = r'\b(TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\b'
        match = re.search(level_pattern, log_line)
        
        if match:
            return match.group(1)
        
        return 'UNKNOWN'
    
    def _extract_logger(self, log_line: str) -> str:
        """Extract logger name from raw log line."""
        import re
        
        # Look for Java package/class patterns
        logger_pattern = r'\b([a-z]+(?:\.[a-z][a-zA-Z0-9]*)*)\b'
        matches = re.findall(logger_pattern, log_line)
        
        # Find the most likely logger (longest match that looks like a package)
        for match in sorted(matches, key=len, reverse=True):
            if '.' in match and len(match.split('.')) >= 2:
                return match
        
        return 'unknown'
    
    def _calculate_relevance_score(self, log_line: str, search_type: str, level: str) -> float:
        """Calculate relevance score for a log entry."""
        base_score = 0.5
        
        # Boost score based on log level
        level_boosts = {
            'ERROR': 0.3,
            'WARN': 0.2,
            'FATAL': 0.4,
            'INFO': 0.1,
            'DEBUG': 0.0,
            'TRACE': 0.0
        }
        
        score = base_score + level_boosts.get(level, 0.0)
        
        # Boost score based on search type
        if search_type == 'exception_search' and any(exc in log_line for exc in [
            'Exception', 'Error', 'Failed', 'Timeout'
        ]):
            score += 0.2
        
        # Boost for production issue indicators
        if search_type == 'production_issue' and any(indicator in log_line.lower() for indicator in [
            'certificate', 'expired', '500', '502', '503', '504', 'disk space', 'dead letter'
        ]):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate log entries based on content similarity."""
        if not results:
            return results
        
        unique_results = []
        seen_content = set()
        
        for result in results:
            content = result.get('content', '')
            
            # Create a simple hash of the content for deduplication
            # Remove timestamps and other variable parts for better matching
            import re
            normalized_content = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '', content)
            normalized_content = re.sub(r'\d+', 'NUM', normalized_content)
            
            content_hash = hash(normalized_content.strip())
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        # Sort by relevance score (descending)
        unique_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        
        return unique_results