#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Advanced RAG retrievers for sophisticated ensemble search.
Implements Multi-Query, Contextual Compression, and other advanced retrieval methods.
"""

import os
import logging
import hashlib
import openai
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass

# Try to import reranking libraries
try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    print("⚠️  Cohere not available - install with: pip install cohere")

# Import our base retriever - handle both relative and absolute imports
try:
    # First try absolute import for Jupyter notebooks
    from supabase_retriever import SupabaseRetriever
except ImportError:
    try:
        # Fallback to relative import for package usage
        from .supabase_retriever import SupabaseRetriever
    except ImportError:
        # Final fallback - add current directory to path and import
        import os
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from supabase_retriever import SupabaseRetriever

@dataclass
class RetrievalResult:
    """Standardized retrieval result format."""
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str
    content_hash: Optional[str] = None
    
    def __post_init__(self):
        if self.content_hash is None:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'metadata': self.metadata,
            'score': self.score,
            'source': self.source,
            'content_hash': self.content_hash
        }

class MultiQueryRetriever:
    """
    Multi-Query Retriever that uses LLM to generate multiple variations of the query
    for broader search coverage.
    """
    
    def __init__(self, base_retriever: SupabaseRetriever, llm_model: str = "gpt-3.5-turbo"):
        self.base_retriever = base_retriever
        self.llm_model = llm_model
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logger = logging.getLogger(f'MultiQueryRetriever_{self.base_retriever.collection_name}')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _generate_query_variations(self, original_query: str, num_variations: int = 3) -> List[str]:
        """Generate multiple variations of the original query using LLM."""
        try:
            prompt = f"""Given the following query, generate {num_variations} different variations that would help find relevant information. 
Each variation should approach the topic from a slightly different angle while maintaining the core intent.

Original query: "{original_query}"

Generate {num_variations} variations (one per line, no numbering):"""

            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            
            variations = response.choices[0].message.content.strip().split('\n')
            variations = [v.strip() for v in variations if v.strip()]
            
            # Always include the original query
            all_queries = [original_query] + variations[:num_variations]
            
            self.logger.info(f"Generated {len(all_queries)} query variations")
            return all_queries
            
        except Exception as e:
            self.logger.error(f"Failed to generate query variations: {e}")
            return [original_query]  # Fallback to original query
    
    def retrieve(self, query: str, k: int = 10, num_variations: int = 3) -> List[RetrievalResult]:
        """Retrieve using multiple query variations."""
        try:
            # Generate query variations
            queries = self._generate_query_variations(query, num_variations)
            
            all_results = []
            for q in queries:
                # Use vector search for each variation
                raw_results = self.base_retriever.vector_search(q, k=k//len(queries) + 2)
                
                for result in raw_results:
                    retrieval_result = RetrievalResult(
                        content=result.get('content', ''),
                        metadata=result.get('metadata', {}),
                        score=result.get('score', 0.5),
                        source=f"multi_query_{self.base_retriever.collection_name}"
                    )
                    all_results.append(retrieval_result)
            
            # Deduplicate based on content hash
            deduplicated = self._deduplicate_results(all_results)
            
            # Sort by score and return top k
            deduplicated.sort(key=lambda x: x.score, reverse=True)
            
            self.logger.info(f"Multi-query retrieval: {len(deduplicated)} deduplicated results from {len(queries)} variations")
            return deduplicated[:k]
            
        except Exception as e:
            self.logger.error(f"Multi-query retrieval failed: {e}")
            return []
    
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Remove duplicate results based on content hash."""
        seen_hashes = set()
        deduplicated = []
        
        for result in results:
            if result.content_hash not in seen_hashes:
                deduplicated.append(result)
                seen_hashes.add(result.content_hash)
        
        return deduplicated

