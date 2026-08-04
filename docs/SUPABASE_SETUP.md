# Supabase Setup

This repository already has the application-side wiring for Supabase:

- `frontend/src/auth/AuthContext.tsx` uses Supabase Auth in the browser.
- `frontend/src/services/api.ts` sends the Supabase access token to FastAPI.
- `backend/app/api/auth.py` verifies that token against your Supabase project.
- `backend/app/services/storage_service.py` can use Supabase Storage when enabled.

Use these steps to connect your own project.

## 1. Create a Supabase project

Create a project in Supabase and note:

- Project URL: `https://YOUR_PROJECT.supabase.co`
- Publishable/anon key
- Service role key

## 2. Enable Google sign-in

In Supabase:

1. Open `Authentication` -> `Providers` -> `Google`
2. Enable the provider
3. Add your Google OAuth client ID and secret
4. Add these redirect URLs:

```text
http://localhost:5173
http://localhost:5173/
```

For production, also add your deployed frontend URL.

## 3. Configure the frontend

Edit `frontend/.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
VITE_MEDIA_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

`VITE_SUPABASE_PUBLISHABLE_KEY` should be your browser-safe publishable/anon key, not the service role key.

## 4. Configure the backend

Edit `backend/.env`:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql://POSTGRES_USER:POSTGRES_PASSWORD@db_host:5432/postgres
FRONTEND_ORIGIN=http://localhost:5173
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

SUPABASE_URL=https://YOUR_PROJECT.supabase.co

STORAGE_BACKEND=supabase
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
SUPABASE_STORAGE_BUCKET=potato-inspections
```

Notes:

- `SUPABASE_URL` is enough for backend token verification.
- `SUPABASE_SERVICE_ROLE_KEY` is required only for Supabase Storage operations.
- Never put `SUPABASE_SERVICE_ROLE_KEY` in the frontend.

## 5. Provision the bucket and SQL

Run the provided SQL in Supabase SQL editor:

```text
deployment/supabase/setup.sql
```

That creates the expected storage bucket/policies for this project template.

## 6. Run the app

Backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

## 7. Verify the connection

1. Open `http://localhost:5173`
2. Click `Continue with Google`
3. Finish the Google OAuth flow
4. Return to the app
5. Open the browser dev tools and confirm API requests include `Authorization: Bearer ...`

If login succeeds but API calls return `401`, the backend usually has the wrong `SUPABASE_URL` or is still running with an old `.env`.

## 8. Optional: use Supabase Postgres too

If you want Supabase for the database as well, copy the Supabase Postgres connection string into `backend/.env` as `DATABASE_URL`, then run:

```bash
cd backend
alembic upgrade head
```

## Common mistakes

- Frontend uses the service role key instead of the publishable/anon key
- Google provider is not enabled in Supabase
- Google OAuth redirect URL does not include `http://localhost:5173/`
- Backend `.env` is missing `SUPABASE_URL`
- Backend process was not restarted after editing `.env`
