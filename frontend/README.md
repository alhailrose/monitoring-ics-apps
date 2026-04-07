# ICS Monitoring Hub — Frontend

Next.js web app for the ICS Monitoring Hub platform. See the [root README](../README.md) for full project overview.

## Dev

```bash
cp .env.local.example .env.local  # fill in JWT_SECRET
npm install
npm run dev
```

Runs at `http://localhost:3000`. Requires backend at `http://localhost:8000`.

## Commands

```bash
npm run dev        # development server
npm run build      # production build
npm run typecheck  # TypeScript check (CI gate)
npm run lint       # ESLint
```
