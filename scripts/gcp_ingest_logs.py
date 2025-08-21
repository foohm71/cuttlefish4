#!/usr/bin/env python3
# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
GCP Cloud Logging ingestion script for Cuttlefish4.
Ingests log files into Google Cloud Logging using the Cloud Logging API.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import time
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add the app directory to the path so we can import our tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from google.cloud import logging
    from google.cloud.logging import Resource
    from app.tools.gcp_auth import get_gcp_client, test_gcp_auth, get_deployment_info
except ImportError as e:
    print(f"❌ Error: Required packages not installed. Run: pip install google-cloud-logging")
    print(f"   Import error: {e}")
    sys.exit(1)

DEFAULT_BATCH_SIZE = 100
DEFAULT_LOG_NAME = "cuttlefish_synthetic_logs"

class GCPLogIngester:
    def __init__(self, project_id: str = None, log_name: str = DEFAULT_LOG_NAME):
        """Initialize GCP Log ingester with project configuration."""
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project_id required")
        
        self.log_name = log_name
        
        # Initialize the logging client using cloud-ready authentication
        try:
            self.client = get_gcp_client(self.project_id)
            self.logger = self.client.logger(self.log_name)
            
            # Get deployment info for logging
            deployment_info = get_deployment_info()
            
            print(f"✅ GCP Log ingester initialized")
            print(f"   Project: {self.project_id}")
            print(f"   Log Name: {self.log_name}")
            if deployment_info.get("is_gcp"):
                print(f"   Running on GCP: {deployment_info.get('gcp_service', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Failed to initialize GCP Logging client: {e}")
            print(f"💡 Deployment info: {get_deployment_info()}")
            raise ValueError(f"Failed to initialize GCP Logging client: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to GCP Cloud Logging."""
        try:
            print("🔗 Testing GCP Cloud Logging connection...")
            
            # Send a simple test event
            test_entry = {
                'level': 'INFO',
                'logger': 'gcp_ingester_test',
                'thread': 'main',
                'message': 'GCP logging ingester connection test',
                'timestamp': datetime.now().isoformat()
            }
            
            # Create resource for the log entry
            resource = Resource(
                type="global",
                labels={}
            )
            
            # Log the test entry
            self.logger.log_struct(test_entry, severity='INFO', resource=resource)
            
            print("✅ GCP Cloud Logging connection successful")
            return True
            
        except Exception as e:
            print(f"❌ GCP Cloud Logging connection test failed: {e}")
            return False
    
    def ingest_log_file(self, log_file_path: str, batch_size: int = DEFAULT_BATCH_SIZE) -> Dict[str, Any]:
        """
        Ingest a log file into GCP Cloud Logging.
        
        Args:
            log_file_path: Path to the log file
            batch_size: Number of log entries to process per batch
            
        Returns:
            Dictionary with ingestion statistics
        """
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"Log file not found: {log_file_path}")
        
        print(f"📂 Ingesting log file: {log_file_path}")
        
        # Get file info
        file_size_mb = os.path.getsize(log_file_path) / 1024 / 1024
        print(f"   File size: {file_size_mb:.2f} MB")
        
        start_time = time.time()
        total_lines = 0
        successful_entries = 0
        failed_entries = 0
        
        # Create resource for all log entries
        resource = Resource(
            type="generic_node",
            labels={
                "location": "global",
                "namespace": "cuttlefish4",
                "node_id": "log-ingester"
            }
        )
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                batch_entries = []
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse log entry
                    log_entry = self._parse_log4j_entry(line)
                    if log_entry:
                        # Structure for GCP Logging
                        structured_entry = {
                            'level': log_entry.get('level', 'INFO'),
                            'logger': log_entry.get('logger', 'unknown'),
                            'thread': log_entry.get('thread', 'main'),
                            'message': log_entry.get('message', ''),
                            'raw_log': line,
                            'timestamp': log_entry.get('timestamp', datetime.now().isoformat()),
                            'source_file': os.path.basename(log_file_path),
                            'line_number': line_num
                        }
                        
                        batch_entries.append((structured_entry, log_entry.get('level', 'INFO')))
                        
                        # Process batch when it's full
                        if len(batch_entries) >= batch_size:
                            success_count = self._process_batch(batch_entries, resource)
                            successful_entries += success_count
                            failed_entries += (len(batch_entries) - success_count)
                            batch_entries = []
                    
                    total_lines += 1
                    
                    # Progress indicator
                    if total_lines % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = total_lines / elapsed if elapsed > 0 else 0
                        print(f"   Processed {total_lines} lines ({rate:.0f} lines/sec)")
                
                # Process remaining batch
                if batch_entries:
                    success_count = self._process_batch(batch_entries, resource)
                    successful_entries += success_count
                    failed_entries += (len(batch_entries) - success_count)
        
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            raise
        
        # Calculate statistics
        end_time = time.time()
        total_time = end_time - start_time
        
        stats = {
            'log_file': log_file_path,
            'project_id': self.project_id,
            'log_name': self.log_name,
            'file_size_mb': file_size_mb,
            'total_lines_processed': total_lines,
            'successful_entries': successful_entries,
            'failed_entries': failed_entries,
            'total_entries': successful_entries + failed_entries,
            'processing_time_seconds': total_time,
            'lines_per_second': total_lines / total_time if total_time > 0 else 0,
            'success_rate': successful_entries / (successful_entries + failed_entries) if (successful_entries + failed_entries) > 0 else 0
        }
        
        print(f"✅ Ingestion complete:")
        print(f"   Lines processed: {stats['total_lines_processed']}")
        print(f"   Entries sent: {stats['successful_entries']}")
        print(f"   Failed entries: {stats['failed_entries']}")
        print(f"   Processing time: {stats['processing_time_seconds']:.1f}s")
        print(f"   Rate: {stats['lines_per_second']:.0f} lines/sec")
        print(f"   Success rate: {stats['success_rate']:.1%}")
        
        return stats
    
    def _parse_log4j_entry(self, log_line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Log4j log entry.
        Expected format: timestamp [thread] level logger - message
        """
        try:
            # Regular expression to parse Log4j format
            # Example: 2025-08-19 09:47:16.529 [main] INFO org.hibernate.engine.SessionManager - Configuration loaded from: value_54
            log_pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\[([^\]]+)\]\s+(\w+)\s+([^\s]+)\s+-\s+(.+)$'
            
            match = re.match(log_pattern, log_line)
            if match:
                timestamp_str, thread, level, logger, message = match.groups()
                
                # Parse timestamp
                try:
                    timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                    timestamp_iso = timestamp_dt.isoformat()
                except ValueError:
                    timestamp_iso = datetime.now().isoformat()
                
                return {
                    'timestamp': timestamp_iso,
                    'thread': thread,
                    'level': level,
                    'logger': logger,
                    'message': message
                }
            
            # If regex doesn't match, treat as unstructured log
            return {
                'timestamp': datetime.now().isoformat(),
                'thread': 'unknown',
                'level': 'INFO',
                'logger': 'unparsed',
                'message': log_line
            }
            
        except Exception as e:
            print(f"⚠️  Error parsing log line: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'thread': 'unknown',
                'level': 'ERROR',
                'logger': 'parser_error',
                'message': f"Failed to parse: {log_line}"
            }
    
    def _process_batch(self, batch_entries: List[tuple], resource: Resource) -> int:
        """Process a batch of log entries."""
        successful_count = 0
        
        for structured_entry, level in batch_entries:
            try:
                # Map log levels to GCP severity
                severity_mapping = {
                    'ERROR': 'ERROR',
                    'WARN': 'WARNING',
                    'WARNING': 'WARNING',
                    'INFO': 'INFO',
                    'DEBUG': 'DEBUG',
                    'TRACE': 'DEBUG'
                }
                severity = severity_mapping.get(level.upper(), 'INFO')
                
                # Log the structured entry
                self.logger.log_struct(
                    structured_entry,
                    severity=severity,
                    resource=resource
                )
                successful_count += 1
                
            except Exception as e:
                print(f"⚠️  Failed to log entry: {e}")
                continue
        
        return successful_count
    
    def ingest_multiple_files(self, log_directory: str, pattern: str = "*.log") -> Dict[str, Any]:
        """
        Ingest multiple log files from a directory.
        
        Args:
            log_directory: Directory containing log files
            pattern: File pattern to match (default: *.log)
            
        Returns:
            Dictionary with overall statistics
        """
        log_dir = Path(log_directory)
        if not log_dir.exists():
            raise FileNotFoundError(f"Log directory not found: {log_directory}")
        
        # Find matching files
        log_files = list(log_dir.glob(pattern))
        
        if not log_files:
            print(f"⚠️  No log files found matching pattern '{pattern}' in {log_directory}")
            return {}
        
        print(f"📁 Found {len(log_files)} log files to ingest")
        
        overall_stats = {
            'total_files': len(log_files),
            'successful_files': 0,
            'failed_files': 0,
            'total_lines': 0,
            'total_entries': 0,
            'total_time': 0,
            'file_stats': []
        }
        
        start_time = time.time()
        
        for i, log_file in enumerate(log_files, 1):
            print(f"\\n📄 Processing file {i}/{len(log_files)}: {log_file.name}")
            
            try:
                file_stats = self.ingest_log_file(str(log_file))
                overall_stats['successful_files'] += 1
                overall_stats['total_lines'] += file_stats['total_lines_processed']
                overall_stats['total_entries'] += file_stats['successful_entries']
                overall_stats['file_stats'].append(file_stats)
                
            except Exception as e:
                print(f"❌ Failed to ingest {log_file.name}: {e}")
                overall_stats['failed_files'] += 1
        
        overall_stats['total_time'] = time.time() - start_time
        
        print(f"\\n🎉 Batch ingestion complete:")
        print(f"   Files processed: {overall_stats['successful_files']}/{overall_stats['total_files']}")
        print(f"   Total lines: {overall_stats['total_lines']}")
        print(f"   Total entries: {overall_stats['total_entries']}")
        print(f"   Total time: {overall_stats['total_time']:.1f}s")
        
        return overall_stats

def main():
    parser = argparse.ArgumentParser(description='Ingest log files into Google Cloud Logging')
    parser.add_argument('input', nargs='?', help='Log file or directory to ingest')
    parser.add_argument('--project-id', '-p', help='GCP Project ID (default: from GOOGLE_CLOUD_PROJECT env var)')
    parser.add_argument('--log-name', '-l', default=DEFAULT_LOG_NAME,
                      help=f'GCP log name (default: {DEFAULT_LOG_NAME})')
    parser.add_argument('--batch-size', '-b', type=int, default=DEFAULT_BATCH_SIZE,
                      help=f'Batch size for processing (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--pattern', '-pt', default='*.log',
                      help='File pattern for directory ingestion (default: *.log)')
    parser.add_argument('--test-connection', '-t', action='store_true',
                      help='Test connection to GCP Cloud Logging and exit')
    
    args = parser.parse_args()
    
    try:
        # Initialize ingester
        ingester = GCPLogIngester(project_id=args.project_id, log_name=args.log_name)
        
        # Test connection if requested
        if args.test_connection:
            success = ingester.test_connection()
            return 0 if success else 1
        
        # Check if input is provided for non-test operations
        if not args.input:
            print("❌ Error: input file or directory is required (unless using --test-connection)")
            return 1
        
        # Determine if input is file or directory
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Single file ingestion
            stats = ingester.ingest_log_file(str(input_path), args.batch_size)
            
            # Save statistics
            stats_file = input_path.parent / f"{input_path.stem}_gcp_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            print(f"📊 Statistics saved to: {stats_file}")
            
        elif input_path.is_dir():
            # Directory ingestion
            stats = ingester.ingest_multiple_files(str(input_path), args.pattern)
            
            # Save statistics
            stats_file = input_path / 'gcp_ingestion_stats.json'
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            print(f"📊 Statistics saved to: {stats_file}")
            
        else:
            print(f"❌ Input path not found: {args.input}")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())