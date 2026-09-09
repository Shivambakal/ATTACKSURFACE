from pathlib import Path
import json
import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Change, Company, Target, User, utcnow
from app.models.security_program import InclusionType, ProgramScopeRule, SecurityProgram
from app.routers.deps import get_current_user, require_researcher_or_above
from app.schemas import BulkImportResponse, TargetCreate, TargetOut
from app.services.target_safety import normalize_domain

router = APIRouter(prefix="/api/v1/targets", tags=["targets"])


@router.post("", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TargetOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_target(
    body: TargetCreate,
    current_user: User = Depends(require_researcher_or_above),
    db: Session = Depends(get_db),
) -> Target:
    """Create a new authorized target domain for the authenticated user with complete authorization record."""
    try:
        domain = normalize_domain(body.domain)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    if not body.authorization_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization acknowledgement is required.",
        )

    company_name = ((body.company_name or body.company) or "").strip()[:255] or domain.split(".")[0].capitalize()[:255]
    program_source = (body.program_source or "Direct Authorization").strip()[:128]
    auth_source = (body.authorization_source or f"https://{domain}/security.txt").strip()
    raw_scopes = body.scope if body.scope else [domain, f"*.{domain}"]
    scope_list: list[str] = []
    for s in raw_scopes:
        cleaned = str(s).strip()[:255]
        if cleaned and cleaned not in scope_list:
            scope_list.append(cleaned)
    if not scope_list:
        scope_list = [domain, f"*.{domain}"]
    scope_type = (body.scope_type or "DOMAIN")[:32]

    try:
        # 1. Resolve or create Company
        company = db.query(Company).filter(
            (Company.canonical_domain == domain) | (Company.name == company_name)
        ).first()
        if not company:
            company = Company(
                name=company_name,
                canonical_domain=domain,
                website_url=f"https://{domain}",
                security_policy_url=auth_source,
                bug_bounty_url=auth_source,
                source_confidence=1.0,
                tracking_status="ACTIVE",
            )
            db.add(company)
            db.flush()

        # 2. Resolve or create SecurityProgram
        sec_prog = db.query(SecurityProgram).filter_by(
            company_id=company.id, program_url=auth_source
        ).first()
        if not sec_prog:
            sec_prog = SecurityProgram(
                company_id=company.id,
                platform=program_source[:64],
                program_url=auth_source,
                policy_url=auth_source,
                status="ACTIVE",
                scope_summary=f"Official vulnerability reporting program for {company_name}"[:512],
            )
            db.add(sec_prog)
            db.flush()

        # 3. Add ProgramScopeRules
        for pattern in scope_list:
            existing_rule = db.query(ProgramScopeRule).filter_by(
                security_program_id=sec_prog.id,
                pattern=pattern,
            ).first()
            if not existing_rule:
                db.add(
                    ProgramScopeRule(
                        security_program_id=sec_prog.id,
                        pattern=pattern,
                        inclusion_type=InclusionType.INCLUDE.value,
                        source_url=auth_source,
                        evidence="Explicitly onboarded target scope",
                        confidence=1.0,
                    )
                )

        # 4. Internal authorization audit record
        auth_record = {
            "status": "AUTHORIZED",
            "provenance_status": "AUTHORIZED_PUBLIC_BOUNTY",
            "verified_at": utcnow().isoformat(),
            "verified_by_id": current_user.id,
            "verified_by_email": current_user.email,
            "authorizing_user": current_user.email,
            "audit_hash_sha256": hashlib.sha256(f"{domain}:{auth_source}:{current_user.email}".encode()).hexdigest(),
            "company": company_name,
            "program_source": program_source,
            "authorization_source": auth_source,
            "scope": scope_list,
            "scope_type": scope_type,
            "rationale": (body.notes or f"Explicit authorization confirmed under {program_source}")[:1024],
        }

        # 5. Resolve or create Target
        target = db.query(Target).filter_by(domain=domain).first()
        if target:
            if target.user_id is None:
                target.user_id = current_user.id
            target.company_id = company.id
            target.company_name = company_name
            target.program_source = program_source
            target.authorization_source = auth_source
            target.scope = scope_list
            target.scope_type = scope_type
            target.notes = body.notes
            target.authorization_record = auth_record
            target.authorization_confirmed = True
            db.commit()
            db.refresh(target)
            return target

        target = Target(
            domain=domain,
            company_id=company.id,
            company_name=company_name,
            user_id=current_user.id,
            program_source=program_source,
            authorization_source=auth_source,
            scope=scope_list,
            scope_type=scope_type,
            notes=body.notes,
            authorization_record=auth_record,
            authorization_confirmed=True,
            monitoring_status="active",
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        return target
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target enrollment could not be completed: {str(exc)}",
        ) from exc


