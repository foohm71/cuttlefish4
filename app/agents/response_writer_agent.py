#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
ResponseWriterAgent - Final response generation using GPT-4o reasoning.
Generates contextual responses based on retrieved JIRA ticket information.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# LangSmith tracing
try:
    from langsmith import traceable
except ImportError:
    def traceable(func):
        return func

# Handle both relative and absolute imports for Jupyter compatibility
try:
    from .common import (
        AgentState, measure_performance, format_context_for_llm, extract_ticket_info
    )
except ImportError:
    from common import (
        AgentState, measure_performance, format_context_for_llm, extract_ticket_info
    )

class ResponseWriterAgent:
    """ResponseWriter agent for generating contextual responses using GPT-4o reasoning."""
    
    def __init__(self, response_writer_llm):
        self.response_writer_llm = response_writer_llm
        self.response_prompt = self._create_response_prompt()
    
    def _create_response_prompt(self):
        """Create the response generation prompt."""
        return ChatPromptTemplate.from_template("""
        You are a RESPONSE WRITER agent for a JIRA ticket retrieval system. Generate helpful, contextual responses based on MULTI-AGENT retrieved JIRA ticket information.
        
        CONTEXT:
        Query: {query}
        Production Incident: {production_incident}
        Retrieval Methods Used: {retrieval_methods}
        Agents Executed: {agents_executed}
        
        MULTI-AGENT RESULTS:
        {agent_results_summary}
        
        COMBINED RETRIEVED CONTEXTS:
        {retrieved_contexts}
        
        INSTRUCTIONS:
        1. You have results from multiple specialized agents - synthesize them intelligently
        2. Prioritize information based on relevance and agent reliability:
           - LogSearch: Production logs, errors, system issues
           - WebSearch: Real-time status, external service outages
           - BM25: Exact ticket matches, specific references
           - ContextualCompression: Semantic similarity, related issues
           - Ensemble: Comprehensive coverage, research queries
        3. For production incidents: prioritize LogSearch and WebSearch results
        4. Cross-reference information between agents when possible
        5. If agents provide conflicting information, acknowledge and explain
        6. Reference specific JIRA tickets with confidence scores when available
        7. If no relevant information found from any agent, clearly state this
        
        RESPONSE STYLE:
        - Production Incident: Direct, actionable, highlight urgent findings from each agent
        - General Query: Synthesize comprehensive view from all agents
        - Conflicting Results: Present multiple perspectives clearly
        - No Results: Explain which agents were consulted and suggest alternatives
        
        Generate a response that synthesizes multi-agent findings to answer the user's query:
        """)
    
    @traceable(name="ResponseWriterAgent.generate_response")
    def generate_response(self, query: str, retrieved_contexts: List[Dict], 
                         production_incident: bool, retrieval_methods: List[str], 
                         agent_results: Dict[str, List[Dict]], agents_executed: List[str]) -> str:
        """Generate contextual response based on multi-agent retrieved information."""
        try:
            # Format retrieved contexts for the prompt
            context_text = format_context_for_llm(retrieved_contexts)
            
            # Create agent results summary
            agent_summary = self._create_agent_results_summary(agent_results, agents_executed)
            
            # Create response chain
            response_chain = self.response_prompt | self.response_writer_llm | StrOutputParser()
            
            # Generate response
            response = response_chain.invoke({
                "query": query,
                "production_incident": production_incident,
                "retrieval_methods": ", ".join(retrieval_methods) if retrieval_methods else "Unknown",
                "agents_executed": ", ".join(agents_executed) if agents_executed else "Unknown",
                "agent_results_summary": agent_summary,
                "retrieved_contexts": context_text if context_text != "No relevant context found." else "No relevant JIRA tickets found for this query."
            })
            
            return response.strip()
            
        except Exception as e:
            print(f"❌ Response generation error: {e}")
            
            # Fallback response
            if production_incident:
                return f"Unable to generate response for production incident query: '{query}'. Please check system logs or contact support immediately."
            else:
                return f"Unable to generate response for query: '{query}'. Please try rephrasing your question or contact support."
    
    def _create_agent_results_summary(self, agent_results: Dict[str, List[Dict]], agents_executed: List[str]) -> str:
        """Create a summary of results from each agent."""
        if not agent_results or not agents_executed:
            return "No agent results available."
        
        summary_lines = []
        for agent in agents_executed:
            results = agent_results.get(agent, [])
            count = len(results)
            
            if count > 0:
                summary_lines.append(f"- {agent}: Found {count} relevant result(s)")
                # Add brief preview of top result if available
                if results and 'content' in results[0]:
                    preview = results[0]['content'][:100] + "..." if len(results[0]['content']) > 100 else results[0]['content']
                    summary_lines.append(f"  Top result: {preview}")
            else:
                summary_lines.append(f"- {agent}: No results found")
        
        return "\n".join(summary_lines) if summary_lines else "No agent results available."
    
    @traceable(name="ResponseWriterAgent.process")
    def process(self, state: AgentState) -> AgentState:
        """Process state and generate final response from multi-agent results."""
        start_time = datetime.now()
        
        query = state['query']
        retrieved_contexts = state.get('retrieved_contexts', [])
        production_incident = state['production_incident']
        retrieval_methods = state.get('retrieval_methods', [])
        agent_results = state.get('agent_results', {})
        
        # Extract agents executed from retrieval metadata or agent_results
        agents_executed = list(agent_results.keys()) if agent_results else []
        
        incident_label = "[PRODUCTION INCIDENT]" if production_incident else ""
        print(f"✍️  ResponseWriter Agent {incident_label} synthesizing multi-agent response...")
        print(f"   Agents consulted: {', '.join(agents_executed)}")
        print(f"   Total contexts: {len(retrieved_contexts)}")
        
        # Generate response
        final_answer = self.generate_response(
            query, retrieved_contexts, production_incident, retrieval_methods, agent_results, agents_executed
        )
        
        # Extract relevant tickets
        relevant_tickets = extract_ticket_info(retrieved_contexts)
        
        # Update state
        state['final_answer'] = final_answer
        state['relevant_tickets'] = relevant_tickets
        
        # Add processing message
        state['messages'].append(AIMessage(
            content=f"ResponseWriter generated final answer with {len(relevant_tickets)} relevant tickets"
        ))
        
        processing_time = measure_performance(start_time)
        print(f"✅ ResponseWriter completed in {processing_time:.2f}s")
        print(f"   Generated response: {len(final_answer)} characters")
        print(f"   Relevant tickets: {len(relevant_tickets)}")
        
        return state