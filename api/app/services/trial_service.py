"""Safe orchestration and accounting for the 50 Target Trial."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Asset, Change, Company, Evidence, ResearchSignal, SecurityEvent, SecurityProgram, Snapshot, Target, TrialRun, TrialTarget, User
from app.models.security_program import InclusionType, ProgramScopeRule
from app.services.target_safety import normalize_domain

REGISTRY_PATH = Path(os.getenv("TRIAL_REGISTRY_PATH", "data/trial_targets.json"))
TRIAL_SIZE = 50
TRIAL_WINDOW_HOURS = 24


def load_registry(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"Trial registry not found: {path}")
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Trial registry must be valid JSON.") from exc
    if not isinstance(entries, list) or len(entries) != TRIAL_SIZE:
        raise ValueError(f"Trial registry must contain exactly {TRIAL_SIZE} explicit authorized targets.")
    normalized: list[dict[str, Any]] = []
    domains: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Registry entry {index} must be an object.")
        required = ("company", "primary_domain", "scope", "authorization_source", "source")
        missing = [key for key in required if not entry.get(key)]
        if missing:
            raise ValueError(f"Registry entry {index} is missing: {', '.join(missing)}")
        if entry.get("authorized") is not True:
            raise ValueError(f"Registry entry {index} must explicitly set authorized=true.")
        if not isinstance(entry["scope"], list) or not entry["scope"]:
            raise ValueError(f"Registry entry {index} must include one or more scope rules.")
        domain = normalize_domain(str(entry["primary_domain"]))
        if domain in domains:
            raise ValueError(f"Duplicate primary domain in registry: {domain}")
        domains.add(domain)
        normalized.append({**entry, "primary_domain": domain})
    return normalized


def _queue() -> Queue:
    return Queue("snapshots", connection=Redis.from_url(settings.redis_url))


def start_trial(db: Session, user: User, path: Path = REGISTRY_PATH) -> dict[str, Any]:
    entries = load_registry(path)
    run = TrialRun(registry_source=str(path), status="queued", window_hours=TRIAL_WINDOW_HOURS)
    db.add(run)
    db.flush()
    queue = _queue()
    for entry in entries:
        company = db.query(Company).filter_by(canonical_domain=entry["primary_domain"]).first()
        if company is None:
            company = Company(name=entry["company"], canonical_domain=entry["primary_domain"], tracking_status="INITIALIZING")
            db.add(company)
            db.flush()
        program = db.query(SecurityProgram).filter_by(company_id=company.id, program_url=entry["authorization_source"]).first()
        if program is None:
            program = SecurityProgram(company_id=company.id, platform=entry["source"], program_url=entry["authorization_source"], source_url=entry["authorization_source"], status="ACTIVE", scope_summary="Explicitly supplied public program scope")
            db.add(program)
            db.flush()
        for pattern in entry["scope"]:
            existing_rule = db.query(ProgramScopeRule).filter_by(
                security_program_id=program.id,
                pattern=pattern,
                inclusion_type=InclusionType.INCLUDE.value,
            ).first()
            if existing_rule is None:
                db.add(ProgramScopeRule(
                    security_program_id=program.id,
                    pattern=pattern,
                    inclusion_type=InclusionType.INCLUDE.value,
                    source_url=entry["authorization_source"],
                    evidence="Explicitly supplied authorized trial registry entry",
                    confidence=1.0,
                ))
        target = db.query(Target).filter_by(domain=entry["primary_domain"]).first()
        if target is None:
            target = Target(domain=entry["primary_domain"], company_id=company.id, user_id=user.id, authorization_confirmed=True)
            db.add(target)
            db.flush()
        elif target.user_id is None:
            target.user_id = user.id
        target.company_id = company.id
        trial_target = TrialTarget(trial_run_id=run.id, target_id=target.id, company_id=company.id, company_name=entry["company"], primary_domain=entry["primary_domain"], scope=entry["scope"], authorization_source=entry["authorization_source"], source=entry["source"], collection_status="queued")
        db.add(trial_target)
        db.flush()
        job = queue.enqueue("app.jobs.snapshot_job.run_snapshot", target.id)
        trial_target.meta = {"job_id": job.id, "queued_at": datetime.now(timezone.utc).isoformat()}
    run.status = "running"
    db.commit()
    return {"trial_run_id": run.id, "status": run.status, "targets": len(entries), "window_hours": TRIAL_WINDOW_HOURS}


def trial_metrics(db: Session, run_id: int | None = None) -> dict[str, Any]:
    run = db.get(TrialRun, run_id) if run_id else db.query(TrialRun).order_by(TrialRun.started_at.desc()).first()
    if not run:
        return {"status": "not_started", "targets": 0, "window_hours": TRIAL_WINDOW_HOURS}
    since = datetime.now(timezone.utc) - timedelta(hours=run.window_hours)
    trial_targets = db.query(TrialTarget).filter_by(trial_run_id=run.id).all()
    target_ids = [item.target_id for item in trial_targets]
    snapshots = db.query(Snapshot).filter(Snapshot.target_id.in_(target_ids), Snapshot.collected_at >= since).all() if target_ids else []
    changes = db.query(Change).filter(Change.target_id.in_(target_ids), Change.detected_at >= since).all() if target_ids else []
    company_ids = [item.company_id for item in trial_targets if item.company_id]
    assets = db.query(Asset).filter(Asset.company_id.in_(company_ids)).all() if company_ids else []
    signals = db.query(ResearchSignal).filter(ResearchSignal.target_id.in_(target_ids), ResearchSignal.created_at >= since).all() if target_ids else []
    correlations = db.query(SecurityEvent).filter(SecurityEvent.target_id.in_(target_ids)).count() if target_ids else 0
    evidence = db.query(Evidence).filter(Evidence.target_id.in_(target_ids), Evidence.retrieved_at >= since).count() if target_ids else 0
    unique_fingerprints = {change.fingerprint for change in changes}
    duplicates = max(0, len(changes) - len(unique_fingerprints))
    noise = sum(1 for change in changes if str(change.category).upper() == "NOISE")
    succeeded = sum(1 for snapshot in snapshots if snapshot.status in ("complete", "empty"))
    failed = sum(1 for snapshot in snapshots if snapshot.status == "failed")
    all_success_times = [s.collected_at for s in snapshots if s.status in ("complete", "empty") and s.collected_at]
    last_successful_collection = max(all_success_times).isoformat() if all_success_times else None

    # Calculate latest event timestamp across changes and signals
    event_timestamps = [c.detected_at for c in changes if c.detected_at] + [s.created_at for s in signals if s.created_at]
    latest_event_timestamp = max(event_timestamps).isoformat() if event_timestamps else last_successful_collection

    now_utc = datetime.now(timezone.utc)
    started_at_dt = run.started_at if run.started_at else now_utc
    if started_at_dt.tzinfo is None:
        started_at_dt = started_at_dt.replace(tzinfo=timezone.utc)
    runtime_seconds = max(0, int((now_utc - started_at_dt).total_seconds()))
    hours = runtime_seconds // 3600
    minutes = (runtime_seconds % 3600) // 60
    runtime_formatted = f"{hours}h {minutes}m"

    for item in trial_targets:
        successes = [s.collected_at for s in snapshots if s.target_id == item.target_id and s.status in ("complete", "empty")]
        failures = any(s.target_id == item.target_id and s.status == "failed" for s in snapshots)
        item.collection_status = "success" if successes else ("failed" if failures else item.collection_status)
        if successes:
            item.last_successful_collection = max(successes)
    db.commit()

    total_platform_targets = db.query(Target).count()
    total_companies = db.query(Company).count()

    return {
        "trial_run_id": run.id,
        "status": run.status,
        "started_at": run.started_at,
        "runtime_seconds": runtime_seconds,
        "runtime_formatted": runtime_formatted,
        "window_hours": run.window_hours,
        "targets": len(trial_targets) or 50,
        "targets_monitored": total_platform_targets,
        "companies_tracked": total_companies,
        "collection_cycles": len(snapshots),
        "collection_runs": len(snapshots),
        "success": succeeded,
        "successful_runs": succeeded,
        "failed": failed,
        "failed_runs": failed,
        "assets_discovered": len(assets),
        "real_changes": max(0, len(changes) - duplicates - noise),
        "changes_detected": len(changes),
        "changes_today": len(changes),
        "duplicates": duplicates,
        "noise_rejected": noise,
        "security_correlations": correlations,
        "research_signals": len(signals),
        "signals_today": len(signals),
        "high_value_findings": sum(1 for signal in signals if signal.priority in ("CRITICAL", "HIGH")),
        "high_value_signals": sum(1 for signal in signals if signal.priority in ("CRITICAL", "HIGH")),
        "evidence_records": evidence,
        "last_successful_collection": last_successful_collection,
        "latest_event_timestamp": latest_event_timestamp,
        "target_status": [
            {
                "company": item.company_name,
                "domain": item.primary_domain,
                "scope": item.scope,
                "source": item.source,
                "authorization_source": item.authorization_source,
                "collection_status": item.collection_status,
                "last_successful_collection": item.last_successful_collection.isoformat() if item.last_successful_collection else None,
            }
            for item in trial_targets
        ],
    }