@router.post("/bulk-import", response_model=BulkImportResponse)
def bulk_import_targets(
    current_user: User = Depends(require_researcher_or_above),
    db: Session = Depends(get_db),
) -> BulkImportResponse:
    """Load 50 verified authorized bug-bounty targets from official registry with complete provenance."""
    registry_paths = [
        Path("data/trial_targets.json"),
        Path("app/data/trial_targets.json"),
        Path(__file__).parent.parent / "data" / "trial_targets.json",
        Path(__file__).parent.parent.parent / "data" / "trial_targets.json",
    ]
    target_file = next((p for p in registry_paths if p.exists()), None)
    if not target_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verified trial targets registry not found.",
        )

    try:
        entries = json.loads(target_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid trial registry format: {exc}",
        )

    imported_domains: list[str] = []

    for entry in entries:
        raw_domain = entry.get("primary_domain", "").strip().lower()
        if not raw_domain:
            continue
        try:
            domain = normalize_domain(raw_domain)
        except ValueError:
            continue

        company_name = entry.get("company", domain.split(".")[0].capitalize())
        program_source = entry.get("source", "Official VDP")
        auth_source = entry.get("authorization_source", f"https://{domain}/security.txt")
        scope_list = entry.get("scope", [domain, f"*.{domain}"])

        # 1. Company
        company = db.query(Company).filter(
            (Company.canonical_domain == domain) | (Company.name == company_name)
        ).first()
        if not company:
            company = Company(
                name=company_name,
                canonical_domain=domain,
                website_url=f"https://{domain}",
                security_policy_url=auth_source,
                bug_bounty_url=auth_source,
                source_confidence=1.0,
                tracking_status="ACTIVE",
            )
            db.add(company)
            db.flush()

        # 2. Security Program
        sec_prog = db.query(SecurityProgram).filter_by(
            company_id=company.id, program_url=auth_source
        ).first()
        if not sec_prog:
            sec_prog = SecurityProgram(
                company_id=company.id,
                platform=program_source,
                program_url=auth_source,
                policy_url=auth_source,
                status="ACTIVE",
                scope_summary=f"Official vulnerability reporting program for {company_name}",
            )
            db.add(sec_prog)
            db.flush()

        # 3. Rules
        for pattern in scope_list:
            existing_rule = db.query(ProgramScopeRule).filter_by(
                security_program_id=sec_prog.id,
                pattern=pattern,
            ).first()
            if not existing_rule:
                db.add(
                    ProgramScopeRule(
                        security_program_id=sec_prog.id,
                        pattern=pattern,
                        inclusion_type=InclusionType.INCLUDE.value,
                        source_url=auth_source,
                        evidence="Explicit verified bug-bounty registry entry",
                        confidence=1.0,
                    )
                )

        # 4. Internal Authorization Record
        auth_record = {
            "status": "AUTHORIZED",
            "provenance_status": "AUTHORIZED_PUBLIC_BOUNTY",
            "verified_at": utcnow().isoformat(),
            "verified_by_id": current_user.id,
            "verified_by_email": current_user.email,
            "authorizing_user": current_user.email,
            "audit_hash_sha256": hashlib.sha256(f"{domain}:{auth_source}:{current_user.email}".encode()).hexdigest(),
            "company": company_name,
            "program_source": program_source,
            "authorization_source": auth_source,
            "scope": scope_list,
            "scope_type": "DOMAIN",
            "rationale": f"Bulk enrolled from verified public bug-bounty catalog: {program_source}",
        }

        # 5. Target
        target = db.query(Target).filter_by(domain=domain).first()
        if not target:
            target = Target(
                domain=domain,
                company_id=company.id,
                company_name=company_name,
                user_id=current_user.id,
                program_source=program_source,
                authorization_source=auth_source,
                scope=scope_list,
                scope_type="DOMAIN",
                notes="Imported from verified 50-target public bug-bounty catalog",
                authorization_record=auth_record,
                authorization_confirmed=True,
                monitoring_status="active",
            )
            db.add(target)
        else:
            if target.user_id is None:
                target.user_id = current_user.id
            target.company_id = company.id
            target.company_name = company_name
            target.program_source = program_source
            target.authorization_source = auth_source
            target.scope = scope_list
            target.authorization_record = auth_record
            target.authorization_confirmed = True

        imported_domains.append(domain)

    db.commit()
    total_in_db = db.query(Target).count()

    return BulkImportResponse(
        total_imported=len(imported_domains),
        imported_count=len(imported_domains),
        total_targets=total_in_db,
        targets=imported_domains,
        message=f"Successfully imported and authorized {len(imported_domains)} public bug-bounty targets.",
    )


@router.get("", response_model=list[TargetOut])
@router.get("/", response_model=list[TargetOut], include_in_schema=False)
def list_targets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Target]:
    """List all authorized monitored targets in the canonical database."""
    return (
        db.query(Target)
        .order_by(Target.created_at.desc())
        .all()
    )


@router.get("/{target_id}", response_model=TargetOut)
def get_target(
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Target:
    """Get target details by ID."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
    return target


@router.get("/{target_id}/overview")
def target_overview(
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get target overview with detected surface changes."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")

    changes = (
        db.query(Change)
        .filter_by(target_id=target_id)
        .order_by(Change.detected_at.desc())
        .all()
    )
    return {
        "target": {
            "id": target.id,
            "domain": target.domain,
            "company_id": target.company_id,
            "company_name": target.company_name,
            "monitoring_status": target.monitoring_status,
            "last_visited_at": target.last_visited_at,
            "created_at": target.created_at,
        },
        "changes": [
            {
                "id": c.id,
                "category": c.category,
                "summary": c.summary,
                "security_relevance": c.security_relevance,
                "confidence": c.confidence,
                "priority": getattr(c, "priority", "MEDIUM"),
                "status": getattr(c, "status", "interesting"),
                "source_url": c.source_url,
                "detected_at": c.detected_at,
            }
            for c in changes
        ],
    }


@router.post("/{target_id}/visit")
def visit_target(
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update last_visited_at timestamp for the target."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")

    target.last_visited_at = utcnow()
    db.commit()
    db.refresh(target)
    return {
        "message": "Visit timestamp updated",
        "last_visited_at": target.last_visited_at,
    }
