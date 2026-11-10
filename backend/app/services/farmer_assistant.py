from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import Batch, TradeListing
from app.services.market_service import MarketService


_TOKEN_RE = re.compile(r"[a-zA-Z0-9₹]+|[\u0C80-\u0CFF]+")


class FarmerAssistantService:
    def __init__(self) -> None:
        self.settings = get_settings()
        kb_path = Path(__file__).resolve().parents[1] / "data" / "farmer_kb.json"
        self.docs: list[dict[str, Any]] = json.loads(kb_path.read_text(encoding="utf-8"))
        self.market_service = MarketService()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token.lower() for token in _TOKEN_RE.findall(text)]

    def _retrieve(self, message: str, k: int = 3) -> list[dict[str, Any]]:
        query = Counter(self._tokens(message))
        scores: list[tuple[float, dict[str, Any]]] = []
        for doc in self.docs:
            document_text = " ".join([doc["title"], " ".join(doc.get("keywords", [])), doc["answer_en"], doc["answer_kn"]])
            doc_tokens = Counter(self._tokens(document_text))
            overlap = 0.0
            for token, q_count in query.items():
                if token in doc_tokens:
                    overlap += q_count * (1.0 + math.log1p(doc_tokens[token]))
                    if token in [str(x).lower() for x in doc.get("keywords", [])]:
                        overlap += 2.2
            scores.append((overlap, doc))
        scores.sort(key=lambda item: item[0], reverse=True)
        selected = [doc for score, doc in scores[:k] if score > 0]
        return selected or [next(doc for doc in self.docs if doc["id"] == "quality-grading")]

    def _context(self, db: Session, batch_id: int | None, state: str | None, district: str | None) -> tuple[list[str], list[dict[str, str]]]:
        facts: list[str] = []
        sources: list[dict[str, str]] = []
        if batch_id:
            batch = db.scalar(
                select(Batch)
                .where(Batch.id == batch_id)
                .options(selectinload(Batch.assessment), selectinload(Batch.recommendation))
            )
            if batch:
                if batch.assessment:
                    facts.append(
                        f"Batch {batch.batch_code}: {batch.variety}, {batch.quantity_kg:.0f} kg, "
                        f"grade {batch.assessment.quality_grade}, quality {batch.assessment.quality_score:.1f}/100, "
                        f"rejection probability {batch.assessment.rejection_probability:.1f}%."
                    )
                if batch.recommendation:
                    facts.append(
                        f"TuberIntel recommendation for this batch: {batch.recommendation.recommended_action} at/through "
                        f"{batch.recommendation.recommended_market}; expected net operating profit ₹{batch.recommendation.expected_net_profit:,.0f}."
                    )
                sources.append({"title": batch.batch_code, "kind": "batch", "detail": "Your analyzed TuberIntel batch"})

        chosen_state = state or "Karnataka"
        prices = self.market_service.latest_prices(db, state=chosen_state)
        if district:
            prices = [item for item in prices if item.district.lower() == district.lower()]
        if prices:
            top = sorted(prices, key=lambda item: item.modal_price, reverse=True)[:3]
            facts.append(
                "Latest available price records: "
                + "; ".join(f"{item.market} ₹{item.modal_price:,.0f}/q ({item.variety})" for item in top)
                + "."
            )
            source_kind = "live_market" if any("data.gov.in" in item.source.lower() for item in top) else "demo_market"
            sources.append({"title": "Mandi price context", "kind": source_kind, "detail": f"Latest available records for {chosen_state}"})

        listings = list(
            db.scalars(
                select(TradeListing)
                .where(TradeListing.status == "ACTIVE")
                .order_by(TradeListing.created_at.desc())
                .limit(5)
            )
        )
        if listings:
            facts.append(
                "Recent trade posts: "
                + "; ".join(
                    f"{item.listing_type} {item.variety} {item.quantity_kg / 100:.1f} q at ₹{item.price_per_quintal:,.0f}/q in {item.district}"
                    for item in listings[:3]
                )
                + "."
            )
            sources.append({"title": "Trade board", "kind": "marketplace", "detail": "Recent active TuberIntel buy/sell posts"})
        return facts, sources

    @staticmethod
    def _suggestions(language: str) -> list[str]:
        if language == "kn":
            return ["ಈ ಬ್ಯಾಚ್ ಈಗ ಮಾರಬೇಕಾ?", "ಕೋಲ್ಡ್ ಸ್ಟೋರೇಜ್ ಲಾಭದಾಯಕವೇ?", "ನನ್ನ ಲಾಟ್‌ಗೆ ಸರಿಯಾದ ಗ್ರೇಡ್ ಯಾವುದು?"]
        return ["Should I sell this batch now?", "Is cold storage profitable for this lot?", "How is my quality grade calculated?"]

    def _local_answer(self, docs: list[dict[str, Any]], facts: list[str], language: str) -> str:
        parts = [doc["answer_kn" if language == "kn" else "answer_en"] for doc in docs[:2]]
        if facts:
            context_label = "ನಿಮ್ಮ ಪ್ರಸ್ತುತ TuberIntel ಡೇಟಾ: " if language == "kn" else "From your current TuberIntel data: "
            parts.append(context_label + " ".join(facts[:2]))
        return "\n\n".join(parts)

    async def _openai_answer(self, message: str, docs: list[dict[str, Any]], facts: list[str], language: str) -> str | None:
        if not self.settings.openai_api_key:
            return None
        context = "\n\n".join(
            [f"KNOWLEDGE: {doc['title']}\n{doc['answer_en']}" for doc in docs]
            + [f"SYSTEM FACT: {fact}" for fact in facts]
        )
        instructions = (
            "You are Tuber Mitra, a concise farmer-facing potato decision assistant inside TuberIntel. "
            "Answer only from the supplied context. Never fabricate live prices, disease diagnosis, buyer acceptance, or official grades. "
            "If context is insufficient, say what must be measured or checked. Prefer practical next steps. "
            + ("Reply in Kannada." if language == "kn" else "Reply in clear Indian English.")
        )
        payload = {
            "model": self.settings.openai_model,
            "store": False,
            "instructions": instructions,
            "input": f"CONTEXT\n{context}\n\nFARMER QUESTION\n{message}",
        }
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                if data.get("output_text"):
                    return str(data["output_text"]).strip()
                chunks: list[str] = []
                for item in data.get("output", []):
                    for content in item.get("content", []):
                        if content.get("type") == "output_text" and content.get("text"):
                            chunks.append(str(content["text"]))
                return "\n".join(chunks).strip() or None
        except Exception:
            return None

    async def answer(
        self,
        db: Session,
        *,
        message: str,
        language: str,
        batch_id: int | None,
        state: str | None,
        district: str | None,
    ) -> dict[str, Any]:
        docs = self._retrieve(message)
        facts, dynamic_sources = self._context(db, batch_id, state, district)
        answer = await self._openai_answer(message, docs, facts, language)
        mode = "openai_grounded" if answer else "local_grounded"
        if not answer:
            answer = self._local_answer(docs, facts, language)
        sources = [
            {"title": doc["title"], "kind": "knowledge_base", "detail": f"Local TuberIntel guidance: {doc['id']}"}
            for doc in docs
        ] + dynamic_sources
        disclaimer = (
            "ಇದು ನಿರ್ಧಾರ ಸಹಾಯ ಮಾತ್ರ; ತುರ್ತು ಬೆಳೆ ರೋಗ/ರಾಸಾಯನಿಕ ಚಿಕಿತ್ಸೆಗಾಗಿ ಸ್ಥಳೀಯ ಕೃಷಿ ತಜ್ಞರನ್ನು ಸಂಪರ್ಕಿಸಿ."
            if language == "kn"
            else "Decision support only. For urgent crop disease or chemical-treatment decisions, confirm with a local agronomist or official advisory."
        )
        return {
            "answer": answer,
            "mode": mode,
            "sources": sources[:6],
            "suggestions": self._suggestions(language),
            "disclaimer": disclaimer,
        }
