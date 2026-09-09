"""Sync canonical company catalog, products, and historical timelines into DB."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from app.db import SessionLocal
from app.models import (
    Company,
    Product,
    TimelineEvent,
    HistoricalCoverage,
    SecurityProgram,
)

def sync_catalog():
    db = SessionLocal()
    with open("app/data/seed_290_companies.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now(timezone.utc)
    added_prods = 0
    added_timelines = 0

    print(f"Syncing {len(data)} companies from seed_290_companies.json...")

    for item in data:
        domain = item["canonical_domain"].strip().lower()
        company = db.query(Company).filter(Company.canonical_domain == domain).first()
        if not company:
            company = Company(
                name=item["name"],
                canonical_domain=domain,
                legal_name=item.get("legal_name"),
                description=item.get("description"),
                industry=item.get("industry"),
                country=item.get("country"),
                website_url=item.get("website_url"),
                security_policy_url=item.get("security_policy_url"),
                bug_bounty_url=item.get("bug_bounty_url"),
                source_confidence=item.get("source_confidence", 0.98),
                aliases=item.get("aliases", []),
                meta={
                    "technology_stack": item.get("technology_stack", {}),
                    "provenance": item.get("provenance", "Authoritative Seed Catalog"),
                },
                tracking_status="ACTIVE",
            )
            db.add(company)
            db.flush()
        else:
            # Update metadata if missing
            if not company.description or len(company.description) < 10:
                company.description = item.get("description")
            if not company.industry:
                company.industry = item.get("industry")
            if not company.country:
                company.country = item.get("country")
            if not company.security_policy_url:
                company.security_policy_url = item.get("security_policy_url")
            if not company.bug_bounty_url:
                company.bug_bounty_url = item.get("bug_bounty_url")
            if not company.aliases and item.get("aliases"):
                company.aliases = item.get("aliases")

        # Sync Products
        for p in item.get("products", []):
            p_name = p.get("name", "").strip()
            if not p_name:
                continue
            exists = db.query(Product).filter(
                Product.company_id == company.id,
                Product.name == p_name,
            ).first()
            if not exists:
                new_p = Product(
                    company_id=company.id,
                    name=p_name,
                    description=p.get("description", f"Core component observed for {company.name}"),
                    confidence=0.95,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                db.add(new_p)
                added_prods += 1

        # Sync Historical Timeline Events
        for tev_data in item.get("historical_timeline", []):
            t_title = tev_data.get("title", "").strip()
            if not t_title:
                continue
            exists = db.query(TimelineEvent).filter(
                TimelineEvent.company_id == company.id,
                TimelineEvent.title == t_title,
            ).first()
            if not exists:
                pub_date = (
                    datetime.fromisoformat(tev_data["published_at"].replace("Z", "+00:00"))
                    if tev_data.get("published_at")
                    else now
                )
                new_tev = TimelineEvent(
                    company_id=company.id,
                    event_type=tev_data.get("event_type", "HISTORICAL_EVENT"),
                    title=t_title,
                    summary=tev_data.get("summary", ""),
                    source=tev_data.get("source", "Corporate Intelligence Archive"),
                    source_url=tev_data.get("source_url", company.website_url),
                    observed_at=pub_date,
                    published_at=pub_date,
                    confidence=float(tev_data.get("confidence", 0.95)),
                    relevance_score=0.85,
                    priority="HIGH" if "vulnerability" in t_title.lower() or "cve" in t_title.lower() else "MEDIUM",
                    temporal_category="HISTORICAL",
                    provenance_category="HISTORICAL_RECONSTRUCTION",
                    quality_badge="CONFIRMED_HISTORY",
                    metadata={"provenance_hash": tev_data.get("provenance_hash", "")},
                )
                db.add(new_tev)
                added_timelines += 1

    db.commit()
    print(f"Catalog Sync Complete: Added {added_prods} products and {added_timelines} historical timeline events.")
    db.close()

if __name__ == "__main__":
    sync_catalog()
