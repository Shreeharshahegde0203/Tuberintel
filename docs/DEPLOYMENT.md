# Production deployment

## Recommended topology

- **Vercel:** React/Vite frontend (`vercel.json` is included)
- **Render/Railway/Cloud Run:** FastAPI backend (`render.yaml` is included)
- **Supabase:** PostgreSQL and image object storage
- **Dedicated model endpoint:** later, when validated PyTorch/YOLO weights are available

A full PyTorch/OpenCV model service should not be forced into a frontend serverless deployment. The frontend remains Vercel-ready while the operational API uses a persistent container.

## Required secrets

Frontend on Vercel:

```env
VITE_API_URL=https://YOUR-API/api/v1
VITE_MEDIA_URL=
VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

Backend:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql://...
FRONTEND_ORIGIN=https://YOUR-FRONTEND.vercel.app
DATA_GOV_API_KEY=...
STORAGE_BACKEND=supabase
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=potato-inspections
MODEL_MODE=cv_demo
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` in a `VITE_` variable.

For the end-to-end local setup, including Google Auth provider configuration and redirect URLs, see `docs/SUPABASE_SETUP.md`.

## Database

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

The application still calls `create_all` as a local-development safety net, but production changes should be applied through Alembic.

## Storage

Run `deployment/supabase/setup.sql`. The supplied demonstration policy creates a public image bucket. A real farmer deployment should use a private bucket and signed URLs if inspection images or identity are sensitive.

## Model status

Deploy with `MODEL_MODE=cv_demo` until research-validated weights exist. Do not change the value to `hybrid` merely to make the UI look complete.
