#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
ContextualCompressionAgent - Fast semantic retrieval with contextual compression.
Handles production incidents and general troubleshooting with speed priority.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_core.documents import Document

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

class ContextualCompressionAgent:
    """Agent for fast semantic retrieval with direct vectorstore and contextual compression."""
    
    def __init__(self, vectorstore, rag_llm, k=10):
        self.vectorstore = vectorstore
        self.rag_llm = rag_llm
        self.k = k
        self.compression_retriever = None
        self._setup_compression_retriever()
    
    def _setup_compression_retriever(self):
        """Setup contextual compression retriever with Cohere reranking."""
        try:
            # Base retriever from vectorstore
            base_retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.k * 2})  # Get more for reranking
            
            # Try to setup Cohere reranking
            try:
                compressor = CohereRerank(model="rerank-v3.5")
                self.compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=base_retriever
                )
                print("✅ ContextualCompression with Cohere reranking initialized")
                
            except Exception as cohere_error:
                print(f"⚠️  Cohere reranking unavailable: {cohere_error}")
                print("🔄 Using LLM-based contextual compression instead")
                
                # Fallback to LLM-based compression
                compressor = LLMChainExtractor.from_llm(self.rag_llm)
                self.compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=base_retriever
                )
                print("✅ ContextualCompression with LLM compression initialized")
                
        except Exception as e:
            print(f"⚠️  Error setting up ContextualCompression: {e}")
            # Fallback to basic retriever
            self.compression_retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.k})
            print("✅ Fallback to basic vector retriever")
    
    def retrieve(self, query: str, is_urgent: bool = False) -> List[Dict[str, Any]]:
        """Perform contextual compression retrieval with direct vectorstore client."""
        try:
            # Validate query
            if not query or not isinstance(query, str) or not query.strip():
                print("⚠️  Invalid query provided to ContextualCompression retrieve")
                return []
            
            # Adjust parameters for urgent queries
            if is_urgent:
                # For production incidents, prioritize speed
                limit = min(self.k, 5)  # Fewer results for speed
            else:
                limit = self.k
            
            # Try compression retriever with LangChain wrapper
            print("🔄 Using compression retriever with LangChain wrapper")
            
            # Get base documents first and check content
            base_retriever = self.vectorstore.as_retriever(search_kwargs={"k": limit * 2})
            base_docs = base_retriever.get_relevant_documents(query)
            
            # Extract content from base documents
            valid_docs = []
            for doc in base_docs:
                content = extract_content_from_document(doc)
                if content and content.strip():
                    # Update the document with extracted content
                    doc.page_content = content
                    valid_docs.append(doc)
            
            if not valid_docs:
                print("⚠️  No valid documents after content extraction for compression")
                return []
            
            # Try compression with valid documents
            try:
                if hasattr(self.compression_retriever, 'get_relevant_documents'):
                    compressed_docs = self.compression_retriever.get_relevant_documents(query)
                else:
                    compressed_docs = self.compression_retriever.invoke(query)
                
                # Convert to standardized format
                results = []
                for doc in compressed_docs[:limit]:
                    content = extract_content_from_document(doc)
                    if content and content.strip():
                        metadata = {k: v for k, v in doc.metadata.items() 
                                  if k not in ['title', 'description']} if hasattr(doc, 'metadata') and doc.metadata else {}
                        
                        results.append({
                            'content': content,
                            'metadata': metadata,
                            'source': 'contextual_compression_extracted',
                            'score': getattr(doc, 'relevance_score', getattr(doc, 'score', 0.8))
                        })
                
                if results:
                    print(f"✅ Compression retriever with content extraction: {len(results)} results")
                    return results
                
            except Exception as compression_error:
                print(f"⚠️  Compression retrieval failed: {compression_error}")
            
            # FALLBACK: Basic vector search with content extraction
            print("🔄 Final fallback to basic vector search with content extraction")
            
            fallback_results = []
            for doc in valid_docs[:limit]:
                content = extract_content_from_document(doc)
                if content and content.strip():
                    metadata = {k: v for k, v in doc.metadata.items() 
                              if k not in ['title', 'description']} if hasattr(doc, 'metadata') and doc.metadata else {}
                    
                    fallback_results.append({
                        'content': content,
                        'metadata': metadata,
                        'source': 'vector_fallback_extracted',
                        'score': getattr(doc, 'score', 0.7)
                    })
            
            print(f"✅ Vector fallback with content extraction: {len(fallback_results)} results")
            return fallback_results
            
        except Exception as e:
            print(f"❌ ContextualCompression retrieval error: {e}")
            return []
    
    def process(self, state: AgentState) -> AgentState:
        """Process query using ContextualCompression agent with direct vectorstore client."""
        start_time = datetime.now()
        
        is_urgent = state.get('production_incident', False)
        urgency_label = "[URGENT]" if is_urgent else ""
        
        print(f"⚡ ContextualCompression Agent {urgency_label} processing: '{state['query']}'")
        
        # Perform retrieval with urgency consideration
        retrieved_contexts = self.retrieve(state['query'], is_urgent=is_urgent)
        
        # Update state
        state['retrieved_contexts'] = retrieved_contexts
        state['retrieval_method'] = 'ContextualCompression'
        state['retrieval_metadata'] = {
            'agent': 'ContextualCompression',
            'num_results': len(retrieved_contexts),
            'processing_time': measure_performance(start_time),
            'method_type': 'semantic_with_reranking',
            'is_urgent': is_urgent,
            'primary_source': retrieved_contexts[0].get('source') if retrieved_contexts else 'none'
        }
        
        # Add processing message
        urgency_note = " (urgent mode)" if is_urgent else ""
        primary_method = "Compression retriever"
        state['messages'].append(AIMessage(
            content=f"ContextualCompression Agent retrieved {len(retrieved_contexts)} documents using {primary_method} with content extraction{urgency_note}"
        ))
        
        print(f"✅ ContextualCompression Agent completed: {len(retrieved_contexts)} results in {measure_performance(start_time):.2f}s")
        return state