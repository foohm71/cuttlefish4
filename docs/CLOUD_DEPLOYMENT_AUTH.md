# Cloud Deployment Authentication Guide

## Service Account Setup for LogSearch Agent

### 1. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create logsearch-agent \
    --description="Service account for LogSearch agent" \
    --display-name="LogSearch Agent"

# Get service account email
SA_EMAIL=$(gcloud iam service-accounts list \
    --filter="displayName:LogSearch Agent" \
    --format="value(email)")

echo "Service Account: $SA_EMAIL"
```

### 2. Grant Required Permissions

```bash
# Grant Cloud Logging permissions
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/logging.viewer"

# For more restrictive access, use custom role (optional)
gcloud iam roles create logSearchAgent \
    --project=$GOOGLE_CLOUD_PROJECT \
    --title="LogSearch Agent Role" \
    --description="Custom role for LogSearch agent" \
    --permissions="logging.entries.list,logging.entries.create,logging.logEntries.list"
```

### 3. Create Service Account Key (For Non-GCP Deployments)

```bash
# Create and download key file
gcloud iam service-accounts keys create logsearch-sa-key.json \
    --iam-account=$SA_EMAIL

# This creates logsearch-sa-key.json file
```

## Deployment Scenarios

### Scenario A: Google Cloud Platform (GKE, Cloud Run, Compute Engine)

**Authentication Method:** Workload Identity or Default Service Account

```yaml
# Kubernetes deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logsearch-agent
spec:
  template:
    spec:
      serviceAccountName: logsearch-agent-ksa  # Kubernetes SA linked to Google SA
      containers:
      - name: logsearch-agent
        image: gcr.io/octopus-282815/logsearch-agent:latest
        env:
        - name: GOOGLE_CLOUD_PROJECT
          value: "octopus-282815"
        - name: USE_GCP_LOGGING
          value: "true"
        # No GOOGLE_APPLICATION_CREDENTIALS needed - uses Workload Identity
```

**Advantages:**
- ✅ No credential files to manage
- ✅ Automatic credential rotation
- ✅ Most secure approach
- ✅ Native GCP integration

### Scenario B: AWS/Azure/Other Cloud Providers

**Authentication Method:** Service Account Key File

```yaml
# Docker Compose example
version: '3.8'
services:
  logsearch-agent:
    image: logsearch-agent:latest
    environment:
      - GOOGLE_CLOUD_PROJECT=octopus-282815
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/sa-key.json
      - USE_GCP_LOGGING=true
    volumes:
      - ./credentials/logsearch-sa-key.json:/app/credentials/sa-key.json:ro
    secrets:
      - gcp-service-account-key
```

### Scenario C: On-Premise/Hybrid

**Authentication Method:** Service Account Key with Secret Management

```python
# Enhanced authentication in code
import os
import json
from google.cloud import logging
from google.oauth2 import service_account

def get_gcp_client():
    """Get authenticated GCP Logging client with multiple auth methods."""
    
    # Method 1: Try Workload Identity (GKE/Cloud Run)
    try:
        client = logging.Client()
        # Test authentication
        client.list_entries(max_results=1)
        print("✅ Using Workload Identity authentication")
        return client
    except Exception as e:
        print(f"⚠️  Workload Identity not available: {e}")
    
    # Method 2: Try Application Default Credentials
    try:
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            client = logging.Client()
            print("✅ Using Application Default Credentials")
            return client
    except Exception as e:
        print(f"⚠️  Application Default Credentials failed: {e}")
    
    # Method 3: Try environment variable with JSON
    try:
        sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if sa_json:
            sa_info = json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(sa_info)
            client = logging.Client(credentials=credentials)
            print("✅ Using Service Account JSON from environment")
            return client
    except Exception as e:
        print(f"⚠️  Service Account JSON failed: {e}")
    
    raise Exception("No valid authentication method found")
```

## Security Best Practices

### 1. **Principle of Least Privilege**

```bash
# Create minimal custom role instead of predefined roles
gcloud iam roles create logSearchMinimal \
    --project=$GOOGLE_CLOUD_PROJECT \
    --title="LogSearch Minimal Access" \
    --permissions="logging.entries.list,logging.logEntries.list"
```

### 2. **Credential Management**

```bash
# Use secret management systems
kubectl create secret generic gcp-sa-key \
    --from-file=key.json=logsearch-sa-key.json

# Or with Helm
helm install logsearch ./charts/logsearch \
    --set-file gcpServiceAccountKey=logsearch-sa-key.json
```

### 3. **Environment-Specific Configuration**

```yaml
# Environment-specific values
development:
  authentication: "application-default"
  project_id: "octopus-dev-282815"
  
staging:
  authentication: "workload-identity" 
  project_id: "octopus-staging-282815"
  
production:
  authentication: "workload-identity"
  project_id: "octopus-prod-282815"
  monitoring_enabled: true
```

## Updated LogSearch Agent Code

The agent will need minimal changes to support different auth methods:

```python
class CloudLogSearchAgent:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = self._get_authenticated_client()
    
    def _get_authenticated_client(self):
        """Initialize GCP client with cloud-appropriate authentication."""
        project_id = self.config.get('gcp_project_id')
        
        # Try multiple auth methods as shown above
        return get_gcp_client()
    
    def search_logs(self, query: str) -> List[Dict[str, Any]]:
        """Search logs using authenticated client."""
        # Implementation remains the same
        pass
```

## Monitoring and Troubleshooting

### 1. **Health Checks**

```python
def health_check():
    """Health check endpoint for cloud deployment."""
    try:
        client = get_gcp_client()
        # Simple test query
        list(client.list_entries(max_results=1))
        return {"status": "healthy", "gcp_auth": "ok"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 2. **Logging Authentication Events**

```python
import logging

# Log authentication method used
auth_logger = logging.getLogger('auth')
auth_logger.info(f"GCP Authentication successful: {auth_method}")
```

## Cost Considerations

- **API Calls:** Free tier includes substantial quotas
- **Log Storage:** 50GB free per month
- **Egress:** Minimal for log search operations
- **Service Account:** Free

## Deployment Checklist

- [ ] Service account created with minimal permissions
- [ ] Authentication method chosen based on deployment environment  
- [ ] Credentials securely stored (no plaintext in code/configs)
- [ ] Health checks implemented
- [ ] Monitoring and alerting configured
- [ ] Environment-specific configurations
- [ ] Backup authentication method (if needed)
- [ ] Security review completed

The LogSearch agent will work seamlessly in cloud environments with proper service account setup!