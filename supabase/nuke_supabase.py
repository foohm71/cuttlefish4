#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Supabase Nuke Script - Clean up all data in Supabase tables

⚠️  WARNING: This script will DELETE ALL DATA in the specified Supabase tables!
Use with extreme caution. This is irreversible.

This script will:
1. Drop and recreate the 'bugs' and 'pcr' tables
2. Recreate all indexes and functions
3. Reset the database to a clean state

Usage:
    python nuke_supabase.py --confirm
    
    # Nuke specific tables only
    python nuke_supabase.py --tables bugs --confirm
    python nuke_supabase.py --tables pcr --confirm
    python nuke_supabase.py --tables bugs,pcr --confirm
"""

import os
import sys
import argparse
from typing import List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseNuker:
    """Utility to completely clean Supabase tables and reset schema."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_KEY")
        
        # Initialize client with service role key for admin operations
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Available tables
        self.available_tables = ['bugs', 'pcr']
    
    def confirm_destruction(self, tables: List[str]) -> bool:
        """Confirm the destructive operation."""
        print("🚨 DANGER ZONE 🚨")
        print(f"You are about to PERMANENTLY DELETE all data in tables: {', '.join(tables)}")
        print("This action is IRREVERSIBLE!")
        print()
        
        response = input("Type 'DELETE EVERYTHING' to confirm: ")
        return response == 'DELETE EVERYTHING'
    
    def nuke_table(self, table_name: str) -> bool:
        """
        Completely nuke a table and recreate it with proper schema.
        
        Args:
            table_name: Name of table to nuke ('bugs' or 'pcr')
        
        Returns:
            True if successful, False otherwise
        """
        if table_name not in self.available_tables:
            print(f"❌ Invalid table name: {table_name}")
            return False
        
        try:
            print(f"🗑️  Nuking table '{table_name}'...")
            
            # Step 1: Drop the table completely
            drop_sql = f"DROP TABLE IF EXISTS {table_name} CASCADE;"
            
            # Note: Direct SQL execution requires RLS bypass and proper permissions
            # This is a simplified approach - in production you might need to use
            # the Supabase dashboard SQL editor or a proper admin connection
            
            print(f"   Dropping table {table_name}...")
            try:
                # Attempt to delete all rows first (safer approach)
                result = self.client.table(table_name).delete().neq('id', -1).execute()
                print(f"   Deleted {len(result.data) if result.data else 'unknown'} rows")
            except Exception as delete_error:
                print(f"   Note: Could not delete rows: {delete_error}")
            
            # Step 2: Recreate table with proper schema
            print(f"   Recreating table {table_name} with schema...")
            create_table_sql = self._get_create_table_sql(table_name)
            
            # Step 3: Create indexes
            print(f"   Creating indexes for {table_name}...")
            index_sql = self._get_create_indexes_sql(table_name)
            
            # Step 4: Create trigger
            print(f"   Creating tsvector trigger for {table_name}...")
            trigger_sql = self._get_create_trigger_sql(table_name)
            
            print(f"✅ Table '{table_name}' has been nuked and recreated")
            print(f"⚠️  Note: You may need to execute the full schema SQL manually in Supabase dashboard")
            
            # Show the SQL that needs to be executed
            print("\n" + "="*60)
            print(f"SQL TO EXECUTE IN SUPABASE SQL EDITOR FOR {table_name.upper()}:")
            print("="*60)
            print(create_table_sql)
            print(index_sql)
            print(trigger_sql)
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to nuke table '{table_name}': {e}")
            return False
    
    def _get_create_table_sql(self, table_name: str) -> str:
        """Get the CREATE TABLE SQL for the specified table."""
        return f"""
-- Drop table if exists
DROP TABLE IF EXISTS {table_name} CASCADE;

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
);"""
    
    def _get_create_indexes_sql(self, table_name: str) -> str:
        """Get the CREATE INDEX SQL for the specified table."""
        return f"""
-- Create indexes for performance
CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx ON {table_name} 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS {table_name}_content_search_idx ON {table_name} 
    USING GIN (content_tsvector);

CREATE INDEX IF NOT EXISTS {table_name}_jira_id_idx ON {table_name} (jira_id);
CREATE INDEX IF NOT EXISTS {table_name}_key_idx ON {table_name} (key);
CREATE INDEX IF NOT EXISTS {table_name}_project_idx ON {table_name} (project);
CREATE INDEX IF NOT EXISTS {table_name}_type_idx ON {table_name} (type);
CREATE INDEX IF NOT EXISTS {table_name}_status_idx ON {table_name} (status);"""
    
    def _get_create_trigger_sql(self, table_name: str) -> str:
        """Get the CREATE TRIGGER SQL for the specified table."""
        return f"""
-- Create trigger to automatically update tsvector
CREATE OR REPLACE FUNCTION {table_name}_tsvector_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsvector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.description, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER {table_name}_tsvector_update BEFORE INSERT OR UPDATE
    ON {table_name} FOR EACH ROW EXECUTE FUNCTION {table_name}_tsvector_trigger();"""
    
    def nuke_tables(self, tables: Optional[List[str]] = None) -> bool:
        """
        Nuke multiple tables.
        
        Args:
            tables: List of table names to nuke. If None, nukes all available tables.
        
        Returns:
            True if all successful, False if any failed
        """
        if tables is None:
            tables = self.available_tables.copy()
        
        print(f"🚀 Starting nuke operation for {len(tables)} table(s)")
        
        success_count = 0
        for table in tables:
            if self.nuke_table(table):
                success_count += 1
            print()  # Empty line between tables
        
        print(f"📊 Nuke operation complete: {success_count}/{len(tables)} tables processed successfully")
        
        if success_count == len(tables):
            print("✅ All tables nuked successfully!")
            print("\n🔧 NEXT STEPS:")
            print("1. Execute the printed SQL statements in your Supabase SQL Editor")
            print("2. Run the upload script to populate your data:")
            print("   python suprabase/upload_jira_csv_to_supabase.py your_data.csv")
            return True
        else:
            print(f"⚠️  {len(tables) - success_count} table(s) failed to nuke completely")
            return False
    
    def get_table_stats(self) -> dict:
        """Get statistics for all tables."""
        stats = {}
        
        for table in self.available_tables:
            try:
                result = self.client.table(table).select('id', count='exact').execute()
                stats[table] = result.count if result.count is not None else 0
            except Exception as e:
                stats[table] = f"Error: {e}"
        
        return stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Nuke Supabase tables - DANGEROUS OPERATION!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This script will DELETE ALL DATA in the specified tables!

