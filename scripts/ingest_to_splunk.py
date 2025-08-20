#!/usr/bin/env python3
"""
Splunk ingestion script for Cuttlefish4.
Ingests log files into Splunk Cloud using HTTP Event Collector (HEC).
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import time
from pathlib import Path
import urllib3

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, skip loading .env file
    pass

# Disable SSL warnings for testing (remove in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add the app directory to the path so we can import our tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

DEFAULT_BATCH_SIZE = 100
DEFAULT_CHUNK_SIZE_MB = 5

class SplunkIngester:
    def __init__(self):
        """Initialize Splunk ingester with environment configuration."""
        self.splunk_host = os.environ.get('SPLUNK_HOST')
        self.splunk_token = os.environ.get('SPLUNK_TOKEN')
        self.index_name = os.environ.get('SPLUNK_INDEX', 'cuttlefish')
        
        if not self.splunk_host:
            raise ValueError("SPLUNK_HOST environment variable is required")
        
        if not self.splunk_token:
            raise ValueError("SPLUNK_TOKEN environment variable is required")
        
        # Setup HEC endpoint
        self.hec_endpoint = f"{self.splunk_host}/services/collector"
        
        # Setup session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Splunk {self.splunk_token}',
            'Content-Type': 'application/json'
        })
        
        print(f"✅ Splunk ingester initialized")
        print(f"   Host: {self.splunk_host}")
        print(f"   Index: {self.index_name}")
    
    def test_connection(self) -> bool:
        """Test connection to Splunk HEC."""
        try:
            print("🔗 Testing Splunk HEC connection...")
            
            # Send a simple test event
            test_event = {
                'time': int(datetime.now().timestamp()),
                'index': self.index_name,
                'source': 'cuttlefish_ingester_test',
                'sourcetype': 'test_log',
                'event': {
                    'level': 'INFO',
                    'message': 'Splunk ingester connection test',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            response = self.session.post(self.hec_endpoint, 
                                       data=json.dumps(test_event),
                                       timeout=30,
                                       verify=False)
            
            if response.status_code == 200:
                print("✅ Splunk HEC connection successful")
                return True
            else:
                print(f"❌ HEC connection failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ HEC connection test failed: {e}")
            return False
    
    def ingest_log_file(self, log_file_path: str, batch_size: int = DEFAULT_BATCH_SIZE, 
                       chunk_size_mb: float = DEFAULT_CHUNK_SIZE_MB) -> Dict[str, Any]:
        """
        Ingest a log file into Splunk.
        
        Args:
            log_file_path: Path to the log file
            batch_size: Number of log entries to send per batch
            chunk_size_mb: Maximum size of each batch in MB
            
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
        successful_batches = 0
        failed_batches = 0
        total_events_sent = 0
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                batch = []
                batch_size_bytes = 0
                chunk_size_bytes = int(chunk_size_mb * 1024 * 1024)
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse log entry
                    log_entry = self._parse_log4j_entry(line)
                    if log_entry:
                        # Create Splunk event
                        event = {
                            'time': log_entry.get('timestamp_unix', int(datetime.now().timestamp())),
                            'index': self.index_name,
                            'source': os.path.basename(log_file_path),
                            'sourcetype': 'java_log4j',
                            'event': {
                                'raw': line,
                                'level': log_entry.get('level'),
                                'logger': log_entry.get('logger'),
                                'thread': log_entry.get('thread'),
                                'message': log_entry.get('message'),
                                'timestamp': log_entry.get('timestamp')
                            }
                        }
                        
                        batch.append(event)
                        batch_size_bytes += len(json.dumps(event).encode('utf-8'))
                        
                        # Send batch if it's full or reached size limit
                        if len(batch) >= batch_size or batch_size_bytes >= chunk_size_bytes:
                            success = self._send_batch(batch)
                            if success:
                                successful_batches += 1
                                total_events_sent += len(batch)
                            else:
                                failed_batches += 1
                            
                            batch = []
                            batch_size_bytes = 0
                    
                    total_lines += 1
                    
                    # Progress indicator
                    if total_lines % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = total_lines / elapsed if elapsed > 0 else 0
                        print(f"   Processed {total_lines} lines ({rate:.0f} lines/sec)")
                
                # Send remaining batch
                if batch:
                    success = self._send_batch(batch)
                    if success:
                        successful_batches += 1
                        total_events_sent += len(batch)
                    else:
                        failed_batches += 1
        
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            raise
        
        # Calculate statistics
        end_time = time.time()
        total_time = end_time - start_time
        
        stats = {
            'log_file': log_file_path,
            'file_size_mb': file_size_mb,
            'total_lines_processed': total_lines,
            'total_events_sent': total_events_sent,
            'successful_batches': successful_batches,
            'failed_batches': failed_batches,
            'total_batches': successful_batches + failed_batches,
            'processing_time_seconds': total_time,
            'lines_per_second': total_lines / total_time if total_time > 0 else 0,
            'success_rate': successful_batches / (successful_batches + failed_batches) if (successful_batches + failed_batches) > 0 else 0
        }
        
        print(f"✅ Ingestion complete:")
        print(f"   Lines processed: {stats['total_lines_processed']}")
        print(f"   Events sent: {stats['total_events_sent']}")
        print(f"   Successful batches: {stats['successful_batches']}/{stats['total_batches']}")
        print(f"   Processing time: {stats['processing_time_seconds']:.1f}s")
        print(f"   Rate: {stats['lines_per_second']:.0f} lines/sec")
        
        return stats
    
    def _parse_log4j_entry(self, log_line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Log4j log entry.
        Expected format: timestamp [thread] level logger - message
        """
        try:
            # Regular expression to parse Log4j format
            # Example: 2025-08-18 15:30:45.123 [main] INFO com.cuttlefish.Application - Starting application
            log_pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\[([^\]]+)\]\s+(\w+)\s+([^\s]+)\s+-\s+(.+)$'
            
            match = re.match(log_pattern, log_line)
            if match:
                timestamp_str, thread, level, logger, message = match.groups()
                
                # Parse timestamp
                try:
                    timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                    timestamp_unix = int(timestamp_dt.timestamp())
                except ValueError:
                    timestamp_dt = datetime.now()
                    timestamp_unix = int(timestamp_dt.timestamp())
                
                return {
                    'timestamp': timestamp_str,
                    'timestamp_unix': timestamp_unix,
                    'thread': thread,
                    'level': level,
                    'logger': logger,
                    'message': message
                }
            
            # If regex doesn't match, treat as a continuation line or malformed entry
            return {
                'timestamp': datetime.now().isoformat(),
                'timestamp_unix': int(datetime.now().timestamp()),
                'thread': 'unknown',
                'level': 'INFO',
                'logger': 'unparsed',
                'message': log_line
            }
            
        except Exception as e:
            print(f"⚠️  Error parsing log line: {e}")
            return None
    
    def _send_batch(self, batch: List[Dict[str, Any]]) -> bool:
        """Send a batch of events to Splunk HEC."""
        try:
            # Convert batch to newline-delimited JSON (required by HEC)
            payload = '\n'.join(json.dumps(event) for event in batch)
            
            response = self.session.post(self.hec_endpoint,
                                       data=payload,
                                       timeout=60,
                                       verify=False)
            
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️  Batch failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"⚠️  Error sending batch: {e}")
            return False
    
    def ingest_multiple_files(self, log_directory: str, pattern: str = "*.log") -> Dict[str, Any]:
        """
        Ingest multiple log files from a directory.
        
        Args:
            log_directory: Directory containing log files
            pattern: File pattern to match (default: *.log)
            
        Returns:
            Dictionary with overall statistics
        """
        from pathlib import Path
        
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
            'total_events': 0,
            'total_time': 0,
            'file_stats': []
        }
        
        start_time = time.time()
        
        for i, log_file in enumerate(log_files, 1):
            print(f"\n📄 Processing file {i}/{len(log_files)}: {log_file.name}")
            
            try:
                file_stats = self.ingest_log_file(str(log_file))
                overall_stats['successful_files'] += 1
                overall_stats['total_lines'] += file_stats['total_lines_processed']
                overall_stats['total_events'] += file_stats['total_events_sent']
                overall_stats['file_stats'].append(file_stats)
                
            except Exception as e:
                print(f"❌ Failed to ingest {log_file.name}: {e}")
                overall_stats['failed_files'] += 1
        
        overall_stats['total_time'] = time.time() - start_time
        
        print(f"\n🎉 Batch ingestion complete:")
        print(f"   Files processed: {overall_stats['successful_files']}/{overall_stats['total_files']}")
        print(f"   Total lines: {overall_stats['total_lines']}")
        print(f"   Total events: {overall_stats['total_events']}")
        print(f"   Total time: {overall_stats['total_time']:.1f}s")
        
        return overall_stats


def main():
    parser = argparse.ArgumentParser(description='Ingest log files into Splunk Cloud')
    parser.add_argument('input', help='Log file or directory to ingest')
    parser.add_argument('--batch-size', '-b', type=int, default=DEFAULT_BATCH_SIZE,
                      help=f'Batch size for ingestion (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--chunk-size', '-c', type=float, default=DEFAULT_CHUNK_SIZE_MB,
                      help=f'Maximum batch size in MB (default: {DEFAULT_CHUNK_SIZE_MB})')
    parser.add_argument('--pattern', '-p', default='*.log',
                      help='File pattern for directory ingestion (default: *.log)')
    parser.add_argument('--test-connection', '-t', action='store_true',
                      help='Test connection to Splunk HEC and exit')
    
    args = parser.parse_args()
    
    try:
        # Initialize ingester
        ingester = SplunkIngester()
        
        # Test connection if requested
        if args.test_connection:
            success = ingester.test_connection()
            return 0 if success else 1
        
        # Determine if input is file or directory
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Single file ingestion
            stats = ingester.ingest_log_file(str(input_path), args.batch_size, args.chunk_size)
            
            # Save statistics
            stats_file = input_path.with_suffix('.json')
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
            print(f"📊 Statistics saved to: {stats_file}")
            
        elif input_path.is_dir():
            # Directory ingestion
            stats = ingester.ingest_multiple_files(str(input_path), args.pattern)
            
            # Save statistics
            stats_file = input_path / 'ingestion_stats.json'
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
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