# Insta-Agent: Commercial Readiness & SaaS Operational Strategy

## 1. Multi-Tenant Architecture & Commercialization

Insta-Agent is architected to operate as a commercial B2B/B2C SaaS platform:
- **Tiered Subscriptions**: Managed via the `Organization.plan` attribute (`starter`, `pro`, `agency`, `enterprise`).
- **Account Provisioning**: Agency tier supports up to 50 isolated Instagram accounts under a single organization.
- **Cost Allocation & Metering**: Tracks Gemini AI token usage, image generation counts, and compute rendering duration per account.

---

## 2. API Contract & Integration Points

| Endpoint | Method | Role | Commercial Use Case |
| :--- | :--- | :--- | :--- |
| `/api/health` | GET | System Diagnostics | Uptime monitoring, health checks |
| `/api/accounts` | POST | Account Onboarding | Connect new Instagram handles, set niche & brand voice |
| `/api/accounts` | GET | Tenant Account Listing | Multi-account dashboard display |
| `/api/niches` | GET | Niche Catalog | Browse supported industry presets |
| `/api/content/generate` | POST | 1-Click Content Engine | Generate on-demand creative brief and queue job |
| `/api/jobs/{job_id}` | GET | Job Telemetry | Real-time generation progress and status inspection |
| `/api/analytics/{account_id}/summary` | GET | ROI & Performance Reporting | Client analytics reports with genuine engagement & save rates |

---

## 3. SLA & Operational Reliability

- **Graceful Degradation**: If an external provider experiences transient downtime, the system falls back without dropping jobs:
  - Gemini API -> Automatic fallback through model tiers (`3.5-flash-lite` -> `3.5-flash` -> `3-flash-preview`).
  - Blender 3D -> Automatic procedural 3D or Ken Burns visual engine.
  - Live Meta API -> Automatic idempotent retry with exponential backoff.
- **Zero Accidental Posting**: `AUTO_PUBLISH` defaults to `false`. No test, deployment, or dev run will ever post live content to customer accounts.
