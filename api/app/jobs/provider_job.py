"""Provider data refresh background job.

Enables on-demand or periodic re-fetching of intelligence records from specific
external providers (e.g. GitHub, OSV, CISA KEV, NVD) for an established target.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from app.db import SessionLocal
from app.models.base import utcnow
from app.models import Target, Evidence, TimelineEvent, SecurityEvent, Alert
from app.services.provider_manager import get_provider_manager

logger = logging.getLogger(__name__)


def refresh_provider_data(target_id: int, provider_name: str) -> dict[str, Any]:
    """RQ background job to fetch fresh data from a specific provider for a target.

    Queries the designated external data provider, normalizes records, creates
    immutable Evidence records, links Timeline events, and triggers alerts if necessary.
    """
    logger.info(
        "Starting provider refresh job for target_id=%d, provider='%s'",
        target_id,
        provider_name,
    )
    db = SessionLocal()

    try:
        target = db.get(Target, target_id)
        if not target:
            logger.warning("Target %d not found during provider refresh", target_id)
            return {"status": "error", "message": f"Target {target_id} not found."}

        pm = get_provider_manager()
        provider = pm.get_provider(provider_name)
        if not provider:
            logger.warning("Provider '%s' not registered", provider_name)
            return {"status": "error", "message": f"Provider '{provider_name}' not registered."}

        if not provider.is_configured():
            logger.info("Provider '%s' is not configured; skipping refresh", provider_name)
            return {"status": "skipped", "message": f"Provider '{provider_name}' not configured."}

        # Run provider fetch in asyncio loop
        domain = target.domain.strip().lower()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                records = pool.submit(
                    asyncio.run, provider.fetch(target=domain, limit=20)
                ).result()
        else:
            records = asyncio.run(provider.fetch(target=domain, limit=20))

        created_evidences: list[Evidence] = []
        created_events: list[TimelineEvent] = []

        for rec in records:
            chash = rec.content_hash or hashlib.sha256(
                f"{rec.source}:{rec.source_url}:{rec.title}".encode()
            ).hexdigest()

            # Ensure evidence record exists
            evidence = (
                db.query(Evidence)
                .filter(Evidence.target_id == target.id, Evidence.content_hash == chash)
                .first()
            )
            if not evidence:
                evidence = Evidence(
                    target_id=target.id,
                    source=rec.source,
                    source_url=rec.source_url,
                    retrieved_at=rec.observed_at or utcnow(),
                    content_hash=chash,
                    evidence_type=rec.event_type,
                    excerpt=rec.summary[:1000],
                )
                evidence.metadata = rec.metadata
                db.add(evidence)
                db.flush()
                created_evidences.append(evidence)

            # Determine event priority
            is_vuln = rec.event_type in (
                "vulnerability",
                "known_exploited_vulnerability",
                "advisory",
            )
            priority = "CRITICAL" if rec.event_type == "known_exploited_vulnerability" else (
                "HIGH" if is_vuln else "INFO"
            )
            rel_score = 90 if priority == "CRITICAL" else (75 if priority == "HIGH" else 40)

            # Create or update security event if CVE is present
            cve_id = rec.metadata.get("cve_id") or (
                rec.evidence_reference if rec.evidence_reference.startswith("CVE-") else None
            )
            if cve_id:
                sec_ev = (
                    db.query(SecurityEvent)
                    .filter(
                        SecurityEvent.target_id == target.id,
                        SecurityEvent.cve_id == cve_id,
                    )
                    .first()
                )
                if not sec_ev:
                    sec_ev = SecurityEvent(
                        target_id=target.id,
                        cve_id=cve_id,
                        source=rec.source,
                        severity=rec.metadata.get("severity") or priority,
                        summary=rec.summary,
                        published=rec.published_at,
                        references=rec.metadata.get("references", []),
                    )
                    sec_ev.metadata = rec.metadata
                    db.add(sec_ev)

            # Create Timeline event
            timeline_ev = TimelineEvent(
                target_id=target.id,
                event_type=f"{rec.source}_{rec.event_type}",
                title=rec.title,
                summary=rec.summary,
                source=rec.source,
                source_url=rec.source_url,
                observed_at=rec.observed_at or utcnow(),
                published_at=rec.published_at,
                confidence=0.9,
                relevance_score=rel_score,
                priority=priority,
                evidence_ids=[evidence.id] if evidence else [],
            )
            timeline_ev.metadata = rec.metadata
            db.add(timeline_ev)
            created_events.append(timeline_ev)

            # Trigger alert for CRITICAL / HIGH findings
            if target.user_id and priority in ("CRITICAL", "HIGH"):
                alert = Alert(
                    user_id=target.user_id,
                    alert_type=timeline_ev.event_type,
                    entity_type="timeline_event",
                    entity_id=timeline_ev.id,
                    title=timeline_ev.title[:255],
                    summary=timeline_ev.summary,
                    priority=priority,
                    read=False,
                    created_at=utcnow(),
                )
                db.add(alert)

        db.commit()
        logger.info(
            "Provider '%s' refresh complete for target_id=%d: %d records, %d new events",
            provider_name,
            target_id,
            len(records),
            len(created_events),
        )

        return {
            "status": "complete",
            "target_id": target_id,
            "provider": provider_name,
            "records_fetched": len(records),
            "events_created": len(created_events),
            "evidence_created": len(created_evidences),
        }

    except Exception as exc:
        db.rollback()
        logger.error(
            "Provider refresh job failed for target_id=%d, provider='%s': %s",
            target_id,
            provider_name,
            exc,
            exc_info=True,
        )
        return {
            "status": "failed",
            "target_id": target_id,
            "provider": provider_name,
            "error": str(exc),
        }

    finally:
        db.close()
