# TuberIntel — tomorrow's working-demo guide

This recovered build is designed to run **without any external API key**. Optional keys upgrade live data or the assistant, but the core demo remains functional using local CV processing and clearly labelled demonstration market/service data.

## Fastest Windows setup

Prerequisites: Python 3.11+ and Node.js 20+.

### 1. One-time install

Open **Command Prompt** in this project folder and run:

```bat
setup_windows.bat
```

The setup script also runs `npm run build` and the backend test suite, so failures are caught before the demo.

### 2. Start the application

```bat
run_windows.bat
```

Then open `http://localhost:5173`.

Local demo login: use any valid 10-digit Indian mobile number and OTP **123456**.

## Manual setup

Backend terminal:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# Windows: copy .env.example .env
# Linux/macOS: cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```bash
cd frontend
npm install
# Windows: copy .env.example .env
# Linux/macOS: cp .env.example .env
npm run dev
```

## 5-minute presentation flow

1. **Login** — mobile number + local OTP `123456`.
2. **Quality check** — create a batch and upload `data/demo-potato.jpg`.
3. Optionally enter a ruler measurement, e.g. length `72 mm`, width `54 mm`, source `Manual ruler`.
4. **Analyze** — show annotated image, quality grade, defects, confidence, and ranked `SELL_NOW / STORE / PROCESS / WAIT` economics.
5. **Buy / Sell** — publish a SELL post and attach the analyzed batch. It will automatically carry the TuberIntel grade and quality score.
6. Favorite another post, view buyer requirements, cold-storage demo directory and transport demo directory.
7. Open **Tuber Mitra** and ask: `Should I sell this batch now or store it?` On a batch-result page the bot automatically includes that batch as context.
8. **Mandi prices** — explain that the included Karnataka series is visibly demonstration data until `DATA_GOV_API_KEY` is configured.

## API placeholders (all optional for the demo)

Edit `backend/.env` only when you want the integration:

```env
# Official AGMARKNET/data.gov.in price refresh
DATA_GOV_API_KEY=

# Optional LLM enhancement for Tuber Mitra; blank = local grounded bot
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5

# Optional production object storage
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=

# Optional trained CV weights; blank/demo mode uses deterministic OpenCV
MODEL_MODE=cv_demo
QUALITY_MODEL_PATH=../ml/artifacts/quality_model.ts
DEFECT_MODEL_PATH=../ml/artifacts/defects/yolo11s-seg.pt
```

Frontend production auth placeholders are in `frontend/.env`:

```env
VITE_AUTH_MODE=demo
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

## What is real vs demonstration

**Real/local:** image upload, OpenCV feature extraction, annotated output, quality score/grade pipeline, recommendation economics, database persistence, market history/forecast calculations, buy/sell CRUD, favorites, linked-quality verification, assistant retrieval/grounding, batch history, storage/transport calculators, health/readiness endpoints.

**Demonstration until an external source is configured:** seeded mandi observations, seeded buyer/seller examples, seeded cold-storage directory, seeded transport directory, local OTP `123456`.

**Optional trained component:** the repo includes model adapters/training pipelines but does not fake trained accuracy. Add actual weights after training.

## Quick health check

Backend API docs: `http://localhost:8000/docs`

- `GET http://localhost:8000/api/v1/health/live`
- `GET http://localhost:8000/api/v1/health/ready`

If both return 200, the API and database are ready.
