---
module: Frontend
date: 2026-04-15
problem_type: ui_bug
component: frontend_stimulus
symptoms:
  - "Card images not showing in autocomplete dropdown"
  - "Error: Invalid src prop (http://localhost:8000/static/cards/39037517.jpg) on next/image, hostname not configured"
  - "Next.js image optimizer returns 500 with ECONNREFUSED fetching http://localhost:8000 from inside Docker"
root_cause: config_error
resolution_type: config_change
severity: medium
tags: [nextjs, docker, image-optimization, localhost, internal-hostname, rewrite-proxy]
---

# Troubleshooting: Next.js Image Optimizer Fails to Fetch Backend Images Inside Docker

## Problem

When the FastAPI backend returns relative image URLs (e.g. `/static/cards/123.jpg`), the Next.js `<Image>` component cannot display them when running in Docker. Adding `localhost:8000` to `remotePatterns` does not help because the Next.js image optimizer fetches images server-side — from inside the container — where `localhost` refers to the container itself, not the backend service.

## Environment

- Module: Frontend (Next.js) + Backend (FastAPI)
- Affected Component: Next.js `<Image>` component / image optimization proxy
- Stack: Next.js 15 (App Router), FastAPI, Docker Compose
- Date: 2026-04-15

## Symptoms

- Card images are missing in the autocomplete dropdown
- Browser console shows: `Error: Invalid src prop (http://localhost:8000/static/cards/39037517.jpg) on next/image, hostname "localhost" is not configured under images in your next.config.js`
- After adding `localhost:8000` to `remotePatterns`, frontend logs show: `[TypeError: fetch failed] { [cause]: [AggregateError: ] { code: 'ECONNREFUSED' } }` and `GET /_next/image?url=http%3A%2F%2Flocalhost%3A8000%2F... 500`

## What Didn't Work

**Attempted Solution 1:** Prefix relative image URL with `NEXT_PUBLIC_API_URL` in `api.ts`
- Changed backend's `/static/cards/123.jpg` response to `http://localhost:8000/static/cards/123.jpg` before passing to `<Image>`
- **Why it failed:** Next.js `<Image>` with an external `http://` URL goes through the image optimization proxy, which fetches the image server-side. Inside the Docker container, `localhost:8000` resolves to the container itself, not the backend service — resulting in ECONNREFUSED.

**Attempted Solution 2:** Add `localhost:8000` to `remotePatterns` in `next.config.ts`
- **Why it failed:** Same root cause — the hostname validation passes, but the fetch still fails because `localhost` inside Docker is not the backend.

## Solution

Use a Next.js `rewrites()` rule to proxy `/static/cards/:path*` to the backend via its Docker-internal hostname. This way the backend returns a relative path, `<Image>` uses a relative URL (treated as an internal Next.js route), and the rewrite transparently forwards the request to the backend using the correct internal hostname.

**`frontend/next.config.ts`:**
```ts
// Before (broken — no proxy, images returned as relative paths with no resolution path):
const nextConfig: NextConfig = {
  images: {
    remotePatterns: [{ protocol: "https", hostname: "images.ygoprodeck.com" }],
  },
};

// After (fixed):
const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [{ protocol: "https", hostname: "images.ygoprodeck.com" }],
  },
  async rewrites() {
    return [
      {
        source: "/static/cards/:path*",
        destination: `${BACKEND_URL}/static/cards/:path*`,
      },
    ];
  },
};
```

**`docker-compose.yml` frontend environment:**
```yaml
environment:
  NEXT_PUBLIC_API_URL: http://localhost:8000   # browser-side (host machine)
  BACKEND_INTERNAL_URL: http://backend:8000    # server-side (Docker internal)
```

**`frontend/app/lib/api.ts`** — keep image URLs as relative paths (no change needed):
```ts
// Backend returns "/static/cards/123.jpg" — leave it as-is
// The rewrite handles resolution server-side
return res.json();
```

## Why This Works

1. **Root cause:** Next.js `<Image>` uses an image optimization proxy (`/_next/image?url=...`) that fetches images *server-side* from within the Node.js process. Inside Docker, `localhost` resolves to the current container, not the backend service.

2. **Why the rewrite fixes it:** When `<Image src="/static/cards/123.jpg">` is rendered, Next.js image optimizer internally fetches `http://localhost:3000/static/cards/123.jpg` (itself). The rewrite intercepts this and forwards it to `http://backend:8000/static/cards/123.jpg` using the Docker service name — which is resolvable within the Docker network.

3. **Key distinction:** `NEXT_PUBLIC_*` env vars are embedded in the browser bundle (client-side). Server-side Next.js processes (SSR, image optimizer, rewrites) need a separate env var pointing to the internal Docker hostname.

## Prevention

- When a Next.js frontend and a separate API backend run in Docker Compose, always define two URL env vars:
  - `NEXT_PUBLIC_API_URL` — the host-machine-accessible URL for browser fetches
  - `BACKEND_INTERNAL_URL` — the Docker-internal service URL for server-side fetches (SSR, rewrites, image optimizer)
- Never put `localhost:<port>` in `remotePatterns` for Docker deployments — it will always ECONNREFUSED from within a container.
- For any backend-served static assets used with `<Image>`, prefer a `rewrites()` proxy over absolute `remotePatterns` URLs.

## Related Issues

No related issues documented yet.
