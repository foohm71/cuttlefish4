#!/usr/bin/env python3
"""
Test script for cloud authentication setup.
Validates service account authentication and cloud deployment readiness.
"""

import os
import sys
import json
from pathlib import Path

# Add the app directory to the path so we can import our tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.tools.gcp_auth import test_gcp_auth, get_deployment_info, get_gcp_client
except ImportError as e:
    print(f"❌ Error: Required packages not installed: {e}")
    sys.exit(1)

def test_service_account_key():
    """Test service account key file authentication."""
    print("\n🔑 Testing Service Account Key Authentication")
    print("=" * 60)
    
    key_file = Path(__file__).parent / "logsearch-sa-key.json"
    
    if not key_file.exists():
        print(f"❌ Service account key file not found: {key_file}")
        return False
    
    print(f"✅ Service account key file found: {key_file}")
    
    # Set environment variable
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_file)
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'octopus-282815'
    
    # Test authentication
    auth_result = test_gcp_auth()
    
    if auth_result['status'] == 'success':
        print(f"✅ Authentication successful")
        print(f"   Method: {auth_result['auth_method']}")
        print(f"   Project: {auth_result['project_id']}")
        print(f"   Test query: {'✅' if auth_result['test_query_successful'] else '❌'}")
        return True
    else:
        print(f"❌ Authentication failed: {auth_result['error']}")
        return False

def test_json_env_auth():
    """Test service account JSON from environment variable."""
    print("\n🌍 Testing Environment Variable JSON Authentication")
    print("=" * 60)
    
    key_file = Path(__file__).parent / "logsearch-sa-key.json"
    
    if not key_file.exists():
        print(f"❌ Service account key file not found: {key_file}")
        return False
    
    # Read key file and set as environment variable
    try:
        with open(key_file, 'r') as f:
            key_content = f.read()
        
        # Clear file-based auth
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        # Set JSON-based auth
        os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'] = key_content
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'octopus-282815'
        
        # Test authentication
        auth_result = test_gcp_auth()
        
        if auth_result['status'] == 'success':
            print(f"✅ JSON environment authentication successful")
            print(f"   Method: {auth_result['auth_method']}")
            print(f"   Project: {auth_result['project_id']}")
            return True
        else:
            print(f"❌ JSON environment authentication failed: {auth_result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test JSON environment auth: {e}")
        return False

def test_log_operations():
    """Test actual log ingestion and search operations."""
    print("\n📝 Testing Log Operations")
    print("=" * 60)
    
    try:
        from datetime import datetime
        
        # Get authenticated client
        client = get_gcp_client('octopus-282815')
        logger = client.logger('cuttlefish_test_cloud_auth')
        
        # Test log ingestion
        print("📤 Testing log ingestion...")
        test_log = {
            'test_id': 'cloud_auth_test',
            'timestamp': datetime.now().isoformat(),
            'message': 'Service account authentication test log',
            'level': 'INFO',
            'source': 'cloud_auth_test'
        }
        
        logger.log_struct(test_log, severity='INFO')
        print("✅ Log ingestion successful")
        
        # Wait a moment for indexing
        import time
        time.sleep(3)
        
        # Test log search
        print("🔍 Testing log search...")
        filter_query = f'logName="projects/octopus-282815/logs/cuttlefish_test_cloud_auth" AND jsonPayload.test_id="cloud_auth_test"'
        
        entries = client.list_entries(filter_=filter_query, max_results=5)
        results = list(entries)
        
        print(f"✅ Log search successful: found {len(results)} entries")
        
        if results:
            latest = results[0]
            if hasattr(latest, 'payload') and hasattr(latest.payload, 'json_payload'):
                payload = dict(latest.payload.json_payload)
                print(f"   Latest entry: {payload.get('message', 'No message')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Log operations failed: {e}")
        return False

def test_deployment_detection():
    """Test deployment environment detection."""
    print("\n🌐 Testing Deployment Environment Detection")
    print("=" * 60)
    
    deployment_info = get_deployment_info()
    
    print(f"Running on GCP: {deployment_info['is_gcp']}")
    print(f"GCP Service: {deployment_info.get('gcp_service', 'N/A')}")
    print(f"Has SA JSON env: {deployment_info['has_sa_json_env']}")
    print(f"Has SA key file: {deployment_info['has_sa_key_file']}")
    print(f"Project ID env: {deployment_info['project_id_env']}")
    
    return True

