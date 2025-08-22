#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Multi-agent workflow orchestration for the FastAPI application.
Integrates all agents and provides the main processing pipeline.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain_openai import ChatOpenAI

# LangSmith tracing
try:
    from langsmith import traceable
    from langchain_core.tracers import LangChainTracer
    LANGSMITH_AVAILABLE = True
except ImportError:
    # Fallback decorator when LangSmith not available
    def traceable(func):
        return func
    LANGSMITH_AVAILABLE = False

try:
    # Try relative imports first (for when imported as part of package)
    from ..agents import (
        AgentState, SupervisorAgent, BM25Agent, ContextualCompressionAgent,
        EnsembleAgent, ResponseWriterAgent, WebSearchAgent, LogSearchAgent, measure_performance
    )
    from ..tools import get_rag_tools
    from ..rag.supabase_retriever import SupabaseRetriever
except ImportError:
    # Fall back to absolute imports (for direct import)
    from agents import (
        AgentState, SupervisorAgent, BM25Agent, ContextualCompressionAgent,
        EnsembleAgent, ResponseWriterAgent, WebSearchAgent, LogSearchAgent, measure_performance
    )
    from tools import get_rag_tools
    from app.rag.supabase_retriever import SupabaseRetriever

class MultiAgentWorkflow:
    """
    Multi-agent workflow that orchestrates the entire RAG pipeline.
    """
    
    def __init__(self):
        """Initialize the multi-agent workflow."""
        self.logger = self._setup_logger()
        
        # Initialize components
        self._initialize_llms()
        self._initialize_vectorstore()
        self._initialize_agents()
        
        self.logger.info("✅ Multi-agent workflow initialized")
    
    def _setup_logger(self):
        """Setup logger for workflow."""
        logger = logging.getLogger('MultiAgentWorkflow')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_llms(self):
        """Initialize LLM clients."""
        try:
            # Get OpenAI API key
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            # Initialize LLMs (using same models as original notebook)
            self.supervisor_llm = ChatOpenAI(
                model="gpt-4o",
                api_key=openai_api_key,
                temperature=0
            )
            
            self.rag_llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_api_key,
                temperature=0
            )
            
            self.response_writer_llm = ChatOpenAI(
                model="gpt-4o",
                api_key=openai_api_key,
                temperature=0
            )
            
            self.logger.info("✅ LLMs initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize LLMs: {e}")
            raise
    
    def _initialize_vectorstore(self):
        """Initialize Supabase retrievers."""
        try:
            # Use Supabase retrievers directly
            self.bugs_retriever = SupabaseRetriever('bugs')
            self.pcr_retriever = SupabaseRetriever('pcr')
            
            # Test connections
            if self.bugs_retriever.test_connection() and self.pcr_retriever.test_connection():
                self.logger.info("✅ Connected to Supabase retrievers (bugs & pcr)")
            else:
                raise Exception("Failed to connect to Supabase retrievers")
                
            # Set vectorstore to None since we're using retrievers directly  
            self.vectorstore = None
            
            # Initialize RAG tools (Supabase-based)
            self.rag_tools = get_rag_tools()
            
            self.logger.info("✅ Vectorstore and RAG tools initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize vectorstore: {e}")
            raise
    
    def _initialize_agents(self):
        """Initialize all agents."""
        try:
            # Initialize supervisor agent (always needed)
            self.supervisor_agent = SupervisorAgent(self.supervisor_llm)
            
            # Initialize response writer agent (always needed)
            self.response_writer_agent = ResponseWriterAgent(self.response_writer_llm)
            
            # Initialize web search agent (always available)
            self.web_search_agent = WebSearchAgent(self.supervisor_llm)
            
            # Initialize log search agent with GCP backend
            self.log_search_agent = LogSearchAgent(self.rag_llm)
            
            # Initialize retrieval agents
            if self.vectorstore:
                # Use vectorstore-based agents
                self.bm25_agent = BM25Agent(self.vectorstore, self.rag_llm)
                self.contextual_compression_agent = ContextualCompressionAgent(self.vectorstore, self.rag_llm)
                self.ensemble_agent = EnsembleAgent(
                    self.vectorstore, self.rag_llm, 
                    self.bm25_agent, self.contextual_compression_agent
                )
            else:
                # Use Supabase-based agents (mock for now - would need full implementation)
                self.logger.warning("Using mock agents - full Supabase integration needed")
                self.bm25_agent = None
                self.contextual_compression_agent = None
                self.ensemble_agent = None
            
            self.logger.info("✅ Agents initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize agents: {e}")
            raise
    
    @traceable(name="MultiAgentWorkflow.process_query")
    async def process_query(
        self,
        query: str,
        user_can_wait: bool = False,
        production_incident: bool = False,
        openai_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process query through the multi-agent workflow.
        
        Args:
            query: User query
            user_can_wait: Whether user can wait for comprehensive results
            production_incident: Whether this is a production incident
            openai_api_key: Optional OpenAI API key for this request
        
        Returns:
            Complete results from multi-agent processing
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Processing query: '{query[:50]}...'")
            
            # Update API key if provided
            if openai_api_key:
                self._update_api_keys(openai_api_key)
            
            # Initialize state
            initial_state: AgentState = {
                'query': query,
                'user_can_wait': user_can_wait,
                'production_incident': production_incident,
                'routing_decision': None,
                'routing_reasoning': None,
                'retrieved_contexts': [],
                'retrieval_method': None,
                'retrieval_metadata': {},
                'final_answer': None,
                'relevant_tickets': [],
                'messages': []
            }
            
            # Step 1: Supervisor routing
            state = self.supervisor_agent.process(initial_state)
            
            # Step 2: Route to appropriate retrieval agent
            state = await self._route_to_agent(state)
            
            # Step 3: Generate final response
            state = self.response_writer_agent.process(state)
            
            # Calculate total processing time
            total_time = measure_performance(start_time)
            
            # Format response
            response = {
                'query': state['query'],
                'final_answer': state['final_answer'],
                'relevant_tickets': state['relevant_tickets'],
                'routing_decision': state['routing_decision'],
                'routing_reasoning': state['routing_reasoning'],
                'retrieval_method': state['retrieval_method'],
                'retrieved_contexts': state['retrieved_contexts'],
                'retrieval_metadata': state['retrieval_metadata'],
                'user_can_wait': user_can_wait,
                'production_incident': production_incident,
                'messages': [{'content': msg.content, 'type': type(msg).__name__} for msg in state['messages']],
                'timestamp': datetime.now().isoformat(),
                'total_processing_time': total_time
            }
            
            self.logger.info(f"Query processed successfully in {total_time:.2f}s")
            return response
            
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            raise
    
    @traceable(name="MultiAgentWorkflow.get_routing_decision") 
    async def get_routing_decision(
        self,
        query: str,
        user_can_wait: bool = False,
        production_incident: bool = False
    ) -> Dict[str, str]:
        """
        Get routing decision without full processing (for debug endpoint).
        
        Args:
            query: User query
            user_can_wait: Whether user can wait
            production_incident: Whether this is production incident
        
        Returns:
            Routing decision and reasoning
        """
        try:
            self.logger.info(f"Getting routing decision for: '{query[:50]}...'")
            
            # Initialize minimal state for routing
            state: AgentState = {
                'query': query,
                'user_can_wait': user_can_wait,
                'production_incident': production_incident,
                'routing_decision': None,
                'routing_reasoning': None,
                'retrieved_contexts': [],
                'retrieval_method': None,
                'retrieval_metadata': {},
                'final_answer': None,
                'relevant_tickets': [],
                'messages': []
            }
            
            # Get routing decision from supervisor
            state = self.supervisor_agent.process(state)
            
            return {
                'routing_decision': state['routing_decision'],
                'routing_reasoning': state['routing_reasoning']
            }
            
        except Exception as e:
            self.logger.error(f"Routing decision failed: {e}")
            raise
    
    @traceable(name="MultiAgentWorkflow._route_to_agent")
    async def _route_to_agent(self, state: AgentState) -> AgentState:
        """Route to the appropriate retrieval agent based on supervisor decision."""
        routing_decision = state['routing_decision']
        
        try:
            if routing_decision == 'BM25':
                if self.bm25_agent:
                    return self.bm25_agent.process(state)
                else:
                    # Fallback to Supabase BM25/keyword search
                    return await self._supabase_bm25_fallback(state)
            
            elif routing_decision == 'ContextualCompression':
                if self.contextual_compression_agent:
                    return self.contextual_compression_agent.process(state)
                else:
                    # Fallback to Supabase vector search
                    return await self._supabase_vector_fallback(state)
            
            elif routing_decision == 'Ensemble':
                if self.ensemble_agent:
                    return self.ensemble_agent.process(state)
                else:
                    # Fallback to Supabase hybrid search
                    return await self._supabase_hybrid_fallback(state)
            
            elif routing_decision == 'WebSearch':
                # Use WebSearch agent for real-time information
                return self.web_search_agent.process(state)
            
            elif routing_decision == 'LogSearch':
                # Use LogSearch agent for log analysis
                return self.log_search_agent.process(state)
            
            else:
                # Default fallback
                self.logger.warning(f"Unknown routing decision: {routing_decision}")
                return await self._supabase_vector_fallback(state)
        
        except Exception as e:
            self.logger.error(f"Agent routing failed: {e}")
            # Last resort fallback
            return await self._supabase_vector_fallback(state)
    
    async def _supabase_bm25_fallback(self, state: AgentState) -> AgentState:
        """Fallback to Supabase BM25/keyword search."""
        start_time = datetime.now()
        
        try:
            query = state['query']
            
            # Use RAG tools for keyword search
            results = self.rag_tools.keyword_search_bugs(query, k=10)
            
            # Convert to expected format
            retrieved_contexts = []
            for result in results:
                retrieved_contexts.append({
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'source': result['source'],
                    'score': result['score']
                })
            
            # Update state
            state['retrieved_contexts'] = retrieved_contexts
            state['retrieval_method'] = 'Supabase_BM25'
            state['retrieval_metadata'] = {
                'agent': 'Supabase_BM25',
                'num_results': len(retrieved_contexts),
                'processing_time': measure_performance(start_time),
                'method_type': 'keyword_based',
                'source': 'supabase_fallback'
            }
            
            self.logger.info(f"Supabase BM25 fallback: {len(retrieved_contexts)} results")
            return state
        
        except Exception as e:
            self.logger.error(f"Supabase BM25 fallback failed: {e}")
            return self._empty_results_fallback(state, 'Supabase_BM25_Failed')
    
    async def _supabase_vector_fallback(self, state: AgentState) -> AgentState:
        """Fallback to Supabase vector search."""
        start_time = datetime.now()
        
        try:
            query = state['query']
            is_urgent = state.get('production_incident', False)
            
            # Use RAG tools for vector search
            k = 5 if is_urgent else 10
            results = self.rag_tools.vector_search_bugs(query, k=k)
            
            # Convert to expected format
            retrieved_contexts = []
            for result in results:
                retrieved_contexts.append({
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'source': result['source'],
                    'score': result['score']
                })
            
            # Update state
            state['retrieved_contexts'] = retrieved_contexts
            state['retrieval_method'] = 'Supabase_Vector'
            state['retrieval_metadata'] = {
                'agent': 'Supabase_Vector',
                'num_results': len(retrieved_contexts),
                'processing_time': measure_performance(start_time),
                'method_type': 'semantic_vector',
                'is_urgent': is_urgent,
                'source': 'supabase_fallback'
            }
            
            self.logger.info(f"Supabase vector fallback: {len(retrieved_contexts)} results")
            return state
        
        except Exception as e:
            self.logger.error(f"Supabase vector fallback failed: {e}")
            return self._empty_results_fallback(state, 'Supabase_Vector_Failed')
    
    async def _supabase_hybrid_fallback(self, state: AgentState) -> AgentState:
        """Fallback to Supabase hybrid search."""
        start_time = datetime.now()
        
        try:
            query = state['query']
            
            # Use RAG tools for hybrid search
            results = self.rag_tools.hybrid_search_bugs(query, k=10)
            
            # Convert to expected format
            retrieved_contexts = []
            for result in results:
                retrieved_contexts.append({
                    'content': result['content'],
                    'metadata': result['metadata'],
                    'source': result['source'],
                    'score': result['score']
                })
            
            # Update state
            state['retrieved_contexts'] = retrieved_contexts
            state['retrieval_method'] = 'Supabase_Hybrid'
            state['retrieval_metadata'] = {
                'agent': 'Supabase_Hybrid',
                'num_results': len(retrieved_contexts),
                'processing_time': measure_performance(start_time),
                'method_type': 'hybrid_search',
                'source': 'supabase_fallback'
            }
            
            self.logger.info(f"Supabase hybrid fallback: {len(retrieved_contexts)} results")
            return state
        
        except Exception as e:
            self.logger.error(f"Supabase hybrid fallback failed: {e}")
            return self._empty_results_fallback(state, 'Supabase_Hybrid_Failed')
    
    def _empty_results_fallback(self, state: AgentState, method_name: str) -> AgentState:
        """Fallback when all retrieval methods fail."""
        start_time = datetime.now()
        
        state['retrieved_contexts'] = []
        state['retrieval_method'] = method_name
        state['retrieval_metadata'] = {
            'agent': method_name,
            'num_results': 0,
            'processing_time': measure_performance(start_time),
            'method_type': 'empty_fallback',
            'source': 'error_fallback'
        }
        
        self.logger.warning(f"Using empty results fallback: {method_name}")
        return state
    
    def _update_api_keys(self, openai_api_key: str):
        """Update OpenAI API keys for this request."""
        try:
            # Update LLM configurations with new API key
            # Note: This is a simplified approach - in production you might want
            # to create new LLM instances for security
            
            os.environ['OPENAI_API_KEY'] = openai_api_key
            
            # Reinitialize LLMs with new key
            self._initialize_llms()
            
            # Reinitialize agents with new LLMs
            self.supervisor_agent = SupervisorAgent(self.supervisor_llm)
            self.response_writer_agent = ResponseWriterAgent(self.response_writer_llm)
            self.web_search_agent = WebSearchAgent(self.supervisor_llm)
            self.log_search_agent = LogSearchAgent(self.rag_llm)
            
            self.logger.info("API keys updated for this request")
            
        except Exception as e:
            self.logger.error(f"Failed to update API keys: {e}")
            # Continue with existing keys