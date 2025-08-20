#!/usr/bin/env python3
"""
BM25Agent - Keyword-based search using BM25 algorithm.
Handles specific ticket references and keyword queries.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain_core.messages import AIMessage
from langchain_community.retrievers import BM25Retriever
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

class BM25Agent:
    """Agent for keyword-based search using BM25 algorithm."""
    
    def __init__(self, vectorstore, rag_llm, k=10):
        self.vectorstore = vectorstore
        self.rag_llm = rag_llm
        self.k = k
        self.bm25_retriever = None
        self.logger = self._setup_logger()
        self._setup_bm25_retriever()
    
    def _setup_logger(self):
        """Setup logger for BM25Agent."""
        logger = logging.getLogger('BM25Agent')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _validate_documents(self, docs):
        """Validate documents for BM25 processing."""
        if not docs:
            self.logger.warning("No documents provided for BM25 validation")
            return False, "No documents found"
        
        if len(docs) == 0:
            self.logger.warning("Empty document list provided")
            return False, "Document list is empty"
        
        # Use the shared filter function
        valid_docs = filter_empty_documents(docs)
        
        if len(valid_docs) == 0:
            return False, "No documents with valid content found"
        
        if len(valid_docs) < 2:
            return False, f"Insufficient documents for BM25 (need ≥2, found {len(valid_docs)})"
        
        # Check average content length
        total_chars = sum(len(doc.page_content.strip()) for doc in valid_docs)
        avg_content_length = total_chars / len(valid_docs)
        
        if avg_content_length < 10:
            return False, f"Documents too short for meaningful BM25 scoring (avg: {avg_content_length:.1f} chars)"
        
        self.logger.info(f"Document validation passed: {len(valid_docs)}/{len(docs)} valid docs, avg length: {avg_content_length:.1f} chars")
        return True, f"Validation passed: {len(valid_docs)} valid documents"
    
    def _filter_valid_documents(self, docs):
        """Filter documents to only include those with valid content."""
        return filter_empty_documents(docs)
    
    def _setup_bm25_retriever(self):
        """Setup BM25 retriever from vectorstore documents with comprehensive validation."""
        try:
            self.logger.info("Setting up BM25 retriever...")
            
            # Check if vectorstore supports similarity search
            if not hasattr(self.vectorstore, 'similarity_search'):
                self.logger.warning("Vectorstore doesn't support similarity_search method")
                self.bm25_retriever = None
                return
            
            # Try to get documents from vectorstore
            try:
                self.logger.info("Fetching sample documents from vectorstore...")
                sample_docs = self.vectorstore.similarity_search(
                    "sample query", k=100  # Get more docs for better BM25 performance
                )
                self.logger.info(f"Retrieved {len(sample_docs)} documents from vectorstore")
                
            except Exception as fetch_error:
                self.logger.error(f"Failed to fetch documents from vectorstore: {fetch_error}")
                self.bm25_retriever = None
                return
            
            # Validate documents
            is_valid, validation_message = self._validate_documents(sample_docs)
            if not is_valid:
                self.logger.warning(f"Document validation failed: {validation_message}")
                self.logger.info("BM25 retriever will not be available - falling back to vector search")
                self.bm25_retriever = None
                return
            
            # Filter to only valid documents
            valid_docs = self._filter_valid_documents(sample_docs)
            if len(valid_docs) < 2:
                self.logger.warning(f"Insufficient valid documents after filtering: {len(valid_docs)}")
                self.bm25_retriever = None
                return
            
            # Create BM25 retriever with error handling
            try:
                self.logger.info(f"Creating BM25 retriever with {len(valid_docs)} valid documents...")
                
                # Additional safety check: ensure we have diverse content
                unique_contents = set(doc.page_content.strip()[:100] for doc in valid_docs)
                if len(unique_contents) < max(2, len(valid_docs) // 2):
                    self.logger.warning("Documents appear to have very similar content - may cause BM25 scoring issues")
                
                self.bm25_retriever = BM25Retriever.from_documents(
                    valid_docs, k=self.k
                )
                
                self.logger.info(f"✅ BM25 retriever successfully initialized with {len(valid_docs)} documents")
                print(f"✅ BM25 retriever initialized with {len(valid_docs)} documents")
                
            except ZeroDivisionError as zde:
                self.logger.error(f"ZeroDivisionError in BM25 creation: {zde}")
                self.logger.error("This usually indicates identical or very similar documents")
                self.bm25_retriever = None
                print("⚠️  BM25 setup failed due to division by zero - documents may be too similar")
                
            except Exception as bm25_error:
                self.logger.error(f"Error creating BM25 retriever: {bm25_error}")
                self.bm25_retriever = None
                print(f"⚠️  Error setting up BM25 retriever: {bm25_error}")
                
        except Exception as e:
            self.logger.error(f"Unexpected error in BM25 setup: {e}")
            self.bm25_retriever = None
            print(f"⚠️  Unexpected error setting up BM25 retriever: {e}")
    
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Perform BM25-based retrieval with fallback and content filtering."""
        try:
            # Validate query
            if not query or not isinstance(query, str) or not query.strip():
                self.logger.warning("Invalid query provided to BM25 retrieve")
                return []
            
            if self.bm25_retriever:
                try:
                    self.logger.info(f"Using BM25 retriever for query: '{query[:50]}...'")
                    # Use BM25 retriever
                    docs = self.bm25_retriever.get_relevant_documents(query)
                    self.logger.info(f"BM25 retriever returned {len(docs)} documents")
                    
                except Exception as bm25_error:
                    self.logger.error(f"BM25 retrieval failed: {bm25_error}")
                    # Fallback to vectorstore similarity search
                    self.logger.info("Falling back to vectorstore similarity search")
                    docs = self.vectorstore.similarity_search(query, k=self.k)
                    
            else:
                self.logger.info("BM25 retriever not available, using vectorstore similarity search")
                # Fallback to vectorstore similarity search
                docs = self.vectorstore.similarity_search(query, k=self.k)
            
            # Filter out empty documents before processing
            valid_docs = filter_empty_documents(docs)
            self.logger.info(f"Filtered {len(docs)} -> {len(valid_docs)} valid documents")
            
            # Convert to standardized format
            results = []
            for doc in valid_docs:
                if hasattr(doc, 'page_content') and doc.page_content and doc.page_content.strip():
                    results.append({
                        'content': doc.page_content,
                        'metadata': doc.metadata if hasattr(doc, 'metadata') else {},
                        'source': 'bm25' if self.bm25_retriever else 'vector_fallback',
                        'score': getattr(doc, 'score', 1.0)
                    })
            
            self.logger.info(f"BM25 retrieve returning {len(results)} results with valid content")
            return results
            
        except Exception as e:
            self.logger.error(f"BM25 retrieval error: {e}")
            print(f"❌ BM25 retrieval error: {e}")
            return []
    
    def process(self, state: AgentState) -> AgentState:
        """Process query using BM25 agent."""
        start_time = datetime.now()
        
        query = state.get('query', '')
        self.logger.info(f"BM25 Agent processing query: '{query}'")
        print(f"🔍 BM25 Agent processing: '{query}'")
        
        # Perform retrieval
        retrieved_contexts = self.retrieve(query)
        
        # Update state
        state['retrieved_contexts'] = retrieved_contexts
        state['retrieval_method'] = 'BM25'
        state['retrieval_metadata'] = {
            'agent': 'BM25',
            'num_results': len(retrieved_contexts),
            'processing_time': measure_performance(start_time),
            'method_type': 'keyword_based',
            'bm25_available': self.bm25_retriever is not None,
            'source': 'bm25' if self.bm25_retriever else 'vector_fallback',
            'content_filtered': True
        }
        
        # Add processing message
        method_used = "BM25 keyword search" if self.bm25_retriever else "vector similarity (BM25 fallback)"
        state['messages'].append(AIMessage(
            content=f"BM25 Agent retrieved {len(retrieved_contexts)} documents using {method_used} (content filtered)"
        ))
        
        processing_time = measure_performance(start_time)
        self.logger.info(f"BM25 Agent completed in {processing_time:.2f}s with {len(retrieved_contexts)} results")
        print(f"✅ BM25 Agent completed: {len(retrieved_contexts)} results in {processing_time:.2f}s")
        
        return state