def generate_deployment_configs():
    """Generate example deployment configurations."""
    print("\n📋 Generating Deployment Configurations")
    print("=" * 60)
    
    configs_dir = Path(__file__).parent.parent / "deployment_configs"
    configs_dir.mkdir(exist_ok=True)
    
    # Docker Compose configuration
    docker_compose = """version: '3.8'
services:
  logsearch-agent:
    image: logsearch-agent:latest
    environment:
      - GOOGLE_CLOUD_PROJECT=octopus-282815
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/sa-key.json
      - USE_GCP_LOGGING=true
      - LOG_LEVEL=INFO
    volumes:
      - ./logsearch-sa-key.json:/app/credentials/sa-key.json:ro
    ports:
      - "8080:8080"
    restart: unless-stopped
"""
    
    # Kubernetes deployment
    k8s_deployment = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: logsearch-agent
  labels:
    app: logsearch-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: logsearch-agent
  template:
    metadata:
      labels:
        app: logsearch-agent
    spec:
      containers:
      - name: logsearch-agent
        image: gcr.io/octopus-282815/logsearch-agent:latest
        env:
        - name: GOOGLE_CLOUD_PROJECT
          value: "octopus-282815"
        - name: USE_GCP_LOGGING
          value: "true"
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: "/app/credentials/sa-key.json"
        volumeMounts:
        - name: gcp-sa-key
          mountPath: /app/credentials
          readOnly: true
        ports:
        - containerPort: 8080
      volumes:
      - name: gcp-sa-key
        secret:
          secretName: gcp-service-account-key
---
apiVersion: v1
kind: Secret
metadata:
  name: gcp-service-account-key
type: Opaque
data:
  sa-key.json: # Base64 encoded service account key
"""
    
    # Environment variables template
    env_template = """# Google Cloud Platform Configuration
GOOGLE_CLOUD_PROJECT=octopus-282815
GOOGLE_APPLICATION_CREDENTIALS=/path/to/logsearch-sa-key.json
USE_GCP_LOGGING=true

# Alternative: JSON as environment variable
# GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'

# Optional: Log configuration
GCP_LOG_NAME=cuttlefish_synthetic_logs
LOG_LEVEL=INFO
"""
    
    # Write configuration files
    (configs_dir / "docker-compose.yml").write_text(docker_compose)
    (configs_dir / "kubernetes-deployment.yaml").write_text(k8s_deployment)
    (configs_dir / "environment.env").write_text(env_template)
    
    print(f"✅ Configuration files generated in: {configs_dir}")
    print("   - docker-compose.yml")
    print("   - kubernetes-deployment.yaml") 
    print("   - environment.env")

def main():
    """Run all authentication tests."""
    print("🚀 Cloud Authentication Test Suite")
    print("=" * 60)
    
    # Test environment detection first
    test_deployment_detection()
    
    # Test service account key authentication
    sa_key_success = test_service_account_key()
    
    # Test JSON environment authentication
    json_env_success = test_json_env_auth()
    
    # Test actual log operations if auth works
    log_ops_success = False
    if sa_key_success or json_env_success:
        log_ops_success = test_log_operations()
    
    # Generate deployment configurations
    generate_deployment_configs()
    
    # Final summary
    print(f"\n{'='*60}")
    print("🏁 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Service Account Key Auth: {'✅' if sa_key_success else '❌'}")
    print(f"JSON Environment Auth: {'✅' if json_env_success else '❌'}")
    print(f"Log Operations: {'✅' if log_ops_success else '❌'}")
    
    if sa_key_success or json_env_success:
        print(f"\n🎉 Cloud authentication is working!")
        print(f"💡 Ready for cloud deployment")
        print(f"📋 Check deployment_configs/ for example configurations")
        return 0
    else:
        print(f"\n❌ Cloud authentication failed")
        print(f"🔧 Check service account setup and key file")
        return 1

if __name__ == "__main__":
    exit(main())