# AttackSurface Timeline — Production Deployment Limits & Tier Analysis

This document provides a realistic, documentation-verified breakdown of platform quotas, limitations, cold start behavior, and upgrade paths across our target deployment stack.

---

## 1. Frontend: Netlify (Free Tier / Starter)

### Official Quotas & Limits:
- **Bandwidth**: 100 GB / month
- **Build Minutes**: 300 minutes / month
- **Serverless Function Execution**: 125,000 requests / month
- **Function Timeout**: 10 seconds default (26 seconds max on paid)
- **Concurrent Builds**: 1 build at a time
- **Custom Domains & SSL**: Free automated Let's Encrypt certificates for `attacksurface.online` and `www.attacksurface.online`

### Architectural Impact & Mitigations:
- **SSR & Next.js Runtime**: We use `@netlify/plugin-nextjs`. Server components and dynamic routes run as Netlify Functions.
- **Reverse Proxy Rewrites**: Our `netlify.toml` rewrites `/api/*` to the FastAPI backend. Netlify proxying counts towards monthly bandwidth (100 GB). At typical response sizes (~15 KB average), 100 GB supports ~6.6 million API calls/month.
- **Upgrade Trigger**: Upgrade to Netlify Pro ($19/seat/mo) when bandwidth exceeds 100 GB/month or build concurrency needs to scale.

---

## 2. Database: Supabase PostgreSQL (Free Tier)

### Official Quotas & Limits:
- **Database Size**: 500 MB PostgreSQL disk storage
- **Compute / RAM**: Shared CPU, 500 MB RAM
- **Direct Database Connections (Port 5432)**: Max 60 concurrent connections
- **Connection Pooler (Supavisor / Port 6543)**: Up to 200 concurrent pooler clients in transaction mode
- **Project Pausing**: Free-tier projects pause after **7 days of inactivity** (inactivity defined as 0 HTTP/API/direct queries).
- **Egress**: 2 GB / month
- **Storage / File Uploads**: 1 GB free bucket storage

### Architectural Impact & Mitigations:
- **Project Pausing Prevention**: Because AttackSurface runs periodic 10-minute snapshot checks and scheduled jobs, ongoing database queries keep the project active.
- **Connection Management**:
  - Direct connection (`port 5432`) is reserved for Alembic migrations (`alembic upgrade head`).
  - FastAPI web instances connect via the connection pooler (`port 6543`) with SQLAlchemy `pool_pre_ping=True`, `pool_size=5`, `max_overflow=10` to avoid exhausting connection slots.
- **500 MB Capacity**: Current schema with 1,000 canonical companies and initial snapshot indexes consumes ~15–30 MB. 500 MB easily accommodates ~50,000 timeline events.
- **Upgrade Trigger**: Upgrade to Supabase Pro ($25/mo) when database size approaches 400 MB or to enable automated daily backups with PITR (Point In Time Recovery).

---

## 3. Backend Web Service: Render (Free Web Service)

### Official Quotas & Limits:
- **RAM / CPU**: 512 MB RAM, 0.1 shared vCPU
- **Monthly Compute Hours**: 750 free instance hours / month (sufficient to run 1 service 24/7)
- **Bandwidth**: 100 GB / month
- **Inactivity Sleep (Spin-down)**: Free web services automatically spin down after **15 minutes of zero incoming HTTP traffic**.
- **Cold Start Latency**: On spin-down, the first incoming request takes **30–50 seconds** to boot the container.
- **Outbound Execution**: Custom domains supported with free TLS.

### Architectural Impact & Mitigations:
- **Cold Starts**: When spinning down, the first visitor experiences a delay.
- **Worker Separation**: Render Free **does not** support persistent Background Worker services for free (Render Workers cost $7/mo minimum).
- **Decoupled Strategy**:
  - FastAPI runs as a Render Web Service or on Fly.io / Railway.
  - Periodic cron pings (e.g. from Netlify scheduled functions or external monitor) can prevent idle spin-down if desired.
- **Upgrade Trigger**: Upgrade to Render Starter ($7/mo) for 24/7 zero-spin-down uptime and persistent background workers.

---

## 4. Redis & Background Processing: Upstash / Self-Hosted

### Upstash Redis (Free Tier):
- **Commands**: 10,000 commands / day free
- **Storage**: 256 MB max memory
- **Connections**: Concurrent connections handled via serverless REST or direct redis protocol.
- **Worker Compatibility**: Direct RQ workers require persistent socket connections (`redis-py`). If using standard RQ `Worker(queues, connection=redis)`, a standard persistent Redis instance is required (e.g. Render Redis $7/mo, Railway Redis $5/mo, or a small VPS container).

---

## 5. Transactional Email: Resend (Free Tier)

### Official Quotas & Limits:
- **Volume**: 3,000 emails / month (100 emails / day)
- **Sending Domain**: Custom domain verification required for `attacksurface.online` via DKIM, SPF, and DMARC TXT records.
- **Rate Limit**: 2 emails / second

### Architectural Impact & Mitigations:
- Password resets, email verifications, and high-priority alert notifications utilize this pool.
- Daily transactional volume in initial phases is well under 100 emails/day.
- Upgrade to Resend Pro ($20/mo) for 50,000 emails/month when user base grows.

---

## 6. Payments: Razorpay (Standard Tier)

### Pricing & Quotas:
- **Setup Fee**: ₹0 (No monthly subscription)
- **Transaction Fee**: 2% per successful domestic transaction (+18% GST). International cards: 3%.
- **Test Mode**: Unlimited sandbox transactions with simulated card numbers.
- **Webhook Verifications**: Unlimited HMAC-SHA256 signature verification.

---

## 7. AI & Intelligence Providers

| Provider | Free / Included Tier | Rate Limit / Quotas | Architecture Handling |
| :--- | :--- | :--- | :--- |
| **Google Gemini** | Free Tier via Google AI Studio | 15 RPM, 1,500 RPD | Default AI provider; filtered through relevance gate |
| **NVIDIA NIM** | 1,000 free inference credits | Rate limits per model | Secondary evaluation engine |
| **GitHub API** | 5,000 requests / hour with token | 60 req/hr unauthenticated | Monitored with rate-limit headers |
| **CISA KEV** | 100% Free / Public Domain | Unmetered (Cached locally) | 24-hour hash-based conditional GET |
| **NVD API 2.0** | Free with API Key | 50 requests / 30 seconds | Exponential backoff retry handler |
| **OSV.dev** | 100% Free / Public | Unmetered public REST | Direct batch queries |
