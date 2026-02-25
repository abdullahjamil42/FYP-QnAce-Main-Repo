# Render Deployment Guide for Q&ACE Backend

## Prerequisites
1. GitHub account with your code pushed to repository
2. Render account (free tier available)

## Deployment Steps

### 1. Connect to Render
1. Go to [render.com](https://render.com)
2. Sign up/Login with your GitHub account
3. Click "New +" → "Web Service"
4. Connect your GitHub repository

### 2. Configure Service
**Basic Settings:**
- **Name**: `qnace-backend`
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty (deploy from repository root)

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn integrated_system.api.main:app --host 0.0.0.0 --port $PORT`

**Note about Root Directory:**
- **Leave empty** to deploy from repository root (recommended)
- **Alternative**: Set to `integrated_system` if you want to deploy only the backend folder
  - If using this, update Start Command to: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### 3. Environment Variables
Add these in Render dashboard:
- `PYTHON_VERSION` = `3.11.0`

### 4. Plan Selection
**Free Tier Limitations:**
- ⚠️ **Spins down after 15 minutes** of inactivity
- ⚠️ **Cold starts** - first request after sleep takes 30+ seconds
- ⚠️ **512 MB RAM** - may cause issues with ML models
- ✅ **750 hours/month** runtime

**Paid Starter Plan ($7/month):**
- ✅ **Always on** - no cold starts
- ✅ **Better performance** for ML models

## Alternative Render.yaml Deployment

If you prefer infrastructure-as-code:

1. Push the `render.yaml` file to your repo
2. In Render dashboard: "New +" → "Blueprint"
3. Connect your repository
4. Render will auto-detect the YAML configuration

## Important Notes

### Model Loading Considerations
- **Large Models**: Your ML models may take time to load on first start
- **Memory Usage**: Monitor RAM usage in Render dashboard
- **Cold Starts**: Free tier will restart models on each wake-up

### Optimization Tips
1. **Model Caching**: Consider using Redis for model caching (paid add-on)
2. **Lighter Models**: Use smaller/quantized models for free tier
3. **Health Checks**: The `/health` endpoint helps with monitoring

### Testing Your Deployment
Once deployed, test these endpoints:
```
GET  https://your-app.onrender.com/health
POST https://your-app.onrender.com/analyze/facial
POST https://your-app.onrender.com/analyze/voice
POST https://your-app.onrender.com/analyze/multimodal
```

## Troubleshooting

### Build Issues
- Check build logs in Render dashboard
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

### Runtime Issues  
- Monitor memory usage
- Check application logs for model loading errors
- Verify environment variables are set

### Performance Issues
- Consider upgrading to paid plan for ML workloads
- Optimize model loading and caching
- Use `opencv-python-headless` for smaller Docker images

## Cost Estimation
- **Free Tier**: $0/month (with limitations)
- **Starter Plan**: $7/month (recommended for ML models)
- **Pro Plan**: $25/month (for production workloads)

## Next Steps
1. Deploy to Render using above instructions
2. Test all API endpoints
3. Update your frontend to use the new Render URL
4. Consider upgrading to paid plan for production use