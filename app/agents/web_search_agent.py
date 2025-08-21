#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
WebSearch Agent for Cuttlefish4 multi-agent system.
Handles web searches for production incident research and real-time information.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from langchain_openai import ChatOpenAI
    from .common import AgentState, measure_performance, format_sources
except ImportError:
    from langchain_openai import ChatOpenAI
    from common import AgentState, measure_performance, format_sources

try:
    from ..tools.web_search_tools import WebSearchTools
except ImportError:
    from app.tools.web_search_tools import WebSearchTools

logger = logging.getLogger(__name__)

class WebSearchAgent:
    """
    Web Search Agent that performs intelligent web searches for production incidents.
    Uses GPT-4o model to assess queries and perform multiple refined searches.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, max_searches: int = 5):
        """
        Initialize WebSearch Agent.
        
        Args:
            llm: Language model for query assessment and refinement
            max_searches: Maximum number of web searches to perform
        """
        self.llm = llm or ChatOpenAI(model="gpt-4o", temperature=0)
        self.max_searches = max_searches
        self.web_search_tools = WebSearchTools()
        
        logger.info(f"✅ WebSearch Agent initialized (max_searches={max_searches})")
    
    def process(self, state: AgentState) -> AgentState:
        """
        Process query through web search agent.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with web search results
        """
        start_time = datetime.now()
        
        try:
            query = state['query']
            production_incident = state.get('production_incident', False)
            user_can_wait = state.get('user_can_wait', True)
            
            logger.info(f"WebSearch Agent processing: '{query[:50]}...'")
            
            # Assess query and generate search strategy
            search_strategy = self._assess_query_and_plan_searches(
                query, production_incident, user_can_wait
            )
            
            # Perform web searches based on strategy
            all_results = self._execute_search_strategy(search_strategy)
            
            # Format results for output
            retrieved_contexts = self._format_web_results(all_results)
            
            # Update state
            state['retrieved_contexts'] = retrieved_contexts
            state['retrieval_method'] = 'WebSearch'
            state['retrieval_metadata'] = {
                'agent': 'WebSearch',
                'num_results': len(retrieved_contexts),
                'processing_time': measure_performance(start_time),
                'method_type': 'web_search',
                'searches_performed': len(search_strategy.get('queries', [])),
                'max_searches': self.max_searches,
                'production_incident': production_incident
            }
            
            logger.info(f"WebSearch Agent completed: {len(retrieved_contexts)} results")
            return state
            
        except Exception as e:
            logger.error(f"WebSearch Agent error: {e}")
            # Return empty results on error
            state['retrieved_contexts'] = []
            state['retrieval_method'] = 'WebSearch_Failed'
            state['retrieval_metadata'] = {
                'agent': 'WebSearch',
                'num_results': 0,
                'processing_time': measure_performance(start_time),
                'method_type': 'web_search_error',
                'error': str(e)
            }
            return state
    
    def _assess_query_and_plan_searches(
        self, 
        query: str, 
        production_incident: bool = False, 
        user_can_wait: bool = True
    ) -> Dict[str, Any]:
        """
        Use GPT-4o to assess the query and plan search strategy.
        
        Args:
            query: User query
            production_incident: Whether this is a production incident
            user_can_wait: Whether comprehensive search is acceptable
            
        Returns:
            Search strategy with queries and priorities
        """
        try:
            # Create assessment prompt
            assessment_prompt = f"""
            Analyze this query and create a web search strategy:
            
            Query: "{query}"
            Production Incident: {production_incident}
            User Can Wait: {user_can_wait}
            Max Searches: {self.max_searches}
            
            Based on the query, determine:
            1. What type of information is needed (status pages, error solutions, general info)
            2. Key search terms and variations
            3. Specific services/technologies mentioned
            4. Priority order for searches
            
            Generate up to {self.max_searches} focused search queries that would help answer this query.
            For production incidents, prioritize status pages and known issue tracking.
            
            Return a JSON-like response with:
            - query_type: "status_check", "error_troubleshooting", "general_research"
            - technologies: list of technologies mentioned
            - services: list of services mentioned  
            - queries: list of specific search queries to perform
            - priority: "urgent" if production incident, "normal" otherwise
            """
            
            response = self.llm.invoke(assessment_prompt)
            strategy_text = response.content
            
            # Parse the strategy (simplified - in production might use structured output)
            strategy = self._parse_strategy_response(strategy_text, query, production_incident)
            
            logger.info(f"Search strategy: {strategy.get('query_type', 'unknown')} with {len(strategy.get('queries', []))} queries")
            return strategy
            
        except Exception as e:
            logger.error(f"Query assessment failed: {e}")
            # Fallback to simple strategy
            return self._create_fallback_strategy(query, production_incident)
    
    def _parse_strategy_response(self, strategy_text: str, query: str, production_incident: bool) -> Dict[str, Any]:
        """Parse the LLM strategy response into structured format."""
        # Simplified parsing - extract key information
        strategy = {
            'query_type': 'general_research',
            'technologies': [],
            'services': [],
            'queries': [],
            'priority': 'urgent' if production_incident else 'normal'
        }
        
        # Extract technologies and services mentioned in query
        tech_keywords = ['java', 'spring', 'hbase', 'jboss', 'eclipse', 'richfaces', 'oauth', 'jwt']
        service_keywords = ['github', 'jira', 'confluence', 'aws', 'docker', 'kubernetes']
        
        query_lower = query.lower()
        strategy['technologies'] = [tech for tech in tech_keywords if tech in query_lower]
        strategy['services'] = [service for service in service_keywords if service in query_lower]
        
        # Determine query type based on content
        if any(word in query_lower for word in ['down', 'outage', 'status', 'unavailable']):
            strategy['query_type'] = 'status_check'
        elif any(word in query_lower for word in ['error', 'exception', 'failed', 'issue', 'problem']):
            strategy['query_type'] = 'error_troubleshooting'
        
        # Generate search queries based on type and content
        if strategy['query_type'] == 'status_check':
            strategy['queries'] = self._generate_status_queries(query, strategy['services'])
        elif strategy['query_type'] == 'error_troubleshooting':
            strategy['queries'] = self._generate_error_queries(query, strategy['technologies'])
        else:
            strategy['queries'] = self._generate_general_queries(query)
        
        return strategy
    
    def _generate_status_queries(self, query: str, services: List[str]) -> List[str]:
        """Generate status check queries."""
        queries = [f"{query} status"]
        
        for service in services:
            queries.extend([
                f"{service} status page",
                f"{service} downdetector",
                f"is {service} down"
            ])
        
        # Add general downdetector search
        if not services:
            queries.append("downdetector outage status")
        
        return queries[:self.max_searches]
    
    def _generate_error_queries(self, query: str, technologies: List[str]) -> List[str]:
        """Generate error troubleshooting queries."""
        queries = [f'"{query}" solution fix']
        
        for tech in technologies:
            queries.extend([
                f"{tech} {query} fix",
                f"{tech} production issue solution"
            ])
        
        # Add Stack Overflow specific search
        queries.append(f"stackoverflow {query}")
        
        return queries[:self.max_searches]
    
    def _generate_general_queries(self, query: str) -> List[str]:
        """Generate general research queries."""
        return [
            query,
            f"{query} documentation",
            f"{query} best practices",
            f"{query} troubleshooting guide"
        ][:self.max_searches]
    
    def _create_fallback_strategy(self, query: str, production_incident: bool) -> Dict[str, Any]:
        """Create a simple fallback strategy when LLM assessment fails."""
        return {
            'query_type': 'general_research',
            'technologies': [],
            'services': [],
            'queries': [query],
            'priority': 'urgent' if production_incident else 'normal'
        }
    
    def _execute_search_strategy(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the planned search strategy."""
        all_results = []
        
        try:
            query_type = strategy.get('query_type', 'general_research')
            queries = strategy.get('queries', [])
            
            for i, search_query in enumerate(queries):
                if i >= self.max_searches:
                    break
                
                logger.info(f"Executing search {i+1}/{len(queries)}: '{search_query[:50]}...'")
                
                # Perform web search based on query type
                if query_type == 'status_check' and strategy.get('services'):
                    # Use status page search for services
                    for service in strategy.get('services', []):
                        results = self.web_search_tools.search_status_pages(service)
                        all_results.extend(results)
                        break  # Just search for first service to avoid too many results
                else:
                    # Regular web search
                    results = self.web_search_tools.web_search(search_query, max_results=3)
                    all_results.extend(results)
            
            logger.info(f"Total web search results: {len(all_results)}")
            return all_results
            
        except Exception as e:
            logger.error(f"Search strategy execution failed: {e}")
            return []
    
    def _format_web_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format web search results for consistent output."""
        formatted_results = []
        
        for result in results:
            # Create content in expected format
            title = result.get('title', 'Web Search Result')
            content = result.get('content', '')
            url = result.get('url', '')
            
            formatted_content = f"Title: {title}\n\nContent: {content}"
            if url:
                formatted_content += f"\n\nURL: {url}"
            
            formatted_result = {
                'content': formatted_content,
                'metadata': {
                    'url': url,
                    'title': title,
                    'search_type': result.get('search_type', 'web_search'),
                    'source': result.get('source', 'web'),
                    'timestamp': result.get('timestamp', datetime.now().isoformat())
                },
                'source': f"web_{result.get('source', 'search')}",
                'score': result.get('score', 0.7)  # Web results get decent relevance score
            }
            
            formatted_results.append(formatted_result)
        
        return formatted_results[:10]  # Limit to top 10 results

# Test function
def test_web_search_agent():
    """Test the WebSearch agent."""
    agent = WebSearchAgent()
    
    # Test state
    test_state = {
        'query': 'GitHub status outage',
        'production_incident': True,
        'user_can_wait': False,
        'routing_decision': 'WebSearch',
        'routing_reasoning': 'Production incident requires real-time status check'
    }
    
    result_state = agent.process(test_state)
    print(f"Results: {len(result_state.get('retrieved_contexts', []))}")
    print(f"Method: {result_state.get('retrieval_method')}")
    print(f"Metadata: {result_state.get('retrieval_metadata', {})}")

if __name__ == "__main__":
    test_web_search_agent()