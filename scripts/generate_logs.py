#!/usr/bin/env python3
"""
Log generator script for Cuttlefish4 testing.
Generates synthetic Log4j Java application logs with realistic patterns and controlled error injection.
"""

import os
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
import argparse

# Configuration
DEFAULT_MAX_SIZE_MB = 20
DEFAULT_ERROR_RATE = 0.001  # 0.1% error rate
DEFAULT_OUTPUT_FILE = "cuttlefish_synthetic_logs.log"

# Log levels and their weights (higher weight = more frequent)
LOG_LEVELS = {
    'TRACE': 5,
    'DEBUG': 15, 
    'INFO': 60,
    'WARN': 15,
    'ERROR': 5
}

# Common Java package names for realistic logger names
JAVA_PACKAGES = [
    'com.cuttlefish.core',
    'com.cuttlefish.service', 
    'com.cuttlefish.repository',
    'com.cuttlefish.controller',
    'com.cuttlefish.security',
    'com.cuttlefish.config',
    'com.cuttlefish.util',
    'org.springframework.web',
    'org.springframework.security',
    'org.hibernate.engine',
    'org.apache.kafka.clients',
    'org.apache.http.impl'
]

# Common class names
CLASS_NAMES = [
    'UserService', 'AuthController', 'DatabaseManager', 'CacheService',
    'MessageProducer', 'ConfigLoader', 'SecurityFilter', 'DataProcessor',
    'ApiGateway', 'SessionManager', 'FileHandler', 'MetricsCollector'
]

# Normal log messages
NORMAL_MESSAGES = [
    'Processing user request for user ID: {}',
    'Database connection established successfully',
    'Cache hit for key: {}', 
    'Cache miss for key: {}',
    'Request processed successfully in {}ms',
    'Starting scheduled task: {}',
    'Configuration loaded from: {}',
    'Authentication successful for user: {}',
    'Session created with ID: {}',
    'Message published to topic: {}',
    'File uploaded successfully: {}',
    'Metric recorded: {} = {}',
    'Health check passed for service: {}',
    'API call completed: {} {}',
    'Transaction committed successfully',
    'Connection pool size: {} active, {} idle'
]

# Error types and their corresponding messages/stack traces
ERROR_TYPES = {
    'CertificateExpiredException': {
        'messages': [
            'Certificate expired for domain: {}',
            'SSL handshake failed: Certificate not valid after {}',
            'X.509 certificate expired on {}',
            'TLS connection failed: Certificate validation error'
        ],
        'stack_traces': [
            'java.security.cert.CertificateExpiredException: NotAfter: {}',
            'javax.net.ssl.SSLException: Certificate expired',
            'sun.security.validator.ValidatorException: PKIX path validation failed'
        ]
    },
    'HttpServerErrorException': {
        'messages': [
            'HTTP 500 Internal Server Error from upstream service: {}',
            'HTTP 502 Bad Gateway: Service unavailable',
            'HTTP 503 Service Unavailable: {}', 
            'HTTP 504 Gateway Timeout: Request timed out after {}ms'
        ],
        'stack_traces': [
            'org.springframework.web.client.HttpServerErrorException$InternalServerError: 500 Internal Server Error',
            'java.net.ConnectException: Connection refused by upstream service',
            'java.net.SocketTimeoutException: Read timed out'
        ]
    },
    'DiskSpaceExceededException': {
        'messages': [
            'Insufficient disk space: {} MB available, {} MB required',
            'Disk full: Cannot write to {}',
            'Storage quota exceeded for partition: {}',
            'Low disk space warning: {} MB remaining'
        ],
        'stack_traces': [
            'java.io.IOException: No space left on device',
            'com.cuttlefish.storage.DiskSpaceExceededException: Available: {} MB, Required: {} MB',
            'java.nio.file.FileSystemException: No space left on device'
        ]
    },
    'DeadLetterQueueException': {
        'messages': [
            'Message sent to dead letter queue after {} retry attempts',
            'Dead letter queue full: {} messages, max capacity: {}',
            'Message processing failed permanently: {}',
            'DLQ consumer lag detected: {} unprocessed messages'
        ],
        'stack_traces': [
            'com.cuttlefish.messaging.DeadLetterQueueException: Max retries exceeded',
            'org.apache.kafka.clients.consumer.OffsetOutOfRangeException',
            'javax.jms.JMSException: Dead letter queue capacity exceeded'
        ]
    }
}

