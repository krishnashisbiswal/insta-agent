# Insta-Agent: External Provider Integration Guide

## 1. Provider Landscape & Authentication

| Provider | Purpose | Status | Authentication | Failover Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Meta Instagram Graph API** | Official Reel, Carousel, Story & Image Publishing | Production Ready | OAuth 2.0 User Token (`INSTAGRAM_ACCESS_TOKEN`) | Safe Dry-Run Simulation |
| **Google Gemini API** | Scriptwriting, Creative Direction, JSON Generation | Production Ready | API Key (`GEMINI_API_KEY`) | Multi-model fallback (`3.5-flash-lite` -> `3.5-flash` -> `3-flash-preview`) |
| **Microsoft Edge TTS** | Natural Vocal Synthesis | Production Ready | Native WebSocket | Multi-voice failover (Madhur, Swara, Prabhat, Guy) |
| **Blender (Headless)** | Genuine 3D Asset & Scene Rendering | Ready (Local CLI) | System Executable (`BLENDER_PATH`) | Procedural 3D (`Engine3D`) + Ken Burns Engine |
| **Runway Gen-3** | External AI Video Generation | Interface Ready | API Key (`RUNWAY_API_KEY`) | Procedural & Dynamic Photographic Engine |
| **Luma Dream Machine** | External AI Video Generation | Interface Ready | API Key (`LUMA_API_KEY`) | Procedural & Dynamic Photographic Engine |

---

## 2. Meta Instagram Graph API Integration

### Requirements
- Instagram Professional / Business or Creator Account.
- Connected Facebook Page.
- Facebook Developer App with `instagram_basic`, `instagram_content_publish`, and `instagram_manage_insights` permissions.

### Container Lifecycle & Status Polling
Reel uploads use the official resumable binary chunk protocol:
1. `POST /{ig_user_id}/media?media_type=REELS&upload_type=resumable` -> Returns `container_id` and `upload_uri`.
2. Binary stream video bytes directly to `upload_uri` with header `offset=0` and `file_size`.
3. Poll `GET /{container_id}?fields=status_code` until `FINISHED` (exponential backoff 3s to 15s).
4. `POST /{ig_user_id}/media_publish?creation_id={container_id}` -> Returns published `media_id`.
5. Fetch permanent permalink and engagement metadata via `GET /{media_id}?fields=permalink,timestamp`.

---

## 3. Google Gemini Model Routing

Insta-Agent connects via the official `google-genai` SDK (`Client`).
The client automatically normalizes model identifiers and utilizes the ultra-fast, high-capacity models:
- **Primary**: `models/gemini-3.5-flash-lite`
- **Fallback Tier 1**: `models/gemini-3.5-flash`
- **Fallback Tier 2**: `models/gemini-3-flash-preview`

HTTP timeouts are explicitly configured to prevent hung socket connections.
