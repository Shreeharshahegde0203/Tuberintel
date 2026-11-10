# TuberIntel — Post-Harvest Decision Intelligence for Potato Value Realization

TuberIntel is a complete, explainable decision-support application for potato batches. It links computer-vision quality assessment with mandi prices, storage and logistics economics, market-risk analysis, and a ranked recommendation across **sell now, store, process, or delay release**.

The implementation follows the project report's end-to-end architecture:

`image capture → preprocessing → feature/defect assessment → grading → market analytics → economic intelligence → recommendation → explainability → feedback`

## What is implemented

- Multi-image potato batch creation and inspection.
- OpenCV preprocessing, foreground segmentation, lighting/blur checks, size/shape uniformity and transparent visual defect measurements.
- Defect indicators for bruising, cracks, scab-like texture, discoloration/greening, deformity and sprouting.
- Grades A–D, commercial class, quality score, rejection probability, annotated images and confidence.
- Optional trained **EfficientNetV2-S / DenseNet169 classifier** and **YOLO11 segmentation** adapters without changing the API contract.
- Current mandi-price ingestion from the official data.gov.in AGMARKNET resource when an API key is configured.
- Auditable price trend/forecast fallback and a LightGBM training pipeline for longer histories.
- A risk-adjusted recommendation engine that calculates revenue, transport, handling, storage, processing, expected loss, net operating profit and ROI for every pathway.
- Exact decision-factor contribution decomposition plus standalone Grad-CAM and SHAP tooling.
- Dashboard, batch history, market intelligence, model registry, JSON export and actual-outcome feedback.
- Functional BUY/SELL marketplace with buyer requirements, seller lots, filters, favorites, idempotent posting, cursor pagination and quality-linked analyzed batches.
- Tuber Mitra farmer assistant: works offline from a local potato knowledge base and can optionally use an LLM without changing the API.
- Cold-storage and transport service directories with clearly labelled demonstration seeds until verified external sources are configured.
- Calibrated/manual physical-size metadata; arbitrary image pixels are never presented as millimetres.
- English/Kannada bilingual interface with persistent language selection, larger touch targets and PWA shell caching.
- Responsive agricultural operations interface without decorative AI-dashboard styling.
- PostgreSQL/Supabase-ready database and object-storage adapter, Alembic schema, Vercel frontend config and Render backend blueprint.

## Repository structure

```text
backend/                 FastAPI, SQLAlchemy, OpenCV, market and recommendation services
frontend/                React + TypeScript + Vite operational interface
ml/scripts/              classifier, segmentation and price-forecast training pipelines
ml/explainability/       Grad-CAM and SHAP utilities
ml/configs/              dataset configuration templates
data/                    demonstration potato image
docs/                    architecture, deployment and research documentation
ml/data/                 licensed-source registry, validation, manifest, deduplication and split tooling
deployment/              nginx configuration
```

## Start here

For tomorrow's demo, read **`START_HERE.md`** first. On Windows, `setup_windows.bat` performs one-time dependency setup and tests; `run_windows.bat` launches both servers.

## Run locally

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: `http://localhost:8000/docs`

Optional demonstration data:

```bash
python scripts/seed_demo.py
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Application: `http://localhost:5173`

The Vite development server proxies `/api` and `/media` to FastAPI.

## Start with Docker

```bash
docker compose up --build
```

Open `http://localhost:8080`. The database and uploaded images are stored in Docker volumes.

## Configure official market data

Create a free data.gov.in API key and set:

```env
DATA_GOV_API_KEY=your_key
DATA_GOV_RESOURCE_ID=9ef84268-d588-465a-a308-a864a43d0070
```

Without a key, the application stays fully usable using a clearly labelled seeded Karnataka demonstration series. It never presents seeded data as live data.

## Configure the optional farmer-assistant LLM

Tuber Mitra works without a key. To enhance generation while keeping retrieval grounding, set:

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5
```

Without a key or if the provider fails, the assistant falls back to its local grounded response path.

## Configure trained vision models

The base installation runs in `cv_demo` mode and uses real, deterministic image processing. For learned inference:

```bash
cd backend
pip install -r requirements-ml.txt
```

Train/export models:

```bash
python ml/scripts/train_quality_classifier.py \
  --data /path/to/potato-classification-dataset \
  --output ml/artifacts/quality_model.ts

