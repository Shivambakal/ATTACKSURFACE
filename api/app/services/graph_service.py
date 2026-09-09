"""Graph Intelligence Service — aggregates and visualizes the organizational security graph."""
from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.asset import Asset
from app.models.product import Product
from app.models.feature import Feature
from app.models.api_surface import ApiSurface
from app.models.security import SecurityEvent
from app.models.signal import ResearchSignal
from app.models.security_program import SecurityProgram


class GraphService:
    """Constructs visual graph representations and structured exports of an organization's attack surface."""

    @classmethod
    def get_attack_surface_graph(
        cls,
        db: Session,
        company: Company,
        scope_filter: str | None = None,
        min_confidence: float = 0.0,
    ) -> dict[str, Any]:
        """Returns nodes and edges for the interactive Attack-Surface Graph UI."""
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        # 1. Root Company Node
        company_node_id = f"company_{company.id}"
        nodes.append({
            "id": company_node_id,
            "label": company.name,
            "type": "COMPANY",
            "canonical_domain": company.canonical_domain,
            "scope": "ROOT_ORGANIZATION",
            "confidence": company.source_confidence,
            "details": {
                "industry": company.industry,
                "country": company.country,
                "website": company.website_url,
                "security_policy": company.security_policy_url,
                "bug_bounty_program": company.bug_bounty_url,
            },
        })

        # 2. Products
        products = db.query(Product).filter(Product.company_id == company.id).all()
        for prod in products:
            prod_node_id = f"product_{prod.id}"
            nodes.append({
                "id": prod_node_id,
                "label": prod.name,
                "type": "PRODUCT",
                "scope": "IN_SCOPE",
                "confidence": prod.confidence,
                "details": {
                    "description": prod.description,
                    "status": prod.status,
                },
            })
            edges.append({
                "id": f"edge_comp_prod_{prod.id}",
                "source": company_node_id,
                "target": prod_node_id,
                "label": "OFFERS_PRODUCT",
            })

        # 3. Assets / Domains
        assets_query = db.query(Asset).filter(Asset.company_id == company.id)
        if scope_filter and scope_filter.upper() != "ALL":
            assets_query = assets_query.filter(Asset.scope_status == scope_filter.upper())
        if min_confidence > 0.0:
            assets_query = assets_query.filter(Asset.confidence >= min_confidence)

        assets = assets_query.all()
        for asset in assets:
            asset_node_id = f"asset_{asset.id}"
            nodes.append({
                "id": asset_node_id,
                "label": asset.normalized_hostname or asset.name,
                "type": asset.asset_type,
                "scope": asset.scope_status,
                "confidence": asset.confidence,
                "verification_status": asset.verification_status,
                "details": {
                    "url": asset.url,
                    "source": asset.source,
                    "discovered_at": asset.discovered_at.isoformat() if asset.discovered_at else None,
                    "evidence_count": len(asset.evidence_records),
                },
            })

            # Connect asset to company
            edges.append({
                "id": f"edge_comp_asset_{asset.id}",
                "source": company_node_id,
                "target": asset_node_id,
                "label": "OWNS_ASSET",
            })

            # Check if asset links to any product
            for prod in products:
                if asset.id in (prod.domain_ids or []):
                    edges.append({
                        "id": f"edge_prod_asset_{prod.id}_{asset.id}",
                        "source": f"product_{prod.id}",
                        "target": asset_node_id,
                        "label": "HOSTS_PRODUCT",
                    })

        # 4. APIs
        apis = db.query(ApiSurface).filter(ApiSurface.company_id == company.id).all()
        for api in apis:
            api_node_id = f"api_{api.id}"
            nodes.append({
                "id": api_node_id,
                "label": f"{api.method} {api.path}",
                "type": "API",
                "scope": "IN_SCOPE",
                "confidence": api.confidence,
                "details": {
                    "version": api.version,
                    "auth": api.auth_requirement,
                },
            })
            if api.asset_id:
                edges.append({
                    "id": f"edge_asset_api_{api.asset_id}_{api.id}",
                    "source": f"asset_{api.asset_id}",
                    "target": api_node_id,
                    "label": "EXPOSES_API",
                })
            elif api.product_id:
                edges.append({
                    "id": f"edge_prod_api_{api.product_id}_{api.id}",
                    "source": f"product_{api.product_id}",
                    "target": api_node_id,
                    "label": "EXPOSES_API",
                })

        # 5. Features
        features = db.query(Feature).filter(Feature.company_id == company.id).all()
        for feat in features:
            feat_node_id = f"feature_{feat.id}"
            nodes.append({
                "id": feat_node_id,
                "label": feat.name,
                "type": "FEATURE",
                "category": feat.category,
                "scope": "IN_SCOPE",
                "confidence": feat.confidence,
                "details": {
                    "description": feat.description,
                },
            })
            if feat.product_id:
                edges.append({
                    "id": f"edge_prod_feat_{feat.product_id}_{feat.id}",
                    "source": f"product_{feat.product_id}",
                    "target": feat_node_id,
                    "label": "INCLUDES_FEATURE",
                })
            elif feat.asset_id:
                edges.append({
                    "id": f"edge_asset_feat_{feat.asset_id}_{feat.id}",
                    "source": f"asset_{feat.asset_id}",
                    "target": feat_node_id,
                    "label": "EXPOSES_FEATURE",
                })

        # 6. Research Signals (Top priority)
        signals = (
            db.query(ResearchSignal)
            .filter(ResearchSignal.company_id == company.id)
            .order_by(ResearchSignal.relevance_score.desc())
            .limit(10)
            .all()
        )
        for sig in signals:
            sig_node_id = f"signal_{sig.id}"
            nodes.append({
                "id": sig_node_id,
                "label": sig.title,
                "type": "RESEARCH_SIGNAL",
                "priority": sig.priority,
                "relevance_score": sig.relevance_score,
                "confidence": sig.confidence_score / 100.0,
                "scope": "SIGNAL",
                "details": {
                    "why_it_matters": sig.why_it_matters,
                    "recommended_area": sig.recommended_research_area,
                },
            })
            if sig.asset_id:
                edges.append({
                    "id": f"edge_sig_asset_{sig.id}_{sig.asset_id}",
                    "source": sig_node_id,
                    "target": f"asset_{sig.asset_id}",
                    "label": "AFFECTS_ASSET",
                })
            elif sig.product_id:
                edges.append({
                    "id": f"edge_sig_prod_{sig.id}_{sig.product_id}",
                    "source": sig_node_id,
                    "target": f"product_{sig.product_id}",
                    "label": "AFFECTS_PRODUCT",
                })
            else:
                edges.append({
                    "id": f"edge_sig_comp_{sig.id}",
                    "source": sig_node_id,
                    "target": company_node_id,
                    "label": "AFFECTS_COMPANY",
                })

        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "canonical_domain": company.canonical_domain,
            },
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "assets_count": len(assets),
                "products_count": len(products),
                "apis_count": len(apis),
                "features_count": len(features),
                "signals_count": len(signals),
            },
        }

    @classmethod
    def export_company_graph(cls, db: Session, company_id: int) -> dict[str, Any]:
        """Exports the entire company graph into a portable JSON document (no secrets)."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found.")

        programs = db.query(SecurityProgram).filter(SecurityProgram.company_id == company.id).all()
        assets = db.query(Asset).filter(Asset.company_id == company.id).all()
        products = db.query(Product).filter(Product.company_id == company.id).all()
        features = db.query(Feature).filter(Feature.company_id == company.id).all()
        apis = db.query(ApiSurface).filter(ApiSurface.company_id == company.id).all()
        events = db.query(SecurityEvent).filter(SecurityEvent.company_id == company.id).all()
        signals = db.query(ResearchSignal).filter(ResearchSignal.company_id == company.id).all()

        return {
            "export_version": "1.0",
            "company": {
                "id": company.id,
                "name": company.name,
                "canonical_domain": company.canonical_domain,
                "industry": company.industry,
                "country": company.country,
                "description": company.description,
                "website_url": company.website_url,
                "security_policy_url": company.security_policy_url,
                "bug_bounty_url": company.bug_bounty_url,
                "source_confidence": company.source_confidence,
                "created_at": company.created_at.isoformat(),
            },
            "security_programs": [
                {
                    "id": p.id,
                    "platform": p.platform,
                    "status": p.status,
                    "program_url": p.program_url,
                    "policy_url": p.policy_url,
                    "scope_rules": [
                        {
                            "pattern": r.pattern,
                            "inclusion_type": r.inclusion_type,
                            "confidence": r.confidence,
                        }
                        for r in p.rules
                    ],
                }
                for p in programs
            ],
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "confidence": p.confidence,
                }
                for p in products
            ],
            "assets": [
                {
                    "id": a.id,
                    "hostname": a.normalized_hostname or a.name,
                    "asset_type": a.asset_type,
                    "scope_status": a.scope_status,
                    "verification_status": a.verification_status,
                    "confidence": a.confidence,
                    "source": a.source,
                    "evidence": [
                        {
                            "source_type": ev.source_type,
                            "source_url": ev.source_url,
                            "evidence_text": ev.evidence_text,
                            "confidence": ev.confidence,
                        }
                        for ev in a.evidence_records
                    ],
                }
                for a in assets
            ],
            "features": [
                {
                    "id": f.id,
                    "name": f.name,
                    "category": f.category,
                    "description": f.description,
                    "confidence": f.confidence,
                    "product_id": f.product_id,
                    "asset_id": f.asset_id,
                }
                for f in features
            ],
            "apis": [
                {
                    "id": api.id,
                    "method": api.method,
                    "path": api.path,
                    "version": api.version,
                    "auth_requirement": api.auth_requirement,
                    "confidence": api.confidence,
                }
                for api in apis
            ],
            "security_events": [
                {
                    "id": ev.id,
                    "cve_id": ev.cve_id,
                    "source": ev.source,
                    "severity": ev.severity,
                    "summary": ev.summary,
                }
                for ev in events
            ],
            "research_signals": [
                {
                    "id": s.id,
                    "title": s.title,
                    "signal_type": s.signal_type,
                    "priority": s.priority,
                    "relevance_score": s.relevance_score,
                    "confidence_score": s.confidence_score,
                    "why_it_matters": s.why_it_matters,
                    "recommended_research_area": s.recommended_research_area,
                }
                for s in signals
            ],
        }
