# Insta-Agent: Database Architecture & Design Specification

## 1. Overview

The storage architecture of Insta-Agent is designed for high-concurrency multi-tenant SaaS workloads. Built with SQLAlchemy 2.0 ORM, it natively supports both local SQLite (for embedded development and testing) and production PostgreSQL with connection pooling.

---

## 2. Entity-Relationship Model

```mermaid
erDiagram
    ORGANIZATION ||--o{ USER : contains
    ORGANIZATION ||--o{ INSTAGRAM_ACCOUNT : owns
    ORGANIZATION ||--o{ NICHE_PROFILE : customizes
    INSTAGRAM_ACCOUNT ||--o{ PUBLISHING_JOB : executes
    INSTAGRAM_ACCOUNT ||--o{ POST_METRICS : records

    ORGANIZATION {
        string org_id PK
        string name
        string plan
        float monthly_budget_usd
        float created_at
    }

    USER {
        string user_id PK
        string org_id FK
        string email
        string role
        string hashed_password
        boolean is_active
        float created_at
    }

    INSTAGRAM_ACCOUNT {
        string account_id PK
        string org_id FK
        string username
        string instagram_user_id
        text encrypted_access_token
        string niche_id
        string brand_handle
        text target_audience
        string language
        boolean auto_publish
        integer daily_post_limit
        string preferred_format
        boolean is_active
        float created_at
    }

    NICHE_PROFILE {
        string niche_id PK
        string org_id FK
        string name
        text target_audience
        string language
        string tone
        text content_pillars_json
        text visual_style
        string audio_style
        text cta_presets_json
        text glossary_json
        float created_at
    }

    PUBLISHING_JOB {
        string job_id PK
        string account_id FK
        string idempotency_key UK
        string niche_id
        string content_format
        string state
        string topic
        text script_json
        text rendered_assets_json
        string meta_container_id
        string meta_media_id
        string meta_permalink
        text error_message
        float created_at
        float updated_at
    }

    POST_METRICS {
        string media_id PK
        string account_id FK
        string topic
        string niche_id
        string format
        integer reach
        integer impressions
        integer likes
        integer comments
        integer saves
        integer shares
        float engagement_rate
        float save_rate
        float published_at
    }
```

---

## 3. Security & Indexing Strategy

1. **Idempotency Index**:
   - `publishing_jobs.idempotency_key` carries a unique constraint. Any concurrent attempt to insert an identical content hash fails with `DuplicateJobError`.
2. **Account & State Query Composite Index**:
   - `Index("idx_account_state", "account_id", "state")` accelerates frequent queue and status inspection queries.
3. **Encrypted Token Protection**:
   - `encrypted_access_token` is handled through transparent ORM accessors (`set_access_token` and `get_access_token`) ensuring raw OAuth keys are never exposed in SQL queries or logs.
