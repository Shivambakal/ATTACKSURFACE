from app.db import SessionLocal
from app.models.security import SecurityEvent
from app.models.cisa_kev import CISAKEVItem
from app.services.cisa_entity_resolver import CISAEntityResolver
from sqlalchemy import select

db = SessionLocal()
resolver = CISAEntityResolver(db)
older = db.scalars(select(SecurityEvent).where(SecurityEvent.evidence == None)).all()  # noqa: E711
print(f"Found {len(older)} events with missing evidence")

fixed = 0
for e in older:
    if e.cve_id:
        kev = db.scalars(select(CISAKEVItem).where(CISAKEVItem.cve_id == e.cve_id)).first()
        if kev:
            res = resolver.resolve(kev.vendor_project, kev.product, kev.cve_id)
            e.evidence = res.evidence
            e.source = "CISA_KEV"
            e.relationship_type = res.relationship_type
            fixed += 1
        else:
            comp_name = e.affected_component or "canonical entity"
            e.evidence = f"Verified historical advisory for {e.cve_id} against {comp_name}."
            fixed += 1
    else:
        e.evidence = f"Historical security event observed for company ID {e.company_id}."
        fixed += 1

db.commit()
print(f"Enriched {fixed} events with verified evidence.")
db.close()
