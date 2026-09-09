"""Unit and regression tests for deterministic CISA Entity Resolution."""
from __future__ import annotations

import pytest
from app.models.company import Company
from app.models.product import Product
from app.services.cisa_entity_resolver import CISAEntityResolver


def test_direct_vendor_match(db_session):
    """Verify that verified vendor aliases map to canonical companies with HIGH confidence."""
    resolver = CISAEntityResolver(db_session)
    result = resolver.resolve(vendor_project="Google", product_name="Unknown Tool", cve_id="CVE-2024-0001")
    assert result.relationship_type == "DIRECT_VENDOR_MATCH"
    assert result.is_confirmed is True
    assert result.confidence >= 0.80
    assert result.canonical_domain == "google.com"


def test_direct_product_match(db_session):
    """Verify vendor + registered product match produces DIRECT_PRODUCT_MATCH with 0.95 confidence."""
    # Ensure company and product exist in test db
    comp = db_session.query(Company).filter(Company.canonical_domain == "google.com").first()
    if not comp:
        comp = Company(name="Google LLC", canonical_domain="google.com")
        db_session.add(comp)
        db_session.flush()

    prod = db_session.query(Product).filter(Product.company_id == comp.id, Product.name == "Chrome").first()
    if not prod:
        prod = Product(company_id=comp.id, name="Chrome")
        db_session.add(prod)
        db_session.commit()

    resolver = CISAEntityResolver(db_session)
    result = resolver.resolve(vendor_project="Google", product_name="Chrome", cve_id="CVE-2024-0002")
    assert result.relationship_type == "DIRECT_PRODUCT_MATCH"
    assert result.is_confirmed is True
    assert result.confidence == 0.95


def test_unverified_never_confirmed(db_session):
    """Verify that unverified or ambiguous vendors are marked UNVERIFIED/NO_RELATIONSHIP and NEVER confirmed."""
    resolver = CISAEntityResolver(db_session)
    result = resolver.resolve(vendor_project="CompletelyUnknownVendorXYZ", product_name="Widget", cve_id="CVE-2024-9999")
    assert result.is_confirmed is False
    assert result.relationship_type in ("NO_RELATIONSHIP", "UNVERIFIED", "POSSIBLE_MATCH")
    assert result.company_id is None