class ContextualCompressionRetriever:
    """
    Contextual Compression Retriever that uses reranking to improve result quality.
    """
    
    def __init__(self, base_retriever: SupabaseRetriever, reranker_type: str = "cohere"):
        self.base_retriever = base_retriever
        self.reranker_type = reranker_type
        self.logger = self._setup_logger()
        
        # Initialize reranker
        self.reranker = None
        if reranker_type == "cohere" and COHERE_AVAILABLE:
            try:
                api_key = os.getenv('COHERE_API_KEY')
                if api_key:
                    self.reranker = cohere.Client(api_key)
                    self.logger.info("Cohere reranker initialized")
                else:
                    self.logger.warning("COHERE_API_KEY not found")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Cohere: {e}")
        
    def _setup_logger(self):
        logger = logging.getLogger(f'ContextualCompressionRetriever_{self.base_retriever.collection_name}')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def retrieve(self, query: str, k: int = 10, initial_k: int = 20) -> List[RetrievalResult]:
        """Retrieve with contextual compression and reranking."""
        try:
            # Get more initial results for reranking
            raw_results = self.base_retriever.vector_search(query, k=initial_k)
            
            if not raw_results:
                return []
            
            # Convert to RetrievalResult format
            results = []
            for result in raw_results:
                retrieval_result = RetrievalResult(
                    content=result.get('content', ''),
                    metadata=result.get('metadata', {}),
                    score=result.get('score', 0.5),
                    source=f"contextual_compression_{self.base_retriever.collection_name}"
                )
                results.append(retrieval_result)
            
            # Apply reranking if available
            if self.reranker and self.reranker_type == "cohere":
                reranked_results = self._cohere_rerank(query, results, k)
                if reranked_results:
                    return reranked_results
            
            # Fallback: return top results by original score
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:k]
            
        except Exception as e:
            self.logger.error(f"Contextual compression retrieval failed: {e}")
            return []
    
    def _cohere_rerank(self, query: str, results: List[RetrievalResult], k: int) -> List[RetrievalResult]:
        """Rerank results using Cohere reranker."""
        try:
            if not self.reranker:
                return results
            
            # Prepare documents for reranking
            documents = [result.content for result in results]
            
            # Call Cohere rerank API
            rerank_response = self.reranker.rerank(
                model="rerank-english-v2.0",
                query=query,
                documents=documents,
                top_k=k
            )
            
            # Reconstruct results with new scores
            reranked_results = []
            for rerank_result in rerank_response.results:
                original_result = results[rerank_result.index]
                # Update score with rerank score
                original_result.score = rerank_result.relevance_score
                original_result.source += "_cohere_reranked"
                reranked_results.append(original_result)
            
            self.logger.info(f"Cohere reranking: {len(reranked_results)} results reranked")
            return reranked_results
            
        except Exception as e:
            self.logger.error(f"Cohere reranking failed: {e}")
            return results  # Return original results on failure

