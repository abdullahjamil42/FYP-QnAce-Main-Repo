# Vercel Frontend + Render Backend Connection Guide

## Step 1: Get Your Render Backend URL

1. Go to your Render dashboard
2. Find your `qnace-backend` service
3. Copy the **Service URL** (should look like: `https://qnace-backend-xxxx.onrender.com`)

## Step 2: Deploy Frontend to Vercel

### Option A: Quick Deploy via Vercel Dashboard
1. Go to [vercel.com](https://vercel.com)
2. Sign up/Login with GitHub
3. Click "Add New..." → "Project"
4. Import your GitHub repository
5. **Configure project:**
   - **Framework Preset**: Next.js
   - **Root Directory**: `Frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`

### Option B: Deploy via Vercel CLI
```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to your project
cd c:\Users\admin\Documents\GitHub\FYP-QnAce-Main-Repo

# Deploy
vercel

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? Select your account
# - Link to existing project? No
# - Project name: qnace-frontend
# - In which directory is your code located? ./Frontend
```

## Step 3: Configure Environment Variables

In your Vercel project settings, add:

**Environment Variable:**
- **Name**: `NEXT_PUBLIC_API_URL`
- **Value**: `https://your-render-backend-url.onrender.com`
- **Environment**: Production, Preview, Development

**Example:**
```
NEXT_PUBLIC_API_URL=https://qnace-backend-xxxx.onrender.com
```

## Step 4: Redeploy Backend (Updated CORS)

Since we updated the CORS settings, redeploy your Render backend:
1. Go to Render dashboard
2. Click your `qnace-backend` service
3. Click "Manual Deploy" → "Deploy latest commit"

## Step 5: Test the Connection

Once both are deployed:

### Test Backend Endpoints
```bash
# Health check
curl https://your-render-backend.onrender.com/health

# Test CORS
curl -H "Origin: https://your-vercel-app.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://your-render-backend.onrender.com/analyze/facial
```

### Test Frontend
1. Visit your Vercel app URL
2. Open browser DevTools → Network tab
3. Try using the interview features
4. Check that API calls go to your Render backend

## Troubleshooting

### CORS Issues
If you see CORS errors:
1. Check that `NEXT_PUBLIC_API_URL` is set correctly
2. Verify backend CORS includes your Vercel domain
3. Ensure both HTTP and HTTPS protocols are allowed

### API Connection Issues
1. **Check URLs**: Ensure no trailing slashes
2. **Environment Variables**: Verify `NEXT_PUBLIC_API_URL` in Vercel
3. **Backend Status**: Check Render logs for errors
4. **Cold Start**: First request might be slow (free tier)

### Build Issues
1. **Dependencies**: Ensure all packages are in `package.json`
2. **TypeScript**: Check for type errors
3. **Build Command**: Verify build succeeds locally

## URLs Summary

After deployment, you'll have:
- **Frontend**: `https://your-app.vercel.app`
- **Backend API**: `https://your-backend.onrender.com`
- **API Health**: `https://your-backend.onrender.com/health`

## Performance Notes

### Free Tier Limitations
- **Render Free**: Backend spins down after 15min (cold starts)
- **Vercel Free**: 100GB bandwidth/month, generous limits

### Production Recommendations
- **Render Starter**: $7/month for always-on backend
- **Vercel Pro**: $20/month for team features (usually not needed)

## Next Steps

1. Deploy frontend to Vercel
2. Set environment variable
3. Test the full application
4. Monitor performance and consider upgrading plans if needed

Your interview analysis app will be live! 🚀