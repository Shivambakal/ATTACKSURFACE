"""AI-Powered Security News & Vulnerability Intelligence Collector.

Uses Google Gemini with Google Search Grounding to continuously collect,
validate, normalize, deduplicate, score, correlate, and persist public security
news, CVE disclosures, zero-days, and bug bounty developments.

IMPORTANT INVARIANTS:
1. Public observation and threat intelligence only.
2. AI-discovered news is EVIDENCE/CONTEXT, never proof of target compromise.
3. Every entry requires canonical source URLs and citations.
4. Complete auditability with raw response and grounding metadata preservation.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from google.protobuf.json_format import MessageToDict
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    Company,
    Product,
    ResearchSignal,
    SecurityAdvisory,
    SecurityIntelligenceEvent,
    SignalStatus,
    SignalType,
    Technology,
    TimelineEvent,
    utcnow,
)

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    from google.generativeai import protos
except ImportError:
    genai = None
    protos = None


class RawIntelligenceItem(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    summary: str = Field(..., min_length=5)
    event_type: str = Field(default="SECURITY_NEWS")
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    source_url: str = Field(default="https://www.cisa.gov")
    source_name: str = Field(default="Web")
    additional_sources: list[str] = Field(default_factory=list)
    cve_ids: list[str] = Field(default_factory=list)
    cwe_ids: list[str] = Field(default_factory=list)
    affected_products: list[str] = Field(default_factory=list)
    affected_companies: list[str] = Field(default_factory=list)
    severity: str = Field(default="UNKNOWN")
    actively_exploited: bool = Field(default=False)
    known_exploitation_evidence: Optional[str] = None
    security_relevance: Optional[str] = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class RawIntelligenceBatch(BaseModel):
    items: list[RawIntelligenceItem] = Field(default_factory=list)


def parse_iso_datetime(dt_str: str | None) -> datetime:
    """Safely parse an ISO-8601 datetime string with UTC fallback."""
    if not dt_str:
        return utcnow()
    try:
        cleaned = dt_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return utcnow()


def compute_fingerprint(source_name: str, source_url: str, cve_ids: list[str], title: str) -> str:
    """Generate deterministic canonical SHA-256 fingerprint for deduplication."""
    primary_cve = cve_ids[0].strip().upper() if cve_ids else ""
    norm_url = source_url.strip().lower()
    norm_title = title.strip().lower()
    norm_source = source_name.strip().lower()
    raw = f"{norm_source}|{norm_url}|{primary_cve}|{norm_title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_priority_scores(
    severity: str,
    actively_exploited: bool,
    has_exploitation_evidence: bool,
    published_at: datetime,
    has_cves: bool,
    has_entities: bool,
    confidence: float,
) -> dict[str, Any]:
    """Calculate multi-factor priority scores (0-100) and categorical priority."""
    # 1. Severity Score
    sev_map = {
        "CRITICAL": 95,
        "HIGH": 80,
        "MEDIUM": 50,
        "LOW": 20,
        "UNKNOWN": 35,
    }
    severity_score = sev_map.get(severity.upper(), 35)

    # 2. Exploitation Score
    if actively_exploited:
        exploitation_score = 100 if has_exploitation_evidence else 85
    else:
        exploitation_score = 0

    # 3. Freshness Score
    age_hours = (utcnow() - published_at).total_seconds() / 3600.0
    if age_hours <= 24:
        freshness_score = 100
    elif age_hours <= 48:
        freshness_score = 85
    elif age_hours <= 168:  # 7 days
        freshness_score = 65
    elif age_hours <= 720:  # 30 days
        freshness_score = 40
    else:
        freshness_score = 20

    # 4. Relevance Score
    rel_score = 40
    if has_cves:
        rel_score += 25
    if has_entities:
        rel_score += 20
    if confidence >= 0.8:
        rel_score += 15
    relevance_score = min(100, rel_score)

    # 5. Composite Priority Score
    composite = int(
        0.35 * severity_score
        + 0.30 * exploitation_score
        + 0.20 * freshness_score
        + 0.15 * relevance_score
    )
    priority_score = max(0, min(100, composite))

    # Priority category
    if priority_score >= 85 or (actively_exploited and severity_score >= 80):
        priority = "CRITICAL"
    elif priority_score >= 70:
        priority = "HIGH"
    elif priority_score >= 45:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return {
        "severity_score": severity_score,
        "freshness_score": freshness_score,
        "exploitation_score": exploitation_score,
        "relevance_score": relevance_score,
        "priority_score": priority_score,
        "priority": priority,
    }


class SecurityIntelligenceCollector:
    """Continuous AI-powered Security News & Vulnerability Intelligence collector."""

    DEFAULT_MODEL = "models/gemini-3.6-flash"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._init_sdk()

    def _init_sdk(self) -> None:
        """Configure Gemini SDK if API key is present."""
        if genai is not None and settings.gemini_api_key:
            try:
                genai.configure(api_key=settings.gemini_api_key)
            except Exception as exc:
                logger.warning("Failed to configure Google Generative AI SDK: %s", exc)

    def is_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(settings.gemini_api_key and genai is not None)

    def _build_intelligence_prompt(self, target_focus: str | None = None) -> str:
        """Construct a structured prompt guiding Gemini with Google Search grounding."""
        focus_clause = f"\nFocus specifically on security events relating to: {target_focus}." if target_focus else ""

        return f"""You are an elite, objective cybersecurity threat intelligence collector for AttackSurface Timeline.{focus_clause}

