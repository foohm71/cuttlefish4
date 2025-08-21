#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
RAG tools module that maps retrieval functions to agent tools.
Provides a unified interface for all retrieval operations.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

# Handle both relative imports (normal usage) and absolute imports (Jupyter notebooks)
try:
    # Try relative import first (normal module usage)
    from ..rag import SupabaseRetriever, create_bugs_retriever, create_pcr_retriever
except ImportError:
    # Fallback to absolute import (Jupyter notebook usage)
    try:
        from rag.supabase_retriever import SupabaseRetriever, create_bugs_retriever, create_pcr_retriever
    except ImportError:
        # Final fallback: add current directory to path and import
        import os
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from rag.supabase_retriever import SupabaseRetriever, create_bugs_retriever, create_pcr_retriever

class RAGTools:
    """
    Unified RAG tools interface that wraps Supabase retrievers.
    Maps each RAG retrieval function to a tool that agents can use.
    """
    
    def __init__(self, default_collection: str = 'bugs'):
        """
        Initialize RAG tools.
        
        Args:
            default_collection: Default collection to use ('bugs' or 'pcr')
        """
        self.default_collection = default_collection
        self.bugs_retriever = None
        self.pcr_retriever = None
        self.logger = self._setup_logger()
        
        # Initialize retrievers lazily
        self._initialized = False
    
    def _setup_logger(self):
        """Setup logger for RAGTools."""
        logger = logging.getLogger('RAGTools')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _ensure_initialized(self):
        """Ensure retrievers are initialized."""
        if not self._initialized:
            try:
                self.bugs_retriever = create_bugs_retriever()
                self.pcr_retriever = create_pcr_retriever()
                self._initialized = True
                self.logger.info("✅ RAG tools initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize RAG tools: {e}")
                raise
    
    def _get_retriever(self, collection: Optional[str] = None) -> SupabaseRetriever:
        """Get appropriate retriever for collection."""
        self._ensure_initialized()
        
        target_collection = collection or self.default_collection
        
        if target_collection == 'bugs':
            return self.bugs_retriever
        elif target_collection == 'pcr':
            return self.pcr_retriever
        else:
            raise ValueError(f"Invalid collection: {target_collection}. Must be 'bugs' or 'pcr'")
    
    # Vector Search Tools
    
    def vector_search_bugs(
        self, 
        query: str, 
        k: int = 10, 
        similarity_threshold: float = 0.2,  # More reasonable threshold for semantic similarity
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Vector similarity search in bugs collection.
        
        Args:
            query: Search query
            k: Number of results to return
            similarity_threshold: Minimum similarity score
            filters: Additional filters
        
        Returns:
            List of relevant bug documents
        """
        try:
            retriever = self._get_retriever('bugs')
            results = retriever.vector_search(query, k, similarity_threshold, filters)
            self.logger.info(f"Vector search (bugs): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Vector search (bugs) failed: {e}")
            return []
    
    def vector_search_pcr(
        self, 
        query: str, 
        k: int = 10, 
        similarity_threshold: float = 0.2,  # More reasonable threshold for semantic similarity
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Vector similarity search in PCR collection.
        
        Args:
            query: Search query
            k: Number of results to return
            similarity_threshold: Minimum similarity score
            filters: Additional filters
        
        Returns:
            List of relevant PCR documents
        """
        try:
            retriever = self._get_retriever('pcr')
            results = retriever.vector_search(query, k, similarity_threshold, filters)
            self.logger.info(f"Vector search (pcr): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Vector search (pcr) failed: {e}")
            return []
    
    # Keyword Search Tools (BM25-style)
    
    def keyword_search_bugs(
        self, 
        query: str, 
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Keyword/BM25-style search in bugs collection.
        
        Args:
            query: Search query
            k: Number of results to return
            filters: Additional filters
        
        Returns:
            List of relevant bug documents
        """
        try:
            retriever = self._get_retriever('bugs')
            results = retriever.keyword_search(query, k, filters)
            self.logger.info(f"Keyword search (bugs): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Keyword search (bugs) failed: {e}")
            return []
    
    def keyword_search_pcr(
        self, 
        query: str, 
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Keyword/BM25-style search in PCR collection.
        
        Args:
            query: Search query
            k: Number of results to return
            filters: Additional filters
        
        Returns:
            List of relevant PCR documents
        """
        try:
            retriever = self._get_retriever('pcr')
            results = retriever.keyword_search(query, k, filters)
            self.logger.info(f"Keyword search (pcr): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Keyword search (pcr) failed: {e}")
            return []
    
    # Hybrid Search Tools
    
    def hybrid_search_bugs(
        self, 
        query: str, 
        k: int = 10,
        similarity_threshold: float = 0.2,  # More reasonable threshold for semantic similarity
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Hybrid search combining vector and keyword search in bugs collection.
        
        Args:
            query: Search query
            k: Number of results to return
            similarity_threshold: Minimum similarity score for vector search
            vector_weight: Weight for vector search results
            keyword_weight: Weight for keyword search results
            filters: Additional filters
        
        Returns:
            List of relevant bug documents with combined scoring
        """
        try:
            retriever = self._get_retriever('bugs')
            results = retriever.hybrid_search(query, k, similarity_threshold, vector_weight, keyword_weight, filters)
            self.logger.info(f"Hybrid search (bugs): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Hybrid search (bugs) failed: {e}")
            return []
    
    def hybrid_search_pcr(
        self, 
        query: str, 
        k: int = 10,
        similarity_threshold: float = 0.2,  # More reasonable threshold for semantic similarity
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Hybrid search combining vector and keyword search in PCR collection.
        
        Args:
            query: Search query
            k: Number of results to return
            similarity_threshold: Minimum similarity score for vector search
            vector_weight: Weight for vector search results
            keyword_weight: Weight for keyword search results
            filters: Additional filters
        
        Returns:
            List of relevant PCR documents with combined scoring
        """
        try:
            retriever = self._get_retriever('pcr')
            results = retriever.hybrid_search(query, k, similarity_threshold, vector_weight, keyword_weight, filters)
            self.logger.info(f"Hybrid search (pcr): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Hybrid search (pcr) failed: {e}")
            return []
    
    # BM25 Tools (alias to keyword search)
    
    def bm25_search_bugs(
        self, 
        query: str, 
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: BM25 search in bugs collection (alias to keyword search).
        
        Args:
            query: Search query
            k: Number of results to return
            filters: Additional filters
        
        Returns:
            List of relevant bug documents
        """
        return self.keyword_search_bugs(query, k, filters)
    
    def bm25_search_pcr(
        self, 
        query: str, 
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: BM25 search in PCR collection (alias to keyword search).
        
        Args:
            query: Search query
            k: Number of results to return
            filters: Additional filters
        
        Returns:
            List of relevant PCR documents
        """
        return self.keyword_search_pcr(query, k, filters)
    
    # Contextual Compression Tools (using vector search with higher similarity)
    
    def contextual_compression_search_bugs(
        self, 
        query: str, 
        k: int = 5,  # Fewer results for compression
        similarity_threshold: float = 0.8,  # Higher threshold
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Contextual compression search in bugs collection (high-quality vector search).
        
        Args:
            query: Search query
            k: Number of results to return (typically fewer for compression)
            similarity_threshold: Minimum similarity score (higher for compression)
            filters: Additional filters
        
        Returns:
            List of highly relevant bug documents
        """
        try:
            retriever = self._get_retriever('bugs')
            results = retriever.vector_search(query, k, similarity_threshold, filters)
            self.logger.info(f"Contextual compression search (bugs): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Contextual compression search (bugs) failed: {e}")
            return []
    
    def contextual_compression_search_pcr(
        self, 
        query: str, 
        k: int = 5,
        similarity_threshold: float = 0.8,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Tool: Contextual compression search in PCR collection (high-quality vector search).
        
        Args:
            query: Search query
            k: Number of results to return (typically fewer for compression)
            similarity_threshold: Minimum similarity score (higher for compression)
            filters: Additional filters
        
        Returns:
            List of highly relevant PCR documents
        """
        try:
            retriever = self._get_retriever('pcr')
            results = retriever.vector_search(query, k, similarity_threshold, filters)
            self.logger.info(f"Contextual compression search (pcr): {len(results)} results for '{query[:50]}...'")
            return results
        except Exception as e:
            self.logger.error(f"Contextual compression search (pcr) failed: {e}")
            return []
    
    # Ensemble Tools (combining multiple methods)
    
    def ensemble_search_bugs(
        self, 
        query: str, 
        k: int = 10,
        use_advanced: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Tool: Ensemble search combining multiple methods in bugs collection.
        
        Args:
            query: Search query
            k: Number of results to return
            use_advanced: Whether to use advanced ensemble (Multi-Query, Contextual Compression, etc.)
        
        Returns:
            List of relevant bug documents from multiple search methods
        """
        if use_advanced:
            return self._advanced_ensemble_search_bugs(query, k)
        
        try:
            all_results = []
            
            # Get results from different methods
            vector_results = self.vector_search_bugs(query, k//2)
            keyword_results = self.keyword_search_bugs(query, k//2)
            hybrid_results = self.hybrid_search_bugs(query, k//2)
            
            # Combine results
            for results in [vector_results, keyword_results, hybrid_results]:
                all_results.extend(results)
            
            # Simple deduplication based on metadata ID
            seen_ids = set()
            deduplicated = []
            
            for result in all_results:
                doc_id = result.get('metadata', {}).get('id') or result.get('metadata', {}).get('jira_id')
                if doc_id and doc_id not in seen_ids:
                    deduplicated.append(result)
                    seen_ids.add(doc_id)
                elif not doc_id:  # Keep results without IDs
                    deduplicated.append(result)
            
            # Sort by score and return top k
            deduplicated.sort(key=lambda x: x.get('score', 0), reverse=True)
            results = deduplicated[:k]
            
            self.logger.info(f"Ensemble search (bugs): {len(results)} deduplicated results for '{query[:50]}...'")
            return results
            
        except Exception as e:
            self.logger.error(f"Ensemble search (bugs) failed: {e}")
            return []
    
    def _advanced_ensemble_search_bugs(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Advanced ensemble search using sophisticated retrieval methods."""
        try:
            # Import advanced retrievers
            from ..rag.advanced_retrievers import create_advanced_ensemble_bugs
            
            # Create advanced ensemble retriever
            advanced_ensemble = create_advanced_ensemble_bugs()
            
            # Retrieve using advanced methods
            retrieval_results = advanced_ensemble.retrieve(query, k=k)
            
            # Convert RetrievalResult objects to standard format
            results = []
            for result in retrieval_results:
                formatted_result = {
                    'content': result.content,
                    'metadata': result.metadata,
                    'score': result.score,
                    'source': result.source,
                    'search_type': 'advanced_ensemble'
                }
                results.append(formatted_result)
            
            self.logger.info(f"Advanced ensemble search (bugs): {len(results)} results for '{query[:50]}...'")
            return results
            
        except Exception as e:
            self.logger.error(f"Advanced ensemble search (bugs) failed: {e}")
            # Fallback to simple ensemble
            return self.ensemble_search_bugs(query, k, use_advanced=False)
    
    def ensemble_search_pcr(
        self, 
        query: str, 
        k: int = 10,
        use_advanced: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Tool: Ensemble search combining multiple methods in PCR collection.
        
        Args:
            query: Search query
            k: Number of results to return
            use_advanced: Whether to use advanced ensemble (Multi-Query, Contextual Compression, etc.)
        
        Returns:
            List of relevant PCR documents from multiple search methods
        """
        if use_advanced:
            return self._advanced_ensemble_search_pcr(query, k)
        
        try:
            all_results = []
            
            # Get results from different methods
            vector_results = self.vector_search_pcr(query, k//2)
            keyword_results = self.keyword_search_pcr(query, k//2)
            hybrid_results = self.hybrid_search_pcr(query, k//2)
            
            # Combine results
            for results in [vector_results, keyword_results, hybrid_results]:
                all_results.extend(results)
            
            # Simple deduplication based on metadata ID
            seen_ids = set()
            deduplicated = []
            
            for result in all_results:
                doc_id = result.get('metadata', {}).get('id') or result.get('metadata', {}).get('jira_id')
                if doc_id and doc_id not in seen_ids:
                    deduplicated.append(result)
                    seen_ids.add(doc_id)
                elif not doc_id:  # Keep results without IDs
                    deduplicated.append(result)
            
            # Sort by score and return top k
            deduplicated.sort(key=lambda x: x.get('score', 0), reverse=True)
            results = deduplicated[:k]
            
            self.logger.info(f"Ensemble search (pcr): {len(results)} deduplicated results for '{query[:50]}...'")
            return results
            
        except Exception as e:
            self.logger.error(f"Ensemble search (pcr) failed: {e}")
            return []
    
    def _advanced_ensemble_search_pcr(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Advanced ensemble search using sophisticated retrieval methods."""
        try:
            # Import advanced retrievers
            from ..rag.advanced_retrievers import create_advanced_ensemble_pcr
            
            # Create advanced ensemble retriever
            advanced_ensemble = create_advanced_ensemble_pcr()
            
            # Retrieve using advanced methods
            retrieval_results = advanced_ensemble.retrieve(query, k=k)
            
            # Convert RetrievalResult objects to standard format
            results = []
            for result in retrieval_results:
                formatted_result = {
                    'content': result.content,
                    'metadata': result.metadata,
                    'score': result.score,
                    'source': result.source,
                    'search_type': 'advanced_ensemble'
                }
                results.append(formatted_result)
            
            self.logger.info(f"Advanced ensemble search (pcr): {len(results)} results for '{query[:50]}...'")
            return results
            
        except Exception as e:
            self.logger.error(f"Advanced ensemble search (pcr) failed: {e}")
            # Fallback to simple ensemble
            return self.ensemble_search_pcr(query, k, use_advanced=False)
    
    # Document Lookup Tools
    
    def get_document_by_id(
        self, 
        doc_id: Union[str, int], 
        collection: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Tool: Get document by ID from specified collection.
        
        Args:
            doc_id: Document ID
            collection: Collection name ('bugs' or 'pcr')
        
        Returns:
            Document if found, None otherwise
        """
        try:
            retriever = self._get_retriever(collection)
            result = retriever.get_by_id(doc_id)
            self.logger.info(f"Document lookup by ID: {'found' if result else 'not found'}")
            return result
        except Exception as e:
            self.logger.error(f"Document lookup by ID failed: {e}")
            return None
    
    def get_document_by_jira_id(
        self, 
        jira_id: str, 
        collection: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Tool: Get document by JIRA ID from specified collection.
        
        Args:
            jira_id: JIRA ticket ID (e.g., 'HBASE-123')
            collection: Collection name ('bugs' or 'pcr')
        
        Returns:
            Document if found, None otherwise
        """
        try:
            retriever = self._get_retriever(collection)
            result = retriever.get_by_jira_id(jira_id)
            self.logger.info(f"Document lookup by JIRA ID: {'found' if result else 'not found'}")
            return result
        except Exception as e:
            self.logger.error(f"Document lookup by JIRA ID failed: {e}")
            return None
    
    # Utility Tools
    
    def count_documents_bugs(
        self, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Tool: Count documents in bugs collection.
        
        Args:
            filters: Optional filters to apply
        
        Returns:
            Number of documents
        """
        try:
            retriever = self._get_retriever('bugs')
            count = retriever.count_documents(filters)
            self.logger.info(f"Document count (bugs): {count}")
            return count
        except Exception as e:
            self.logger.error(f"Document count (bugs) failed: {e}")
            return 0
    
    def count_documents_pcr(
        self, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Tool: Count documents in PCR collection.
        
        Args:
            filters: Optional filters to apply
        
        Returns:
            Number of documents
        """
        try:
            retriever = self._get_retriever('pcr')
            count = retriever.count_documents(filters)
            self.logger.info(f"Document count (pcr): {count}")
            return count
        except Exception as e:
            self.logger.error(f"Document count (pcr) failed: {e}")
            return 0
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Tool: Test connections to both collections.
        
        Returns:
            Dictionary with connection status for each collection
        """
        results = {}
        
        try:
            self._ensure_initialized()
            results['bugs'] = self.bugs_retriever.test_connection()
            results['pcr'] = self.pcr_retriever.test_connection()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            results = {'bugs': False, 'pcr': False}
        
        return results
    
    # Tool Registry (for dynamic tool access)
    
    def get_all_tools(self) -> Dict[str, Callable]:
        """
        Get all available tools as a dictionary.
        
        Returns:
            Dictionary mapping tool names to callable functions
        """
        return {
            # Vector search tools
            'vector_search_bugs': self.vector_search_bugs,
            'vector_search_pcr': self.vector_search_pcr,
            
            # Keyword search tools
            'keyword_search_bugs': self.keyword_search_bugs,
            'keyword_search_pcr': self.keyword_search_pcr,
            
            # BM25 tools
            'bm25_search_bugs': self.bm25_search_bugs,
            'bm25_search_pcr': self.bm25_search_pcr,
            
            # Hybrid search tools
            'hybrid_search_bugs': self.hybrid_search_bugs,
            'hybrid_search_pcr': self.hybrid_search_pcr,
            
            # Contextual compression tools
            'contextual_compression_search_bugs': self.contextual_compression_search_bugs,
            'contextual_compression_search_pcr': self.contextual_compression_search_pcr,
            
            # Ensemble tools (both simple and advanced)
            'ensemble_search_bugs': self.ensemble_search_bugs,
            'ensemble_search_pcr': self.ensemble_search_pcr,
            'advanced_ensemble_search_bugs': lambda query, k=10: self.ensemble_search_bugs(query, k, use_advanced=True),
            'advanced_ensemble_search_pcr': lambda query, k=10: self.ensemble_search_pcr(query, k, use_advanced=True),
            
            # Document lookup tools
            'get_document_by_id': self.get_document_by_id,
            'get_document_by_jira_id': self.get_document_by_jira_id,
            
            # Utility tools
            'count_documents_bugs': self.count_documents_bugs,
            'count_documents_pcr': self.count_documents_pcr,
            'test_connections': self.test_connections
        }


# Global instance for easy access
_rag_tools_instance = None

def get_rag_tools(default_collection: str = 'bugs') -> RAGTools:
    """
    Get or create a global RAGTools instance.
    
    Args:
        default_collection: Default collection to use
    
    Returns:
        RAGTools instance
    """
    global _rag_tools_instance
    
    if _rag_tools_instance is None:
        _rag_tools_instance = RAGTools(default_collection)
    
    return _rag_tools_instance


if __name__ == "__main__":
    # Test the RAG tools
    print("Testing RAG Tools...")
    
    try:
        rag_tools = get_rag_tools()
        
        # Test connections
        connections = rag_tools.test_connections()
        print(f"Connections: {connections}")
        
        if any(connections.values()):
            # Test various search tools
            test_query = "authentication error"
            
            print(f"\n🔍 Testing tools with query: '{test_query}'")
            
            # Test vector search
            try:
                results = rag_tools.vector_search_bugs(test_query, k=2)
                print(f"Vector search bugs: {len(results)} results")
            except Exception as e:
                print(f"Vector search bugs failed: {e}")
            
            # Test keyword search
            try:
                results = rag_tools.keyword_search_bugs(test_query, k=2)
                print(f"Keyword search bugs: {len(results)} results")
            except Exception as e:
                print(f"Keyword search bugs failed: {e}")
            
            # Test hybrid search
            try:
                results = rag_tools.hybrid_search_bugs(test_query, k=2)
                print(f"Hybrid search bugs: {len(results)} results")
            except Exception as e:
                print(f"Hybrid search bugs failed: {e}")
            
            # Test ensemble search
            try:
                results = rag_tools.ensemble_search_bugs(test_query, k=3)
                print(f"Ensemble search bugs: {len(results)} results")
            except Exception as e:
                print(f"Ensemble search bugs failed: {e}")
            
            # Test document counts
            bugs_count = rag_tools.count_documents_bugs()
            pcr_count = rag_tools.count_documents_pcr()
            print(f"Document counts - Bugs: {bugs_count}, PCR: {pcr_count}")
            
        else:
            print("❌ No connections available for testing")
    
    except Exception as e:
        print(f"❌ RAG tools test failed: {e}")
        print("Please check your environment variables and Supabase setup")