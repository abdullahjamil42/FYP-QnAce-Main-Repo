# Q&ACE Deployment Guide

## GitHub-Based Cloud Deployment (Recommended)

### Quick Deployment Steps:

1. **Backend on Railway:**
   - Go to [Railway.app](https://railway.app)
   - Connect your GitHub account
   - Deploy from your GitHub repo
   - Set environment variables in Railway dashboard

2. **Frontend on Vercel:**
   - Go to [Vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Set root directory to `Frontend`
   - Configure environment variables

### Automatic Deployment (GitHub Actions):
The repository includes GitHub Actions that auto-deploy when you push code:
- `.github/workflows/deploy-backend.yml` - Deploys to Railway
- `.github/workflows/deploy-frontend.yml` - Deploys to Vercel

## Manual Cloud Deployment Options

### Option 1: AWS ECS/Fargate
1. Push Docker images to ECR
2. Create ECS task definitions
3. Deploy using ECS service
4. Configure ALB for load balancing

### Option 2: Google Cloud Run
1. Build and push to GCR
2. Deploy backend to Cloud Run
3. Deploy frontend to Cloud Run or Firebase Hosting
4. Configure custom domain

### Option 3: Azure Container Instances
1. Push images to ACR
2. Create container groups
3. Configure networking and domains
4. Set up monitoring

### Option 4: Heroku (Simple)
1. Create two Heroku apps (frontend/backend)
2. Configure buildpacks
3. Set environment variables
4. Deploy using Git

### Option 5: Vercel + Railway
1. Deploy frontend to Vercel
2. Deploy backend to Railway
3. Configure environment variables
4. Connect custom domain

## Environment Variables

### Backend (.env)
```
PYTHONPATH=/app/integrated_system:/app/interview_emotion_detection/src
HF_HOME=/app/.huggingface
API_HOST=0.0.0.0
API_PORT=8001
FRONTEND_URL=https://your-frontend-domain.com
```

### Frontend (.env)
```
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
NEXT_PUBLIC_APP_NAME=Q&ACE Interview Analyzer
```

## Performance Optimization

1. **Model Caching:**
   - Pre-download HuggingFace models
   - Use persistent volumes for model cache

2. **Resource Limits:**
   - Backend: 2-4 CPU cores, 4-8GB RAM
   - Frontend: 1 CPU core, 1GB RAM

3. **CDN Setup:**
   - Use CloudFlare or AWS CloudFront
   - Cache static assets

## Monitoring & Logging

1. **Health Checks:**
   - Backend: `GET /health`
   - Frontend: `GET /`

2. **Logging:**
   - Centralized logging with ELK stack
   - Application performance monitoring

3. **Alerts:**
   - CPU/Memory usage alerts
   - Error rate monitoring
   - Response time tracking

## Security

1. **HTTPS/SSL:**
   - Use Let's Encrypt certificates
   - Redirect HTTP to HTTPS

2. **CORS Configuration:**
   - Restrict origins in production
   - Configure proper headers

3. **Rate Limiting:**
   - Implement API rate limiting
   - DDoS protection

## Scaling

1. **Horizontal Scaling:**
   - Multiple backend instances
   - Load balancer configuration

2. **Database:**
   - Use managed database service
   - Connection pooling

3. **File Storage:**
   - Use object storage (S3, GCS)
   - CDN for static files