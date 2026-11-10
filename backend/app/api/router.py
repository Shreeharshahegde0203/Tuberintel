from __future__ import annotations

import shutil
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Batch, BatchImage, Feedback, QualityAssessment, Recommendation
from app.schemas.assistant import AssistantQuery, AssistantResponse
from app.schemas.marketplace import (
    ColdStorageRead, FavoriteResponse, ListingCreate, ListingPage, ListingRead, ListingUpdate,
    MarketplaceSummary, TransportProviderRead,
)
from app.schemas.batches import (
    AnalysisOptions,
    BatchCreate,
    BatchListItem,
    BatchRead,
    FeedbackCreate,
)
from app.schemas.dashboard import DashboardSummary
from app.schemas.market import (
    ConsolidatedMarketReport,
    MarketAnalytics,
    MandiDirectoryResponse,
    MarketFilters,
    MarketForecastResponse,
    MarketOutlookResponse,
    MarketOverview,
    MarketStateOption,
    MarketPriceRead,
    NewsResponse,
    StoragePlanRequest,
    StoragePlanResponse,
    TransportPlanRequest,
    TransportPlanResponse,
    WeatherResponse,
)
from app.services.farmer_assistant import FarmerAssistantService
from app.services.marketplace_service import MarketplaceService
from app.services.image_analysis import PotatoImageAnalyzer
from app.services.market_service import MarketService
from app.services.agmarknet_service import AgmarknetUpstreamError, agmarknet_service
from app.services.model_registry import ModelRegistry
from app.services.news_service import NewsService
from app.services.recommendation_engine import RecommendationEngine
from app.services.storage_service import StorageService
from app.services.weather_service import WeatherService


router = APIRouter()
settings = get_settings()
market_service = MarketService()
news_service = NewsService()
weather_service = WeatherService()
recommendation_engine = RecommendationEngine()
model_registry = ModelRegistry(
    settings.roi_model_path,
    settings.condition_model_path or settings.quality_model_path,
    settings.defect_model_path,
)
storage_service = StorageService(settings)
marketplace_service = MarketplaceService()
farmer_assistant = FarmerAssistantService()


