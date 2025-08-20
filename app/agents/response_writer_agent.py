#!/usr/bin/env python3
"""
ResponseWriterAgent - Final response generation using GPT-4o reasoning.
Generates contextual responses based on retrieved JIRA ticket information.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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
        You are a RESPONSE WRITER agent for a JIRA ticket retrieval system. Generate helpful, contextual responses based on retrieved JIRA ticket information.
        
        CONTEXT:
        Query: {query}
        Production Incident: {production_incident}
        Retrieval Method Used: {retrieval_method}
        
        RETRIEVED JIRA TICKETS:
        {retrieved_contexts}
        
        INSTRUCTIONS:
        1. Analyze the user's query and the retrieved JIRA ticket information
        2. Generate a helpful response that addresses the user's specific question
        3. If this is a production incident, prioritize urgent/actionable information
        4. Reference specific JIRA tickets when relevant (use ticket keys like HBASE-123)
        5. If no relevant information is found, clearly state this
        6. Keep the response concise but informative
        
        RESPONSE STYLE:
        - Production Incident: Direct, actionable, prioritize immediate solutions
        - General Query: Comprehensive, educational, include background context
        - No Results: Suggest alternative search terms or approaches
        
        Generate a response that directly answers the user's query:
        """)
    
    def generate_response(self, query: str, retrieved_contexts: List[Dict], 
                         production_incident: bool, retrieval_method: str) -> str:
        """Generate contextual response based on retrieved information."""
        try:
            # Format retrieved contexts for the prompt
            context_text = format_context_for_llm(retrieved_contexts)
            
            # Create response chain
            response_chain = self.response_prompt | self.response_writer_llm | StrOutputParser()
            
            # Generate response
            response = response_chain.invoke({
                "query": query,
                "production_incident": production_incident,
                "retrieval_method": retrieval_method,
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
    
    def process(self, state: AgentState) -> AgentState:
        """Process state and generate final response."""
        start_time = datetime.now()
        
        query = state['query']
        retrieved_contexts = state.get('retrieved_contexts', [])
        production_incident = state['production_incident']
        retrieval_method = state.get('retrieval_method', 'Unknown')
        
        incident_label = "[PRODUCTION INCIDENT]" if production_incident else ""
        print(f"✍️  ResponseWriter Agent {incident_label} generating response...")
        
        # Generate response
        final_answer = self.generate_response(
            query, retrieved_contexts, production_incident, retrieval_method
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