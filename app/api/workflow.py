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
import asyncio
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
                'routing_decisions': [],
                'routing_reasoning': None,
                'agent_results': {},
                'retrieved_contexts': [],
                'retrieval_methods': [],
                'retrieval_metadata': {},
                'final_answer': None,
                'relevant_tickets': [],
                'messages': []
            }
            
            # Step 1: Supervisor routing
            state = self.supervisor_agent.process(initial_state)
            
            # Step 2: Route to appropriate retrieval agents (parallel execution)
            state = await self._route_to_agents(state)
            
            # Step 3: Generate final response
            state = self.response_writer_agent.process(state)
            
            # Calculate total processing time
            total_time = measure_performance(start_time)
            
            # Format response
            response = {
                'query': state['query'],
                'final_answer': state['final_answer'],
                'relevant_tickets': state['relevant_tickets'],
                'routing_decisions': state['routing_decisions'],
                'routing_reasoning': state['routing_reasoning'],
                'retrieval_methods': state['retrieval_methods'],
                'retrieved_contexts': state['retrieved_contexts'],
                'agent_results': state['agent_results'],
                'retrieval_metadata': state['retrieval_metadata'],
                'user_can_wait': user_can_wait,
                'production_incident': production_incident,
                'messages': [{'content': msg.content, 'type': type(msg).__name__} for msg in state['messages']],
                'timestamp': datetime.now().isoformat(),
                'total_processing_time': total_time,
                
                # Legacy compatibility fields
                'routing_decision': state['routing_decisions'][0] if state['routing_decisions'] else 'Unknown',
                'retrieval_method': ', '.join(state['retrieval_methods']) if state['retrieval_methods'] else 'Unknown'
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
                'routing_decisions': [],
                'routing_reasoning': None,
                'agent_results': {},
                'retrieved_contexts': [],
                'retrieval_methods': [],
                'retrieval_metadata': {},
                'final_answer': None,
                'relevant_tickets': [],
                'messages': []
            }
            
            # Get routing decision from supervisor
            state = self.supervisor_agent.process(state)
            
            return {
                'routing_decisions': state['routing_decisions'],
                'routing_reasoning': state['routing_reasoning'],
                # Legacy compatibility field
                'routing_decision': state['routing_decisions'][0] if state['routing_decisions'] else 'Unknown'
            }
            
        except Exception as e:
            self.logger.error(f"Routing decision failed: {e}")
            raise
    
    @traceable(name="MultiAgentWorkflow._route_to_agents")
    async def _route_to_agents(self, state: AgentState) -> AgentState:
        """Route to multiple agents in parallel based on supervisor decisions."""
        routing_decisions = state['routing_decisions']
        
        if not routing_decisions:
            self.logger.warning("No routing decisions found, using default")
            routing_decisions = ["ContextualCompression"]
        
        try:
            self.logger.info(f"Executing {len(routing_decisions)} agents in parallel: {routing_decisions}")
            
            # Create tasks for parallel execution
            tasks = []
            for agent_name in routing_decisions:
                task = self._execute_single_agent(agent_name, state)
                tasks.append(task)
            
            # Execute all agents in parallel
            agent_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and combine
            return self._merge_agent_results(state, routing_decisions, agent_results)
        
        except Exception as e:
            self.logger.error(f"Multi-agent routing failed: {e}")
            # Fallback to single agent
            return await self._execute_single_agent("ContextualCompression", state)
    
    async def _execute_single_agent(self, agent_name: str, state: AgentState) -> Dict[str, Any]:
        """Execute a single agent and return its results."""
        try:
            # Create a copy of state for this agent
            agent_state = state.copy()
            
            if agent_name == 'BM25':
                if self.bm25_agent:
                    result_state = self.bm25_agent.process(agent_state)
                else:
                    result_state = await self._supabase_bm25_fallback(agent_state)
            
            elif agent_name == 'ContextualCompression':
                if self.contextual_compression_agent:
                    result_state = self.contextual_compression_agent.process(agent_state)
                else:
                    result_state = await self._supabase_vector_fallback(agent_state)
            
            elif agent_name == 'Ensemble':
                if self.ensemble_agent:
                    result_state = self.ensemble_agent.process(agent_state)
                else:
                    result_state = await self._supabase_hybrid_fallback(agent_state)
            
            elif agent_name == 'WebSearch':
                result_state = self.web_search_agent.process(agent_state)
            
            elif agent_name == 'LogSearch':
                result_state = self.log_search_agent.process(agent_state)
            
            else:
                self.logger.warning(f"Unknown agent: {agent_name}, using fallback")
                result_state = await self._supabase_vector_fallback(agent_state)
            
            return {
                'agent_name': agent_name,
                'contexts': result_state['retrieved_contexts'],
                'method': result_state.get('retrieval_method', agent_name),
                'metadata': result_state.get('retrieval_metadata', {}),
                'success': True,
                'error': None
            }
        
        except Exception as e:
            self.logger.error(f"Agent {agent_name} failed: {e}")
            return {
                'agent_name': agent_name,
                'contexts': [],
                'method': f"{agent_name}_Failed",
                'metadata': {'error': str(e)},
                'success': False,
                'error': str(e)
            }
    
    def _merge_agent_results(self, state: AgentState, agent_names: List[str], agent_results: List[Dict[str, Any]]) -> AgentState:
        """Merge results from multiple agents into the state."""
        start_time = datetime.now()
        
        combined_contexts = []
        methods_used = []
        agent_results_dict = {}
        combined_metadata = {
            'agents_executed': [],
            'agents_succeeded': [],
            'agents_failed': [],
            'total_contexts': 0,
            'merge_time': 0
        }
        
        for i, result in enumerate(agent_results):
            agent_name = agent_names[i] if i < len(agent_names) else f"Agent_{i}"
            
            # Handle exceptions from asyncio.gather
            if isinstance(result, Exception):
                self.logger.error(f"Agent {agent_name} raised exception: {result}")
                combined_metadata['agents_failed'].append(agent_name)
                agent_results_dict[agent_name] = []
                continue
            
            # Process successful results
            if result['success']:
                contexts = result['contexts']
                combined_contexts.extend(contexts)
                methods_used.append(result['method'])
                agent_results_dict[agent_name] = contexts
                combined_metadata['agents_succeeded'].append(agent_name)
                
                # Add agent-specific metadata
                combined_metadata[f'{agent_name}_results'] = len(contexts)
                combined_metadata[f'{agent_name}_metadata'] = result['metadata']
            else:
                combined_metadata['agents_failed'].append(agent_name)
                agent_results_dict[agent_name] = []
            
            combined_metadata['agents_executed'].append(agent_name)
        
        # Remove duplicates while preserving order and source
        unique_contexts = self._deduplicate_contexts(combined_contexts)
        
        # Update state with merged results
        state['retrieved_contexts'] = unique_contexts
        state['retrieval_methods'] = methods_used
        state['agent_results'] = agent_results_dict
        
        combined_metadata['total_contexts'] = len(unique_contexts)
        combined_metadata['merge_time'] = measure_performance(start_time)
        state['retrieval_metadata'] = combined_metadata
        
        self.logger.info(f"Merged results from {len(agent_names)} agents: {len(unique_contexts)} unique contexts")
        return state
    
    def _deduplicate_contexts(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate contexts while preserving the best scores and source information."""
        seen_content = {}
        unique_contexts = []
        
        for context in contexts:
            content = context.get('content', '')
            content_hash = hash(content.strip())
            
            if content_hash not in seen_content:
                # First time seeing this content
                seen_content[content_hash] = context
                unique_contexts.append(context)
            else:
                # Duplicate content - keep the one with better score or more metadata
                existing = seen_content[content_hash]
                current_score = context.get('score', 0)
                existing_score = existing.get('score', 0)
                
                if current_score > existing_score:
                    # Replace with better score
                    idx = unique_contexts.index(existing)
                    unique_contexts[idx] = context
                    seen_content[content_hash] = context
        
        return unique_contexts
    
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