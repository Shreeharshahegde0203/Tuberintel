from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import NewsArticle


class NewsService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _strip_html(value: str | None) -> str:
        text = re.sub(r"<[^>]+>", " ", value or "")
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _published(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _category(title: str, summary: str) -> str:
        text = f"{title} {summary}".lower()
        groups = [
            ("Market", ("price", "mandi", "market", "trade", "export", "import")),
            ("Weather", ("weather", "rain", "temperature", "flood", "drought")),
            ("Government", ("government", "scheme", "subsidy", "ministry", "policy")),
            ("Storage", ("storage", "warehouse", "cold store", "cold storage")),
            ("Research", ("research", "study", "scientist", "variety", "breeding")),
            ("Disease", ("blight", "disease", "rot", "virus", "pest")),
            ("Processing", ("processing", "chips", "fries", "starch")),
        ]
        for label, keywords in groups:
            if any(keyword in text for keyword in keywords):
                return label
        return "Potato industry"

    @staticmethod
    def _text(node: ET.Element, names: tuple[str, ...]) -> str:
        for child in node.iter():
            tag = child.tag.split("}")[-1].lower()
            if tag in names and child.text:
                return child.text.strip()
        return ""

    @staticmethod
    def _link(node: ET.Element) -> str:
        for child in node.iter():
            tag = child.tag.split("}")[-1].lower()
            if tag != "link":
                continue
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if child.text:
                return child.text.strip()
        return ""

    def _parse_feed(self, content: bytes) -> list[dict[str, str | datetime | None]]:
        root = ET.fromstring(content)
        entries = [node for node in root.iter() if node.tag.split("}")[-1].lower() in {"item", "entry"}]
        output: list[dict[str, str | datetime | None]] = []
        for entry in entries:
            title = self._strip_html(self._text(entry, ("title",)))
            url = self._link(entry)
            summary = self._strip_html(self._text(entry, ("description", "summary", "content")))[:1200]
            published_raw = self._text(entry, ("pubdate", "published", "updated"))
            source = self._strip_html(self._text(entry, ("source",)))
            if not source:
                source = urlparse(url).netloc.replace("www.", "") or "Potato industry source"
            if title and url:
                output.append(
                    {
                        "title": title,
                        "url": url,
                        "summary": summary,
                        "published_at": self._published(published_raw),
                        "source": source,
                    }
                )
        return output

    def needs_refresh(self, db: Session) -> bool:
        latest = db.scalar(select(NewsArticle.fetched_at).order_by(desc(NewsArticle.fetched_at)).limit(1))
        if not latest:
            return True
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - latest >= timedelta(minutes=self.settings.news_cache_minutes)

    def refresh(self, db: Session, limit_per_feed: int = 30) -> dict[str, object]:
        received = inserted = updated = 0
        errors: list[str] = []
        seen_urls: set[str] = set()

        try:
            with httpx.Client(
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": "TuberIntel/1.0"},
            ) as client:
                for feed_url in self.settings.news_feed_urls:
                    try:
                        response = client.get(feed_url)
                        response.raise_for_status()
                        entries = self._parse_feed(response.content)
                    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
                        errors.append(f"{feed_url}: {exc}")
                        continue

                    for entry in entries[:limit_per_feed]:
                        raw_url = str(entry["url"] or "").strip()

                        if not raw_url:
                            continue

                        # The database column stores at most 1000 characters.
                        # Use exactly the same value for lookup and insertion.
                        stored_url = raw_url[:1000]

                        # Google News can return the same article from multiple
                        # RSS feeds during one refresh. Avoid queueing it twice.
                        if stored_url in seen_urls:
                            continue

                        seen_urls.add(stored_url)
                        received += 1

                        title = str(entry["title"] or "")
                        summary = str(entry["summary"] or "")
                        source = str(entry["source"] or "Potato industry source")

                        row = db.scalar(
                            select(NewsArticle).where(NewsArticle.url == stored_url)
                        )

                        values = {
                            "source": source[:140],
                            "title": title[:500],
                            "summary": summary,
                            "category": self._category(title, summary),
                            "language": "en",
                            "published_at": entry["published_at"],
                            "fetched_at": datetime.now(timezone.utc),
                        }

                        if row:
                            for key, value in values.items():
                                setattr(row, key, value)
                            updated += 1
                        else:
                            db.add(
                                NewsArticle(
                                    url=stored_url,
                                    image_url=None,
                                    **values,
                                )
                            )
                            inserted += 1

            db.commit()

        except Exception:
            db.rollback()
            raise

        return {
            "received": received,
            "inserted": inserted,
            "updated": updated,
            "errors": errors,
            "live_data": received > 0,
            "note": "Potato-news headlines refreshed. Full articles remain on the original publisher websites.",
        }

    def list(
        self,
        db: Session,
        *,
        category: str | None = None,
        search: str | None = None,
        limit: int = 30,
        auto_refresh: bool = True,
    ) -> dict[str, object]:
        note = "Showing cached potato-industry headlines."
        live_data = False
        if auto_refresh and self.needs_refresh(db):
            try:
                result = self.refresh(db)
                live_data = bool(result["live_data"])
                note = str(result["note"])
                if result["errors"]:
                    note += " Some sources were temporarily unavailable."
            except Exception as exc:
                db.rollback()
                note = f"Live news refresh was unavailable; showing cached headlines. {exc}"

        conditions = []
        if category:
            conditions.append(NewsArticle.category == category)
        if search:
            conditions.append(NewsArticle.title.ilike(f"%{search.strip()}%"))
        query = select(NewsArticle)
        if conditions:
            query = query.where(*conditions)
        query = query.order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc()).limit(min(max(limit, 1), 100))
        articles = list(db.scalars(query))
        categories = [str(v) for v in db.scalars(select(NewsArticle.category).distinct().order_by(NewsArticle.category)) if v]
        sources = [str(v) for v in db.scalars(select(NewsArticle.source).distinct().order_by(NewsArticle.source)) if v]
        freshest = max((a.fetched_at for a in articles), default=None)
        return {
            "articles": articles,
            "categories": categories,
            "sources": sources,
            "freshness": freshest.isoformat() if freshest else "unavailable",
            "live_data": live_data or bool(articles),
            "note": note,
        }
