#!/usr/bin/env python3
"""
Common utilities and shared functions for all agents.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from langchain_core.documents import Document

# State type definition (shared across all agents)
class AgentState(TypedDict):
    """State shared between all agents in the graph."""
    query: str
    user_can_wait: bool
    production_incident: bool
    routing_decision: Optional[str]
    routing_reasoning: Optional[str]
    retrieved_contexts: List[Dict[str, Any]]
    retrieval_method: Optional[str]
    retrieval_metadata: Dict[str, Any]
    final_answer: Optional[str]
    relevant_tickets: List[Dict[str, str]]
    messages: List[Any]

def measure_performance(start_time: datetime) -> float:
    """Calculate processing time in seconds."""
    return (datetime.now() - start_time).total_seconds()

def extract_content_from_document(doc: Document) -> str:
    """Extract content from LangChain Document, prioritizing payload data over page_content."""
    # First, try to get content from metadata/payload (like cuttlefish2)
    if hasattr(doc, 'metadata') and doc.metadata:
        title = doc.metadata.get('title', '')
        description = doc.metadata.get('description', '')
        
        if title or description:
            # Construct content like cuttlefish2: "Title: {title}\nDescription: {description}"
            content = f"Title: {title}\nDescription: {description}"
            
            # Update the document for future use
            if hasattr(doc, 'page_content'):
                doc.page_content = content
            
            return content
    
    # Fallback to existing page_content if available
    if hasattr(doc, 'page_content') and doc.page_content and doc.page_content.strip():
        return doc.page_content
    
    return ""

def filter_empty_documents(docs: List[Document]) -> List[Document]:
    """Filter out documents with empty content, using content extraction."""
    if not docs:
        return []
    
    valid_docs = []
    for doc in docs:
        # Extract content using the same method as agents
        content = extract_content_from_document(doc)
        
        if content and content.strip() and len(content.strip()) >= 3:
            valid_docs.append(doc)
    
    return valid_docs

def format_context_for_llm(retrieved_contexts: List[Dict]) -> str:
    """Format retrieved contexts for LLM consumption."""
    if not retrieved_contexts:
        return "No relevant context found."
    
    context_parts = []
    for i, ctx in enumerate(retrieved_contexts[:10]):  # Limit to top 10
        content = ctx.get('content', '')
        
        # Skip empty content
        if not content or not content.strip():
            continue
            
        metadata = ctx.get('metadata', {})
        key = metadata.get('key', f'DOC-{i+1}')
        
        context_parts.append(f"[{key}] {content}")
    
    if not context_parts:
        return "No relevant context with valid content found."
    
    return "\n\n".join(context_parts)

def extract_ticket_info(retrieved_contexts: List[Dict]) -> List[Dict[str, str]]:
    """Extract ticket key and title information from retrieved contexts."""
    tickets = []
    seen_keys = set()
    
    for ctx in retrieved_contexts:
        content = ctx.get('content', '')
        
        # Skip empty content
        if not content or not content.strip():
            continue
            
        metadata = ctx.get('metadata', {})
        key = metadata.get('key', '')
        
        if key and key not in seen_keys:
            # Extract title from content (which should now be in format "Title: {title}\nDescription: {description}")
            title = metadata.get('title', '')
            if not title and content.startswith('Title: '):
                # Extract title from the content
                lines = content.split('\n')
                if len(lines) > 0:
                    title = lines[0].replace('Title: ', '').strip()
            
            tickets.append({
                'key': key,
                'title': title or 'No title available'
            })
            seen_keys.add(key)
    
    return tickets

def format_sources(retrieved_contexts: List[Dict]) -> str:
    """Format sources from retrieved contexts for display."""
    if not retrieved_contexts:
        return "No sources found."
    
    sources = []
    seen_sources = set()
    
    for ctx in retrieved_contexts:
        metadata = ctx.get('metadata', {})
        
        # Try to get URL first (for web search results)
        url = metadata.get('url', '')
        if url and url not in seen_sources:
            title = metadata.get('title', url)
            sources.append(f"• {title} ({url})")
            seen_sources.add(url)
            continue
        
        # Fallback to ticket key (for RAG results)
        key = metadata.get('key', '')
        if key and key not in seen_sources:
            title = metadata.get('title', key)
            sources.append(f"• {title} (Ticket: {key})")
            seen_sources.add(key)
    
    return "\n".join(sources) if sources else "No valid sources found."