def _load_batch(db: Session, batch_id: int) -> Batch:
    batch = db.scalar(
        select(Batch)
        .where(Batch.id == batch_id)
        .options(
            selectinload(Batch.images),
            selectinload(Batch.assessment),
            selectinload(Batch.recommendation),
        )
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


def _batch_code(db: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = db.scalar(select(func.count(Batch.id)).where(Batch.batch_code.like(f"PV-{today}-%"))) or 0
    return f"PV-{today}-{count + 1:04d}"


def _batch_response(batch: Batch) -> dict:
    payload = BatchRead.model_validate(batch).model_dump()
    for image_item, model_image in zip(payload["images"], batch.images, strict=False):
        upload_key = f"uploads/{Path(model_image.file_path).name}"
        annotated_key = f"annotated/{Path(model_image.annotated_path).name}" if model_image.annotated_path else None
        image_item["image_url"] = storage_service.public_url(upload_key) or f"/media/uploads/{Path(model_image.file_path).name}"
        image_item["annotated_url"] = (storage_service.public_url(annotated_key) if annotated_key else None) or (
            f"/media/annotated/{Path(model_image.annotated_path).name}" if model_image.annotated_path else None
        )
    return payload


@router.get("/health")
@router.get("/health/live")
def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
        "model_mode": settings.model_mode,
    }


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {
        "status": "ready",
        "database": "ok",
        "market_data_mode": "live" if settings.data_gov_api_key else "seeded_demo",
        "assistant_mode": "openai_optional" if settings.openai_api_key else "local_grounded",
    }


@router.get("/models")
def models() -> dict:
    return {
        "runtime_mode": settings.model_mode,
        "models": model_registry.as_dict(),
        "fallback": {
            "name": "Transparent OpenCV feature pipeline",
            "active": True,
            "features": [
                "potato foreground segmentation",
                "size and shape uniformity",
                "dark bruise proxy",
                "scab texture proxy",
                "crack edge proxy",
                "greening/discoloration",
                "solidity-based deformity and sprout risk",
            ],
        },
    }


@router.post("/batches", status_code=status.HTTP_201_CREATED)
def create_batch(payload: BatchCreate, db: Session = Depends(get_db)) -> dict:
    batch = Batch(batch_code=_batch_code(db), **payload.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _batch_response(_load_batch(db, batch.id))


@router.get("/batches")
def list_batches(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[BatchListItem]:
    batches = list(
        db.scalars(
            select(Batch)
            .options(selectinload(Batch.assessment), selectinload(Batch.recommendation))
            .order_by(Batch.created_at.desc())
            .limit(limit)
        )
    )
    return [
        BatchListItem(
            id=batch.id,
            batch_code=batch.batch_code,
            variety=batch.variety,
            quantity_kg=batch.quantity_kg,
            source_location=batch.source_location,
            status=batch.status,
            created_at=batch.created_at,
            grade=batch.assessment.quality_grade if batch.assessment else None,
            quality_score=batch.assessment.quality_score if batch.assessment else None,
            action=batch.recommendation.recommended_action if batch.recommendation else None,
            expected_net_profit=batch.recommendation.expected_net_profit if batch.recommendation else None,
        )
        for batch in batches
    ]


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_db)) -> dict:
    return _batch_response(_load_batch(db, batch_id))


@router.post("/batches/{batch_id}/images", status_code=status.HTTP_201_CREATED)
def upload_batch_images(
    batch_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> dict:
    batch = _load_batch(db, batch_id)
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one potato image")
    if len(files) > 12:
        raise HTTPException(status_code=400, detail="A maximum of 12 images can be uploaded per request")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    for file in files:
        if file.content_type not in allowed:
            raise HTTPException(status_code=415, detail=f"Unsupported image type: {file.content_type}")
        suffix = Path(file.filename or "image.jpg").suffix.lower() or ".jpg"
        saved_name = f"{batch.batch_code.lower()}-{uuid.uuid4().hex[:10]}{suffix}"
        destination = settings.upload_dir / saved_name
        with destination.open("wb") as output:
            shutil.copyfileobj(file.file, output)
        if destination.stat().st_size > settings.max_upload_mb * 1024 * 1024:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=413, detail=f"Each image must be under {settings.max_upload_mb} MB")
        storage_service.upload(destination, f"uploads/{saved_name}", file.content_type)
        image_record = BatchImage(
            batch_id=batch.id,
            file_name=file.filename or saved_name,
            file_path=str(destination),
            mime_type=file.content_type,
        )
        batch.images.append(image_record)
        db.add(image_record)
    batch.status = "images_uploaded"
    db.commit()
    return _batch_response(_load_batch(db, batch.id))


@router.post("/batches/{batch_id}/analyze")
def analyze_batch(
    batch_id: int,
    options: AnalysisOptions,
    db: Session = Depends(get_db),
) -> dict:
    batch = _load_batch(db, batch_id)
    if not batch.images:
        raise HTTPException(status_code=400, detail="Upload at least one image before analysis")

    analyzer = PotatoImageAnalyzer(settings.model_mode)
    analyses = []
    errors: list[str] = []
    for image in batch.images:
        annotated_name = f"annotated-{Path(image.file_path).stem}.jpg"
        annotated_path = settings.annotated_dir / annotated_name
        try:
            source_path = Path(image.file_path)
            if not source_path.is_absolute():
                source_path = settings.upload_dir / source_path
            if not source_path.exists() and storage_service.enabled:
                storage_service.download(f"uploads/{Path(image.file_path).name}", source_path)
            metrics = analyzer.analyze(source_path, annotated_path)
            storage_service.upload(annotated_path, f"annotated/{annotated_name}", "image/jpeg")
            image.annotated_path = annotated_name
            image.analysis_json = metrics.to_dict()
            analyses.append(metrics)
        except ValueError as exc:
            errors.append(f"{image.file_name}: {exc}")

    if not analyses:
        raise HTTPException(status_code=422, detail={"message": "No image could be analysed", "errors": errors})

    aggregated = analyzer.aggregate(analyses, settings.model_mode)
    if options.measurement_source == "not_available" and (options.measured_length_mm or options.measured_width_mm):
        raise HTTPException(status_code=422, detail="Set measurement_source when supplying physical measurements")
    if options.measurement_source != "not_available" and not (options.measured_length_mm or options.measured_width_mm):
        raise HTTPException(status_code=422, detail="Supply a measured length or width for the selected measurement source")
    if options.measured_length_mm or options.measured_width_mm:
        width_mm = options.measured_width_mm or options.measured_length_mm
        length_mm = options.measured_length_mm or options.measured_width_mm
        if width_mm < 40:
            size_class = "S (<40 mm)"
        elif width_mm < 60:
            size_class = "M (40â€“59 mm)"
        elif width_mm < 80:
            size_class = "L (60â€“79 mm)"
        else:
            size_class = "XL (â‰¥80 mm)"
        summary = dict(aggregated.get("feature_summary") or {})
        summary["physical_measurement"] = {
            "length_mm": round(float(length_mm), 1),
            "width_mm": round(float(width_mm), 1),
            "length_width_ratio": round(float(length_mm) / max(float(width_mm), 0.1), 2),
            "source": options.measurement_source,
            "calibrated": options.measurement_source in {"potato_ruler", "calibrated_image"},
        }
        summary["size_class"] = size_class
        summary["size_class_note"] = "Configurable demo diameter bands; buyer/mandi contracts can override them."
        aggregated["feature_summary"] = summary
    else:
        summary = dict(aggregated.get("feature_summary") or {})
        summary.setdefault("size_class", "Relative size only â€” physical calibration not supplied")
        aggregated["feature_summary"] = summary
    if batch.assessment:
        for key, value in aggregated.items():
            setattr(batch.assessment, key, value)
        assessment = batch.assessment
    else:
        assessment = QualityAssessment(batch_id=batch.id, **aggregated)
        batch.assessment = assessment
        db.add(assessment)
    db.flush()

    latest_markets = market_service.latest_prices(db, state=batch.state)
    forecast_payload = market_service.forecast_detailed(
        db,
        state=batch.state,
        district=batch.district,
        market=batch.intended_market,
        variety=batch.variety,
        horizon_days=settings.price_forecast_max_horizon_days,
        persist=True,
    )
    forecast = forecast_payload["points"]
    recommendation_payload = recommendation_engine.evaluate(batch, assessment, latest_markets, forecast, options)
    if batch.recommendation:
        for key, value in recommendation_payload.items():
            setattr(batch.recommendation, key, value)
    else:
        recommendation = Recommendation(batch_id=batch.id, **recommendation_payload)
        batch.recommendation = recommendation
        db.add(recommendation)

    batch.status = "analyzed"
    db.commit()
    result = _batch_response(_load_batch(db, batch.id))
    result["analysis_warnings"] = errors
    return result


@router.post("/batches/{batch_id}/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(batch_id: int, payload: FeedbackCreate, db: Session = Depends(get_db)) -> dict:
    batch = _load_batch(db, batch_id)
    feedback = Feedback(batch_id=batch.id, **payload.model_dump())
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {
        "id": feedback.id,
        "batch_id": feedback.batch_id,
        "message": "Outcome recorded for the continuous learning dataset.",
    }


@router.get("/market/overview", response_model=MarketOverview)
def market_overview(state: str = "Karnataka", db: Session = Depends(get_db)) -> dict:
    ensure_web_prices(db, state=state)
    return market_service.overview(db, state=state)


@router.get("/market/directory/states", response_model=list[MarketStateOption])
def market_directory_states(db: Session = Depends(get_db)) -> list[dict]:
    return market_service.directory_states(db)


@router.get("/market/directory/mandis", response_model=MandiDirectoryResponse)
def market_directory_mandis(
    state: str = Query(min_length=2),
    district: str | None = None,
    search: str | None = None,
    limit: int = Query(default=2500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    ensure_web_prices(db, state=state)
    return market_service.mandi_directory(db, state=state, district=district, search=search, limit=limit)


@router.post("/market/directory/sync")
def sync_market_directory(
    state: str = Query(min_length=2), max_pages: int | None = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = sync_web_prices(db,state=state,force=True)
        directory = market_service.mandi_directory(db,state=state)
        return dict(result, state=state, mandi_count=directory["count"], note="Public webpage connector: Bangalore APMC aggregate coverage only; not a complete official APMC directory.")
    except Exception as exc:
        raise HTTPException(502, f"Public webpage directory update failed: {exc}") from exc


@router.get("/market/filters", response_model=MarketFilters)
def market_filters(state: str | None = None, db: Session = Depends(get_db)) -> dict:
    ensure_web_prices(db, state=state)
    return market_service.filters(db, state=state)


@router.get("/market/prices", response_model=list[MarketPriceRead])
def market_prices(
    state: str | None = None,
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    grade: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    latest_only: bool = False,
    limit: int = Query(default=250, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list:
    ensure_web_prices(db, state=state)
    return market_service.list_prices(
        db,
        state=state,
        district=district,
        market=market,
        variety=variety,
        grade=grade,
        date_from=date_from,
        date_to=date_to,
        latest_only=latest_only,
        limit=limit,
        offset=offset,
    )


@router.get("/market/consolidated", response_model=ConsolidatedMarketReport)
def market_consolidated(
    state: str | None = "Karnataka",
    district: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    ensure_web_prices(db, state=state)
    return market_service.consolidated(db, state=state, district=district)


@router.get("/market/analytics", response_model=MarketAnalytics)
def market_analytics(
    state: str = "Karnataka",
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    window_days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
) -> dict:
    ensure_web_prices(db, state=state)
    return market_service.analytics(
        db,
        state=state,
        district=district,
        market=market,
        variety=variety,
        window_days=window_days,
    )


@router.get("/market/forecast", response_model=MarketForecastResponse)
def market_forecast(
    state: str = "Karnataka",
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    horizon_days: int = Query(default=30, ge=1, le=30),
    db: Session = Depends(get_db),
) -> dict:
    ensure_web_prices(db, state=state)
    try:
        return market_service.forecast_detailed(
            db, state=state, district=district, market=market, variety=variety, horizon_days=horizon_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/market/outlook", response_model=MarketOutlookResponse)
def market_outlook(
    state: str = "Karnataka",
    district: str | None = None,
    market: str | None = None,
    variety: str | None = None,
    horizon_days: int = Query(default=60, ge=31, le=90),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return market_service.outlook(
            db, state=state, district=district, market=market, variety=variety, horizon_days=horizon_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/market/refresh")
def refresh_market(
    state: str | None = "Karnataka", district: str | None = None,
    max_pages: int | None = Query(default=None, ge=1, le=25), db: Session = Depends(get_db),
) -> dict:
    try:
        return sync_web_prices(db, state=state, district=district, force=True)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Webpage refresh failed; stored observations retained: {exc}") from exc

def _resolve_user_ref(
    x_user_ref: str | None,
    authorization: str | None = None,
    *,
    required: bool = True,
) -> str | None:
    """Resolve demo identity locally or verify a Supabase access token in production mode."""
    if settings.auth_mode.lower() != "supabase":
        value = (x_user_ref or "").strip()
        if not value and required:
            raise HTTPException(status_code=401, detail="X-User-Ref header is required in demo auth mode")
        return value[:160] if value else None

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase authentication is selected but backend Supabase settings are incomplete")
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Bearer access token is required")
        return None
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_service_role_key,
                },
            )
        if response.status_code != 200:
            if required:
                raise HTTPException(status_code=401, detail="Invalid or expired Supabase session")
            return None
        user_id = str((response.json() or {}).get("id") or "").strip()
        if not user_id:
            if required:
                raise HTTPException(status_code=401, detail="Supabase session did not resolve a user")
            return None
        return user_id[:160]
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        if required:
            raise HTTPException(status_code=503, detail="Could not verify Supabase session") from exc
        return None


@router.get("/marketplace/summary", response_model=MarketplaceSummary)
def marketplace_summary(db: Session = Depends(get_db)) -> dict:
    return marketplace_service.summary(db)


@router.get("/marketplace/listings", response_model=ListingPage)
def marketplace_listings(
    listing_type: str | None = Query(default=None, pattern="^(BUY|SELL)$"),
    state: str | None = None, district: str | None = None, variety: str | None = None, search: str | None = None,
    sort: str = Query(default="newest", pattern="^(newest|price_low|price_high|quantity_high)$"),
    only_owner: bool = False, favorites_only: bool = False, cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    x_user_ref: str | None = Header(default=None, alias="X-User-Ref"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    owner_ref = _resolve_user_ref(x_user_ref, authorization, required=False)
    items, next_cursor = marketplace_service.list_listings(
        db, owner_ref=owner_ref, listing_type=listing_type, state=state, district=district,
        variety=variety, search=search, sort=sort, only_owner=only_owner, favorites_only=favorites_only,
        cursor=cursor, limit=limit,
    )
    return {"items": items, "next_cursor": next_cursor, "total_returned": len(items)}


@router.post("/marketplace/listings", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_marketplace_listing(
    payload: ListingCreate,
    x_user_ref: str | None = Header(default=None, alias="X-User-Ref"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> ListingRead:
    user_ref = _resolve_user_ref(x_user_ref, authorization, required=True)
    return marketplace_service.create_listing(db, payload, user_ref, idempotency_key)


@router.patch("/marketplace/listings/{listing_id}", response_model=ListingRead)
def update_marketplace_listing(
    listing_id: int, payload: ListingUpdate,
    x_user_ref: str | None = Header(default=None, alias="X-User-Ref"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> ListingRead:
    user_ref = _resolve_user_ref(x_user_ref, authorization, required=True)
    return marketplace_service.update_listing(db, listing_id, payload, user_ref)


@router.post("/marketplace/listings/{listing_id}/favorite", response_model=FavoriteResponse)
def favorite_marketplace_listing(
    listing_id: int, x_user_ref: str | None = Header(default=None, alias="X-User-Ref"),
    authorization: str | None = Header(default=None, alias="Authorization"), db: Session = Depends(get_db),
) -> dict:
    user_ref = _resolve_user_ref(x_user_ref, authorization, required=True)
    return {"listing_id": listing_id, "favorite": marketplace_service.set_favorite(db, listing_id, user_ref, True)}


@router.delete("/marketplace/listings/{listing_id}/favorite", response_model=FavoriteResponse)
def unfavorite_marketplace_listing(
    listing_id: int, x_user_ref: str | None = Header(default=None, alias="X-User-Ref"),
    authorization: str | None = Header(default=None, alias="Authorization"), db: Session = Depends(get_db),
) -> dict:
    user_ref = _resolve_user_ref(x_user_ref, authorization, required=True)
    return {"listing_id": listing_id, "favorite": marketplace_service.set_favorite(db, listing_id, user_ref, False)}


@router.get("/marketplace/cold-storage", response_model=list[ColdStorageRead])
def marketplace_cold_storage(
    state: str | None = None, district: str | None = None, limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return marketplace_service.cold_storage(db, state=state, district=district, limit=limit)


@router.get("/marketplace/transport", response_model=list[TransportProviderRead])
def marketplace_transport(
    state: str | None = None, district: str | None = None, limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return marketplace_service.transport(db, state=state, district=district, limit=limit)


@router.post("/assistant/query", response_model=AssistantResponse)
async def farmer_assistant_query(payload: AssistantQuery, db: Session = Depends(get_db)) -> dict:
    return await farmer_assistant.answer(
        db, message=payload.message, language=payload.language, batch_id=payload.batch_id,
        state=payload.state, district=payload.district,
    )


@router.get("/news", response_model=NewsResponse)
def potato_news(
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    return news_service.list(db, category=category, search=search, limit=limit, auto_refresh=refresh or True)


@router.post("/news/refresh")
def refresh_news(db: Session = Depends(get_db)) -> dict:
    try:
        return news_service.refresh(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Potato-news refresh failed: {exc}") from exc


@router.get("/weather", response_model=WeatherResponse)
def weather(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    days: int = Query(default=5, ge=1, le=10),
) -> dict:
    try:
        return weather_service.forecast(latitude, longitude, days)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Weather request failed: {exc}") from exc


@router.post("/tools/storage-plan", response_model=StoragePlanResponse)
def storage_plan(payload: StoragePlanRequest) -> dict:
    return market_service.storage_plan(payload)


@router.post("/tools/transport-plan", response_model=TransportPlanResponse)
def transport_plan(payload: TransportPlanRequest) -> dict:
    return market_service.transport_plan(payload)


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(db: Session = Depends(get_db)) -> dict:
    batches = list(
        db.scalars(
            select(Batch)
            .options(selectinload(Batch.assessment), selectinload(Batch.recommendation))
            .order_by(Batch.created_at.desc())
        )
    )
    analyzed = [b for b in batches if b.assessment and b.recommendation]
    avg_quality = sum(b.assessment.quality_score for b in analyzed) / len(analyzed) if analyzed else 0.0
    projected_value = sum(b.recommendation.expected_net_profit for b in analyzed) if analyzed else 0.0

    overview = market_service.overview(db)
    latest_prices = overview["latest_prices"]
    latest_modal = sum(p.modal_price for p in latest_prices) / len(latest_prices) if latest_prices else 0.0

    grade_distribution: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0}
    action_distribution: dict[str, int] = {"SELL_NOW": 0, "STORE": 0, "PROCESS": 0, "WAIT": 0}
    for b in analyzed:
        grade_distribution[b.assessment.quality_grade] = grade_distribution.get(b.assessment.quality_grade, 0) + 1
        action = b.recommendation.recommended_action
        action_distribution[action] = action_distribution.get(action, 0) + 1

    recent = [
        BatchListItem(
            id=b.id,
            batch_code=b.batch_code,
            variety=b.variety,
            quantity_kg=b.quantity_kg,
            source_location=b.source_location,
            status=b.status,
            created_at=b.created_at,
            grade=b.assessment.quality_grade if b.assessment else None,
            quality_score=b.assessment.quality_score if b.assessment else None,
            action=b.recommendation.recommended_action if b.recommendation else None,
            expected_net_profit=b.recommendation.expected_net_profit if b.recommendation else None,
        )
        for b in batches[:8]
    ]

    return {
        "total_batches": len(batches),
        "analyzed_batches": len(analyzed),
        "average_quality_score": round(avg_quality, 2),
        "projected_value": round(projected_value, 2),
        "latest_modal_price": round(latest_modal, 2),
        "price_change_percent": overview["change_percent"],
        "recent_batches": recent,
        "price_forecast": overview["forecast"][:14],
        "grade_distribution": grade_distribution,
        "action_distribution": action_distribution,
    }


# TUBERINTEL PUBLIC WEB PRICES V1
from app.services.web_market_service import ensure_web_prices, sync as sync_web_prices, web_status

@router.get("/market/web-status")
def market_web_status() -> dict:
    return web_status()
