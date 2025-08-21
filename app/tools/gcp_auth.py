# Copyright (c) 2025 Heemeng Foo
# SPDX-License-Identifier: BUSL-1.1
# See the LICENSE file for usage restrictions and the 2029-08-20 Apache-2.0 conversion.

"""
Google Cloud Platform authentication module for LogSearch agent.
Supports multiple authentication methods for cloud deployment.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from google.cloud import logging as cloud_logging
from google.oauth2 import service_account
from google.auth import default

logger = logging.getLogger(__name__)

class GCPAuthenticator:
    """Handle multiple GCP authentication methods for cloud deployment."""
    
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project_id required")
        
        self.client = None
        self.auth_method = None
        
    def get_authenticated_client(self) -> cloud_logging.Client:
        """Get authenticated GCP Logging client with fallback methods."""
        
        if self.client:
            return self.client
        
        # Method 1: Try Workload Identity (GKE/Cloud Run/Compute Engine)
        try:
            self.client = cloud_logging.Client(project=self.project_id)
            # Test authentication with a simple operation
            list(self.client.list_entries(max_results=1))
            self.auth_method = "workload_identity"
            logger.info("✅ Using Workload Identity authentication")
            return self.client
        except Exception as e:
            logger.debug(f"Workload Identity not available: {e}")
        
        # Method 2: Try Service Account Key from environment variable (JSON string)
        try:
            sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
            if sa_json:
                sa_info = json.loads(sa_json)
                credentials = service_account.Credentials.from_service_account_info(sa_info)
                self.client = cloud_logging.Client(project=self.project_id, credentials=credentials)
                self.auth_method = "service_account_json"
                logger.info("✅ Using Service Account JSON from environment")
                return self.client
        except Exception as e:
            logger.debug(f"Service Account JSON from environment failed: {e}")
        
        # Method 3: Try Service Account Key from file path
        try:
            sa_key_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if sa_key_path and os.path.exists(sa_key_path):
                credentials = service_account.Credentials.from_service_account_file(sa_key_path)
                self.client = cloud_logging.Client(project=self.project_id, credentials=credentials)
                self.auth_method = "service_account_file"
                logger.info(f"✅ Using Service Account Key from: {sa_key_path}")
                return self.client
        except Exception as e:
            logger.debug(f"Service Account Key file failed: {e}")
        
        # Method 4: Try Application Default Credentials
        try:
            credentials, project = default()
            self.client = cloud_logging.Client(project=self.project_id, credentials=credentials)
            self.auth_method = "application_default"
            logger.info("✅ Using Application Default Credentials")
            return self.client
        except Exception as e:
            logger.debug(f"Application Default Credentials failed: {e}")
        
        raise Exception(
            "No valid authentication method found. Please set up one of:\n"
            "1. Workload Identity (for GKE/Cloud Run)\n"
            "2. GOOGLE_SERVICE_ACCOUNT_JSON environment variable\n"
            "3. GOOGLE_APPLICATION_CREDENTIALS environment variable\n"
            "4. Application Default Credentials (gcloud auth application-default login)"
        )
    
    def test_authentication(self) -> Dict[str, Any]:
        """Test authentication and return status info."""
        try:
            client = self.get_authenticated_client()
            
            # Test with a simple query
            entries = list(client.list_entries(max_results=1))
            
            return {
                "status": "success",
                "auth_method": self.auth_method,
                "project_id": self.project_id,
                "client_initialized": True,
                "test_query_successful": True
            }
        except Exception as e:
            return {
                "status": "failure",
                "error": str(e),
                "auth_method": None,
                "project_id": self.project_id,
                "client_initialized": False,
                "test_query_successful": False
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the authenticated service."""
        try:
            client = self.get_authenticated_client()
            
            # Get project information
            project_info = {
                "project_id": self.project_id,
                "auth_method": self.auth_method,
                "service_available": True
            }
            
            # If using service account, get additional info
            if hasattr(client._credentials, 'service_account_email'):
                project_info["service_account_email"] = client._credentials.service_account_email
            
            return project_info
        except Exception as e:
            return {
                "project_id": self.project_id,
                "auth_method": None,
                "service_available": False,
                "error": str(e)
            }

# Singleton instance for reuse
_gcp_auth_instance = None

def get_gcp_client(project_id: Optional[str] = None) -> cloud_logging.Client:
    """Get authenticated GCP client (singleton pattern)."""
    global _gcp_auth_instance
    
    if _gcp_auth_instance is None:
        _gcp_auth_instance = GCPAuthenticator(project_id)
    
    return _gcp_auth_instance.get_authenticated_client()

def test_gcp_auth(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Test GCP authentication and return status."""
    try:
        auth = GCPAuthenticator(project_id)
        return auth.test_authentication()
    except Exception as e:
        return {
            "status": "failure",
            "error": str(e),
            "project_id": project_id
        }

# Environment detection helpers
def is_running_on_gcp() -> bool:
    """Detect if running on Google Cloud Platform."""
    try:
        import requests
        # Check GCP metadata server
        response = requests.get(
            'http://metadata.google.internal/computeMetadata/v1/project/project-id',
            headers={'Metadata-Flavor': 'Google'},
            timeout=1
        )
        return response.status_code == 200
    except:
        return False

def get_deployment_info() -> Dict[str, Any]:
    """Get information about the deployment environment."""
    info = {
        "is_gcp": is_running_on_gcp(),
        "has_sa_json_env": bool(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')),
        "has_sa_key_file": bool(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')),
        "project_id_env": os.environ.get('GOOGLE_CLOUD_PROJECT')
    }
    
    # Detect specific GCP services
    if info["is_gcp"]:
        info["gcp_service"] = "unknown"
        
        # Check for Cloud Run
        if os.environ.get('K_SERVICE'):
            info["gcp_service"] = "cloud_run"
        
        # Check for GKE
        elif os.environ.get('KUBERNETES_SERVICE_HOST'):
            info["gcp_service"] = "gke"
        
        # Check for Compute Engine
        elif os.path.exists('/sys/class/dmi/id/product_name'):
            try:
                with open('/sys/class/dmi/id/product_name', 'r') as f:
                    if 'Google' in f.read():
                        info["gcp_service"] = "compute_engine"
            except:
                pass
    
    return info