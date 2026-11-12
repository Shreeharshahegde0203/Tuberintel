from datetime import date, timedelta
import math

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models import ColdStorageFacility, MarketPrice, TradeListing, TransportProvider
from app.services.market_service import MarketService


# Development-only demonstration series. The UI labels it as demo data. Production
# deployments should configure DATA_GOV_API_KEY and refresh the official feed.
SEED_MARKETS = [
    ("Karnataka", "Bengaluru", "Binny Mill (F&V), Bengaluru", "Local", 2050),
    ("Karnataka", "Kolar", "Kolar APMC", "Local", 1980),
    ("Karnataka", "Chikkaballapur", "Chikkaballapur APMC", "Local", 1940),
    ("Karnataka", "Belagavi", "Belagavi APMC", "Local", 1840),
    ("Uttar Pradesh", "Agra", "Agra APMC", "Chipsona", 1510),
    ("Uttar Pradesh", "Kanpur", "Kanpur APMC", "Kufri Jyoti", 1460),
    ("Gujarat", "Ahmedabad", "Ahmedabad APMC", "Badshah", 1480),
    ("Gujarat", "Banaskantha", "Deesa APMC", "LR", 1450),
    ("Madhya Pradesh", "Indore", "Indore APMC", "Kufri Jyoti", 1470),
    ("Punjab", "Jalandhar", "Jalandhar City", "Kufri Pukhraj", 1540),
    ("West Bengal", "Hooghly", "Sheoraphuli", "Jyoti", 1620),
    ("Bihar", "Patna", "Patna City", "Kufri Sindhuri", 1580),
]


def _seed_marketplace(db) -> None:
    if not db.scalar(select(TradeListing.id).limit(1)):
        demo_posts = [
            ("SELL", "seed-demo-kolar", "Kolar Grower Collective", "Kufri Jyoti", 8200, 2120, "Karnataka", "Kolar", "Kolar APMC belt", "Fresh demonstration lot; contact details are intentionally omitted."),
            ("BUY", "seed-demo-bengaluru", "Bengaluru Chips Buyer", "Chipsona", 12000, 2250, "Karnataka", "Bengaluru Urban", "Yeshwanthpur", "Looking for processing-size potatoes. Demonstration buyer post."),
            ("SELL", "seed-demo-chikkaballapur", "Chikkaballapur Farmer Group", "Local", 6500, 1980, "Karnataka", "Chikkaballapur", "Chikkaballapur", "Demo seller post. Quality is not TuberIntel-verified."),
            ("BUY", "seed-demo-agra", "Agra Bulk Buyer", "Chipsona", 20000, 1650, "Uttar Pradesh", "Agra", "Agra", "Demo bulk requirement."),
            ("SELL", "seed-demo-deesa", "Deesa Potato Farmer", "LR", 15000, 1580, "Gujarat", "Banaskantha", "Deesa", "Demo listing for marketplace discovery."),
        ]
        for listing_type, owner_ref, owner_name, variety, qty, price, state, district, location, notes in demo_posts:
            db.add(TradeListing(
                listing_code=f"DEMO-{listing_type}-{len(db.new)+1:03d}", listing_type=listing_type,
                owner_ref=owner_ref, owner_name=owner_name, contact_phone=None, variety=variety,
                quantity_kg=qty, price_per_quintal=price, state=state, district=district,
                location=location, notes=notes, status="ACTIVE", verified_quality=False,
                size_class="Buyer specification required",
            ))

    if not db.scalar(select(ColdStorageFacility.id).limit(1)):
        facilities = [
            ("Kolar Demo Cold Store", "Karnataka", "Kolar", "Kolar industrial area", 4200, 1250, 7.5),
            ("Chikkaballapur Demo Cold Store", "Karnataka", "Chikkaballapur", "Near APMC", 2800, 760, 8.0),
            ("Bengaluru Rural Demo Storage", "Karnataka", "Bengaluru Rural", "Doddaballapur road", 5000, 1800, 8.8),
        ]
        for name, state, district, location, total, available, cost in facilities:
            db.add(ColdStorageFacility(name=name, state=state, district=district, location=location,
                total_capacity_tonnes=total, available_capacity_tonnes=available,
                estimated_cost_per_quintal_day=cost, phone=None, verified=False))

    if not db.scalar(select(TransportProvider.id).limit(1)):
        providers = [
            ("Kolar Demo Farm Logistics", "Karnataka", "Kolar", "Kolar", ["LCV", "10T truck"], 42.0),
            ("Bengaluru Demo Produce Transport", "Karnataka", "Bengaluru Urban", "Yeshwanthpur", ["Pickup", "14T truck"], 46.0),
            ("Chikkaballapur Demo Haulage", "Karnataka", "Chikkaballapur", "APMC Road", ["LCV", "6T truck"], 40.0),
        ]
        for name, state, district, location, vehicles, rate in providers:
            db.add(TransportProvider(name=name, state=state, district=district, base_location=location,
                vehicle_types=vehicles, rate_per_km_tonne=rate, phone=None, verified=False))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    market_service = MarketService()
    with SessionLocal() as db:
        market_service.seed_state_directory(db)
        db.commit()
        market_service.bootstrap_directory_from_prices(db)
        if get_settings().environment != "production":
            _seed_marketplace(db)
        db.commit()
