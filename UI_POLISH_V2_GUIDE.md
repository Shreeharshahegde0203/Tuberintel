# TuberIntel UI Polish V2

This patch updates the authenticated frontend without changing Supabase authentication, backend services, database files or ML code.

## Included changes

- Replaces the leaf brand mark with the existing Tuber Mitra mascot.
- Replaces the unreliable header state select with a controlled state + city / mandi popover.
- Persists the selected state and city and broadcasts the choice to dashboard and mandi pages.
- Adds a warmer multi-accent visual system while preserving the light white/green product theme.
- Restyles all quick-action icons as clean line icons with distinct functional colors.
- Rebuilds the Mandi Prices page around the consolidated report, popular mandi rail, circular mandi browser, state/city/variety explorer and market-wise price table.
- Continues to read market report values and price records from the existing backend endpoints.

## Apply

From the repository root:

```bash
cp frontend/src/components/AppShell.tsx frontend/src/components/AppShell.tsx.before-ui-v2
cp frontend/src/pages/DashboardPage.tsx frontend/src/pages/DashboardPage.tsx.before-ui-v2
cp frontend/src/pages/MarketPage.tsx frontend/src/pages/MarketPage.tsx.before-ui-v2
cp frontend/src/market-ui-phase1.css frontend/src/market-ui-phase1.css.before-ui-v2
unzip -o ~/Desktop/tuberintel_ui_polish_v2.zip -d .
```

Then restart the frontend:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` and hard refresh with `Ctrl + Shift + R`.

## Files changed

- `frontend/src/components/AppShell.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/MarketPage.tsx`
- `frontend/src/data/marketLocations.ts`
- `frontend/src/market-ui-phase1.css`
- `frontend/public/brand/tuber-mitra.png`
