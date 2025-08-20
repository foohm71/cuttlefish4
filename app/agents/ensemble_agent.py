#!/usr/bin/env python3
"""
EnsembleAgent - Comprehensive retrieval using ensemble of multiple methods.
Combines BM25, ContextualCompression, naive, and multi-query retrievers.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever

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

class EnsembleAgent:
    """Agent for comprehensive retrieval using ensemble of multiple methods."""
    
    def __init__(self, vectorstore, rag_llm, bm25_agent, contextual_compression_agent, k=10):
        self.vectorstore = vectorstore
        self.rag_llm = rag_llm
        self.bm25_agent = bm25_agent
        self.contextual_compression_agent = contextual_compression_agent
        self.k = k
        self.ensemble_retriever = None
        self.naive_retriever = None
        self.multi_query_retriever = None
        self._setup_ensemble_retriever()
    
    def _setup_ensemble_retriever(self):
        """Setup ensemble retriever combining multiple methods."""
        try:
            # 1. Naive retriever - simple vector similarity
            self.naive_retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.k})
            
            # 2. Multi-query retriever for query expansion
            self.multi_query_retriever = MultiQueryRetriever.from_llm(
                retriever=self.naive_retriever,
                llm=self.rag_llm
            )
            
            # Collect all available retrievers
            retrievers = []
            weights = []
            method_names = []
            
            # Add naive retriever (always available)
            retrievers.append(self.naive_retriever)
            weights.append(0.25)
            method_names.append("Naive")
            
            # Add multi-query retriever (always available)
            retrievers.append(self.multi_query_retriever)
            weights.append(0.25)
            method_names.append("Multi-Query")
            
            # Add contextual compression retriever if available
            if self.contextual_compression_agent.compression_retriever:
                retrievers.append(self.contextual_compression_agent.compression_retriever)
                weights.append(0.25)
                method_names.append("ContextualCompression")
            
            # Add BM25 if available
            if self.bm25_agent.bm25_retriever:
                retrievers.append(self.bm25_agent.bm25_retriever)
                weights.append(0.25)
                method_names.append("BM25")
            
            # Normalize weights to sum to 1.0
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]
            
            # Create ensemble retriever
            if len(retrievers) > 1:
                self.ensemble_retriever = EnsembleRetriever(
                    retrievers=retrievers,
                    weights=weights
                )
                print(f"✅ Ensemble retriever initialized with {len(retrievers)} methods:")
                for name, weight in zip(method_names, weights):
                    print(f"   • {name}: {weight:.2f}")
            else:
                # Fallback to single retriever
                self.ensemble_retriever = self.naive_retriever
                print("✅ Fallback to single naive retriever")
                
        except Exception as e:
            print(f"⚠️  Error setting up Ensemble: {e}")
            # Fallback to basic retriever
            self.ensemble_retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.k})
            print("✅ Fallback to basic vector retriever")
    
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Perform ensemble retrieval using multiple methods."""
        try:
            # Validate query
            if not query or not isinstance(query, str) or not query.strip():
                print("⚠️  Invalid query provided to Ensemble retrieve")
                return []
            
            # Use individual agents directly
            print("🔄 Using individual agent ensemble")
            
            all_results = []
            
            # Get results from BM25 agent
            try:
                bm25_results = self.bm25_agent.retrieve(query)
                for result in bm25_results[:3]:  # Limit from each method
                    if result.get('content', '').strip():
                        result['source'] = 'bm25_ensemble'
                        all_results.append(result)
            except Exception as bm25_error:
                print(f"⚠️  BM25 ensemble failed: {bm25_error}")
            
            # Get results from ContextualCompression agent
            try:
                comp_results = self.contextual_compression_agent.retrieve(query)
                for result in comp_results[:3]:  # Limit from each method
                    if result.get('content', '').strip():
                        result['source'] = 'compression_ensemble'
                        all_results.append(result)
            except Exception as comp_error:
                print(f"⚠️  ContextualCompression ensemble failed: {comp_error}")
            
            # Get results from naive retriever with content extraction
            try:
                naive_docs = self.naive_retriever.get_relevant_documents(query)
                for doc in naive_docs[:3]:  # Limit from each method
                    content = extract_content_from_document(doc)
                    if content and content.strip():
                        metadata = {k: v for k, v in doc.metadata.items() 
                                  if k not in ['title', 'description']} if hasattr(doc, 'metadata') and doc.metadata else {}
                        
                        all_results.append({
                            'content': content,
                            'metadata': metadata,
                            'source': 'naive_ensemble',
                            'score': getattr(doc, 'score', 0.7)
                        })
            except Exception as naive_error:
                print(f"⚠️  Naive ensemble failed: {naive_error}")
            
            # Get results from multi-query retriever with content extraction
            try:
                multi_docs = self.multi_query_retriever.get_relevant_documents(query)
                for doc in multi_docs[:3]:  # Limit from each method
                    content = extract_content_from_document(doc)
                    if content and content.strip():
                        metadata = {k: v for k, v in doc.metadata.items() 
                                  if k not in ['title', 'description']} if hasattr(doc, 'metadata') and doc.metadata else {}
                        
                        all_results.append({
                            'content': content,
                            'metadata': metadata,
                            'source': 'multi_query_ensemble',
                            'score': getattr(doc, 'score', 0.8)
                        })
            except Exception as multi_error:
                print(f"⚠️  Multi-query ensemble failed: {multi_error}")
            
            # Deduplicate and return top results
            deduplicated_results = self._deduplicate_results(all_results)
            
            if deduplicated_results:
                print(f"✅ Individual agent ensemble: {len(deduplicated_results)} deduplicated results")
                return deduplicated_results[:self.k]
            
            # FALLBACK: Try original ensemble retriever with LangChain wrapper
            print("🔄 Final fallback to LangChain ensemble retriever")
            
            if self.ensemble_retriever:
                try:
                    docs = self.ensemble_retriever.get_relevant_documents(query)
                    
                    # Extract content and convert to standardized format
                    fallback_results = []
                    for doc in docs:
                        content = extract_content_from_document(doc)
                        if content and content.strip():
                            metadata = {k: v for k, v in doc.metadata.items() 
                                      if k not in ['title', 'description']} if hasattr(doc, 'metadata') and doc.metadata else {}
                            
                            fallback_results.append({
                                'content': content,
                                'metadata': metadata,
                                'source': 'langchain_ensemble_extracted',
                                'score': getattr(doc, 'score', 0.6)
                            })
                    
                    deduplicated_fallback = self._deduplicate_results(fallback_results)
                    print(f"✅ LangChain ensemble fallback: {len(deduplicated_fallback)} results")
                    return deduplicated_fallback[:self.k]
                    
                except Exception as ensemble_error:
                    print(f"⚠️  LangChain ensemble fallback failed: {ensemble_error}")
            
            print("❌ All ensemble methods failed")
            return []
            
        except Exception as e:
            print(f"❌ Ensemble retrieval error: {e}")
            return []
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Deduplicate results based on content similarity."""
        if not results:
            return []
        
        deduplicated = []
        seen_content_hashes = set()
        
        for result in results:
            content = result.get('content', '')
            if content and content.strip():
                # Use first 200 characters for deduplication (same as original logic)
                content_hash = hash(content[:200])
                
                if content_hash not in seen_content_hashes:
                    deduplicated.append(result)
                    seen_content_hashes.add(content_hash)
        
        return deduplicated
    
    def process(self, state: AgentState) -> AgentState:
        """Process query using Ensemble agent."""
        start_time = datetime.now()
        
        print(f"🔗 Ensemble Agent processing: '{state['query']}'")
        print("   Using comprehensive multi-method retrieval...")
        
        # Perform retrieval
        retrieved_contexts = self.retrieve(state['query'])
        
        # Update state
        state['retrieved_contexts'] = retrieved_contexts
        state['retrieval_method'] = 'Ensemble'
        
        # Build methods list for metadata (only include what's actually available)
        methods_used = []
        if self.bm25_agent.bm25_retriever:
            methods_used.append('bm25')
        if self.contextual_compression_agent.compression_retriever:
            methods_used.append('contextual_compression')
        methods_used.extend(['naive', 'multi_query'])
        
        state['retrieval_metadata'] = {
            'agent': 'Ensemble',
            'num_results': len(retrieved_contexts),
            'processing_time': measure_performance(start_time),
            'method_type': 'multi_method_ensemble',
            'methods_used': methods_used,
            'primary_source': retrieved_contexts[0].get('source') if retrieved_contexts else 'none'
        }
        
        # Add processing message
        primary_method = "Individual agent ensemble"
        state['messages'].append(AIMessage(
            content=f"Ensemble Agent retrieved {len(retrieved_contexts)} documents using {primary_method} ({', '.join(methods_used)})"
        ))
        
        print(f"✅ Ensemble Agent completed: {len(retrieved_contexts)} results in {measure_performance(start_time):.2f}s")
        return state