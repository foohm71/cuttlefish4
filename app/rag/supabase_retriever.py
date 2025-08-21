#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Supabase-based RAG retrieval functions for the Cuttlefish system.
Provides vector search, keyword search, and hybrid search capabilities.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import openai
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseRetriever:
    """
    Supabase-based retriever for both vector and keyword search.
    Supports both 'bugs' and 'pcr' collections with the same schema.
    """
    
    def __init__(self, collection_name: str = 'bugs'):
        """
        Initialize Supabase retriever.
        
        Args:
            collection_name: Collection to search ('bugs' or 'pcr')
        """
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_KEY')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.embed_model = os.environ.get('OPENAI_EMBED_MODEL', 'text-embedding-3-small')
        self.collection_name = collection_name
        
        if not all([self.supabase_url, self.supabase_key, self.openai_api_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY")
        
        # Initialize clients
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        openai.api_key = self.openai_api_key
        
        # Setup logger
        self.logger = self._setup_logger()
        
        # Available collections
        self.available_collections = ['bugs', 'pcr']
        if collection_name not in self.available_collections:
            raise ValueError(f"Invalid collection name. Must be one of: {self.available_collections}")
    
    def _setup_logger(self):
        """Setup logger for SupabaseRetriever."""
        logger = logging.getLogger(f'SupabaseRetriever_{self.collection_name}')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)  # Normal logging level
        return logger
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors with robust format handling."""
        try:
            import math
            import json
            
            # Handle different input formats for vec2 (database embedding)
            if isinstance(vec2, str):
                try:
                    # Try parsing as JSON first
                    vec2 = json.loads(vec2)
                except json.JSONDecodeError:
                    try:
                        # Try eval as fallback
                        vec2 = eval(vec2) if vec2.startswith('[') else None
                    except:
                        self.logger.debug(f"Could not parse embedding string: {vec2[:100]}...")
                        return 0.0
            
            if not isinstance(vec2, (list, tuple)):
                self.logger.debug(f"vec2 is not a list/tuple, got {type(vec2)}")
                return 0.0
                
            if len(vec1) != len(vec2):
                self.logger.debug(f"Vector length mismatch: {len(vec1)} vs {len(vec2)}")
                return 0.0
            
            # Convert to floats if needed
            try:
                vec1 = [float(x) for x in vec1]
                vec2 = [float(x) for x in vec2]
            except (ValueError, TypeError) as e:
                self.logger.debug(f"Vector conversion error: {e}")
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                self.logger.debug("Zero magnitude vector")
                return 0.0
            
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Cosine similarity can be negative, but we'll return actual value
            self.logger.debug(f"Calculated similarity: {similarity:.4f}")
            return similarity
            
        except Exception as e:
            self.logger.debug(f"Cosine similarity calculation error: {e}")
            return 0.0
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = openai.embeddings.create(
                input=text,
                model=self.embed_model
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            raise Exception(f"Failed to generate embedding: {e}")
    
    def vector_search(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.1,  # Much lower default threshold
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using direct HTTP calls and pgvector.
        
        Args:
            query: Text query to search for
            k: Maximum number of results
            similarity_threshold: Minimum similarity score
            filters: Additional filters (e.g., {'project': 'MyProject'})
        
        Returns:
            List of matching records with similarity scores
        """
        try:
            self.logger.info(f"Direct vector search for: '{query[:50]}...' in {self.collection_name}")
            self.logger.info(f"Parameters: k={k}, similarity_threshold={similarity_threshold}, filters={filters}")
            
            # Generate query embedding
            query_embedding = self.get_embedding(query)
            
            # Use direct HTTP calls for vector similarity search with pgvector
            try:
                # Build the query with pgvector similarity search
                query_builder = self.client.table(self.collection_name).select('*')
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        query_builder = query_builder.eq(key, value)
                
                # Execute the query with limit
                # Note: We can't use pgvector operators directly through the Python client
                # So we'll use a hybrid approach: get more results and filter by similarity
                result = query_builder.limit(min(k * 3, 100)).execute()
                
                if result.data:
                    self.logger.info(f"Processing {len(result.data)} candidates for similarity calculation")
                    
                    # Calculate cosine similarity manually and filter
                    results_with_similarity = []
                    similarities_calculated = 0
                    
                    for record in result.data:
                        if 'embedding' in record and record['embedding']:
                            try:
                                # Calculate cosine similarity
                                similarity = self._cosine_similarity(query_embedding, record['embedding'])
                                similarities_calculated += 1
                                
                                self.logger.debug(f"Record {record.get('id', 'unknown')}: similarity = {similarity:.4f}")
                                
                                # Filter by similarity threshold
                                if similarity >= similarity_threshold:
                                    # Add similarity score to record
                                    record['similarity'] = similarity
                                    results_with_similarity.append(record)
                                    
                            except Exception as sim_error:
                                self.logger.debug(f"Similarity calculation failed for record {record.get('id', 'unknown')}: {sim_error}")
                                continue
                        else:
                            self.logger.debug(f"Record {record.get('id', 'unknown')} missing embedding")
                    
                    self.logger.info(f"Calculated {similarities_calculated} similarities, {len(results_with_similarity)} above threshold {similarity_threshold}")
                    if len(results_with_similarity) == 0 and similarities_calculated > 0:
                        # Log the actual similarity scores when no results pass threshold
                        all_similarities = []
                        for record in result.data:
                            if 'embedding' in record and record['embedding']:
                                sim = self._cosine_similarity(query_embedding, record['embedding'])
                                all_similarities.append(sim)
                        if all_similarities:
                            max_sim = max(all_similarities)
                            min_sim = min(all_similarities)
                            self.logger.warning(f"No results above threshold {similarity_threshold}. Actual similarities range: {min_sim:.4f} to {max_sim:.4f}")
                    elif len(results_with_similarity) > 0:
                        similarities = [r.get('similarity', 0) for r in results_with_similarity]
                        self.logger.info(f"Result similarities: {[f'{s:.4f}' for s in similarities[:3]]}")
                    
                    # Sort by similarity (descending) and limit results
                    results_with_similarity.sort(key=lambda x: x['similarity'], reverse=True)
                    top_results = results_with_similarity[:k]
                    
                    self.logger.info(f"Direct vector search returned {len(top_results)} results (from {len(result.data)} candidates)")
                    return self._format_results(top_results, 'direct_vector_search')
                
                else:
                    self.logger.info("No results found in direct vector search")
                    return []
                    
            except Exception as vector_error:
                self.logger.warning(f"Direct vector search failed: {vector_error}")
                # Fallback to text-based search
                return self._fallback_text_search(query, k, filters)
            
        except Exception as e:
            self.logger.error(f"Vector search error: {e}")
            return []
    
    def keyword_search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword search using direct HTTP calls and PostgreSQL text search.
        
        Args:
            query: Text query to search for
            k: Maximum number of results
            filters: Additional filters
        
        Returns:
            List of matching records with relevance scores
        """
        try:
            self.logger.info(f"Direct keyword search for: '{query[:50]}...' in {self.collection_name}")
            
            # Use direct HTTP calls for text search
            try:
                # Build search pattern for ILIKE queries
                search_terms = query.lower().split()
                
                # Start with title search for exact matches
                query_builder = self.client.table(self.collection_name).select('*')
                
                # Apply filters if provided
                if filters:
                    for key, value in filters.items():
                        query_builder = query_builder.eq(key, value)
                
                results = []
                
                # Strategy 1: Search for exact phrase in title (highest priority)
                exact_pattern = f"%{query}%"
                title_exact = query_builder.ilike('title', exact_pattern).limit(k).execute()
                
                if title_exact.data:
                    for result in title_exact.data:
                        result['rank'] = 1.0  # Highest rank for title matches
                        result['match_type'] = 'title_exact'
                        results.append(result)
                
                # Strategy 2: Search for individual terms in title
                if len(results) < k:
                    for term in search_terms:
                        if len(term) > 2:  # Skip very short terms
                            term_pattern = f"%{term}%"
                            query_builder_term = self.client.table(self.collection_name).select('*')
                            
                            if filters:
                                for key, value in filters.items():
                                    query_builder_term = query_builder_term.eq(key, value)
                            
                            term_results = query_builder_term.ilike('title', term_pattern).limit(k - len(results)).execute()
                            
                            if term_results.data:
                                for result in term_results.data:
                                    # Avoid duplicates
                                    if not any(r.get('id') == result.get('id') for r in results):
                                        result['rank'] = 0.8  # High rank for title term matches
                                        result['match_type'] = 'title_term'
                                        results.append(result)
                                        
                                        if len(results) >= k:
                                            break
                        
                        if len(results) >= k:
                            break
                
                # Strategy 3: Search in description if still need more results
                if len(results) < k:
                    desc_query = self.client.table(self.collection_name).select('*')
                    
                    if filters:
                        for key, value in filters.items():
                            desc_query = desc_query.eq(key, value)
                    
                    desc_results = desc_query.ilike('description', exact_pattern).limit(k - len(results)).execute()
                    
                    if desc_results.data:
                        for result in desc_results.data:
                            # Avoid duplicates
                            if not any(r.get('id') == result.get('id') for r in results):
                                result['rank'] = 0.6  # Medium rank for description matches
                                result['match_type'] = 'description_exact'
                                results.append(result)
                
                # Sort by rank (descending) and limit
                results.sort(key=lambda x: x.get('rank', 0), reverse=True)
                final_results = results[:k]
                
                self.logger.info(f"Direct keyword search returned {len(final_results)} results")
                return self._format_results(final_results, 'direct_keyword_search')
                
            except Exception as search_error:
                self.logger.warning(f"Direct keyword search failed: {search_error}")
                # Fallback to ILIKE search
                return self._fallback_keyword_search(query, k, filters)
            
        except Exception as e:
            self.logger.error(f"Keyword search error: {e}")
            return []
    
    def hybrid_search(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.7,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search using direct HTTP calls.
        
        Args:
            query: Text query to search for
            k: Maximum number of results
            similarity_threshold: Minimum similarity score for vector search
            vector_weight: Weight for vector search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)
            filters: Additional filters
        
        Returns:
            List of matching records with combined scores
        """
        try:
            self.logger.info(f"Direct hybrid search for: '{query[:50]}...' in {self.collection_name}")
            
            # Get results from both search methods using our direct implementations
            vector_results = self.vector_search(query, k * 2, similarity_threshold, filters)
            keyword_results = self.keyword_search(query, k * 2, filters)
            
            # Combine and rank results
            combined_results = {}
            
            # Add vector results
            for result in vector_results:
                doc_id = result['metadata'].get('id', result['metadata'].get('jira_id'))
                if doc_id:
                    # Get similarity score from vector search
                    vector_score = result.get('similarity', result.get('score', 0.5))
                    combined_score = vector_score * vector_weight
                    
                    combined_results[doc_id] = {
                        **result,
                        'combined_score': combined_score,
                        'vector_score': vector_score,
                        'keyword_score': 0,
                        'search_type': 'direct_hybrid_search'
                    }
            
            # Add keyword results
            for result in keyword_results:
                doc_id = result['metadata'].get('id', result['metadata'].get('jira_id'))
                if doc_id:
                    # Get rank score from keyword search
                    keyword_score = result.get('rank', result.get('score', 0.8))
                    
                    if doc_id in combined_results:
                        # Update existing result
                        combined_results[doc_id]['combined_score'] += keyword_score * keyword_weight
                        combined_results[doc_id]['keyword_score'] = keyword_score
                    else:
                        # Add new result
                        combined_results[doc_id] = {
                            **result,
                            'combined_score': keyword_score * keyword_weight,
                            'vector_score': 0,
                            'keyword_score': keyword_score,
                            'search_type': 'direct_hybrid_search'
                        }
            
            # Sort by combined score and return top results
            sorted_results = sorted(
                combined_results.values(),
                key=lambda x: x['combined_score'],
                reverse=True
            )
            
            final_results = sorted_results[:k]
            self.logger.info(f"Direct hybrid search returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            self.logger.error(f"Hybrid search error: {e}")
            return []
    
    def bm25_search(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        BM25-style search using keyword search as approximation.
        This delegates to keyword_search since we're using Supabase's full-text search.
        """
        self.logger.info(f"BM25 search (via keyword search) for: '{query[:50]}...'")
        return self.keyword_search(query, k, filters)
    
    def get_by_id(self, doc_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        try:
            result = self.client.table(self.collection_name).select('*').eq('id', doc_id).execute()
            if result.data:
                return self._format_single_result(result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting document by ID: {e}")
            return None
    
    def get_by_jira_id(self, jira_id: str) -> Optional[Dict[str, Any]]:
        """Get document by JIRA ID (searches the 'key' column for JIRA ticket IDs like 'JBIDE-16308')."""
        try:
            # Search in the 'key' column which contains JIRA ticket IDs like "JBIDE-16308"
            result = self.client.table(self.collection_name).select('*').eq('key', jira_id).execute()
            if result.data:
                return self._format_single_result(result.data[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting document by JIRA ID: {e}")
            return None
    
    def count_documents(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents in collection."""
        try:
            query_builder = self.client.table(self.collection_name).select('id', count='exact')
            
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(key, value)
            
            result = query_builder.execute()
            return result.count if result.count else 0
        except Exception as e:
            self.logger.error(f"Error counting documents: {e}")
            return 0
    
    def _format_results(self, raw_results: List[Dict], search_type: str) -> List[Dict[str, Any]]:
        """Format raw results from Supabase into standardized format."""
        formatted_results = []
        
        for result in raw_results:
            formatted_result = self._format_single_result(result)
            formatted_result['search_type'] = search_type
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _format_single_result(self, result: Dict) -> Dict[str, Any]:
        """Format a single result into standardized format."""
        # Create content in the expected format: "Title: {title}\n\nDescription: {description}"
        title = result.get('title', '')
        description = result.get('description', '')
        
        if title and description:
            content = f"Title: {title}\n\nDescription: {description}"
        elif title:
            content = f"Title: {title}"
        elif description:
            content = f"Description: {description}"
        else:
            content = result.get('content', '')
        
        # Build metadata (exclude title and description since they're in content)
        metadata = {k: v for k, v in result.items() 
                   if k not in ['title', 'description', 'content', 'embedding', 'content_tsvector']}
        
        # Add title and description to metadata for reference
        metadata['title'] = title
        metadata['description'] = description
        
        formatted_result = {
            'content': content,
            'metadata': metadata,
            'source': f'supabase_{self.collection_name}',
            'score': result.get('similarity', result.get('rank', result.get('combined_score', 0.5)))
        }
        
        return formatted_result
    
    def _fallback_vector_search(self, query_embedding: List[float], k: int, filters: Optional[Dict]) -> List[Dict]:
        """Fallback vector search using basic table query."""
        try:
            # This is a simplified fallback - in practice you'd need proper vector similarity
            query_builder = (
                self.client.table(self.collection_name)
                .select('*')
                .limit(k)
            )
            
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(key, value)
            
            result = query_builder.execute()
            if result.data:
                return self._format_results(result.data, 'vector_fallback')
            return []
            
        except Exception as e:
            self.logger.error(f"Vector fallback error: {e}")
            return []
    
    def _fallback_keyword_search(self, query: str, k: int, filters: Optional[Dict]) -> List[Dict]:
        """Fallback keyword search using ILIKE."""
        try:
            # Use multiple ilike queries to search across different fields
            search_pattern = f"%{query}%"
            
            # Try searching in title first
            title_results = (
                self.client.table(self.collection_name)
                .select('*')
                .ilike('title', search_pattern)
                .limit(k)
                .execute()
            )
            
            # If not enough results, search in description
            if not title_results.data or len(title_results.data) < k:
                desc_results = (
                    self.client.table(self.collection_name)
                    .select('*')
                    .ilike('description', search_pattern)
                    .limit(k)
                    .execute()
                )
                # Combine results
                all_results = (title_results.data or []) + (desc_results.data or [])
                # Remove duplicates based on id
                seen_ids = set()
                unique_results = []
                for result in all_results:
                    if result.get('id') not in seen_ids:
                        unique_results.append(result)
                        seen_ids.add(result.get('id'))
                return unique_results[:k]
            
            return title_results.data or []
            
        except Exception as e:
            self.logger.error(f"Keyword fallback error: {e}")
            return []
    
    def _fallback_hybrid_search(self, query: str, k: int, vector_weight: float, keyword_weight: float, filters: Optional[Dict]) -> List[Dict]:
        """Fallback hybrid search by combining separate searches."""
        try:
            # Get results from both search methods
            vector_results = self.vector_search(query, k * 2, filters=filters)
            keyword_results = self.keyword_search(query, k * 2, filters=filters)
            
            # Combine and rank results
            combined_results = {}
            
            # Add vector results
            for result in vector_results:
                doc_id = result['metadata'].get('id', result['metadata'].get('jira_id'))
                if doc_id:
                    score = result.get('score', 0.5) * vector_weight
                    combined_results[doc_id] = {
                        **result,
                        'combined_score': score,
                        'vector_score': result.get('score', 0.5),
                        'keyword_score': 0,
                        'search_type': 'hybrid_fallback'
                    }
            
            # Add keyword results
            for result in keyword_results:
                doc_id = result['metadata'].get('id', result['metadata'].get('jira_id'))
                if doc_id:
                    keyword_score = result.get('score', 0.8)
                    
                    if doc_id in combined_results:
                        # Update existing result
                        combined_results[doc_id]['combined_score'] += keyword_score * keyword_weight
                        combined_results[doc_id]['keyword_score'] = keyword_score
                    else:
                        # Add new result
                        combined_results[doc_id] = {
                            **result,
                            'combined_score': keyword_score * keyword_weight,
                            'vector_score': 0,
                            'keyword_score': keyword_score,
                            'search_type': 'hybrid_fallback'
                        }
            
            # Sort by combined score and return top results
            sorted_results = sorted(
                combined_results.values(),
                key=lambda x: x['combined_score'],
                reverse=True
            )
            
            return sorted_results[:k]
            
        except Exception as e:
            self.logger.error(f"Hybrid fallback error: {e}")
            return []
    
    def _fallback_text_search(self, query: str, k: int, filters: Optional[Dict]) -> List[Dict]:
        """Fallback to text-based search when vector search fails."""
        try:
            self.logger.info(f"Using text-based fallback search for: '{query[:50]}...'")
            
            # Use multiple search strategies
            search_pattern = f"%{query}%"
            
            # Try searching in title and description with ILIKE
            query_builder = self.client.table(self.collection_name).select('*')
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(key, value)
            
            # Search in title first
            title_results = query_builder.ilike('title', search_pattern).limit(k).execute()
            results = []
            
            if title_results.data:
                for result in title_results.data:
                    result['similarity'] = 0.8  # Fixed similarity for text matches
                    result['search_type'] = 'text_fallback'
                    results.append(result)
            
            # If not enough results, search in description
            if len(results) < k:
                desc_query = self.client.table(self.collection_name).select('*')
                if filters:
                    for key, value in filters.items():
                        desc_query = desc_query.eq(key, value)
                        
                desc_results = desc_query.ilike('description', search_pattern).limit(k - len(results)).execute()
                
                if desc_results.data:
                    for result in desc_results.data:
                        # Avoid duplicates
                        if not any(r.get('id') == result.get('id') for r in results):
                            result['similarity'] = 0.7  # Slightly lower for description matches
                            result['search_type'] = 'text_fallback'
                            results.append(result)
            
            self.logger.info(f"Text fallback search returned {len(results)} results")
            return self._format_results(results, 'text_fallback')
            
        except Exception as e:
            self.logger.error(f"Text fallback search error: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test connection to Supabase."""
        try:
            result = self.client.table(self.collection_name).select('id').limit(1).execute()
            self.logger.info(f"✅ Connection to {self.collection_name} table successful")
            return True
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            return False


# Convenience functions for creating retrievers
def create_bugs_retriever() -> SupabaseRetriever:
    """Create a SupabaseRetriever for bugs collection."""
    return SupabaseRetriever('bugs')

def create_pcr_retriever() -> SupabaseRetriever:
    """Create a SupabaseRetriever for pcr collection."""
    return SupabaseRetriever('pcr')


if __name__ == "__main__":
    # Test the retriever
    print("Testing Supabase Retriever...")
    
    try:
        # Test bugs retriever
        bugs_retriever = create_bugs_retriever()
        
        if bugs_retriever.test_connection():
            print("✅ Bugs retriever connection successful")
            
            # Test searches
            test_query = "authentication error"
            
            print(f"\n🔍 Testing searches with query: '{test_query}'")
            
            # Vector search
            try:
                vector_results = bugs_retriever.vector_search(test_query, k=3)
                print(f"Vector search: {len(vector_results)} results")
            except Exception as e:
                print(f"Vector search failed: {e}")
            
            # Keyword search
            try:
                keyword_results = bugs_retriever.keyword_search(test_query, k=3)
                print(f"Keyword search: {len(keyword_results)} results")
            except Exception as e:
                print(f"Keyword search failed: {e}")
            
            # Hybrid search
            try:
                hybrid_results = bugs_retriever.hybrid_search(test_query, k=3)
                print(f"Hybrid search: {len(hybrid_results)} results")
            except Exception as e:
                print(f"Hybrid search failed: {e}")
            
            # Document count
            count = bugs_retriever.count_documents()
            print(f"Total documents in bugs: {count}")
            
        else:
            print("❌ Connection test failed")
    
    except Exception as e:
        print(f"❌ Retriever test failed: {e}")
        print("Please check your environment variables: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY")