from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ListingType = Literal["BUY", "SELL"]
ListingStatus = Literal["ACTIVE", "CLOSED"]


class ListingCreate(BaseModel):
    listing_type: ListingType
    owner_name: str = Field(min_length=2, max_length=120)
    contact_phone: str | None = Field(default=None, max_length=24)
    variety: str = Field(min_length=1, max_length=80)
    quantity_kg: float = Field(gt=0, le=2_000_000)
    price_per_quintal: float = Field(gt=0, le=100_000)
    state: str = Field(min_length=2, max_length=80)
    district: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=2, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)
    source_batch_id: int | None = Field(default=None, gt=0)
    size_class: str | None = Field(default=None, max_length=64)


class ListingUpdate(BaseModel):
    price_per_quintal: float | None = Field(default=None, gt=0, le=100_000)
    quantity_kg: float | None = Field(default=None, gt=0, le=2_000_000)
    notes: str | None = Field(default=None, max_length=2000)
    status: ListingStatus | None = None
    size_class: str | None = Field(default=None, max_length=64)


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_code: str
    listing_type: str
    owner_name: str
    contact_phone: str | None
    variety: str
    quantity_kg: float
    price_per_quintal: float
    state: str
    district: str
    location: str
    notes: str | None
    status: str
    source_batch_id: int | None
    quality_grade: str | None
    quality_score: float | None
    size_class: str | None
    verified_quality: bool
    created_at: datetime
    updated_at: datetime
    is_favorite: bool = False
    is_owner: bool = False
    is_demo: bool = False


class ListingPage(BaseModel):
    items: list[ListingRead]
    next_cursor: str | None = None
    total_returned: int


class MarketplaceSummary(BaseModel):
    active_buy_posts: int
    active_sell_posts: int
    verified_quality_posts: int
    varieties: list[str]
    states: list[str]


class FavoriteResponse(BaseModel):
    listing_id: int
    favorite: bool


class ColdStorageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    district: str
    location: str
    total_capacity_tonnes: float
    available_capacity_tonnes: float
    estimated_cost_per_quintal_day: float
    phone: str | None
    source: str
    verified: bool


class TransportProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    district: str
    base_location: str
    vehicle_types: list[str]
    rate_per_km_tonne: float
    phone: str | None
    source: str
    verified: bool
