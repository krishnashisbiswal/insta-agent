# Insta-Agent: Known Technical Limitations & Boundaries

## 1. Meta Instagram Graph API Boundaries

1. **Direct Video Binary Uploads**:
   - Meta Graph API supports direct binary uploads via the Resumable Upload protocol for Reels and Videos.
   - For Carousels and Single Image posts, Meta Graph API v21 requires image assets to be accessible via a public HTTPS URL (`image_url`). In production deployments, images rendered by `CarouselBuilder` should be uploaded to an S3/Cloudflare R2 bucket prior to publishing.
2. **Account Type Requirements**:
   - Meta Graph API publishing requires an Instagram Professional (Business or Creator) account linked to a verified Facebook Page. Personal accounts cannot publish via Graph API.
3. **Daily Publishing Quotas**:
   - Meta enforces a maximum of 25 API-published posts per Instagram account within any rolling 24-hour window. Insta-Agent enforces a safe default limit of 2-3 posts per day.

---

## 2. 3D and AI Video Hardware Requirements

1. **Headless Blender**:
   - Headless Blender rendering requires Blender installed locally on the host machine. On headless cloud servers (e.g. AWS EC2, GCP), an OpenGL software rasterizer (`mesa-utils`, `libgl1-mesa-glx`) or GPU instance is required.
   - When Blender is absent, Insta-Agent automatically and transparently utilizes procedural 3D numpy rendering or Ken Burns photorealistic compositing.
2. **Third-Party AI Video APIs**:
   - Runway and Luma integrations require active paid API credits. When keys are unconfigured, provider status is logged as `BLOCKED` and the system defaults to local high-resolution visual generation.
