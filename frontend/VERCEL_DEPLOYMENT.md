# Cuttlefish4 Frontend Vercel Deployment

## Quick Deploy

1. **Import to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import from GitHub: `foohm71/cuttlefish4`
   - Set root directory to: `frontend`

2. **Environment Variables** (Set in Vercel dashboard):
   ```
   NEXT_PUBLIC_API_URL=https://cuttlefish4.onrender.com
   GOOGLE_CLIENT_ID=your-google-oauth-client-id
   ```

3. **Build Settings** (Should auto-detect from vercel.json):
   - Build Command: `npm run build`
   - Output Directory: `.next`
   - Install Command: `npm install`

## Configuration

- **Backend API**: https://cuttlefish4.onrender.com
- **Framework**: Next.js 14.2.5
- **Region**: PDX1 (Oregon)

## Post-Deployment

After deployment:
1. Test authentication flow
2. Test multi-agent RAG queries
3. Verify LogSearch functionality
4. Update any CORS settings in backend if needed