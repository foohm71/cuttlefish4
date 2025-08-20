# 🚀 Render.com Deployment Guide for Cuttlefish

## Quick Deployment Steps

### 1. **Connect Repository to Render**
1. Go to [render.com](https://render.com) and sign in
2. Click "New" → "Web Service"
3. Connect your GitHub repository: `cuttlefish4`
4. Select deployment branch (usually `main`)

### 2. **Configure Service Settings**
- **Name**: `cuttlefish-backend` (or your choice)
- **Region**: Choose closest to your users
- **Branch**: `main` (or your deployment branch)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m app.api.main`

### 3. **Set Environment Variables** 
In Render Dashboard → Environment, add these:

#### Required API Keys:
```
OPENAI_API_KEY=sk-your-openai-api-key
TAVILY_API_KEY=tvly-your-tavily-key
```

#### GCP LogSearch Configuration:
```
GOOGLE_CLOUD_PROJECT=octopus-282815
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"octopus-282815",...}
```

#### Authentication (Optional):
```
BYPASS_AUTH=true              # Set to 'false' for production auth
SECRET_KEY=auto-generated     # Render auto-generates
JWT_SECRET_KEY=auto-generated # Render auto-generates
```

#### Database (If using external):
```
DATABASE_URL=postgresql://user:pass@host:5432/db
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### 4. **Deploy**
1. Click "Create Web Service" 
2. Render will automatically build and deploy
3. Monitor logs for any issues

## 🔧 Configuration Files Created

- ✅ **render.yaml** - Render service configuration
- ✅ **requirements.txt** - Updated with GCP logging dependency
- ✅ **start.sh** - Production startup script (backup)
- ✅ **Procfile** - Process definition
- ✅ **runtime.txt** - Python version specification

## 🌐 Access Your Deployed API

After successful deployment:
- **API URL**: `https://your-service-name.onrender.com`
- **Health Check**: `https://your-service-name.onrender.com/health`
- **Interactive UI**: `https://your-service-name.onrender.com/`
- **API Docs**: `https://your-service-name.onrender.com/docs`

## 🔐 Security Notes for Production

1. **Set BYPASS_AUTH=false** for production
2. **Restrict CORS_ORIGINS** to your frontend domains
3. **Use secrets** for all API keys (don't put in code)
4. **Set up database** (Render PostgreSQL or external)

## 📋 LogSearch Requirements

For LogSearch to work on Render:

1. **GCP Service Account JSON** must be set as environment variable
2. **GOOGLE_CLOUD_PROJECT** must be set
3. Service account needs these permissions:
   - Cloud Logging Viewer
   - Private Logs Viewer

## 🐛 Troubleshooting

**Build Issues:**
- Check build logs in Render dashboard
- Verify requirements.txt syntax
- Ensure Python version compatibility

**Runtime Issues:**
- Check application logs
- Verify environment variables are set
- Test API endpoints individually

**LogSearch Not Working:**
- Verify GCP credentials in env vars
- Check GCP project permissions
- Test with simple log queries

## 💰 Render Pricing

- **Starter Plan**: $7/month (512MB RAM, 0.5 CPU)
- **Standard Plan**: $25/month (2GB RAM, 1 CPU) - Recommended for production

## 🚀 Ready to Deploy!

Your Cuttlefish backend is now configured for Render.com deployment with full LogSearch, WebSearch, and multi-agent RAG capabilities!