python ml/scripts/train_defect_segmenter.py \
  --data ml/configs/potato_defects.yaml
```

Then set `backend/.env`:

```env
MODEL_MODE=hybrid
QUALITY_MODEL_PATH=/absolute/path/to/ml/artifacts/quality_model.ts
DEFECT_MODEL_PATH=/absolute/path/to/best.pt
```

The hybrid runtime combines trained predictions with measured geometry, texture and colour features. This preserves explainability and provides a safe fallback when a weight file is unavailable.

## Research and dataset engineering

Start with:

```bash
pip install -r ml/data/requirements.txt
python ml/data/download_datasets.py --list
python ml/data/validate_images.py /path/to/raw --output datasets/validation.csv
python ml/data/build_manifest.py /path/to/raw --output datasets/manifest.csv
python ml/data/deduplicate.py datasets/manifest.csv
python ml/data/create_splits.py datasets/manifest.csv
```

See `docs/research/RESEARCH_MATRIX.md`, `DATASET_CATALOG.md`, `BENCHMARK_PROTOCOL.md`, `FARMER_PRODUCT_STANDARD.md` and `DATA_COLLECTION_PROTOCOL.md` for the evidence base and acceptance gates.

## Dataset guidance

For classification, folder names become labels. A practical initial taxonomy is:

- healthy
- black_scurf
- blackspot_bruising
- common_scab
- dry_rot
- pink_rot
- soft_rot
- brown_rot
- blackleg
- miscellaneous

For commercial grading, add locally captured and labelled classes or metadata for cracks, greening, sprouting, cuts, size and grade. Disease datasets alone are not enough to claim a complete post-harvest grading system.

## Tests and verification

```bash
cd backend
pytest -q
DATABASE_URL=sqlite:////tmp/tuberintel-migration-test.db alembic upgrade head

cd ../frontend
npm run lint
npm run build
```

The API integration tests create a temporary database, upload the bundled demonstration image, run the complete analysis, verify all four commercial alternatives, exercise calibrated-size metadata, create a quality-linked trade post with idempotent retry, favorite it, query Tuber Mitra, and verify service discovery.

## Important accuracy statement

The software workflow is complete and executable. The repository does **not** ship invented “98% accurate” weights. Final field accuracy depends on a representative, correctly annotated potato dataset collected under the lighting, varieties, cameras and defect definitions of the target users. The included training/evaluation pipelines report accuracy, precision, recall, F1, confusion matrix, MAE and RMSE so model performance can be defended with evidence.


## Deployment

See `docs/DEPLOYMENT.md`. The frontend is Vercel-ready. The recommended production backend is a persistent container with Supabase PostgreSQL/storage.

## Database-backed mandi directory

The market-location selectors do not embed APMC names in the frontend. They use:

- `market_states`: canonical 28-state + 8-Union-Territory reference table;
- `mandi_directory`: accumulated state/district/market directory discovered from the official AGMARKNET reporting feed;
- `market_prices`: potato price observations used for tables, rankings, trends and forecasts;
- `market_sync_runs`: auditable refresh history and errors.

Relevant endpoints:

```text
GET  /api/v1/market/directory/states
GET  /api/v1/market/directory/mandis?state=Karnataka
POST /api/v1/market/directory/sync?state=Karnataka
GET  /api/v1/market/prices?state=Karnataka&district=Kolar&market=Kolar%20APMC
POST /api/v1/market/refresh?state=Karnataka
```

See `MANDI_DIRECTORY_V4_GUIDE.md` for the Desktop-based update commands and the data-source boundary between AGMARKNET reporting markets and future e-NAM-specific metadata.

## V2 engineering notes

See `docs/SYSTEM_DESIGN_V2.md` for the implemented system-design decisions and production scaling path, and `docs/RECOVERY_AND_SCOPE_V2.md` for what was recovered versus added in this rebuild.