# Thread names
THREAD_NAMES = [
    'main', 'http-nio-8080-exec-{}', 'pool-{}-thread-{}', 'scheduler-{}',
    'kafka-consumer-{}', 'async-task-{}', 'background-worker-{}'
]

class LogGenerator:
    def __init__(self, max_size_mb: float = DEFAULT_MAX_SIZE_MB, error_rate: float = DEFAULT_ERROR_RATE):
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.error_rate = error_rate
        self.current_size = 0
        self.log_entries = []
        
    def generate_logs(self, output_file: str = DEFAULT_OUTPUT_FILE) -> Dict[str, Any]:
        """Generate synthetic logs up to the specified size limit."""
        print(f"🔄 Generating logs (max size: {self.max_size_bytes / 1024 / 1024:.1f} MB, error rate: {self.error_rate:.1%})")
        
        start_time = datetime.now() - timedelta(hours=2)  # Generate logs from 2 hours ago
        current_time = start_time
        
        total_entries = 0
        error_entries = 0
        
        with open(output_file, 'w') as f:
            while self.current_size < self.max_size_bytes:
                # Generate log entry
                if random.random() < self.error_rate:
                    entry = self._generate_error_log(current_time)
                    error_entries += 1
                else:
                    entry = self._generate_normal_log(current_time)
                
                # Write to file
                f.write(entry + '\n')
                
                # Update counters
                entry_size = len(entry.encode('utf-8')) + 1  # +1 for newline
                self.current_size += entry_size
                total_entries += 1
                
                # Advance time randomly (1-60 seconds)
                current_time += timedelta(seconds=random.randint(1, 60))
                
                # Progress indicator
                if total_entries % 1000 == 0:
                    progress = (self.current_size / self.max_size_bytes) * 100
                    print(f"   Generated {total_entries} entries ({progress:.1f}% of target size)")
        
        # Statistics
        actual_size_mb = self.current_size / 1024 / 1024
        actual_error_rate = error_entries / total_entries if total_entries > 0 else 0
        
        stats = {
            'total_entries': total_entries,
            'error_entries': error_entries,
            'actual_size_mb': actual_size_mb,
            'actual_error_rate': actual_error_rate,
            'output_file': output_file,
            'time_span_hours': (current_time - start_time).total_seconds() / 3600
        }
        
        print(f"✅ Log generation complete:")
        print(f"   Total entries: {stats['total_entries']}")
        print(f"   Error entries: {stats['error_entries']} ({stats['actual_error_rate']:.3%})")
        print(f"   File size: {stats['actual_size_mb']:.2f} MB")
        print(f"   Time span: {stats['time_span_hours']:.1f} hours")
        print(f"   Output file: {stats['output_file']}")
        
        return stats
    
    def _generate_normal_log(self, timestamp: datetime) -> str:
        """Generate a normal (non-error) log entry."""
        level = self._weighted_choice(LOG_LEVELS)
        logger = self._get_random_logger()
        thread = self._get_random_thread()
        message = self._get_random_normal_message()
        
        # Format timestamp
        ts = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Millisecond precision
        
        return f"{ts} [{thread}] {level} {logger} - {message}"
    
    def _generate_error_log(self, timestamp: datetime) -> str:
        """Generate an error log entry with one of the 4 specified exception types."""
        error_type = random.choice(list(ERROR_TYPES.keys()))
        error_config = ERROR_TYPES[error_type]
        
        logger = self._get_random_logger()
        thread = self._get_random_thread()
        
        # Get random message and stack trace for this error type
        message_template = random.choice(error_config['messages'])
        stack_trace = random.choice(error_config['stack_traces'])
        
        # Fill in message template with random values
        message = self._fill_message_template(message_template, error_type)
        filled_stack_trace = self._fill_message_template(stack_trace, error_type)
        
        # Format timestamp
        ts = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Create multi-line error log with stack trace
        error_entry = f"{ts} [{thread}] ERROR {logger} - {message}\n"
        error_entry += f"{ts} [{thread}] ERROR {logger} - {filled_stack_trace}"
        
        return error_entry
    
    def _weighted_choice(self, choices: Dict[str, int]) -> str:
        """Choose randomly from weighted options."""
        total = sum(choices.values())
        r = random.randint(1, total)
        
        for choice, weight in choices.items():
            r -= weight
            if r <= 0:
                return choice
        
        return list(choices.keys())[0]  # Fallback
    
    def _get_random_logger(self) -> str:
        """Get a random logger name."""
        package = random.choice(JAVA_PACKAGES)
        class_name = random.choice(CLASS_NAMES)
        return f"{package}.{class_name}"
    
    def _get_random_thread(self) -> str:
        """Get a random thread name."""
        thread_template = random.choice(THREAD_NAMES)
        
        if '{}' in thread_template:
            # Count the number of placeholders
            placeholder_count = thread_template.count('{}')
            
            if 'exec' in thread_template:
                return thread_template.format(random.randint(1, 20))
            elif 'pool' in thread_template and placeholder_count == 2:
                pool_id = random.randint(1, 5)
                thread_id = random.randint(1, 10)
                return thread_template.format(pool_id, thread_id)
            else:
                # Single placeholder templates
                return thread_template.format(random.randint(1, 10))
        
        return thread_template
    
    def _get_random_normal_message(self) -> str:
        """Get a random normal log message."""
        message_template = random.choice(NORMAL_MESSAGES)
        
        if '{}' in message_template:
            # Count placeholders to handle multi-argument templates
            placeholder_count = message_template.count('{}')
            
            # Fill template with appropriate values
            if 'user' in message_template.lower():
                return message_template.format(f"user_{random.randint(1000, 9999)}")
            elif 'key' in message_template.lower():
                return message_template.format(f"cache_key_{uuid.uuid4().hex[:8]}")
            elif 'ms' in message_template:
                return message_template.format(random.randint(10, 2000))
            elif 'task' in message_template.lower():
                return message_template.format(f"data_cleanup_task_{random.randint(1, 10)}")
            elif 'file' in message_template.lower():
                return message_template.format(f"/tmp/upload_{uuid.uuid4().hex[:8]}.dat")
            elif 'topic' in message_template.lower():
                return message_template.format(f"events.user.{random.choice(['login', 'logout', 'update'])}")
            elif 'service' in message_template.lower():
                return message_template.format(random.choice(['database', 'cache', 'auth', 'notification']))
            elif 'pool' in message_template.lower():
                active = random.randint(5, 50)
                idle = random.randint(2, 20)
                return message_template.format(active, idle)
            elif 'metric' in message_template.lower() and placeholder_count == 2:
                metric_name = random.choice(['requests.count', 'response.time', 'cpu.usage', 'memory.used'])
                value = random.randint(1, 1000)
                return message_template.format(metric_name, value)
            elif 'api call' in message_template.lower() and placeholder_count == 2:
                method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
                endpoint = random.choice(['/api/users', '/api/orders', '/api/products', '/api/auth'])
                return message_template.format(method, endpoint)
            else:
                # Handle single placeholder or fallback
                if placeholder_count == 1:
                    return message_template.format(f"value_{random.randint(1, 100)}")
                else:
                    # Multi-placeholder fallback - fill with generic values
                    values = [f"value_{random.randint(1, 100)}" for _ in range(placeholder_count)]
                    return message_template.format(*values)
        
        return message_template
    
    def _fill_message_template(self, template: str, error_type: str) -> str:
        """Fill error message template with appropriate values."""
        if '{}' in template:
            if error_type == 'CertificateExpiredException':
                if 'domain' in template:
                    domain = random.choice(['api.example.com', 'secure.app.com', 'auth.service.io'])
                    return template.format(domain)
                elif 'NotAfter' in template or 'expired on' in template or 'not valid after' in template:
                    exp_date = datetime.now() - timedelta(days=random.randint(1, 30))
                    return template.format(exp_date.strftime('%Y-%m-%d %H:%M:%S'))
                    
            elif error_type == 'HttpServerErrorException':
                if 'service' in template:
                    service = random.choice(['user-service', 'payment-api', 'notification-service'])
                    return template.format(service)
                elif 'ms' in template:
                    return template.format(random.randint(5000, 30000))
                    
            elif error_type == 'DiskSpaceExceededException':
                if 'MB available' in template:
                    available = random.randint(10, 100)
                    required = random.randint(200, 1000)
                    return template.format(available, required)
                elif 'partition' in template:
                    partition = random.choice(['/var/log', '/tmp', '/data'])
                    return template.format(partition)
                elif 'remaining' in template:
                    return template.format(random.randint(50, 200))
                elif 'write to' in template:
                    path = random.choice(['/var/log/app.log', '/tmp/upload.dat', '/data/cache.db'])
                    return template.format(path)
                    
            elif error_type == 'DeadLetterQueueException':
                if 'retry attempts' in template:
                    return template.format(random.randint(3, 10))
                elif 'messages, max capacity' in template:
                    current = random.randint(950, 999)
                    max_cap = 1000
                    return template.format(current, max_cap)
                elif 'unprocessed messages' in template:
                    return template.format(random.randint(100, 5000))
                elif 'processing failed' in template:
                    msg_id = uuid.uuid4().hex[:12]
                    return template.format(f"message_id_{msg_id}")
            
            # Fallback for any unhandled templates with placeholders
            if '{}' in template:
                placeholder_count = template.count('{}')
                
                # Generic fallback values based on error type
                if error_type == 'CertificateExpiredException':
                    exp_date = datetime.now() - timedelta(days=random.randint(1, 30))
                    values = [exp_date.strftime('%Y-%m-%d %H:%M:%S') for _ in range(placeholder_count)]
                elif error_type == 'HttpServerErrorException':
                    values = [random.choice(['user-service', 'payment-api']) for _ in range(placeholder_count)]
                elif error_type == 'DiskSpaceExceededException':
                    values = [str(random.randint(100, 1000)) for _ in range(placeholder_count)]
                elif error_type == 'DeadLetterQueueException':
                    values = [str(random.randint(1, 100)) for _ in range(placeholder_count)]
                else:
                    values = ['unknown' for _ in range(placeholder_count)]
                
                return template.format(*values)
        
        return template


