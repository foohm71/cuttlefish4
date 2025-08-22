#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Supabase-based agents that use RAG tools instead of LangChain vectorstores.
These agents provide the same interface as the LangChain agents but use Supabase backend.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage

# Handle both relative and absolute imports for Jupyter compatibility
try:
    from .common import (
        AgentState, measure_performance, extract_content_from_document, 
        filter_empty_documents
    )
except ImportError:
    from common import (
        AgentState, measure_performance, extract_content_from_document, 
        filter_empty_documents
    )

class SupabaseBM25Agent:
    """Supabase-based BM25 agent using RAG tools for keyword search."""
    
    def __init__(self, bugs_retriever, pcr_retriever, rag_llm, k=10):
        self.bugs_retriever = bugs_retriever
        self.pcr_retriever = pcr_retriever
        self.rag_llm = rag_llm
        self.k = k
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logger = logging.getLogger('SupabaseBM25Agent')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def retrieve(self, query: str, is_urgent: bool = False) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search using Supabase RAG tools."""
        try:
            start_time = datetime.now()
            
            # Validate query
            if not query or not isinstance(query, str) or not query.strip():
                self.logger.warning("⚠️  Invalid query provided to SupabaseBM25 retrieve")
                return []
            
            # Adjust parameters for urgent queries
            if is_urgent:
                limit = min(self.k, 5)  # Fewer results for speed
            else:
                limit = self.k
            
            self.logger.info(f"🔍 Performing BM25 search for: '{query[:50]}...'")
            
            # Search both collections
            bugs_results = self.bugs_retriever.keyword_search(query, k=limit)
            pcr_results = self.pcr_retriever.keyword_search(query, k=limit)
            
            # Combine and deduplicate results
            all_results = []
            seen_keys = set()
            
            # Process bugs results
            for result in bugs_results:
                # The result structure from SupabaseRetriever is:
                # {'content': 'Title: ...\n\nDescription: ...', 'metadata': {...}, 'source': '...', 'score': ...}
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                title = metadata.get('title', '')
                description = metadata.get('description', '')
                key = metadata.get('key', metadata.get('id', ''))
                
                if content and key not in seen_keys:
                    all_results.append({
                        'content': content,
                        'metadata': {
                            'key': key,
                            'title': title,
                            'description': description,
                            'source': 'bugs'
                        },
                        'score': result.get('score', 0.8),  # Use actual score from retriever
                        'source': 'bugs'
                    })
                    seen_keys.add(key)
            
            # Process PCR results
            for result in pcr_results:
                # The result structure from SupabaseRetriever is:
                # {'content': 'Title: ...\n\nDescription: ...', 'metadata': {...}, 'source': '...', 'score': ...}
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                title = metadata.get('title', '')
                description = metadata.get('description', '')
                key = metadata.get('key', metadata.get('id', ''))
                
                if content and key not in seen_keys:
                    all_results.append({
                        'content': content,
                        'metadata': {
                            'key': key,
                            'title': title,
                            'description': description,
                            'source': 'pcr'
                        },
                        'score': result.get('score', 0.8),  # Use actual score from retriever
                        'source': 'pcr'
                    })
                    seen_keys.add(key)
            
            # Sort by score and limit results
            all_results.sort(key=lambda x: x['score'], reverse=True)
            final_results = all_results[:limit]
            
            processing_time = measure_performance(start_time)
            self.logger.info(f"✅ BM25 search completed: {len(final_results)} results in {processing_time:.2f}s")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"❌ BM25 search failed: {e}")
            return []
    
    def process(self, state: AgentState) -> AgentState:
        """Process state using BM25 retrieval."""
        try:
            query = state['query']
            is_urgent = state.get('production_incident', False)
            
            # Perform retrieval
            results = self.retrieve(query, is_urgent)
            
            # Update state
            state['retrieved_contexts'] = results
            state['retrieval_method'] = 'supabase_bm25'
            state['retrieval_metadata'] = {
                'agent': 'SupabaseBM25',
                'num_results': len(results),
                'method_type': 'keyword_search',
                'source': 'supabase'
            }
            
            return state
            
        except Exception as e:
            self.logger.error(f"❌ SupabaseBM25 processing failed: {e}")
            return state

class SupabaseContextualCompressionAgent:
    """Supabase-based contextual compression agent using RAG tools."""
    
    def __init__(self, bugs_retriever, pcr_retriever, rag_llm, k=10):
        self.bugs_retriever = bugs_retriever
        self.pcr_retriever = pcr_retriever
        self.rag_llm = rag_llm
        self.k = k
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logger = logging.getLogger('SupabaseContextualCompressionAgent')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def retrieve(self, query: str, is_urgent: bool = False) -> List[Dict[str, Any]]:
        """Perform contextual compression search using Supabase RAG tools."""
        try:
            start_time = datetime.now()
            
            # Validate query
            if not query or not isinstance(query, str) or not query.strip():
                self.logger.warning("⚠️  Invalid query provided to SupabaseContextualCompression retrieve")
                return []
            
            # Adjust parameters for urgent queries
            if is_urgent:
                limit = min(self.k, 5)  # Fewer results for speed
            else:
                limit = self.k
            
            self.logger.info(f"🔍 Performing contextual compression search for: '{query[:50]}...'")
            
            # Search both collections with vector similarity
            bugs_results = self.bugs_retriever.vector_search(query, k=limit)
            pcr_results = self.pcr_retriever.vector_search(query, k=limit)
            
            # Combine and deduplicate results
            all_results = []
            seen_keys = set()
            
            # Process bugs results
            for result in bugs_results:
                # The result structure from SupabaseRetriever is:
                # {'content': 'Title: ...\n\nDescription: ...', 'metadata': {...}, 'source': '...', 'score': ...}
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                title = metadata.get('title', '')
                description = metadata.get('description', '')
                key = metadata.get('key', metadata.get('id', ''))
                
                if content and key not in seen_keys:
                    all_results.append({
                        'content': content,
                        'metadata': {
                            'key': key,
                            'title': title,
                            'description': description,
                            'source': 'bugs'
                        },
                        'score': result.get('score', 0.5),  # Use actual score from retriever
                        'source': 'bugs'
                    })
                    seen_keys.add(key)
            
            # Process PCR results
            for result in pcr_results:
                # The result structure from SupabaseRetriever is:
                # {'content': 'Title: ...\n\nDescription: ...', 'metadata': {...}, 'source': '...', 'score': ...}
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                title = metadata.get('title', '')
                description = metadata.get('description', '')
                key = metadata.get('key', metadata.get('id', ''))
                
                if content and key not in seen_keys:
                    all_results.append({
                        'content': content,
                        'metadata': {
                            'key': key,
                            'title': title,
                            'description': description,
                            'source': 'pcr'
                        },
                        'score': result.get('score', 0.5),  # Use actual score from retriever
                        'source': 'pcr'
                    })
                    seen_keys.add(key)
            
            # Sort by score and limit results
            all_results.sort(key=lambda x: x['score'], reverse=True)
            final_results = all_results[:limit]
            
            processing_time = measure_performance(start_time)
            self.logger.info(f"✅ Contextual compression search completed: {len(final_results)} results in {processing_time:.2f}s")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"❌ Contextual compression search failed: {e}")
            return []
    
    def process(self, state: AgentState) -> AgentState:
        """Process state using contextual compression retrieval."""
        try:
            query = state['query']
            is_urgent = state.get('production_incident', False)
            
            # Perform retrieval
            results = self.retrieve(query, is_urgent)
            
            # Update state
            state['retrieved_contexts'] = results
            state['retrieval_method'] = 'supabase_contextual_compression'
            state['retrieval_metadata'] = {
                'agent': 'SupabaseContextualCompression',
                'num_results': len(results),
                'method_type': 'vector_similarity',
                'source': 'supabase',
                'is_urgent': is_urgent
            }
            
            return state
            
        except Exception as e:
            self.logger.error(f"❌ SupabaseContextualCompression processing failed: {e}")
            return state

class SupabaseEnsembleAgent:
    """Supabase-based ensemble agent combining multiple retrieval methods."""
    
    def __init__(self, bugs_retriever, pcr_retriever, rag_llm, bm25_agent, contextual_compression_agent, k=10):
        self.bugs_retriever = bugs_retriever
        self.pcr_retriever = pcr_retriever
        self.rag_llm = rag_llm
        self.bm25_agent = bm25_agent
        self.contextual_compression_agent = contextual_compression_agent
        self.k = k
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logger = logging.getLogger('SupabaseEnsembleAgent')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def retrieve(self, query: str, is_urgent: bool = False) -> List[Dict[str, Any]]:
        """Perform ensemble search combining multiple methods."""
        try:
            start_time = datetime.now()
            
            # Validate query
            if not query or not isinstance(query, str) or not query.strip():
                self.logger.warning("⚠️  Invalid query provided to SupabaseEnsemble retrieve")
                return []
            
            self.logger.info(f"🔍 Performing ensemble search for: '{query[:50]}...'")
            
            # Get results from multiple methods
            all_results = []
            methods_used = []
            
            # 1. BM25 search
            if self.bm25_agent:
                try:
                    bm25_results = self.bm25_agent.retrieve(query, is_urgent)
                    all_results.extend(bm25_results)
                    methods_used.append('bm25')
                    self.logger.info(f"   BM25: {len(bm25_results)} results")
                except Exception as e:
                    self.logger.warning(f"   BM25 failed: {e}")
            
            # 2. Contextual compression search
            if self.contextual_compression_agent:
                try:
                    cc_results = self.contextual_compression_agent.retrieve(query, is_urgent)
                    all_results.extend(cc_results)
                    methods_used.append('contextual_compression')
                    self.logger.info(f"   ContextualCompression: {len(cc_results)} results")
                except Exception as e:
                    self.logger.warning(f"   ContextualCompression failed: {e}")
            
            # 3. Hybrid search
            try:
                bugs_hybrid = self.bugs_retriever.hybrid_search(query, k=self.k)
                pcr_hybrid = self.pcr_retriever.hybrid_search(query, k=self.k)
                
                # Process hybrid results
                for result in bugs_hybrid:
                    # The result structure from SupabaseRetriever is:
                    # {'content': 'Title: ...\n\nDescription: ...', 'metadata': {...}, 'source': '...', 'score': ...}
                    content = result.get('content', '')
                    metadata = result.get('metadata', {})
                    title = metadata.get('title', '')
                    description = metadata.get('description', '')
                    key = metadata.get('key', metadata.get('id', ''))
                    
                    if content:
                        all_results.append({
                            'content': content,
                            'metadata': {
                                'key': key,
                                'title': title,
                                'description': description,
                                'source': 'bugs'
                            },
                            'score': result.get('score', 0.5),  # Use actual score from retriever
                            'source': 'bugs'
                        })
                
                for result in pcr_hybrid:
                    # The result structure from SupabaseRetriever is:
                    # {'content': 'Title: ...\n\nDescription: ...', 'metadata': {...}, 'source': '...', 'score': ...}
                    content = result.get('content', '')
                    metadata = result.get('metadata', {})
                    title = metadata.get('title', '')
                    description = metadata.get('description', '')
                    key = metadata.get('key', metadata.get('id', ''))
                    
                    if content:
                        all_results.append({
                            'content': content,
                            'metadata': {
                                'key': key,
                                'title': title,
                                'description': description,
                                'source': 'pcr'
                            },
                            'score': result.get('score', 0.5),  # Use actual score from retriever
                            'source': 'pcr'
                        })
                
                methods_used.append('hybrid')
                self.logger.info(f"   Hybrid: {len(bugs_hybrid) + len(pcr_hybrid)} results")
                
            except Exception as e:
                self.logger.warning(f"   Hybrid search failed: {e}")
            
            # Deduplicate results by key
            unique_results = {}
            for result in all_results:
                key = result['metadata'].get('key', '')
                if key and key not in unique_results:
                    unique_results[key] = result
                elif not key:
                    # For results without keys, use content hash
                    content_hash = hash(result['content'])
                    if content_hash not in unique_results:
                        unique_results[content_hash] = result
            
            # Sort by score and limit results
            final_results = list(unique_results.values())
            final_results.sort(key=lambda x: x['score'], reverse=True)
            final_results = final_results[:self.k]
            
            processing_time = measure_performance(start_time)
            self.logger.info(f"✅ Ensemble search completed: {len(final_results)} results in {processing_time:.2f}s")
            self.logger.info(f"   Methods used: {', '.join(methods_used)}")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"❌ Ensemble search failed: {e}")
            return []
    
    def process(self, state: AgentState) -> AgentState:
        """Process state using ensemble retrieval."""
        try:
            query = state['query']
            is_urgent = state.get('production_incident', False)
            
            # Perform retrieval
            results = self.retrieve(query, is_urgent)
            
            # Update state
            state['retrieved_contexts'] = results
            state['retrieval_method'] = 'supabase_ensemble'
            state['retrieval_metadata'] = {
                'agent': 'SupabaseEnsemble',
                'num_results': len(results),
                'method_type': 'ensemble',
                'source': 'supabase',
                'methods_used': ['bm25', 'contextual_compression', 'hybrid'],
                'primary_source': 'supabase'
            }
            
            return state
            
        except Exception as e:
            self.logger.error(f"❌ SupabaseEnsemble processing failed: {e}")
            return state
