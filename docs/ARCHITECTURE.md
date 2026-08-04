# Architecture

## End-to-end flow

1. A user creates a batch with variety, quantity, source, harvest date and intended market.
2. One to twelve RGB images are uploaded and stored outside the database.
3. The quality service normalizes image scale, checks exposure/sharpness, segments potato regions and measures geometry, colour and texture.
4. Optional learned adapters add classifier probabilities and YOLO segmentation area by defect.
5. Per-image measurements are aggregated into grade, quality score, commercial class and rejection probability.
6. The market service reads the latest potato prices and historical series. Official AGMARKNET data is used when configured; otherwise the source is explicitly marked as demonstration data.
7. The recommendation engine evaluates sell, store, process and wait with a common financial model and pathway-specific deterioration/rejection risk.
8. The highest risk-adjusted score is returned with all alternatives, cost breakdown, exact factor contributions and plain-language reasons.
9. Actual outcome feedback is stored for later calibration and supervised learning.

## Components

- **React client:** operational UI, charts, inspection wizard, explainability and feedback.
- **FastAPI API:** validation, orchestration, error handling, static media and OpenAPI.
- **SQLAlchemy persistence:** batches, images, assessments, recommendations, market prices and feedback.
- **Vision service:** safe baseline and optional trained inference.
- **Market service:** source integration, deduplication, trend and uncertainty bounds.
- **Recommendation service:** deterministic, testable decision logic separated from presentation.

## Deployment boundary

The frontend is static and served by nginx in Docker. nginx proxies `/api/` and `/media/` to FastAPI. The backend can later be moved to a GPU service without changing the browser contract.

## Why this is not a single opaque model

The project combines several different problems: image classification/segmentation, grade derivation, time-series forecasting and constrained economic optimization. Treating the entire system as one black-box neural network would make it difficult to train, audit and defend. Each layer has an explicit contract and can be replaced independently.