def main():
    parser = argparse.ArgumentParser(description='Generate synthetic Log4j logs for Cuttlefish4 testing')
    parser.add_argument('--size', '-s', type=float, default=DEFAULT_MAX_SIZE_MB,
                      help=f'Maximum size in MB (default: {DEFAULT_MAX_SIZE_MB})')
    parser.add_argument('--error-rate', '-e', type=float, default=DEFAULT_ERROR_RATE,
                      help=f'Error rate as decimal (default: {DEFAULT_ERROR_RATE})')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_FILE,
                      help=f'Output filename (default: {DEFAULT_OUTPUT_FILE})')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.size <= 0:
        print("❌ Size must be positive")
        return 1
    
    if not 0 <= args.error_rate <= 1:
        print("❌ Error rate must be between 0 and 1")
        return 1
    
    # Generate logs
    generator = LogGenerator(max_size_mb=args.size, error_rate=args.error_rate)
    
    try:
        stats = generator.generate_logs(args.output)
        
        # Output stats as JSON for potential automation
        stats_file = args.output.replace('.log', '_stats.json')
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"📊 Statistics saved to: {stats_file}")
        return 0
        
    except Exception as e:
        print(f"❌ Error generating logs: {e}")
        return 1


if __name__ == "__main__":
    exit(main())