from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Batch,
    ColdStorageFacility,
    TradeFavorite,
    TradeListing,
    TransportProvider,
)
from app.schemas.marketplace import ListingCreate, ListingRead, ListingUpdate


class MarketplaceService:
    @staticmethod
    def _cursor(created_at: datetime, listing_id: int) -> str:
        raw = json.dumps({"t": created_at.isoformat(), "id": listing_id}).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, int]:
        try:
            padding = "=" * (-len(cursor) % 4)
            payload = json.loads(base64.urlsafe_b64decode(cursor + padding).decode())
            value = datetime.fromisoformat(payload["t"])
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value, int(payload["id"])
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid marketplace cursor") from exc

    @staticmethod
    def _listing_read(db: Session, listing: TradeListing, owner_ref: str | None) -> ListingRead:
        favorite = False
        if owner_ref:
            favorite = bool(
                db.scalar(
                    select(TradeFavorite.id).where(
                        TradeFavorite.owner_ref == owner_ref,
                        TradeFavorite.listing_id == listing.id,
                    )
                )
            )
        return ListingRead.model_validate(listing).model_copy(update={
            "is_favorite": favorite,
            "is_owner": bool(owner_ref and listing.owner_ref == owner_ref),
            "is_demo": listing.owner_ref.startswith("seed-demo"),
        })

    def list_listings(
        self,
        db: Session,
        *,
        owner_ref: str | None = None,
        listing_type: str | None = None,
        state: str | None = None,
        district: str | None = None,
        variety: str | None = None,
        search: str | None = None,
        sort: str = "newest",
        only_owner: bool = False,
        favorites_only: bool = False,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[ListingRead], str | None]:
        query = select(TradeListing).where(TradeListing.status == "ACTIVE")
        if listing_type:
            query = query.where(TradeListing.listing_type == listing_type.upper())
        if state:
            query = query.where(func.lower(TradeListing.state) == state.lower())
        if district:
            query = query.where(func.lower(TradeListing.district) == district.lower())
        if variety:
            query = query.where(func.lower(TradeListing.variety) == variety.lower())
        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    TradeListing.variety.ilike(term),
                    TradeListing.location.ilike(term),
                    TradeListing.district.ilike(term),
                    TradeListing.owner_name.ilike(term),
                    TradeListing.notes.ilike(term),
                )
            )
        if only_owner:
            if not owner_ref:
                raise HTTPException(status_code=401, detail="Demo user identity header is required")
            query = query.where(TradeListing.owner_ref == owner_ref)
        if favorites_only:
            if not owner_ref:
                raise HTTPException(status_code=401, detail="Demo user identity header is required")
            query = query.join(TradeFavorite, TradeFavorite.listing_id == TradeListing.id).where(
                TradeFavorite.owner_ref == owner_ref
            )

        if cursor and sort == "newest":
            created_at, listing_id = self._decode_cursor(cursor)
            query = query.where(
                or_(
                    TradeListing.created_at < created_at,
                    and_(TradeListing.created_at == created_at, TradeListing.id < listing_id),
                )
            )

        if sort == "price_low":
            query = query.order_by(TradeListing.price_per_quintal.asc(), TradeListing.id.desc())
        elif sort == "price_high":
            query = query.order_by(TradeListing.price_per_quintal.desc(), TradeListing.id.desc())
        elif sort == "quantity_high":
            query = query.order_by(TradeListing.quantity_kg.desc(), TradeListing.id.desc())
        else:
            query = query.order_by(TradeListing.created_at.desc(), TradeListing.id.desc())

        rows = list(db.scalars(query.limit(limit + 1)))
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [self._listing_read(db, item, owner_ref) for item in rows]
        next_cursor = self._cursor(rows[-1].created_at, rows[-1].id) if has_more and rows and sort == "newest" else None
        return items, next_cursor

    def create_listing(
        self,
        db: Session,
        payload: ListingCreate,
        owner_ref: str,
        idempotency_key: str | None,
    ) -> ListingRead:
        if idempotency_key:
            existing = db.scalar(select(TradeListing).where(TradeListing.idempotency_key == idempotency_key))
            if existing:
                if existing.owner_ref != owner_ref:
                    raise HTTPException(status_code=409, detail="Idempotency key already belongs to another request")
                return self._listing_read(db, existing, owner_ref)

        data = payload.model_dump()
        source_batch_id = data.pop("source_batch_id")
        quality_grade = None
        quality_score = None
        verified_quality = False
        size_class = data.get("size_class")

        if source_batch_id:
            batch = db.scalar(
                select(Batch)
                .where(Batch.id == source_batch_id)
                .options(selectinload(Batch.assessment))
            )
            if not batch:
                raise HTTPException(status_code=404, detail="Source batch not found")
            if not batch.assessment:
                raise HTTPException(status_code=409, detail="Analyze the source batch before publishing it")
            quality_grade = batch.assessment.quality_grade
            quality_score = batch.assessment.quality_score
            verified_quality = True
            size_class = size_class or str(batch.assessment.feature_summary.get("size_class") or "Relative size only")
            if payload.listing_type == "SELL":
                data["variety"] = batch.variety or data["variety"]
                data["quantity_kg"] = min(data["quantity_kg"], batch.quantity_kg)

        listing = TradeListing(
            listing_code=f"TB-{datetime.now(timezone.utc):%y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            owner_ref=owner_ref,
            source_batch_id=source_batch_id,
            quality_grade=quality_grade,
            quality_score=quality_score,
            verified_quality=verified_quality,
            size_class=size_class,
            idempotency_key=idempotency_key,
            **{k: v for k, v in data.items() if k != "size_class"},
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return self._listing_read(db, listing, owner_ref)

    def update_listing(
        self,
        db: Session,
        listing_id: int,
        payload: ListingUpdate,
        owner_ref: str,
    ) -> ListingRead:
        listing = db.get(TradeListing, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.owner_ref != owner_ref:
            raise HTTPException(status_code=403, detail="You can update only your own listing")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(listing, key, value)
        db.commit()
        db.refresh(listing)
        return self._listing_read(db, listing, owner_ref)

    def set_favorite(self, db: Session, listing_id: int, owner_ref: str, value: bool) -> bool:
        listing = db.get(TradeListing, listing_id)
        if not listing or listing.status != "ACTIVE":
            raise HTTPException(status_code=404, detail="Active listing not found")
        existing = db.scalar(
            select(TradeFavorite).where(
                TradeFavorite.owner_ref == owner_ref,
                TradeFavorite.listing_id == listing_id,
            )
        )
        if value and not existing:
            db.add(TradeFavorite(owner_ref=owner_ref, listing_id=listing_id))
        elif not value and existing:
            db.delete(existing)
        db.commit()
        return value

    @staticmethod
    def summary(db: Session) -> dict:
        buy = db.scalar(select(func.count(TradeListing.id)).where(TradeListing.status == "ACTIVE", TradeListing.listing_type == "BUY")) or 0
        sell = db.scalar(select(func.count(TradeListing.id)).where(TradeListing.status == "ACTIVE", TradeListing.listing_type == "SELL")) or 0
        verified = db.scalar(select(func.count(TradeListing.id)).where(TradeListing.status == "ACTIVE", TradeListing.verified_quality.is_(True))) or 0
        varieties = list(db.scalars(select(TradeListing.variety).where(TradeListing.status == "ACTIVE").distinct().order_by(TradeListing.variety)))
        states = list(db.scalars(select(TradeListing.state).where(TradeListing.status == "ACTIVE").distinct().order_by(TradeListing.state)))
        return {
            "active_buy_posts": buy,
            "active_sell_posts": sell,
            "verified_quality_posts": verified,
            "varieties": varieties,
            "states": states,
        }

    @staticmethod
    def cold_storage(db: Session, state: str | None = None, district: str | None = None, limit: int = 50) -> list[ColdStorageFacility]:
        query = select(ColdStorageFacility)
        if state:
            query = query.where(func.lower(ColdStorageFacility.state) == state.lower())
        if district:
            query = query.where(func.lower(ColdStorageFacility.district) == district.lower())
        return list(db.scalars(query.order_by(ColdStorageFacility.available_capacity_tonnes.desc()).limit(limit)))

    @staticmethod
    def transport(db: Session, state: str | None = None, district: str | None = None, limit: int = 50) -> list[TransportProvider]:
        query = select(TransportProvider)
        if state:
            query = query.where(func.lower(TransportProvider.state) == state.lower())
        if district:
            query = query.where(func.lower(TransportProvider.district) == district.lower())
        return list(db.scalars(query.order_by(TransportProvider.rate_per_km_tonne.asc()).limit(limit)))
