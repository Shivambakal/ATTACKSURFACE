"""20-Year Attack History, Vulnerability Classification, and Threat Intelligence Engine.

Synthesizes historical breach records (2004-2024+), zero-day exploits, CISA KEV data,
and structural attack-surface transformations for high-accuracy threat analysis.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── 20-Year Attack Vector & Vulnerability Taxonomy ─────────────────────────────
VULNERABILITY_TAXONOMY = {
    "RCE_MEMORY_CORRUPTION": {
        "name": "Remote Code Execution & Memory Corruption",
        "description": "Exploitation of memory safety errors (Buffer Overflow, Use-After-Free, Type Confusion, Out-of-Bounds Write) to execute arbitrary code.",
        "cwe_examples": ["CWE-119", "CWE-416", "CWE-122", "CWE-843"],
        "historical_impact": "High proportion of Chrome, Windows, and iOS zero-days over the last 20 years.",
    },
    "APT_STATE_SPONSORED": {
        "name": "Advanced Persistent Threat (APT) & Targeted Intrusion",
        "description": "Multi-stage cyber campaigns executed by state-backed or highly sophisticated actors targeting source code, espionage, and core infrastructure.",
        "mitre_tactics": ["Initial Access", "Lateral Movement", "Persistence", "Exfiltration"],
        "historical_impact": "Operation Aurora (Google 2009-2010), SolarWinds SUNBURST (2020), Hafnium (2021).",
    },
    "IDENTITY_OAUTH_ACCESS_BYPASS": {
        "name": "Authentication, OAuth & Identity Bypass",
        "description": "Token hijacking, OAuth consent screen spoofing, Golden SAML, and broken authentication workflows.",
        "cwe_examples": ["CWE-287", "CWE-306", "CWE-640"],
        "historical_impact": "Google Docs Phishing Worm (2017), Okta Lapsus$ breach (2022), Microsoft Storm-0558 signing key breach (2023).",
    },
    "CLOUD_METADATA_SSRF": {
        "name": "Cloud Infrastructure & Server-Side Request Forgery (SSRF)",
        "description": "Exploiting internal network services or instance metadata services (169.254.169.254) to siphon cloud credentials and IAM roles.",
        "cwe_examples": ["CWE-918"],
        "historical_impact": "Capital One AWS SSRF (2019), internal GCP metadata service isolation developments.",
    },
    "SUPPLY_CHAIN_DEPENDENCY": {
        "name": "Software Supply Chain & Upstream Dependency Hijacking",
        "description": "Compromising upstream open-source packages, build pipelines, or widely embedded libraries.",
        "cwe_examples": ["CWE-1357", "CWE-829"],
        "historical_impact": "Log4Shell (2021), libwebp CVE-2023-4863 (2023), XZ Utils backdoor (2024), SolarWinds (2020).",
    },
    "ZERO_DAY_ACTIVE_EXPLOIT": {
        "name": "In-the-Wild Zero-Day Exploitation",
        "description": "Exploitation of vulnerabilities before vendor disclosure or patch availability, monitored via CISA KEV.",
        "historical_impact": "Surged from ~15/year in 2014 to over 90+/year in 2023-2024 across browsers, hypervisors, and network edge appliances.",
    },
}

# ── Grounded Historic Breaches & Landmark Campaigns (2004-2024+) ───────────────
HISTORIC_COMPANY_CAMPAIGNS: dict[str, list[dict[str, Any]]] = {
    "google.com": [
        {
            "year": 2009,
            "title": "Operation Aurora — Landmark State-Sponsored Cyber Espionage",
            "threat_actor": "Elderwood Group / APT17 (Chinese State-Sponsored)",
            "attack_type": "APT_STATE_SPONSORED",
            "severity": "CRITICAL",
            "cve_id": "CVE-2010-0249",
            "summary": "Targeted spearphishing and zero-day IE vulnerability used to breach Google's corporate network in Mountain View. Attackers sought access to Google source code repositories (Perforce) and the Gmail accounts of Chinese human rights activists.",
            "impact": "Monumental shift in modern enterprise cybersecurity. Led to Google's public disclosure in January 2010, cessation of censored search in mainland China, and the architectural invention of BeyondCorp (Zero Trust Architecture).",
            "affected_assets": ["Perforce Source Code Management", "Corporate Ingress", "Gmail Infrastructure"],
            "biggest_attack": True,
        },
        {
            "year": 2017,
            "title": "Google Docs Phishing Worm & OAuth Abuse",
            "threat_actor": "Independent Threat Actors / Mass Campaign",
            "attack_type": "IDENTITY_OAUTH_ACCESS_BYPASS",
            "severity": "HIGH",
            "cve_id": None,
            "summary": "Mass-scale phishing campaign that disguised a rogue web application as 'Google Docs', requesting legitimate OAuth access to read and send emails. Hit an estimated 1 million users within hours.",
            "impact": "Exploited trust in google.com domain. Google neutralized the rogue client within 1 hour and subsequently instituted mandatory app verification and unverified app warning screens.",
            "affected_assets": ["Google OAuth 2.0 Consent Service", "Gmail API", "Google Contacts"],
            "biggest_attack": False,
        },
        {
            "year": 2023,
            "title": "WebP Heap Buffer Overflow Exploited in the Wild",
            "threat_actor": "Commercial Surveillance Vendors (NSO Group / Predator)",
            "attack_type": "ZERO_DAY_ACTIVE_EXPLOIT",
            "severity": "CRITICAL",
            "cve_id": "CVE-2023-4863",
            "summary": "Heap buffer overflow in libwebp (Huffman table allocation error) used to achieve zero-click remote code execution via malicious WebP images rendered in Google Chrome and Android.",
            "impact": "Emergency zero-day patch across Google Chrome, Chromium browsers, Android OS, and thousands of applications embedding libwebp worldwide (CISA KEV added).",
            "affected_assets": ["Google Chrome (Chromium)", "Android OS Media Framework", "libwebp"],
            "biggest_attack": False,
        },
        {
            "year": 2023,
            "title": "VP8 Video Compression Encoding 0-Day (libvpx)",
            "threat_actor": "Advanced Threat Actors",
            "attack_type": "ZERO_DAY_ACTIVE_EXPLOIT",
            "severity": "HIGH",
            "cve_id": "CVE-2023-5217",
            "summary": "Heap buffer overflow in VP8 encoding in libvpx, allowing remote code execution via crafted web media.",
            "impact": "Patched urgently in Chrome and added to CISA KEV catalog within 48 hours of discovery by Google Threat Analysis Group (TAG).",
            "affected_assets": ["Google Chrome", "libvpx Media Subsystem"],
            "biggest_attack": False,
        },
        {
            "year": 2022,
            "title": "Chrome V8 Animation & Execution Sandbox Escape",
            "threat_actor": "North Korean APTs (Lazarus / Threat Group-4261)",
            "attack_type": "RCE_MEMORY_CORRUPTION",
            "severity": "CRITICAL",
            "cve_id": "CVE-2022-0609",
            "summary": "Use-after-free vulnerability in the Animation component of Google Chrome exploited by North Korean state actors via watering hole attacks targeting cryptocurrency and media researchers.",
            "impact": "Triggered Google TAG public threat advisory and emergency Chrome desktop update.",
            "affected_assets": ["Google Chrome Desktop", "V8 Engine Sandbox"],
            "biggest_attack": False,
        },
        {
            "year": 2015,
            "title": "Android Stagefright Media Framework Vulnerabilities",
            "threat_actor": "Vulnerability Research & Exploitation Proof-of-Concept",
            "attack_type": "RCE_MEMORY_CORRUPTION",
            "severity": "CRITICAL",
            "cve_id": "CVE-2015-1538",
            "summary": "Multiple integer overflows and memory corruptions in libstagefright allowing remote code execution triggered simply by receiving an MMS message with a crafted MP4 video.",
            "impact": "Affected approximately 950 million Android devices; prompted Google to institute monthly Android Security Bulletins.",
            "affected_assets": ["Android OS (Stagefright Framework)", "MMS Subsystem"],
            "biggest_attack": False,
        },
    ],
    "microsoft.com": [
        {
            "year": 2020,
            "title": "SolarWinds SUNBURST Supply Chain Intrusion",
            "threat_actor": "Nobelium / APT29 (Russian SVR)",
            "attack_type": "SUPPLY_CHAIN_DEPENDENCY",
            "severity": "CRITICAL",
            "cve_id": None,
            "summary": "Trojanized SolarWinds Orion build system enabled attackers to compromise Microsoft internal corporate networks, view source code for Azure, Exchange, and Windows components.",
            "impact": "Major supply chain disaster impacting thousands of global enterprises and US government agencies.",
            "biggest_attack": True,
        },
        {
            "year": 2021,
            "title": "Hafnium Microsoft Exchange Server Zero-Days (ProxyLogon)",
            "threat_actor": "Hafnium (Chinese State-Sponsored)",
            "attack_type": "RCE_MEMORY_CORRUPTION",
            "severity": "CRITICAL",
            "cve_id": "CVE-2021-26855",
            "summary": "Four chaining zero-days in on-premises Microsoft Exchange Server allowing pre-auth RCE and web shell deployment on over 250,000 servers globally.",
            "biggest_attack": False,
        },
        {
            "year": 2023,
            "title": "Storm-0558 MSA Cryptographic Signing Key Compromise",
            "threat_actor": "Storm-0558 (Chinese Espionage)",
            "attack_type": "IDENTITY_OAUTH_ACCESS_BYPASS",
            "severity": "CRITICAL",
            "cve_id": None,
            "summary": "Compromised Microsoft MSA signing key used to forge authentication tokens for Exchange Online and Outlook Web Access.",
            "biggest_attack": False,
        },
    ],
}


def analyze_company_attack_history(
    session: Session,
    company_domain_or_name: str,
) -> dict[str, Any]:
    """Retrieve verified database records, CISA KEV data, and 20-year trends for a company."""
    norm = company_domain_or_name.strip().lower()
    if norm.startswith("https://"):
        norm = norm.replace("https://", "")
    if norm.startswith("http://"):
        norm = norm.replace("http://", "")
    norm = norm.split("/")[0].replace("www.", "")

    # 1. Resolve Company from DB
    company_row = session.execute(
        text(
            """
            SELECT id, name, canonical_domain, created_at, metadata
            FROM public.companies
            WHERE lower(canonical_domain) = :dom OR lower(name) LIKE :like_name
            LIMIT 1
            """
        ),
        {"dom": norm, "like_name": f"%{norm.split('.')[0]}%"},
    ).mappings().first()

    company_id = company_row["id"] if company_row else None
    company_name = company_row["name"] if company_row else norm.capitalize()
    canonical_domain = company_row["canonical_domain"] if company_row else norm

    # 2. Query Real Security Events from Supabase
    db_security_events = []
    if company_id:
        db_security_events = session.execute(
            text(
                """
                SELECT id, cve_id, severity, summary, published, relationship_type, confidence
                FROM public.security_events
                WHERE company_id = :cid
                ORDER BY published DESC NULLS LAST, id DESC
                LIMIT 50
                """
            ),
            {"cid": company_id},
        ).mappings().all()

    # 3. Query Real CISA KEV items associated with this vendor
    vendor_pattern = f"%{norm.split('.')[0]}%"
    cisa_items = session.execute(
        text(
            """
            SELECT cve_id, vendor_project, product, vulnerability_name, date_added, notes
            FROM public.cisa_kev_items
            WHERE lower(vendor_project) LIKE :v OR lower(product) LIKE :v
            ORDER BY date_added DESC NULLS LAST
            LIMIT 40
            """
        ),
        {"v": vendor_pattern},
    ).mappings().all()

    # 4. Check Grounded Historic Milestones (2004-2024+)
    curated_history = HISTORIC_COMPANY_CAMPAIGNS.get(canonical_domain, [])
    if not curated_history:
        # Check domain base
        for k, v in HISTORIC_COMPANY_CAMPAIGNS.items():
            if k.split(".")[0] in norm:
                curated_history = v
                break

    # 5. Compute 20-Year Attack Distribution by Year & Type
    year_distribution: dict[int, int] = {}
    attack_type_distribution: dict[str, int] = {}

    for ch in curated_history:
        y = ch.get("year", 2020)
        atype = ch.get("attack_type", "OTHER")
        year_distribution[y] = year_distribution.get(y, 0) + 1
        attack_type_distribution[atype] = attack_type_distribution.get(atype, 0) + 1

    for ev in db_security_events:
        pub = ev.get("published")
        if pub:
            y = pub.year
            year_distribution[y] = year_distribution.get(y, 0) + 1
        rtype = ev.get("relationship_type") or "VULNERABILITY_EVENT"
        attack_type_distribution[rtype] = attack_type_distribution.get(rtype, 0) + 1

    for kev in cisa_items:
        da = kev.get("date_added")
        if da:
            try:
                y = int(str(da)[:4])
                year_distribution[y] = year_distribution.get(y, 0) + 1
            except Exception:
                pass
        attack_type_distribution["CISA_KEV_EXPLOIT"] = attack_type_distribution.get("CISA_KEV_EXPLOIT", 0) + 1

    # Find biggest historic attack
    biggest_attack = None
    for item in curated_history:
        if item.get("biggest_attack"):
            biggest_attack = item
            break
    if not biggest_attack and curated_history:
        biggest_attack = curated_history[0]

    return {
        "company_id": company_id,
        "company_name": company_name,
        "canonical_domain": canonical_domain,
        "total_security_events_db": len(db_security_events),
        "total_cisa_kev_items": len(cisa_items),
        "curated_historical_milestones": curated_history,
        "biggest_attack": biggest_attack,
        "yearly_distribution": dict(sorted(year_distribution.items())),
        "attack_type_distribution": attack_type_distribution,
        "recent_cve_sample": [k["cve_id"] for k in cisa_items[:10] if k.get("cve_id")],
    }


ATTACK_TYPE_DEFINITIONS = VULNERABILITY_TAXONOMY


def classify_vulnerability_type(text_sample: str) -> str:
    """Classifies a vulnerability summary into a deterministic 20-year taxonomy bucket."""
    t = text_sample.lower()
    if any(k in t for k in ["apt", "state-sponsored", "spearphish", "espionage", "aurora", "solarwinds", "unc2452"]):
        return "APT_STATE_SPONSORED"
    if any(k in t for k in ["zero-day", "0-day", "in the wild", "in-the-wild", "active exploit", "actively exploited"]):
        return "ZERO_DAY_ACTIVE_EXPLOIT"
    if any(k in t for k in ["ssrf", "server-side request forgery", "metadata", "169.254.169.254", "imds"]):
        return "CLOUD_METADATA_SSRF"
    if any(k in t for k in ["oauth", "identity", "saml", "token", "auth bypass", "authentication bypass", "credential"]):
        return "IDENTITY_OAUTH_ACCESS_BYPASS"
    if any(k in t for k in ["supply chain", "dependency", "upstream", "package", "backdoor", "xz utils"]):
        return "SUPPLY_CHAIN_DEPENDENCY"
    if any(k in t for k in ["rce", "remote code execution", "heap buffer overflow", "use-after-free", "out-of-bounds", "memory corruption", "overflow"]):
        return "RCE_MEMORY_CORRUPTION"
    return "RCE_MEMORY_CORRUPTION"


def get_grounded_attack_history(
    session: Session,
    company_name: str,
    domain: str | None = None,
) -> dict[str, Any]:
    """Helper alias returning grounded history for tests and services."""
    analysis = analyze_company_attack_history(session, domain or company_name)
    return {
        "company": {
            "name": analysis["company_name"],
            "domain": analysis["canonical_domain"],
            "id": analysis["company_id"],
        },
        "known_historical_milestones": analysis["curated_historical_milestones"],
        "yearly_distribution": analysis["yearly_distribution"],
        "attack_type_distribution": analysis["attack_type_distribution"],
        "taxonomy_definitions": VULNERABILITY_TAXONOMY,
        "biggest_attack": analysis["biggest_attack"],
        "total_cisa_items": analysis["total_cisa_kev_items"],
    }

