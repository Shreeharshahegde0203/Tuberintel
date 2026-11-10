# TuberIntel Mandi Directory V4

This update fixes the blank `/market` page and replaces the incomplete frontend state/APMC lists with a database-backed market directory.

## What changed

- The state selector is loaded from `market_states` and contains all 28 Indian states and 8 Union Territories.
- The selection flow is now: **State → District → APMC / mandi → Potato variety**.
- APMC names are not hardcoded inside React components.
- The backend persists market locations in `mandi_directory` and keeps an audit entry in `market_sync_runs`.
- The official directory sync scans the data.gov.in AGMARKNET resource without a commodity filter, so it discovers every reporting market for the chosen state, not only markets reporting potato that day.
- Repeated synchronisations accumulate markets in the database. A market is not deleted merely because it did not report on the latest day.
- Potato prices continue to be stored separately in `market_prices` and can be filtered by state, district, market and variety.
- Dashboard quick-action icons now use a consistent flat potato-themed vector system instead of 3D/AI-looking artwork.
- Frontend dependency versions are pinned and a valid `package-lock.json` is included.

## Apply the update

The downloaded ZIP is expected to be on the Desktop.

From the current project root, the folder containing `frontend` and `backend`:

```bash
cp backend/tuberintel.db backend/tuberintel.db.before-mandi-v4 2>/dev/null || true
unzip -o ~/Desktop/tuberintel_mandi_directory_v4.zip -d .
```

## Configure the official market source

Open the backend environment file:

```bash
cd backend
cp .env.example .env 2>/dev/null || true
nano .env
```

Add your personal data.gov.in key:

```env
DATA_GOV_API_KEY=your_data_gov_in_key
DATA_GOV_RESOURCE_ID=9ef84268-d588-465a-a308-a864a43d0070
MARKET_DIRECTORY_MAX_PAGES=80
```

The key stays in the backend. Never put it in `frontend/.env` or expose it through Vite variables.

## Start the backend

```bash
cd backend
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`init_db()` also creates missing tables for local SQLite development, but running Alembic keeps the schema history correct.

## Start the frontend

Open a second terminal:

```bash
cd frontend
rm -rf node_modules
npm ci
npm run dev
```

Open:

```text
http://localhost:5173/market
```

## First official directory sync

1. Select a state.
2. Click **Sync official APMC directory**.
3. Wait for the backend to page through the official feed and store unique district/market pairs.
4. The district and APMC dropdowns will reload from the database.
5. Click **Refresh price data** to ingest the latest potato observations for that state/district.

## Data-source boundary

The current data.gov.in resource is the official AGMARKNET daily mandi-price feed. It exposes state, district, market, commodity, variety, grade, date and min/modal/max prices. It does not provide a reliable e-NAM membership flag or a permanent registry of every legally registered APMC. Therefore TuberIntel labels this as an **official reporting-mandi directory** and accumulates it over time. A separate e-NAM registry/trade connector can later populate `is_enam` without changing the frontend or database design.
