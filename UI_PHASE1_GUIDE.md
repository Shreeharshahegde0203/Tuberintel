# TuberIntel Dashboard UI — Phase 1

This patch changes only the protected application shell and dashboard UI. It does not replace Google authentication, `.env.local`, backend configuration, ML files, database files or existing analysis pages.

## Included

- Light, white and soft-green application theme inspired by the information hierarchy of Potato Bazaar, without copying its assets.
- Horizontal header with state selector, search, notifications and Google-account profile menu.
- Desktop top navigation and responsive mobile drawer/bottom navigation.
- No buyer, seller, listing or auction functionality.
- Dashboard greeting and location context.
- Large weather card with safe fallback when the weather endpoint has not been connected.
- Potato-news rail with safe fallback when the news endpoint has not been connected.
- Current price, movement, best mandi and analysed-batch summary.
- Quick-action grid.
- Top mandi ranking, price trend chart and recent batch analysis table.
- English/Kannada UI labels for the new shell and dashboard.

## Apply

From the folder that contains `backend` and `frontend`:

```bash
cp frontend/src/components/AppShell.tsx frontend/src/components/AppShell.tsx.before-ui-phase1
cp frontend/src/pages/DashboardPage.tsx frontend/src/pages/DashboardPage.tsx.before-ui-phase1
unzip -o ~/Desktop/tuberintel_dashboard_ui_phase1.zip -d .
```

Start the backend in terminal 1:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Start the frontend in terminal 2:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

## Expected fallback behaviour

The core dashboard and market sections use the existing `/dashboard` and `/market/overview` APIs.

The new dashboard also attempts:

```text
GET /api/v1/weather
GET /api/v1/news
```

If those endpoints are not yet present, the page remains usable and displays clearly labelled next-phase placeholders. No fabricated live weather or news values are shown.

## Next implementation phase

Phase 2 will redesign the Mandi Prices page around:

- Consolidated mandi report.
- Popular mandis.
- State and district/market selection.
- Official-source timestamp and freshness.
- Min, modal and max prices.
- Historical trend controls.
- Mandi comparison and net-realisation analysis.

After the Mandi UI is approved, the backend will be connected to the official AGMARKNET/data.gov.in flow rather than scraping Potato Bazaar.
