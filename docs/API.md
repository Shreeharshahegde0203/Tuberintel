# API overview

All endpoints are under `/api/v1`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Runtime and model-mode health |
| GET | `/models` | Configured model artefacts and fallback status |
| POST | `/batches` | Create a potato batch |
| GET | `/batches` | List recent batches |
| GET | `/batches/{id}` | Read complete analysis |
| POST | `/batches/{id}/images` | Upload up to 12 images |
| POST | `/batches/{id}/analyze` | Run vision, market and recommendation pipeline |
| POST | `/batches/{id}/feedback` | Store actual commercial outcome |
| GET | `/market/overview` | Prices, source/freshness and forecast |
| POST | `/market/refresh` | Fetch official data.gov.in records |
| GET | `/dashboard` | Operational summary and distributions |

Interactive schemas and examples are available from FastAPI at `/docs`.
