#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Supabase client wrapper with vector and keyword search capabilities.
Provides unified interface for both vector similarity and full-text search.
"""

import os
from typing import List, Dict, Any, Optional, Union, Tuple
from supabase import create_client, Client
import openai
import numpy as np
from dotenv import load_dotenv

load_dotenv()

class SupabaseVectorClient:
    """
    Wrapper for Supabase client with vector and keyword search capabilities.
    Supports both 'bugs' and 'pcr' collections with the same schema.
    """
    
    def __init__(self):
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_KEY')
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.embed_model = os.environ.get('OPENAI_EMBED_MODEL', 'text-embedding-3-small')
        
        if not all([self.supabase_url, self.supabase_key, self.openai_api_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY")
        
        # Initialize clients
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        openai.api_key = self.openai_api_key
        
        # Available tables/collections
        self.available_tables = ['bugs', 'pcr']
    
    def search(
        self,
        query: str,
        table: str = 'bugs',
        search_type: str = 'vector',
        k: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Unified search interface for Supabase.
        
        Args:
            query: The search query string
            table: Table to search ('bugs' or 'pcr')
            search_type: Type of search ('vector', 'keyword', 'hybrid')
            k: Number of results to return
            **kwargs: Additional parameters for specific search types
        
        Returns:
            List of search results
        
        Example:
            # Vector search in bugs table
            results = client.search("authentication error", table="bugs", search_type="vector")
            
            # Keyword search in pcr table
            results = client.search("feature release", table="pcr", search_type="keyword")
            
            # Hybrid search with custom weights
            results = client.search("login issue", search_type="hybrid", 
                                  vector_weight=0.8, keyword_weight=0.2)
        """
        if table not in self.available_tables:
            raise ValueError(f"Invalid table '{table}'. Must be one of: {self.available_tables}")
        
        if search_type == 'vector':
            return self.vector_search(
                query=query,
                table_name=table,
                k=k,
                similarity_threshold=kwargs.get('similarity_threshold', 0.7),
                filters=kwargs.get('filters')
            )
        
        elif search_type == 'keyword':
            return self.keyword_search(
                query=query,
                table_name=table,
                k=k,
                filters=kwargs.get('filters')
            )
        
        elif search_type == 'hybrid':
            return self.hybrid_search(
                query=query,
                table_name=table,
                k=k,
                similarity_threshold=kwargs.get('similarity_threshold', 0.7),
                vector_weight=kwargs.get('vector_weight', 0.7),
                keyword_weight=kwargs.get('keyword_weight', 0.3),
                filters=kwargs.get('filters')
            )
        
        else:
            raise ValueError(f"Invalid search_type '{search_type}'. Must be one of: 'vector', 'keyword', 'hybrid'")
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = openai.embeddings.create(
                input=text,
                model=self.embed_model
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {e}")
    
    def parse_stored_embedding(self, embedding_data) -> List[float]:
        """Parse embedding from Supabase storage format."""
        if isinstance(embedding_data, list):
            return embedding_data
        elif isinstance(embedding_data, str):
            try:
                import json
                parsed = json.loads(embedding_data)
                if isinstance(parsed, list) and len(parsed) == 1536:
                    return parsed
                else:
                    raise ValueError(f"Invalid embedding format: expected list of 1536 floats")
            except json.JSONDecodeError:
                raise ValueError(f"Cannot parse embedding JSON: {embedding_data[:100]}...")
        else:
            raise ValueError(f"Unknown embedding format: {type(embedding_data)}")
    
    def _direct_vector_search(
        self,
        query: str,
        table_name: str,
        limit: int,
        similarity_threshold: float,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Direct vector similarity search using Python computation."""
        import numpy as np
        
        # Get query embedding
        query_embedding = self.get_embedding(query)
        
        # Get all records with embeddings
        query_builder = self.client.table(table_name).select('*')
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                query_builder = query_builder.eq(key, value)
        
        # Get all records (we'll compute similarity in Python)
        result = query_builder.execute()
        if not result.data:
            return []
        
        # Compute similarities for all records
        all_records_with_scores = []
        
        for record in result.data:
            try:
                stored_embedding = self.parse_stored_embedding(record.get('embedding'))
                
                # Compute cosine similarity
                query_vec = np.array(query_embedding)
                stored_vec = np.array(stored_embedding)
                
                # Normalize vectors
                query_norm = np.linalg.norm(query_vec)
                stored_norm = np.linalg.norm(stored_vec)
                
                if query_norm > 0 and stored_norm > 0:
                    similarity = np.dot(query_vec, stored_vec) / (query_norm * stored_norm)
                    record['similarity'] = float(similarity)
                    all_records_with_scores.append(record)
                        
            except Exception as e:
                # Skip records with embedding errors
                continue
        
        # Sort by similarity (highest first)
        all_records_with_scores.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Apply threshold filter and return top-k
        if all_records_with_scores:
            above_threshold = [r for r in all_records_with_scores if r['similarity'] >= similarity_threshold]
            
            if above_threshold:
                return above_threshold[:limit]
            else:
                # Return top-k by similarity if no records meet threshold
                return all_records_with_scores[:limit]
        
        return []
    
    def vector_search(
        self, 
        query: str, 
        table_name: str = 'bugs',
        k: int = 10,
        limit: int = None,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search using cosine similarity.
        
        Args:
            query: Text query to search for
            table_name: Table to search in ('bugs' or 'pcr')
            k: Maximum number of results (preferred parameter)
            limit: Maximum number of results (for backward compatibility)
            similarity_threshold: Minimum similarity score
            filters: Additional filters (e.g., {'project': 'MyProject'})
        
        Returns:
            List of matching records with similarity scores
        """
        # Use k if provided, otherwise use limit
        result_limit = k if k is not None else (limit if limit is not None else 10)
        if table_name not in self.available_tables:
            raise ValueError(f"Invalid table name. Must be one of: {self.available_tables}")
        
        try:
            # Generate query embedding
            query_embedding = self.get_embedding(query)
            
            # Use RPC function for vector similarity search
            # This requires the RPC function to be created in Supabase
            try:
                result = self.client.rpc(
                    'match_documents_vector',
                    {
                        'query_embedding': query_embedding,
                        'match_table': table_name,
                        'match_count': result_limit,
                        'similarity_threshold': similarity_threshold
                    }
                ).execute()
                
                # Check if RPC returned results
                if result.data:
                    return result.data
                else:
                    # Fall back to direct search even if RPC doesn't error
                    raise Exception("RPC returned no results, trying direct approach")
                
            except Exception as rpc_error:
                # Try direct vector similarity search without RPC
                try:
                    return self._direct_vector_search(query, table_name, result_limit, similarity_threshold, filters)
                except Exception as direct_error:
                    # Fall back to text matching if vector search fails
                    return self._fallback_search(query, table_name, result_limit, filters)
            
        except Exception as e:
            # Fallback to simple table query without vector search
            return self._fallback_search(query, table_name, result_limit, filters)
    
    def keyword_search(
        self,
        query: str,
        table_name: str = 'bugs',
        k: int = 10,
        limit: int = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword search using PostgreSQL full-text search.
        
        Args:
            query: Text query to search for
            table_name: Table to search in ('bugs' or 'pcr')
            k: Maximum number of results (preferred parameter)
            limit: Maximum number of results (for backward compatibility)
            filters: Additional filters
        
        Returns:
            List of matching records with relevance scores
        """
        # Use k if provided, otherwise use limit
        result_limit = k if k is not None else (limit if limit is not None else 10)
        if table_name not in self.available_tables:
            raise ValueError(f"Invalid table name. Must be one of: {self.available_tables}")
        
        try:
            # Use PostgreSQL full-text search with proper API
            query_builder = self.client.table(table_name).select('*')
            
            # Apply additional filters if provided
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(key, value)
            
            # Apply text search and limit - use different approach
            try:
                # Format query for PostgreSQL tsquery (escape special characters and join with &)
                formatted_query = ' & '.join(query.split())
                # Build query with text search first
                search_query = query_builder.text_search('content_tsvector', formatted_query)
                result = search_query.execute()
                
                # Apply limit manually since chaining doesn't work
                data = result.data if result.data else []
                
                # If TSQuery found results, return them
                if data:
                    return data[:result_limit]
                else:
                    # Fall back to ILIKE search if no results
                    return self._fallback_search(query, table_name, result_limit, filters)
                
            except Exception as text_search_error:
                # Fall back to ILIKE search if tsvector search fails
                return self._fallback_search(query, table_name, result_limit, filters)
            
        except Exception as e:
            # Fallback to simple ILIKE search
            return self._fallback_keyword_search(query, table_name, result_limit, filters)
    
    def hybrid_search(
        self,
        query: str,
        table_name: str = 'bugs',
        k: int = 10,
        limit: int = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search.
        
        Args:
            query: Text query to search for
            table_name: Table to search in ('bugs' or 'pcr')
            k: Maximum number of results (preferred parameter)
            limit: Maximum number of results (for backward compatibility)
            vector_weight: Weight for vector search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)
            similarity_threshold: Minimum similarity score for vector search
            filters: Additional filters
        
        Returns:
            List of matching records with combined scores
        """
        # Use k if provided, otherwise use limit
        result_limit = k if k is not None else (limit if limit is not None else 10)
        
        # Get results from both search methods
        vector_results = self.vector_search(query, table_name, k=result_limit * 2, similarity_threshold=similarity_threshold, filters=filters)
        keyword_results = self.keyword_search(query, table_name, k=result_limit * 2, filters=filters)
        
        # Combine and rank results
        combined_results = {}
        
        # Add vector results
        for result in vector_results:
            doc_id = result['id']
            score = result.get('similarity', 0.5) * vector_weight
            combined_results[doc_id] = {
                **result,
                'combined_score': score,
                'vector_score': result.get('similarity', 0.5),
                'keyword_score': 0
            }
        
        # Add keyword results
        for result in keyword_results:
            doc_id = result['id']
            keyword_score = 0.8  # Default relevance score for keyword matches
            
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
                    'keyword_score': keyword_score
                }
        
        # Sort by combined score and return top results
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        return sorted_results[:result_limit]
    
    def get_by_id(self, doc_id: Union[str, int], table_name: str = 'bugs') -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        if table_name not in self.available_tables:
            raise ValueError(f"Invalid table name. Must be one of: {self.available_tables}")
        
        try:
            result = self.client.table(table_name).select('*').eq('id', doc_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting document by ID: {e}")
            return None
    
    def get_by_jira_id(self, jira_id: str, table_name: str = 'bugs') -> Optional[Dict[str, Any]]:
        """Get document by JIRA ID."""
        if table_name not in self.available_tables:
            raise ValueError(f"Invalid table name. Must be one of: {self.available_tables}")
        
        try:
            result = self.client.table(table_name).select('*').eq('jira_id', jira_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting document by JIRA ID: {e}")
            return None
    
    def _fallback_search(
        self, 
        query: str, 
        table_name: str, 
        limit: int, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fallback search using simple text matching."""
        try:
            # Split query into words for better multi-word search
            query_words = query.split()
            
            # Try multiple search strategies
            strategies = []
            
            # Strategy 1: Search in key field (for ticket numbers) - exact match
            strategies.append(('key', lambda: self.client.table(table_name).select('*').ilike('key', f'%{query}%').limit(limit).execute()))
            
            # Strategy 2-5: Search each field for each word individually
            for field in ['title', 'description', 'content']:
                for word in query_words:
                    if len(word) >= 3:  # Only search for words 3+ characters
                        strategies.append((f'{field}({word})', lambda w=word, f=field: self.client.table(table_name).select('*').ilike(f, f'%{w}%').limit(limit).execute()))
            
            # Strategy 6: Try exact multi-word match in description (original approach)
            if len(query_words) > 1:
                strategies.append(('description(exact)', lambda: self.client.table(table_name).select('*').ilike('description', f'%{query}%').limit(limit).execute()))
            
            all_results = []
            seen_ids = set()
            
            for i, (field_name, strategy) in enumerate(strategies):
                try:
                    result = strategy()
                    if result.data:
                        for record in result.data:
                            if record['id'] not in seen_ids:
                                all_results.append(record)
                                seen_ids.add(record['id'])
                except Exception as e:
                    continue
            
            # Apply filters if provided
            if filters:
                filtered_results = []
                for record in all_results:
                    matches = True
                    for key, value in filters.items():
                        if record.get(key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_results.append(record)
                all_results = filtered_results
            
            return all_results[:limit]
            
        except Exception as e:
            return []
    
    def _fallback_keyword_search(
        self,
        query: str,
        table_name: str,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fallback keyword search using ILIKE."""
        return self._fallback_search(query, table_name, limit, filters)
    
    def count_documents(self, table_name: str = 'bugs', filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents in table."""
        if table_name not in self.available_tables:
            raise ValueError(f"Invalid table name. Must be one of: {self.available_tables}")
        
        try:
            query_builder = self.client.table(table_name).select('id', count='exact')
            
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(key, value)
            
            result = query_builder.execute()
            return result.count if result.count else 0
        except Exception as e:
            print(f"Error counting documents: {e}")
            return 0
    
    def test_connection(self) -> bool:
        """Test connection to Supabase."""
        try:
            # Try to query both tables
            for table in self.available_tables:
                count_result = self.client.table(table).select('id', count='exact').execute()
                count = count_result.count if count_result.count else 0
                print(f"✅ Table '{table}' accessible ({count} records)")
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


# Convenience functions for backward compatibility
def create_supabase_client() -> SupabaseVectorClient:
    """Create and return a SupabaseVectorClient instance."""
    return SupabaseVectorClient()


def debug_search(client, query, table="bugs"):
    """Debug function showing results from different search methods."""
    print(f"\n🔍 Testing search methods for '{query}' in table '{table}'")
    
    # Test vector search
    try:
        vector_results = client.vector_search(query, table, k=5, similarity_threshold=0.5)
        print(f"\n📊 Vector search: {len(vector_results)} results")
        if vector_results:
            for i, result in enumerate(vector_results[:3]):
                key = result.get('key', 'No key')
                title = result.get('title', 'No title')
                similarity = result.get('similarity', 'N/A')
                print(f"  {i+1}. {key}: {title[:60]}... (sim: {similarity})")
        else:
            print("  No vector results found")
    except Exception as e:
        print(f"  Vector search failed: {e}")
    
    # Test keyword search
    try:
        keyword_results = client.keyword_search(query, table, k=5)
        print(f"\n📝 Keyword search: {len(keyword_results)} results")
        if keyword_results:
            for i, result in enumerate(keyword_results[:3]):
                key = result.get('key', 'No key')
                title = result.get('title', 'No title')
                print(f"  {i+1}. {key}: {title[:60]}...")
        else:
            print("  No keyword results found")
    except Exception as e:
        print(f"  Keyword search failed: {e}")
    
    # Test hybrid search
    try:
        hybrid_results = client.search(query, table=table, search_type="hybrid", k=5)
        print(f"\n🔄 Hybrid search: {len(hybrid_results)} results")
        if hybrid_results:
            for i, result in enumerate(hybrid_results[:3]):
                key = result.get('key', 'No key')
                title = result.get('title', 'No title')
                combined_score = result.get('combined_score', 'N/A')
                vector_score = result.get('vector_score', 0)
                keyword_score = result.get('keyword_score', 0)
                print(f"  {i+1}. {key}: {title[:50]}...")
                print(f"      Combined: {combined_score}, Vector: {vector_score}, Keyword: {keyword_score}")
        else:
            print("  No hybrid results found")
    except Exception as e:
        print(f"  Hybrid search failed: {e}")


if __name__ == "__main__":
    # Test the client
    print("Supabase Vector Client Test")
    
    try:
        client = SupabaseVectorClient()
        
        # Test connection
        if client.test_connection():
            print("✅ Connection test passed")
            
            # Simple interactive mode
            while True:
                test_query = input("\nEnter search query (or 'quit'): ").strip()
                if test_query.lower() == 'quit':
                    break
                if test_query:
                    debug_search(client, test_query)
        else:
            print("❌ Connection test failed")
    
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        print("Please check your environment variables.")