class BM25Retriever:
    """
    BM25-style retriever using Supabase's full-text search capabilities.
    Enhanced version of keyword search with document frequency scoring.
    """
    
    def __init__(self, base_retriever: SupabaseRetriever):
        self.base_retriever = base_retriever
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        logger = logging.getLogger(f'BM25Retriever_{self.base_retriever.collection_name}')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def retrieve(self, query: str, k: int = 10) -> List[RetrievalResult]:
        """Retrieve using BM25-style scoring."""
        try:
            # Use the base retriever's keyword search (which uses PostgreSQL full-text search)
            raw_results = self.base_retriever.keyword_search(query, k=k)
            
            results = []
            for result in raw_results:
                retrieval_result = RetrievalResult(
                    content=result.get('content', ''),
                    metadata=result.get('metadata', {}),
                    score=result.get('score', 0.8),  # Keyword search typically has high precision
                    source=f"bm25_{self.base_retriever.collection_name}"
                )
                results.append(retrieval_result)
            
            self.logger.info(f"BM25 retrieval: {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"BM25 retrieval failed: {e}")
            return []

class AdvancedEnsembleRetriever:
    """
    Advanced Ensemble Retriever that combines multiple sophisticated retrieval methods
    similar to the original Cuttlefish3 implementation.
    """
    
    def __init__(self, base_retriever: SupabaseRetriever, llm_model: str = "gpt-3.5-turbo"):
        self.base_retriever = base_retriever
        self.llm_model = llm_model
        self.logger = self._setup_logger()
        
        # Initialize individual retrievers
        self.multi_query_retriever = MultiQueryRetriever(base_retriever, llm_model)
        self.contextual_compression_retriever = ContextualCompressionRetriever(base_retriever)
        self.bm25_retriever = BM25Retriever(base_retriever)
        
        # Method weights (similar to original Cuttlefish3)
        self.method_weights = {
            'naive': 0.25,
            'multi_query': 0.25,
            'contextual_compression': 0.25,
            'bm25': 0.25
        }
        
    def _setup_logger(self):
        logger = logging.getLogger(f'AdvancedEnsembleRetriever_{self.base_retriever.collection_name}')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def retrieve(self, query: str, k: int = 10) -> List[RetrievalResult]:
        """
        Perform advanced ensemble retrieval combining multiple sophisticated methods.
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Advanced ensemble retrieval for: '{query[:50]}...'")
            
            all_results = []
            methods_used = []
            
            # 1. Naive vector search
            try:
                raw_results = self.base_retriever.vector_search(query, k=k//2)
                for result in raw_results:
                    retrieval_result = RetrievalResult(
                        content=result.get('content', ''),
                        metadata=result.get('metadata', {}),
                        score=result.get('score', 0.5) * self.method_weights['naive'],
                        source=f"naive_{self.base_retriever.collection_name}"
                    )
                    all_results.append(retrieval_result)
                methods_used.append('naive')
                self.logger.info(f"Naive retrieval: {len(raw_results)} results")
            except Exception as e:
                self.logger.error(f"Naive retrieval failed: {e}")
            
            # 2. Multi-Query retrieval
            try:
                multi_results = self.multi_query_retriever.retrieve(query, k=k//2)
                for result in multi_results:
                    result.score *= self.method_weights['multi_query']
                all_results.extend(multi_results)
                methods_used.append('multi_query')
                self.logger.info(f"Multi-query retrieval: {len(multi_results)} results")
            except Exception as e:
                self.logger.error(f"Multi-query retrieval failed: {e}")
            
            # 3. Contextual Compression retrieval
            try:
                compression_results = self.contextual_compression_retriever.retrieve(query, k=k//2)
                for result in compression_results:
                    result.score *= self.method_weights['contextual_compression']
                all_results.extend(compression_results)
                methods_used.append('contextual_compression')
                self.logger.info(f"Contextual compression retrieval: {len(compression_results)} results")
            except Exception as e:
                self.logger.error(f"Contextual compression retrieval failed: {e}")
            
            # 4. BM25 retrieval
            try:
                bm25_results = self.bm25_retriever.retrieve(query, k=k//2)
                for result in bm25_results:
                    result.score *= self.method_weights['bm25']
                all_results.extend(bm25_results)
                methods_used.append('bm25')
                self.logger.info(f"BM25 retrieval: {len(bm25_results)} results")
            except Exception as e:
                self.logger.error(f"BM25 retrieval failed: {e}")
            
            # Advanced deduplication and scoring
            deduplicated_results = self._advanced_deduplicate_and_score(all_results)
            
            # Sort by combined score and return top k
            deduplicated_results.sort(key=lambda x: x.score, reverse=True)
            final_results = deduplicated_results[:k]
            
            # Mark as ensemble
            for result in final_results:
                result.source = f"advanced_ensemble_{self.base_retriever.collection_name}"
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Advanced ensemble completed: {len(final_results)} results in {duration:.2f}s using methods: {', '.join(methods_used)}")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Advanced ensemble retrieval failed: {e}")
            return []
    
    def _advanced_deduplicate_and_score(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Advanced deduplication with score combination for duplicate content.
        """
        content_hash_to_result = {}
        
        for result in results:
            content_hash = result.content_hash
            
            if content_hash in content_hash_to_result:
                # Combine scores for duplicate content (take max score)
                existing_result = content_hash_to_result[content_hash]
                if result.score > existing_result.score:
                    content_hash_to_result[content_hash] = result
            else:
                content_hash_to_result[content_hash] = result
        
        return list(content_hash_to_result.values())

# Convenience functions for creating advanced retrievers
def create_advanced_ensemble_bugs() -> AdvancedEnsembleRetriever:
    """Create an AdvancedEnsembleRetriever for bugs collection."""
    try:
        from supabase_retriever import create_bugs_retriever
    except ImportError:
        from .supabase_retriever import create_bugs_retriever
    base_retriever = create_bugs_retriever()
    return AdvancedEnsembleRetriever(base_retriever)

def create_advanced_ensemble_pcr() -> AdvancedEnsembleRetriever:
    """Create an AdvancedEnsembleRetriever for pcr collection."""
    try:
        from supabase_retriever import create_pcr_retriever
    except ImportError:
        from .supabase_retriever import create_pcr_retriever
    base_retriever = create_pcr_retriever()
    return AdvancedEnsembleRetriever(base_retriever)

if __name__ == "__main__":
    # Test the advanced retrievers
    print("Testing Advanced Retrievers...")
    
    try:
        # Test with bugs collection
        ensemble = create_advanced_ensemble_bugs()
        
        test_query = "authentication error"
        print(f"\n🔍 Testing advanced ensemble with query: '{test_query}'")
        
        results = ensemble.retrieve(test_query, k=5)
        print(f"✅ Advanced ensemble: {len(results)} results")
        
        for i, result in enumerate(results[:3]):
            print(f"   {i+1}. Score: {result.score:.3f}, Source: {result.source}")
            print(f"      Content: {result.content[:100]}...")
        
    except Exception as e:
        print(f"❌ Advanced retriever test failed: {e}")
        print("Please check your environment variables and Supabase setup")