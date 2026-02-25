# GitHub Deployment Guide for Q&ACE

## Step-by-Step Deployment

### 1. Railway (Backend API)
1. Visit [Railway.app](https://railway.app)
2. Sign in with your GitHub account
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `FYP-Main-repo-QnAce` repository
5. Railway will auto-detect and build using `Dockerfile.railway`
6. Add these environment variables in Railway dashboard:
   ```
   PYTHONPATH=/app/integrated_system:/app/interview_emotion_detection/src
   PORT=8001
   ```
7. Your backend will be available at `https://your-app.railway.app`

### 2. Vercel (Frontend)
1. Visit [Vercel.com](https://vercel.com)
2. Sign in with your GitHub account
3. Click "New Project" → Import your repository
4. Set Framework Preset: "Next.js"
5. Set Root Directory: `Frontend`
6. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-backend-url
   ```
7. Deploy! Your frontend will be available at `https://your-project.vercel.app`

### 3. Alternative: Render (Both Frontend & Backend)
1. Visit [Render.com](https://render.com)
2. Connect GitHub account
3. Create two services:
   - **Web Service** for backend (use `Dockerfile.railway`)
   - **Static Site** for frontend (build: `cd Frontend && npm run build`)

### 4. Alternative: Netlify (Frontend) + Railway (Backend)
1. **Netlify for Frontend:**
   - Connect GitHub to [Netlify.com](https://netlify.com)
   - Set build command: `cd Frontend && npm run build`
   - Set publish directory: `Frontend/.next`

2. **Railway for Backend:** (Same as above)

## GitHub Actions (Auto-Deploy)
The workflows are already set up. You need to add these secrets to your GitHub repo:

### Repository Secrets (Settings → Secrets and variables → Actions):
1. **For Railway:**
   - `RAILWAY_TOKEN` - Get from Railway dashboard → Account Settings → Tokens

2. **For Vercel:**
   - `VERCEL_TOKEN` - Get from Vercel dashboard → Settings → Tokens
   - `VERCEL_ORG_ID` - Found in Vercel project settings
   - `VERCEL_PROJECT_ID` - Found in Vercel project settings

After adding secrets, every push to main branch will auto-deploy!

## Free Tier Limits
- **Railway:** $5/month free credit, sleep after inactivity
- **Vercel:** 100GB bandwidth/month, unlimited builds
- **Render:** 750 hours/month free, sleeps after inactivity
- **Netlify:** 100GB bandwidth/month, 300 build minutes

## Custom Domain Setup
1. **Railway:** Go to project → Settings → Domains → Add custom domain
2. **Vercel:** Go to project → Settings → Domains → Add domain
3. **Render/Netlify:** Similar domain settings in dashboard

## Environment Variables
Ensure these are set in your deployment platform:

### Backend (Railway/Render):
```
PYTHONPATH=/app/integrated_system:/app/interview_emotion_detection/src
PORT=8001
FRONTEND_URL=https://your-frontend-domain.com
```

### Frontend (Vercel/Netlify):
```
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
NEXT_PUBLIC_APP_NAME=Q&ACE Interview Analyzer
```