Search the public web right now for:
1. Newly disclosed CVEs (especially Critical, High, or Zero-Day) recently reported.
2. CISA Known Exploited Vulnerabilities (KEV) additions and actively exploited in-the-wild vulnerabilities.
3. Major vendor security advisories and critical security bulletins (Microsoft, Apple, Google, Cisco, Fortinet, Ivanti, Atlassian, Palo Alto, etc.).
4. Public bug bounty writeups, proof-of-concept exploits, and significant incident disclosures.

STRICT REQUIREMENTS:
- Use Google Search grounding to find REAL, VERIFIABLE recent security events with actual URLs.
- Never invent CVE numbers, product names, or dates.
- Extract canonical source URLs and names (e.g. CISA, BleepingComputer, The Hacker News, Dark Reading, vendor bulletins).
- Identify if the vulnerability is ACTIVELY EXPLOITED in the wild (set actively_exploited: true and provide evidence).
- Return ONLY a valid JSON object matching the schema below. Output nothing else.

SCHEMA:
{{
  "items": [
    {{
      "title": "Clear headline of the security disclosure",
      "summary": "Technical summary describing the vulnerability and impact",
      "event_type": "CVE | SECURITY_ADVISORY | EXPLOIT | BUG_BOUNTY | SECURITY_NEWS | INCIDENT | PATCH",
      "published_at": "YYYY-MM-DDTHH:MM:SSZ",
      "source_url": "https://...",
      "source_name": "Source publisher or vendor",
      "additional_sources": ["https://..."],
      "cve_ids": ["CVE-YYYY-NNNNN"],
      "cwe_ids": ["CWE-NNN"],
      "affected_products": ["Product Name"],
      "affected_companies": ["Vendor Name"],
      "severity": "CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN",
      "actively_exploited": true,
      "known_exploitation_evidence": "Evidence string if actively exploited, else null",
      "security_relevance": "Why this matters to attack surface researchers",
      "confidence": 0.95
    }}
  ]
}}
"""

    DEFAULT_MODELS = [
        "models/gemini-3.5-flash",
        "models/gemini-3.6-flash",
        "models/gemini-3.7-flash",
        "models/gemini-3.5-flash-lite",
    ]

    async def collect(
        self,
        db: Session,
        target_focus: str | None = None,
        max_items: int = 20,
    ) -> list[SecurityIntelligenceEvent]:
        """Execute search-grounded collection, validation, correlation, and persistence."""
        if not self.is_configured():
            logger.warning("Gemini AI is not configured. Skipping security intelligence collection.")
            return []

        prompt = self._build_intelligence_prompt(target_focus=target_focus)
        search_tool = protos.Tool(google_search=protos.Tool.GoogleSearch())

        models_to_try = [self.model_name] + [m for m in self.DEFAULT_MODELS if m != self.model_name]

        for model_id in models_to_try:
            try:
                model = genai.GenerativeModel(model_id, tools=[search_tool])
                logger.info("Executing Gemini Google Search grounded intelligence collection with %s...", model_id)
                response = await model.generate_content_async(prompt)
                events = self._process_model_response(response, db, max_items=max_items)
                if events:
                    return events
            except Exception as exc:
                if "429" in str(exc) or "ResourceExhausted" in type(exc).__name__:
                    logger.warning("Model %s exhausted quota, cascading to next model: %s", model_id, exc)
                    continue
                logger.error("Error during security intelligence collection with %s: %s", model_id, exc)
                break
        return []

    def collect_sync(
        self,
        db: Session,
        target_focus: str | None = None,
        max_items: int = 20,
    ) -> list[SecurityIntelligenceEvent]:
        """Synchronous version of collect for RQ worker jobs."""
        if not self.is_configured():
            logger.warning("Gemini AI is not configured. Skipping security intelligence collection.")
            return []

        prompt = self._build_intelligence_prompt(target_focus=target_focus)
        search_tool = protos.Tool(google_search=protos.Tool.GoogleSearch())

        models_to_try = [self.model_name] + [m for m in self.DEFAULT_MODELS if m != self.model_name]

        for model_id in models_to_try:
            try:
                model = genai.GenerativeModel(model_id, tools=[search_tool])
                logger.info("Executing synchronous Gemini collection with %s...", model_id)
                response = model.generate_content(prompt)
                events = self._process_model_response(response, db, max_items=max_items)
                if events:
                    return events
            except Exception as exc:
                if "429" in str(exc) or "ResourceExhausted" in type(exc).__name__:
                    logger.warning("Model %s exhausted quota, cascading to next model: %s", model_id, exc)
                    continue
                logger.error("Error during synchronous collection with %s: %s", model_id, exc)
                break
        return []

    def _extract_grounding_metadata(self, response: Any) -> dict[str, Any]:
        """Safely extract grounding metadata from Gemini response."""
        meta: dict[str, Any] = {"web_search_queries": [], "citations": []}
        try:
            if not hasattr(response, "candidates") or not response.candidates:
                return meta
            
            candidate = response.candidates[0]
            grounding_raw = getattr(candidate, "grounding_metadata", None)
            if not grounding_raw:
                return meta

            # Convert Protobuf message to Python dict
            try:
                meta = MessageToDict(grounding_raw._pb if hasattr(grounding_raw, "_pb") else grounding_raw)
            except Exception:
                # Fallback manual extraction
                queries = getattr(grounding_raw, "web_search_queries", [])
                meta["web_search_queries"] = list(queries)
                chunks = getattr(grounding_raw, "grounding_chunks", [])
                meta["grounding_chunks_count"] = len(chunks)
        except Exception as exc:
            logger.debug("Could not parse grounding metadata: %s", exc)
        return meta

    def _process_model_response(
        self,
        response: Any,
        db: Session,
        max_items: int = 20,
    ) -> list[SecurityIntelligenceEvent]:
        """Parse, validate, deduplicate, score, correlate, and persist response items."""
        text = getattr(response, "text", "") or ""
        grounding_meta = self._extract_grounding_metadata(response)

        # Parse JSON from response
        batch = self._extract_json_batch(text)
        if not batch or not batch.items:
            logger.warning("No structured intelligence items extracted from model response.")
            return []

        persisted_events: list[SecurityIntelligenceEvent] = []

        for item in batch.items[:max_items]:
            try:
                event = self._persist_single_item(item, grounding_meta, text, db)
                if event:
                    persisted_events.append(event)
            except Exception as exc:
                logger.warning("Error persisting intelligence item '%s': %s", item.title, exc)

        try:
            db.commit()
            logger.info("Successfully committed %d security intelligence events.", len(persisted_events))
        except Exception as exc:
            db.rollback()
            logger.error("Failed to commit security intelligence events: %s", exc)
            return []

        # Post-commit: generate timeline events / signals for high priority items
        self._correlate_and_emit_signals(persisted_events, db)

        return persisted_events

    def _extract_json_batch(self, text: str) -> RawIntelligenceBatch | None:
        """Extract, normalize, and validate RawIntelligenceBatch from raw text."""
        raw_obj: Any = None

        # 1. Regex search for ```json ... ``` code fence
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            try:
                raw_obj = json.loads(fence_match.group(1).strip())
            except Exception:
                pass

        # 2. Direct JSON load
        if raw_obj is None:
            try:
                raw_obj = json.loads(text.strip())
            except Exception:
                pass

        # 3. Outermost JSON object or list extraction
        if raw_obj is None:
            for open_char, close_char in [("{", "}"), ("[", "]")]:
                s = text.find(open_char)
                e = text.rfind(close_char)
                if s != -1 and e != -1 and e > s:
                    try:
                        raw_obj = json.loads(text[s : e + 1])
                        break
                    except Exception:
                        pass

        if raw_obj is None:
            logger.debug("Failed to extract JSON object or array from model text: %s", text[:200])
            return None

        # If model returned a bare list: [ {...}, {...} ]
        if isinstance(raw_obj, list):
            raw_obj = {"items": raw_obj}

        if not isinstance(raw_obj, dict) or "items" not in raw_obj or not isinstance(raw_obj["items"], list):
            return None

        normalized_items: list[dict[str, Any]] = []
        for raw_item in raw_obj["items"]:
            if not isinstance(raw_item, dict):
                continue

            # Resolve field aliases
            title = (
                raw_item.get("title")
                or raw_item.get("name")
                or raw_item.get("headline")
                or raw_item.get("cve_id")
                or "Security Vulnerability Disclosure"
            )
            summary = (
                raw_item.get("summary")
                or raw_item.get("description")
                or raw_item.get("details")
                or raw_item.get("impact")
                or title
            )
            cve_ids = raw_item.get("cve_ids") or []
            if not cve_ids and raw_item.get("cve_id"):
                cve_ids = [raw_item["cve_id"]]

            source_url = (
                raw_item.get("source_url")
                or raw_item.get("url")
                or raw_item.get("link")
                or raw_item.get("reference")
                or "https://www.cisa.gov"
            )
            source_name = (
                raw_item.get("source_name")
                or raw_item.get("source")
                or raw_item.get("vendor")
                or "Web"
            )
            published_at = (
                raw_item.get("published_at")
                or raw_item.get("published_date")
                or raw_item.get("date")
            )

            affected_products = raw_item.get("affected_products") or []
            if not affected_products and raw_item.get("product"):
                affected_products = [raw_item["product"]]

            affected_companies = raw_item.get("affected_companies") or []
            if not affected_companies and raw_item.get("company"):
                affected_companies = [raw_item["company"]]

            norm_entry = {
                "title": str(title).strip(),
                "summary": str(summary).strip(),
                "event_type": str(raw_item.get("event_type", "SECURITY_NEWS")).upper(),
                "published_at": str(published_at) if published_at else None,
                "updated_at": raw_item.get("updated_at"),
                "source_url": str(source_url).strip(),
                "source_name": str(source_name).strip(),
                "additional_sources": raw_item.get("additional_sources") or [],
                "cve_ids": [str(c) for c in cve_ids],
                "cwe_ids": [str(c) for c in (raw_item.get("cwe_ids") or [])],
                "affected_products": [str(p) for p in affected_products],
                "affected_companies": [str(c) for c in affected_companies],
                "severity": str(raw_item.get("severity", "UNKNOWN")).upper(),
                "actively_exploited": bool(raw_item.get("actively_exploited", False)),
                "known_exploitation_evidence": raw_item.get("known_exploitation_evidence"),
                "security_relevance": raw_item.get("security_relevance"),
                "confidence": float(raw_item.get("confidence", 0.8)),
            }
            normalized_items.append(norm_entry)

        return RawIntelligenceBatch.model_validate({"items": normalized_items})

    def _persist_single_item(
        self,
        item: RawIntelligenceItem,
        grounding_meta: dict[str, Any],
        raw_text: str,
        db: Session,
    ) -> SecurityIntelligenceEvent | None:
        """Validate, deduplicate, score, and persist a single intelligence item."""
        published_dt = parse_iso_datetime(item.published_at)
        updated_dt = parse_iso_datetime(item.updated_at) if item.updated_at else None

        fingerprint = compute_fingerprint(
            item.source_name, item.source_url, item.cve_ids, item.title
        )

        # Check existing record
        existing = db.execute(
            select(SecurityIntelligenceEvent).where(
                SecurityIntelligenceEvent.fingerprint == fingerprint
            )
        ).scalar_one_or_none()

        scores = compute_priority_scores(
            severity=item.severity,
            actively_exploited=item.actively_exploited,
            has_exploitation_evidence=bool(item.known_exploitation_evidence),
            published_at=published_dt,
            has_cves=bool(item.cve_ids),
            has_entities=bool(item.affected_companies or item.affected_products),
            confidence=item.confidence,
        )

        # Correlate with entities
        correlated_companies = self._correlate_companies(item.affected_companies, db)
        correlated_products = self._correlate_products(item.affected_products, db)
        correlated_technologies = self._correlate_technologies(item.affected_products, db)
        correlated_advisories = self._correlate_advisories(item.cve_ids, db)

        if existing:
            # Update existing record with refreshed intelligence
            existing.updated_at = updated_dt or utcnow()
            existing.summary = item.summary
            existing.severity = item.severity.upper()
            existing.actively_exploited = item.actively_exploited or existing.actively_exploited
            if item.known_exploitation_evidence:
                existing.known_exploitation_evidence = item.known_exploitation_evidence
            existing.priority_score = max(existing.priority_score, scores["priority_score"])
            existing.priority = scores["priority"]
            existing.grounding_metadata = grounding_meta
            existing.correlated_company_ids = list(
                set(existing.correlated_company_ids + correlated_companies)
            )
            existing.correlated_product_ids = list(
                set(existing.correlated_product_ids + correlated_products)
            )
            existing.correlated_technology_ids = list(
                set(existing.correlated_technology_ids + correlated_technologies)
            )
            existing.correlated_advisory_ids = list(
                set(existing.correlated_advisory_ids + correlated_advisories)
            )
            return existing

        # Create new record
        event = SecurityIntelligenceEvent(
            title=item.title,
            summary=item.summary,
            event_type=item.event_type.upper(),
            published_at=published_dt,
            updated_at=updated_dt,
            source_url=item.source_url,
            source_name=item.source_name,
            additional_sources=item.additional_sources,
            cve_ids=item.cve_ids,
            cwe_ids=item.cwe_ids,
            affected_products=item.affected_products,
            affected_companies=item.affected_companies,
            severity=item.severity.upper(),
            actively_exploited=item.actively_exploited,
            known_exploitation_evidence=item.known_exploitation_evidence,
            security_relevance=item.security_relevance,
            confidence=item.confidence,
            fingerprint=fingerprint,
            parser_version="1.0.0",
            severity_score=scores["severity_score"],
            freshness_score=scores["freshness_score"],
            exploitation_score=scores["exploitation_score"],
            relevance_score=scores["relevance_score"],
            priority_score=scores["priority_score"],
            priority=scores["priority"],
            grounding_metadata=grounding_meta,
            raw_model_response={"raw_item": item.model_dump(), "model": self.model_name},
            correlated_company_ids=correlated_companies,
            correlated_product_ids=correlated_products,
            correlated_technology_ids=correlated_technologies,
            correlated_advisory_ids=correlated_advisories,
        )
        db.add(event)
        return event

    def _correlate_companies(self, company_names: list[str], db: Session) -> list[int]:
        """Find matching Company IDs in database."""
        if not company_names:
            return []
        matched_ids: list[int] = []
        for name in company_names:
            clean = name.strip()
            if not clean:
                continue
            companies = db.execute(
                select(Company.id).where(Company.name.ilike(f"%{clean}%"))
            ).scalars().all()
            matched_ids.extend(companies)
        return list(set(matched_ids))

    def _correlate_products(self, product_names: list[str], db: Session) -> list[int]:
        """Find matching Product IDs in database."""
        if not product_names:
            return []
        matched_ids: list[int] = []
        for name in product_names:
            clean = name.strip()
            if not clean:
                continue
            products = db.execute(
                select(Product.id).where(Product.name.ilike(f"%{clean}%"))
            ).scalars().all()
            matched_ids.extend(products)
        return list(set(matched_ids))

    def _correlate_technologies(self, product_names: list[str], db: Session) -> list[int]:
        """Find matching Technology IDs in database."""
        if not product_names:
            return []
        matched_ids: list[int] = []
        for name in product_names:
            clean = name.strip()
            if not clean:
                continue
            techs = db.execute(
                select(Technology.id).where(Technology.name.ilike(f"%{clean}%"))
            ).scalars().all()
            matched_ids.extend(techs)
        return list(set(matched_ids))

    def _correlate_advisories(self, cve_ids: list[str], db: Session) -> list[int]:
        """Find matching SecurityAdvisory IDs in database."""
        if not cve_ids:
            return []
        clean_cves = [c.strip().upper() for c in cve_ids if c.strip()]
        if not clean_cves:
            return []
        advisories = db.execute(
            select(SecurityAdvisory.id).where(SecurityAdvisory.cve_id.in_(clean_cves))
        ).scalars().all()
        return list(set(advisories))

    def _correlate_and_emit_signals(
        self, events: list[SecurityIntelligenceEvent], db: Session
    ) -> None:
        """Emit TimelineEvent and ResearchSignal for high priority correlated events."""
        if not events:
            return

        try:
            for event in events:
                if event.priority not in ("CRITICAL", "HIGH") and not event.actively_exploited:
                    continue

                for company_id in event.correlated_company_ids:
                    # Check company exists
                    company = db.get(Company, company_id)
                    if not company:
                        continue

                    # Find company primary target if exists
                    target_id = None
                    if company.targets:
                        target_id = company.targets[0].id

                    # Create timeline event if target exists
                    if target_id:
                        timeline_event = TimelineEvent(
                            target_id=target_id,
                            event_type="SECURITY_NEWS" if event.event_type != "CVE" else "SECURITY_ADVISORY",
                            title=f"[Intelligence] {event.title[:200]}",
                            summary=(
                                f"Public intelligence alert ({event.source_name}): {event.summary}\n"
                                f"[NOTE: Contextual intelligence observation; not confirmed target exploitation.]"
                            ),
                            source=f"AI Intelligence ({event.source_name})",
                            source_url=event.source_url,
                            observed_at=utcnow(),
                            published_at=event.published_at,
                            confidence=event.confidence,
                            relevance_score=event.priority_score,
                            priority=event.priority,
                        )
                        db.add(timeline_event)

                    # Create ResearchSignal
                    signal = ResearchSignal(
                        company_id=company.id,
                        target_id=target_id,
                        signal_type=SignalType.HIGH_RISK_SURFACE if event.actively_exploited else SignalType.EXPOSURE_RISK,
                        title=f"External Intel: {event.title[:255]}",
                        description=(
                            f"{event.summary}\n\n"
                            f"Source: {event.source_name} ({event.source_url})\n"
                            f"Severity: {event.severity} | Priority: {event.priority} | "
                            f"Actively Exploited: {event.actively_exploited}"
                        ),
                        confidence=event.confidence,
                        severity=event.severity if event.severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "MEDIUM",
                        status=SignalStatus.ACTIVE,
                        evidence_sources=[event.source_url] + (event.additional_sources or []),
                        dedup_hash=f"intel_{event.fingerprint}_{company.id}",
                    )
                    db.add(signal)

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.debug("Failed to emit signals for correlated intelligence: %s", exc)
