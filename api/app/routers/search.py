"""Global search router across all entities."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Asset,
    Change,
    Evidence,
    Feature,
    ResearchFinding,
    ResearchNote,
    Target,
    User,
)
from app.routers.deps import get_current_user

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
@router.get("/", include_in_schema=False)
def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search keyword"),
    limit_per_category: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Perform global keyword search across targets, changes, assets, features, notes, findings, and evidence."""
    term = f"%{q}%"

    # Canonical targets for scoped search
    canonical_targets = db.query(Target).all()
    user_target_ids = [t.id for t in canonical_targets]

    # 1. Targets
    matched_targets = (
        db.query(Target)
        .filter(Target.domain.ilike(term))
        .limit(limit_per_category)
        .all()
    )

    # 2. Changes
    matched_changes = (
        db.query(Change)
        .filter(
            Change.target_id.in_(user_target_ids),
            or_(
                Change.summary.ilike(term),
                Change.category.ilike(term),
                Change.source_url.ilike(term),
                Change.researcher_note.ilike(term),
            ),
        )
        .order_by(Change.detected_at.desc())
        .limit(limit_per_category)
        .all()
        if user_target_ids
        else []
    )

    # 3. Assets
    matched_assets = (
        db.query(Asset)
        .filter(
            Asset.target_id.in_(user_target_ids),
            or_(
                Asset.name.ilike(term),
                Asset.url.ilike(term),
                Asset.asset_type.ilike(term),
            ),
        )
        .order_by(Asset.last_observed.desc())
        .limit(limit_per_category)
        .all()
        if user_target_ids
        else []
    )

    # 4. Features
    matched_features = (
        db.query(Feature)
        .filter(
            Feature.target_id.in_(user_target_ids),
            or_(
                Feature.name.ilike(term),
                Feature.description.ilike(term),
            ),
        )
        .order_by(Feature.last_observed.desc())
        .limit(limit_per_category)
        .all()
        if user_target_ids
        else []
    )

    # 5. Notes
    matched_notes = (
        db.query(ResearchNote)
        .filter(
            ResearchNote.user_id == current_user.id,
            or_(
                ResearchNote.title.ilike(term),
                ResearchNote.body.ilike(term),
            ),
        )
        .order_by(ResearchNote.updated_at.desc())
        .limit(limit_per_category)
        .all()
    )

    # 6. Findings
    matched_findings = (
        db.query(ResearchFinding)
        .filter(
            ResearchFinding.user_id == current_user.id,
            or_(
                ResearchFinding.title.ilike(term),
                ResearchFinding.description.ilike(term),
            ),
        )
        .order_by(ResearchFinding.created_at.desc())
        .limit(limit_per_category)
        .all()
    )

    # 7. Evidence
    matched_evidence = (
        db.query(Evidence)
        .filter(
            Evidence.target_id.in_(user_target_ids),
            or_(
                Evidence.source.ilike(term),
                Evidence.source_url.ilike(term),
                Evidence.excerpt.ilike(term),
            ),
        )
        .order_by(Evidence.retrieved_at.desc())
        .limit(limit_per_category)
        .all()
        if user_target_ids
        else []
    )

    results = {
        "targets": [
            {"id": t.id, "domain": t.domain, "monitoring_status": t.monitoring_status}
            for t in matched_targets
        ],
        "changes": [
            {
                "id": c.id,
                "target_id": c.target_id,
                "category": c.category,
                "summary": c.summary,
                "security_relevance": c.security_relevance,
                "source_url": c.source_url,
                "detected_at": c.detected_at,
            }
            for c in matched_changes
        ],
        "assets": [
            {
                "id": a.id,
                "target_id": a.target_id,
                "name": a.name,
                "url": a.url,
                "asset_type": a.asset_type,
                "status": a.status,
            }
            for a in matched_assets
        ],
        "features": [
            {
                "id": f.id,
                "target_id": f.target_id,
                "name": f.name,
                "description": f.description,
                "status": f.status,
            }
            for f in matched_features
        ],
        "notes": [
            {
                "id": n.id,
                "target_id": n.target_id,
                "title": n.title,
                "body": n.body,
                "updated_at": n.updated_at,
            }
            for n in matched_notes
        ],
        "findings": [
            {
                "id": fd.id,
                "target_id": fd.target_id,
                "title": fd.title,
                "severity": fd.severity,
                "status": fd.status,
            }
            for fd in matched_findings
        ],
        "evidence": [
            {
                "id": e.id,
                "target_id": e.target_id,
                "source": e.source,
                "source_url": e.source_url,
                "evidence_type": e.evidence_type,
                "excerpt": e.excerpt,
            }
            for e in matched_evidence
        ],
    }

    total_count = sum(len(items) for items in results.values())

    return {
        "query": q,
        "total_count": total_count,
        "results": results,
    }
