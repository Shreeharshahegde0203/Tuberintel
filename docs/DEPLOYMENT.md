# TuberIntel deployment

Deploy the React/Vite frontend on Vercel and the FastAPI/OpenCV backend as a persistent container. This repository includes a Render blueprint and uses Supabase for PostgreSQL and image storage.

## Backend

1. Provision a PostgreSQL database and set the backend environment variables below. Use a direct PostgreSQL connection or a session pooler for migrations.
2. From `backend/`, install `requirements.txt` and run `alembic upgrade head` against that database before starting the backend. For an existing database, review its Alembic revision before upgrading.
3. Run `deployment/supabase/setup.sql` for demo image storage. The supplied bucket policy makes images public. Use test images for deployment verification.
4. Deploy the backend with `render.yaml` or its Dockerfile. Check `https://YOUR-API/api/v1/health/ready` before deploying the frontend.

| Variable | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | PostgreSQL connection string |
| `FRONTEND_ORIGIN` | Exact Vercel URL or custom domain, without trailing slash |
| `MODEL_MODE` | `cv_demo` for the included OpenCV implementation |
| `STORAGE_BACKEND` | `supabase` |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only service role key |
| `SUPABASE_STORAGE_BUCKET` | `potato-inspections` |
| `AUTH_MODE` | Match frontend mode. Use `supabase` for verified marketplace identity |
| `ANALYSIS_MARKET_MAX_AGE_DAYS` | Optional. Default `7`, based on reporting date in India |

## Vercel

Import the repository with the project root set to the repository root. Select Node.js 24.x. The root `vercel.json` installs and builds `frontend/` and routes frontend deep links to the SPA. The browser calls FastAPI directly, including for photo uploads.

| Variable | Value |
| --- | --- |
| `VITE_API_URL` | `https://YOUR-API/api/v1` |
| `VITE_MEDIA_URL` | Optional override. Defaults to the backend origin |
| `VITE_AUTH_MODE` | `demo` for test data or `supabase` for Supabase sign-in |
| `VITE_SUPABASE_URL` | Required with Supabase sign-in |
| `VITE_SUPABASE_ANON_KEY` | Public Supabase key, required with Supabase sign-in |

Use a stable preview domain and put that exact origin in `FRONTEND_ORIGIN` on its backend. If using Supabase sign-in, configure the appropriate sign-in providers and allow the deployed frontend URL in Supabase redirect settings.

## Verify the deployment

- Open `/news` and `/analyze` directly and reload each URL. Check that the browser reaches the configured backend and receives no CORS errors.
- Refresh news, change filters and use browser Back. Check the article dates and feed status. If upstream feeds fail, verify that saved headlines are labelled accordingly.
- Run an inspection with a test image and select Bangalore APMC (published aggregate). The market connector checks for updates on its one-hour interval. Compare the reporting date in the result to the source. With an old or missing observation, verify that the inspection still completes and the affected routes do not receive a market-based price.
- Test a current processor quote. Processing means selling raw potatoes to a processor using a quote entered by the user. The app has no live processor bid feed.
- Reopen a saved batch and verify that its inspection date and market evidence are retained. Run a new inspection to use updated inputs.

The built-in public web connector covers the Bangalore APMC aggregate. Other markets require actual imported reports. Forecasts are estimates. Storage and holding scenarios require an explicit weight-loss assumption and a forecast for the selected horizon.

Use non-sensitive test records for preview deployments. The current batch API has shared records without per-user access enforcement, and the demo storage bucket exposes public image URLs. Public production use with private farmer data requires server-side batch authorization and private object storage with signed access.
