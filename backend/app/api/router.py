from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.auth import AuthenticatedUser, enforce_rate_limit, get_optional_current_user, require_admin_user, require_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Batch, BatchImage, Feedback, QualityAssessment, Recommendation
from app.schemas.batches import (
    AnalysisOptions,
    BatchCreate,
    BatchListItem,
    BatchRead,
    FeedbackCreate,
)
from app.schemas.dashboard import DashboardSummary
from app.schemas.market import MarketAnalytics, MarketDirectoryResponse, MarketFilters, MarketOverview, MarketPriceQuery, MarketPriceRead, MarketStateItem, MarketDistrictItem, MarketSyncResponse
from app.services.market_service import MarketService
from app.services.model_registry import ModelRegistry
from app.services.recommendation_engine import RecommendationEngine
from app.services.storage_service import StorageService


router = APIRouter()
settings = get_settings()
market_service = MarketService()
recommendation_engine = RecommendationEngine()
model_registry = ModelRegistry(settings.quality_model_path, settings.defect_model_path)
storage_service = StorageService(settings)


def _load_batch(db: Session, batch_id: int, user: AuthenticatedUser | None = None) -> Batch:
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
    if batch.owner_user_id and user and batch.owner_user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="You do not have access to this batch.")
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
def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
        "model_mode": settings.model_mode,
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
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> dict:
    batch = Batch(batch_code=_batch_code(db), owner_user_id=user.id if user else None, **payload.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _batch_response(_load_batch(db, batch.id))


@router.get("/batches")
def list_batches(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> list[BatchListItem]:
    query = (
        select(Batch)
        .options(selectinload(Batch.assessment), selectinload(Batch.recommendation))
        .order_by(Batch.created_at.desc())
        .limit(limit)
    )
    if user and not user.is_admin:
        query = query.where(or_(Batch.owner_user_id == user.id, Batch.owner_user_id.is_(None)))
    batches = list(
        db.scalars(query)
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
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> dict:
    return _batch_response(_load_batch(db, batch_id, user))


@router.post("/batches/{batch_id}/images", status_code=status.HTTP_201_CREATED)
def upload_batch_images(
    batch_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> dict:
    batch = _load_batch(db, batch_id, user)
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
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> dict:
    from app.services.image_analysis import PotatoImageAnalyzer

    batch = _load_batch(db, batch_id, user)
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
    forecast = market_service.forecast(db, state=batch.state, horizon_days=max(30, options.storage_days))
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
def submit_feedback(
    batch_id: int,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> dict:
    batch = _load_batch(db, batch_id, user)
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
    return market_service.overview(db, state=state)


@router.get("/market/directory/states", response_model=list[MarketStateItem])
def list_market_states(db: Session = Depends(get_db)) -> list[dict]:
    return market_service.list_states(db)


@router.get("/market/directory/districts", response_model=list[MarketDistrictItem])
def list_market_districts(state: str = Query(..., min_length=2, max_length=120), db: Session = Depends(get_db)) -> list[dict]:
    try:
        return market_service.list_districts(db, state=state)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/market/directory/mandis", response_model=MarketDirectoryResponse)
def list_markets(
    state: str | None = Query(default=None, min_length=2, max_length=120),
    district: str | None = Query(default=None, min_length=2, max_length=120),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    db: Session = Depends(get_db),
) -> dict:
    return market_service.list_markets(db, state=state, district=district, search=search, limit=limit, offset=offset)


@router.get("/market/filters", response_model=MarketFilters)
def get_market_filters(
    state: str | None = Query(default=None, min_length=2, max_length=120),
    district: str | None = Query(default=None, min_length=2, max_length=120),
    db: Session = Depends(get_db),
) -> dict:
    return market_service.get_filters(db, state=state, district=district)


@router.get("/market/prices", response_model=list[MarketPriceRead])
def get_market_prices(
    state: str | None = Query(default=None, min_length=2, max_length=120),
    district: str | None = Query(default=None, min_length=2, max_length=120),
    market: str | None = Query(default=None, min_length=2, max_length=160),
    commodity: str = Query(default="Potato", min_length=2, max_length=80),
    variety: str | None = Query(default=None, min_length=1, max_length=80),
    grade: str | None = Query(default=None, min_length=1, max_length=40),
    date_from: str | None = None,
    date_to: str | None = None,
    latest_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=10_000),
    db: Session = Depends(get_db),
) -> list:
    try:
        payload = MarketPriceQuery(
            state=state,
            district=district,
            market=market,
            commodity=commodity,
            variety=variety,
            grade=grade,
            date_from=date_from,
            date_to=date_to,
            latest_only=latest_only,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return market_service.list_prices(db, payload.model_dump())


@router.get("/market/analytics", response_model=MarketAnalytics)
def get_market_analytics(
    state: str | None = Query(default=None, min_length=2, max_length=120),
    district: str | None = Query(default=None, min_length=2, max_length=120),
    market: str | None = Query(default=None, min_length=2, max_length=160),
    commodity: str = Query(default="Potato", min_length=2, max_length=80),
    variety: str | None = Query(default=None, min_length=1, max_length=80),
    window_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict:
    return market_service.analytics(
        db,
        {
            "state": state,
            "district": district,
            "market": market,
            "commodity": commodity,
            "variety": variety,
            "window_days": window_days,
        },
    )


@router.post("/market/refresh", response_model=MarketSyncResponse)
def refresh_market(
    state: str = Query(default="Karnataka", min_length=2, max_length=120),
    max_pages: int = Query(default=3, ge=1, le=5),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
) -> dict:
    enforce_rate_limit(f"market-refresh:{user.id}", limit=3, window_seconds=300)
    try:
        return market_service.refresh_from_data_gov(db, state=state, max_pages=max_pages, triggered_by=user.id)
    except httpx.HTTPError as exc:  # type: ignore[name-defined]
        raise HTTPException(status_code=502, detail="Official market data request failed.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/market/directory/sync", response_model=MarketSyncResponse)
def sync_market_directory(
    state: str | None = Query(default=None, min_length=2, max_length=120),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
) -> dict:
    enforce_rate_limit(f"market-directory-sync:{user.id}", limit=5, window_seconds=300)
    return market_service.sync_directory(db, state=state)


@router.post("/admin/market/prices/refresh", response_model=MarketSyncResponse)
def admin_refresh_market(
    state: str = Query(default="Karnataka", min_length=2, max_length=120),
    max_pages: int = Query(default=3, ge=1, le=5),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
) -> dict:
    enforce_rate_limit(f"admin-market-refresh:{user.id}", limit=3, window_seconds=300)
    return market_service.refresh_from_data_gov(db, state=state, max_pages=max_pages, triggered_by=user.id)


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