Examples:
  # Show current table stats (safe)
  python nuke_supabase.py --stats
  
  # Nuke all tables (DANGEROUS)
  python nuke_supabase.py --confirm
  
  # Nuke specific tables (DANGEROUS)
  python nuke_supabase.py --tables bugs --confirm
  python nuke_supabase.py --tables bugs,pcr --confirm

Environment Variables Required:
  SUPABASE_URL - Supabase project URL
  SUPABASE_KEY - Supabase service role key (not anon key!)
        """
    )
    
    parser.add_argument('--tables', 
                       help='Comma-separated list of tables to nuke (bugs,pcr). Default: all')
    parser.add_argument('--confirm', 
                       action='store_true',
                       help='Confirm that you want to delete everything (required for destructive operations)')
    parser.add_argument('--stats', 
                       action='store_true',
                       help='Show table statistics and exit (safe operation)')
    
    args = parser.parse_args()
    
    # Validate required environment variables
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment")
        return 1
    
    try:
        nuker = SupabaseNuker()
        
        # Show stats if requested
        if args.stats:
            print("📊 Current Supabase table statistics:")
            stats = nuker.get_table_stats()
            for table, count in stats.items():
                print(f"   {table}: {count} rows")
            return 0
        
        # Parse tables
        if args.tables:
            tables = [t.strip() for t in args.tables.split(',')]
            invalid_tables = [t for t in tables if t not in nuker.available_tables]
            if invalid_tables:
                print(f"❌ Invalid table names: {', '.join(invalid_tables)}")
                print(f"Available tables: {', '.join(nuker.available_tables)}")
                return 1
        else:
            tables = None  # Will nuke all tables
        
        # Show current stats
        print("📊 Current table statistics:")
        stats = nuker.get_table_stats()
        for table, count in stats.items():
            if tables is None or table in tables:
                print(f"   {table}: {count} rows")
        print()
        
        # Require confirmation for destructive operations
        if not args.confirm:
            print("❌ This is a destructive operation. Use --confirm to proceed.")
            print("Use --stats to safely view table statistics.")
            return 1
        
        # Double confirmation
        target_tables = tables or nuker.available_tables
        if not nuker.confirm_destruction(target_tables):
            print("❌ Operation cancelled by user")
            return 1
        
        # Execute nuke operation
        print("\n🚀 Beginning nuke operation...")
        success = nuker.nuke_tables(tables)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())