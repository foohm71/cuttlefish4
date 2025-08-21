# Google Cloud Logging Setup for LogSearch System

## Prerequisites

1. **Google Cloud Project**: Create or use existing GCP project
2. **Authentication**: Set up service account or use gcloud auth
3. **API Enablement**: Enable Cloud Logging API
4. **Python Dependencies**: Install google-cloud-logging

## Quick Setup

### 1. Enable Cloud Logging API
```bash
gcloud services enable logging.googleapis.com
```

### 2. Set up Authentication
```bash
# Option A: Use gcloud auth (development)
gcloud auth application-default login

# Option B: Service account (production)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 3. Install Python Dependencies
```bash
pip install google-cloud-logging
```

### 4. Set Environment Variables
```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

## Testing the Setup

Run the example script:
```bash
source venv/bin/activate
python scripts/gcp_logging_example.py
```

## Integration with LogSearch Agent

### Environment Variables
```bash
# Add to .env file
GCP_PROJECT_ID=your-project-id
GCP_LOG_NAME=cuttlefish_synthetic_logs
USE_GCP_LOGGING=true
```

### Filter Query Examples

**Basic log search:**
```
logName="projects/your-project/logs/cuttlefish_synthetic_logs"
```

**Error level logs:**
```
logName="projects/your-project/logs/cuttlefish_synthetic_logs" AND severity="ERROR"
```

**Search by message content:**
```
logName="projects/your-project/logs/cuttlefish_synthetic_logs" AND jsonPayload.message:"CertificateExpired"
```

**Time-based search:**
```
logName="projects/your-project/logs/cuttlefish_synthetic_logs" AND timestamp>"2025-08-19T10:00:00Z"
```

## Cost Considerations

### Free Tier (per month)
- **50 GB** of logs ingested
- **30 days** retention for free
- **No charge** for API calls

### Paid Tier
- **$0.50/GB** for ingestion above free tier
- **$0.01/GB/month** for extended retention
- Very cost-effective compared to Splunk Cloud

## Advantages over Splunk Cloud

| Feature | Splunk Cloud | GCP Logging |
|---------|-------------|-------------|
| API Access | Support ticket required | Immediate |
| Free Tier | No | 50GB/month |
| Setup Time | Days | Minutes |
| Python SDK | Limited | Comprehensive |
| Real-time | Limited | Native streaming |
| Authentication | Complex | Standard OAuth2 |

## Migration Strategy

1. **Parallel Setup**: Run both systems simultaneously
2. **Gradual Migration**: Start with new logs in GCP
3. **Validation**: Compare search results between systems
4. **Full Migration**: Switch LogSearch agent to GCP backend

## Production Considerations

1. **Service Account**: Use dedicated service account with minimal permissions
2. **Log Retention**: Configure appropriate retention policies
3. **Log Routing**: Set up log sinks for long-term storage
4. **Monitoring**: Set up alerting for API quotas and errors
5. **Security**: Enable audit logging and access controls