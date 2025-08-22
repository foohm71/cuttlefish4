#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
SupervisorAgent - Intelligent query routing using GPT-4o reasoning.
Routes queries to the most appropriate retrieval agent based on query characteristics.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# LangSmith tracing
try:
    from langsmith import traceable
except ImportError:
    def traceable(func):
        return func

# State type definition (shared across all agents)
class AgentState(TypedDict):
    """State shared between all agents in the graph."""
    query: str
    user_can_wait: bool
    production_incident: bool
    routing_decision: Optional[str]
    routing_reasoning: Optional[str]
    retrieved_contexts: List[Dict[str, Any]]
    retrieval_method: Optional[str]
    retrieval_metadata: Dict[str, Any]
    final_answer: Optional[str]
    relevant_tickets: List[Dict[str, str]]
    messages: List[Any]

def measure_performance(start_time: datetime) -> float:
    """Calculate processing time in seconds."""
    return (datetime.now() - start_time).total_seconds()

class SupervisorAgent:
    """Supervisor agent for intelligent query routing using GPT-4o reasoning."""
    
    def __init__(self, supervisor_llm):
        self.supervisor_llm = supervisor_llm
        self.routing_prompt = self._create_routing_prompt()
    
    def _create_routing_prompt(self):
        """Create the routing decision prompt."""
        return ChatPromptTemplate.from_template("""
        You are a SUPERVISOR agent for a JIRA ticket retrieval system. 
        Your job is to analyze user queries and route them to the most appropriate retrieval agent. 
        Route to multiple agents if needed. Review the query to see if you are dealing with an analysis query, a ticket query, or a production incident query. 
        If it is a analysis query wear the hat of a seasoned software architect. If it is a production incident query wear the hat of a seasoned devops engineer. If it is a ticket query wear the hat of a seasoned JIRA expert.
        
        AVAILABLE AGENTS:
        1. BM25 - Fast keyword-based search, best for:
           - Specific ticket references (e.g., "HBASE-123", "ticket SPR-456")
           - Exact error messages or specific terms
           - Technical acronyms or specific component names
        
        2. ContextualCompression - Fast semantic search with reranking, best for:
           - Production incidents (when speed is critical)
           - General troubleshooting questions
           - When user cannot wait long
        
        3. Ensemble - Comprehensive multi-method search, best for:
           - Complex queries requiring thorough analysis
           - When user can wait for comprehensive results
           - Research-type questions needing broad coverage
        
        4. WebSearch - Real-time web search using Tavily, best for:
           - Service status checks (e.g., "GitHub down", "AWS outage")
           - Current outages or downtime queries
           - Recent production incidents needing real-time information
           - Status page, downdetctor, X, isdown.app etc lookups and external service issues
           - Queries about "latest", "current", or "recent" issues
        
        5. LogSearch - GCP Cloud log analysis, best for:
           - Production incident log analysis
           - Error pattern investigation (exceptions, timeouts, failures)
           - Application troubleshooting with log data eg. Exceptions, HTTP 5xx errors 
           - Performance issue diagnosis through logs
           - Certificate expiry, disk space, HTTP errors, dead letter queue issues
        
        ROUTING RULES:
        - If query mentions service status/outages (down, outage, status) → WebSearch, LogSearch, ContextualCompression but look for release tickets (eg. PCR-1234)
        - If query contains specific ticket references → BM25
        - If query mentions log analysis, exceptions, errors in production → LogSearch
        - If production_incident=True AND mentions logs, errors, exceptions → LogSearch
        - If user_can_wait=True → Ensemble
        - If production_incident=True AND mentions external services → WebSearch
        - If production_incident=True (urgent) → ContextualCompression
        - Default → ContextualCompression
        
        QUERY: {query}
        USER_CAN_WAIT: {user_can_wait}
        PRODUCTION_INCIDENT: {production_incident}
        
        Analyze the query and respond with ONLY:
        {{"agent": "BM25|ContextualCompression|Ensemble|WebSearch|LogSearch", "reasoning": "brief explanation"}}
        """)
    
    @traceable(name="SupervisorAgent.route_query")
    def route_query(self, query: str, user_can_wait: bool, production_incident: bool) -> Dict[str, str]:
        """Route query to appropriate agent."""
        try:
            # Format prompt
            routing_chain = self.routing_prompt | self.supervisor_llm | StrOutputParser()
            
            # Get routing decision
            response = routing_chain.invoke({
                "query": query,
                "user_can_wait": user_can_wait,
                "production_incident": production_incident
            })
            
            # Parse JSON response
            try:
                routing_decision = json.loads(response)
                agent = routing_decision.get("agent", "ContextualCompression")
                reasoning = routing_decision.get("reasoning", "Default routing")
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                if "WebSearch" in response:
                    agent = "WebSearch"
                elif "LogSearch" in response:
                    agent = "LogSearch"
                elif "BM25" in response:
                    agent = "BM25"
                elif "Ensemble" in response:
                    agent = "Ensemble"
                else:
                    agent = "ContextualCompression"
                reasoning = "Parsed from text response"
            
            # Validate agent choice
            valid_agents = ["BM25", "ContextualCompression", "Ensemble", "WebSearch", "LogSearch"]
            if agent not in valid_agents:
                agent = "ContextualCompression"
                reasoning = "Invalid agent, using default"
            
            return {"agent": agent, "reasoning": reasoning}
            
        except Exception as e:
            print(f"⚠️  Routing error: {e}")
            # Safe fallback
            if production_incident:
                return {"agent": "ContextualCompression", "reasoning": "Emergency fallback for production incident"}
            elif user_can_wait:
                return {"agent": "Ensemble", "reasoning": "Fallback for comprehensive search"}
            else:
                return {"agent": "ContextualCompression", "reasoning": "Safe default fallback"}
    
    @traceable(name="SupervisorAgent.process")
    def process(self, state: AgentState) -> AgentState:
        """Process query and determine routing."""
        start_time = datetime.now()
        
        query = state['query']
        user_can_wait = state['user_can_wait']
        production_incident = state['production_incident']
        
        print(f"🧠 Supervisor Agent analyzing query: '{query}'")
        print(f"   user_can_wait: {user_can_wait}, production_incident: {production_incident}")
        
        # Make routing decision
        routing_result = self.route_query(query, user_can_wait, production_incident)
        
        # Update state
        state['routing_decision'] = routing_result['agent']
        state['routing_reasoning'] = routing_result['reasoning']
        
        # Add processing message
        state['messages'].append(AIMessage(
            content=f"Supervisor routed query to {routing_result['agent']} agent: {routing_result['reasoning']}"
        ))
        
        print(f"✅ Supervisor decision: {routing_result['agent']} - {routing_result['reasoning']}")
        print(f"   Analysis time: {measure_performance(start_time):.2f}s")
        
        return state