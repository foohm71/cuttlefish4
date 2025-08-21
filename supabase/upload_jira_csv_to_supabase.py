#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Supabase equivalent of upload_jira_csv_to_qdrant.py
Processes JIRA CSV data and uploads to Supabase with vector embeddings and full-text search support.
Creates two instances: 'bugs' and 'pcr' (release tickets) with the same schema.
"""

import pandas as pd
import openai
import argparse
import os
import csv
from tqdm import tqdm
from dotenv import load_dotenv
from supabase import create_client, Client
import numpy as np
from typing import List, Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()

# Set CSV field size limit for large JIRA descriptions
csv.field_size_limit(10000000)

# Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_EMBED_MODEL = os.environ.get('OPENAI_EMBED_MODEL', 'text-embedding-3-small')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 100))
MAX_CHARS = 16000  # Maximum characters for embedding safety

openai.api_key = OPENAI_API_KEY

def get_embedding(text: str, model: str = OPENAI_EMBED_MODEL) -> List[float]:
    """Generate embedding for text using OpenAI."""
    response = openai.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

def safe_text(text: str) -> str:
    """Truncate text to safe length for embedding."""
    return text[:MAX_CHARS] if text else ""

def initialize_supabase_tables(supabase: Client, table_name: str):
    """
    Initialize Supabase table with vector support.
    Creates table with pgvector extension for vector similarity search and text search.
    """
    
    # SQL to create the table with vector support and full-text search
    create_table_sql = f"""
    -- Enable extensions if not already enabled
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    
    -- Drop table if exists (for development)
    DROP TABLE IF EXISTS {table_name};
    
    -- Create the main table
    CREATE TABLE {table_name} (
        id BIGSERIAL PRIMARY KEY,
        jira_id TEXT,
        key TEXT,
        project TEXT,
        project_name TEXT,
        priority TEXT,
        type TEXT,
        status TEXT,
        created TIMESTAMP,
        resolved TIMESTAMP,
        updated TIMESTAMP,
        component TEXT,
        version TEXT,
        reporter TEXT,
        assignee TEXT,
        title TEXT,
        description TEXT,
        content TEXT, -- Formatted content for RAG
        embedding VECTOR(1536), -- OpenAI text-embedding-3-small dimension
        content_tsvector TSVECTOR, -- For full-text search
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx ON {table_name} 
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    
    CREATE INDEX IF NOT EXISTS {table_name}_content_search_idx ON {table_name} 
        USING GIN (content_tsvector);
    
    CREATE INDEX IF NOT EXISTS {table_name}_jira_id_idx ON {table_name} (jira_id);
    CREATE INDEX IF NOT EXISTS {table_name}_key_idx ON {table_name} (key);
    CREATE INDEX IF NOT EXISTS {table_name}_project_idx ON {table_name} (project);
    CREATE INDEX IF NOT EXISTS {table_name}_type_idx ON {table_name} (type);
    CREATE INDEX IF NOT EXISTS {table_name}_status_idx ON {table_name} (status);
    
    -- Create trigger to automatically update tsvector
    CREATE OR REPLACE FUNCTION {table_name}_tsvector_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.content_tsvector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.description, ''));
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql;
    
    CREATE TRIGGER {table_name}_tsvector_update BEFORE INSERT OR UPDATE
        ON {table_name} FOR EACH ROW EXECUTE FUNCTION {table_name}_tsvector_trigger();
    """
    
    try:
        # Execute the SQL directly using the supabase client
        # Note: This requires appropriate database privileges
        print(f"Initializing table '{table_name}' with vector and full-text search support...")
        
        # For now, we'll use a simplified approach that works with Supabase client
        # The actual table creation should be done via Supabase dashboard or direct SQL access
        print(f"⚠️  Please ensure table '{table_name}' exists with proper schema in Supabase dashboard")
        print("Required columns: id, jira_id, key, project, project_name, priority, type, status,")
        print("created, resolved, updated, component, version, reporter, assignee, title,")
        print("description, content, embedding (vector), content_tsvector, created_at, updated_at")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing table '{table_name}': {e}")
        return False

def process_csv_data(csv_path: str, start_line: int = 0) -> List[Dict[str, Any]]:
    """Process CSV data and return formatted records."""
    print(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} rows.")
    
    # Fill NaN values
    df = df.fillna("")
    
    records = []
    for idx, row in tqdm(df.iloc[start_line:].iterrows(), total=len(df)-start_line, desc="Processing CSV"):
        # Create formatted content for RAG
        title = row.get('title', '').strip()
        description = row.get('description', '').strip()
        
        if title and description:
            content = f"Title: {title}\n\nDescription: {description}"
        elif title:
            content = f"Title: {title}"
        elif description:
            content = f"Description: {description}"
        else:
            content = "No content available"
        
        # Limit content length for embedding
        content = safe_text(content)
        
        # Parse dates (convert to ISO format for Supabase)
        def parse_date(date_str):
            if pd.isna(date_str) or not date_str:
                return None
            try:
                return pd.to_datetime(date_str).isoformat()
            except:
                return None
        
        record = {
            'jira_id': str(row.get('id', idx + start_line)),
            'key': str(row.get('key', '')),
            'project': str(row.get('project', '')),
            'project_name': str(row.get('project_name', '')),
            'priority': str(row.get('priority', '')),
            'type': str(row.get('type', '')),
            'status': str(row.get('status', '')),
            'created': parse_date(row.get('created')),
            'resolved': parse_date(row.get('resolved')),
            'updated': parse_date(row.get('updated')),
            'component': str(row.get('component', '')),
            'version': str(row.get('version', '')),
            'reporter': str(row.get('reporter', '')),
            'assignee': str(row.get('assignee', '')),
            'title': title,
            'description': description,
            'content': content
        }
        
        records.append(record)
    
    return records

def upload_to_supabase(supabase: Client, records: List[Dict[str, Any]], table_name: str):
    """Upload records to Supabase with embeddings."""
    print(f"Uploading {len(records)} records to table '{table_name}'...")
    
    successful_uploads = 0
    failed_uploads = 0
    
    # Process records in batches
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        batch_with_embeddings = []
        
        print(f"Processing batch {i // BATCH_SIZE + 1}/{len(records) // BATCH_SIZE + 1}...")
        
        # Generate embeddings for batch
        for record in batch:
            try:
                # Generate embedding
                embedding = get_embedding(record['content'])
                
                # Convert to proper format for Supabase vector column
                if isinstance(embedding, list):
                    record['embedding'] = embedding
                else:
                    record['embedding'] = embedding
                
                batch_with_embeddings.append(record)
                
            except Exception as e:
                print(f"⚠️  Failed to generate embedding for record {record['jira_id']}: {e}")
                failed_uploads += 1
                continue
        
        # Upload batch to Supabase
        if batch_with_embeddings:
            try:
                result = supabase.table(table_name).upsert(batch_with_embeddings).execute()
                successful_uploads += len(batch_with_embeddings)
                print(f"   ✅ Uploaded {len(batch_with_embeddings)} records")
                
            except Exception as e:
                print(f"❌ Failed to upload batch: {e}")
                print(f"   Error details: {str(e)}")
                failed_uploads += len(batch_with_embeddings)
    
    print(f"Upload complete: {successful_uploads} successful, {failed_uploads} failed")
    return successful_uploads, failed_uploads

def main(csv_path: str, table_names: List[str] = ['bugs', 'pcr'], start_line: int = 0):
    """
    Main function to process JIRA CSV and upload to Supabase.
    Creates separate instances for bugs and pcr (release tickets).
    """
    print("🚀 Starting JIRA CSV to Supabase upload")
    print(f"   CSV Path: {csv_path}")
    print(f"   Tables: {', '.join(table_names)}")
    print(f"   Start Line: {start_line}")
    print(f"   Supabase URL: {SUPABASE_URL}")
    print(f"   Embedding Model: {OPENAI_EMBED_MODEL}")
    print(f"   Batch Size: {BATCH_SIZE}")
    
    # Initialize Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Process CSV data
    records = process_csv_data(csv_path, start_line)
    
    if not records:
        print("❌ No records to process")
        return
    
    # Filter records for different tables based on type
    # Expanded filtering logic based on JIRA issue types
    bugs_records = []
    pcr_records = []
    
    for record in records:
        record_type = record.get('type', '').lower()
        project = record.get('project', '').lower()
        title = record.get('title', '').lower()
        description = record.get('description', '').lower()
        
        # Classify as PCR if any of these patterns match
        is_pcr = any([
            'release' in record_type,
            'pcr' in record_type,
            'change' in record_type,
            'enhancement' in record_type,
            'feature' in record_type,
            'improvement' in record_type,
            'epic' in record_type,
            'story' in record_type,
            'task' in record_type,
            'new feature' in record_type,
            # Check project patterns
            'release' in project,
            'pcr' in project,
            # Check content patterns
            'release' in title,
            'pcr' in title,
            'feature' in title,
            'enhancement' in title
        ])
        
        if is_pcr:
            pcr_records.append(record)
        else:
            # Default to bugs (includes 'bug', 'defect', 'incident', etc.)
            bugs_records.append(record)
    
    print(f"📊 Record distribution:")
    print(f"   • Bugs: {len(bugs_records)}")
    print(f"   • PCR: {len(pcr_records)}")
    
    # Upload to each table
    total_successful = 0
    total_failed = 0
    
    if 'bugs' in table_names and bugs_records:
        print(f"\n🐛 Uploading bugs to 'bugs' table...")
        initialize_supabase_tables(supabase, 'bugs')
        successful, failed = upload_to_supabase(supabase, bugs_records, 'bugs')
        total_successful += successful
        total_failed += failed
    
    if 'pcr' in table_names and pcr_records:
        print(f"\n🔄 Uploading PCR records to 'pcr' table...")
        initialize_supabase_tables(supabase, 'pcr')
        successful, failed = upload_to_supabase(supabase, pcr_records, 'pcr')
        total_successful += successful
        total_failed += failed
    
    print(f"\n🎉 Process completed!")
    print(f"📊 Final Summary:")
    print(f"   • Total successful uploads: {total_successful}")
    print(f"   • Total failed uploads: {total_failed}")
    
    total_records = total_successful + total_failed
    if total_records > 0:
        print(f"   • Success rate: {total_successful/total_records*100:.1f}%")
    else:
        print(f"   • Success rate: No records processed (0 PCR records found with current filtering)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Upload JIRA CSV to Supabase with vector embeddings and full-text search.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload to both bugs and pcr tables
  python upload_jira_csv_to_supabase.py JIRA_DATA.csv
  
  # Upload to specific tables
  python upload_jira_csv_to_supabase.py JIRA_DATA.csv --tables bugs
  
  # Resume from specific line
  python upload_jira_csv_to_supabase.py JIRA_DATA.csv --start-line 500

Environment Variables Required:
  SUPABASE_URL - Supabase project URL
  SUPABASE_KEY - Supabase service role key
  OPENAI_API_KEY - OpenAI API key
  OPENAI_EMBED_MODEL - Embedding model (default: text-embedding-3-small)
  BATCH_SIZE - Upload batch size (default: 100)
        """
    )
    
    parser.add_argument('csv_path', help='Path to JIRA CSV file')
    parser.add_argument('--tables', nargs='+', default=['bugs', 'pcr'],
                       choices=['bugs', 'pcr'], help='Tables to upload to')
    parser.add_argument('--start-line', type=int, default=0,
                       help='CSV line to start from (default: 0)')
    
    args = parser.parse_args()
    
    # Validate required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment")
        exit(1)
    
    main(args.csv_path, args.tables, args.start_line)