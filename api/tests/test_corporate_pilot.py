"""Real-World Corporate Pilot Validation Suite.

Validates reference company source packs across:
- Google (Cloud, SecOps, Chrome, Android, APIs)
- Cloudflare (Developers, Deprecations, Security)
- AWS / Amazon (What's New, Bulletins, News)
- Microsoft (Graph, MSRC, Azure)
- Apple (Security Releases, Developer)
- GitHub (Changelog, REST API, Advisories)
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.company import Company
from app.services.source_pack_service import SourcePackService
from app.models.source_registry import CompanySource


@pytest.fixture
def pilot_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()

    # Prepopulate pilot companies
    companies = [
        Company(name="Google", canonical_domain="google.com"),
        Company(name="Cloudflare", canonical_domain="cloudflare.com"),
        Company(name="Amazon", canonical_domain="amazon.com"),
        Company(name="Microsoft", canonical_domain="microsoft.com"),
        Company(name="Apple", canonical_domain="apple.com"),
        Company(name="GitHub", canonical_domain="github.com"),
    ]
    session.add_all(companies)
    session.commit()
    yield session
    session.close()


def test_pilot_pack_ingestion_and_coverage(pilot_db: Session):
    service = SourcePackService()
    stats = service.sync_reference_sources(pilot_db)

    assert stats["created"] >= 25
    assert stats["skipped"] >= 0

    # Validate Google sources
    google = pilot_db.query(Company).filter(Company.canonical_domain == "google.com").first()
    assert google is not None
    google_sources = pilot_db.query(CompanySource).filter(CompanySource.company_id == google.id).all()
    assert len(google_sources) >= 8
    source_names = [s.name for s in google_sources]
    assert "Google Cloud Release Notes" in source_names
    assert "Android Security Bulletin" in source_names
    assert "Chrome Releases Blog" in source_names

    # Validate Cloudflare sources
    cf = pilot_db.query(Company).filter(Company.canonical_domain == "cloudflare.com").first()
    assert cf is not None
    cf_sources = pilot_db.query(CompanySource).filter(CompanySource.company_id == cf.id).all()
    assert len(cf_sources) >= 3

    # Validate Apple sources
    apple = pilot_db.query(Company).filter(Company.canonical_domain == "apple.com").first()
    assert apple is not None
    apple_sources = pilot_db.query(CompanySource).filter(CompanySource.company_id == apple.id).all()
    assert any("Apple Security Releases" in s.name for s in apple_sources)
