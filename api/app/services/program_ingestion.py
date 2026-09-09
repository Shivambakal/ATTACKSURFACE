"""Public Bug Bounty & Security Program Ingestion Service.

Fetches, validates, and normalizes public security programs and disclosure
registries across HackerOne, Bugcrowd, Intigriti, YesWeHack, Federacy, and
ProjectDiscovery's public catalog.

Includes offline file cache fallbacks for resilient operation and testability.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "programs_cache"

DATASET_URLS = {
    "projectdiscovery": "https://raw.githubusercontent.com/projectdiscovery/public-bugbounty-programs/main/dist/data.json",
    "hackerone": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/hackerone_data.json",
    "bugcrowd": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/bugcrowd_data.json",
    "intigriti": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/intigriti_data.json",
    "yeswehack": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/yeswehack_data.json",
    "federacy": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/federacy_data.json",
}


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_from_cache(source_name: str) -> Optional[Any]:
    cache_file = CACHE_DIR / f"{source_name}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load cached dataset for %s: %s", source_name, e)
    return None


def _save_to_cache(source_name: str, data: Any):
    _ensure_cache_dir()
    cache_file = CACHE_DIR / f"{source_name}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning("Failed to write cache for %s: %s", source_name, e)


def fetch_raw_dataset(source_name: str, timeout: float = 25.0) -> list | dict:
    """Fetches raw JSON dataset from the remote source or falls back to local cache."""
    url = DATASET_URLS.get(source_name)
    if not url:
        raise ValueError(f"Unknown dataset source: {source_name}")

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                _save_to_cache(source_name, data)
                return data
            else:
                logger.warning("HTTP %d when fetching %s dataset", resp.status_code, source_name)
    except Exception as e:
        logger.warning("Network error fetching %s dataset: %s", source_name, e)

    # Fallback to local cache
    cached = _load_from_cache(source_name)
    if cached is not None:
        logger.info("Using cached dataset for %s", source_name)
        return cached

    logger.error("No data available (remote or cached) for %s", source_name)
    return []


def parse_projectdiscovery_programs(data: Any) -> list[dict[str, Any]]:
    """Normalizes ProjectDiscovery's public catalog."""
    if isinstance(data, dict):
        raw_list = data.get("programs", [])
    elif isinstance(data, list):
        raw_list = data
    else:
        return []

    results = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or ""
        url = item.get("url") or ""
        bounty = bool(item.get("bounty", False))
        domains = item.get("domains") or []

        in_scope = []
        for d in domains:
            if isinstance(d, str) and d.strip():
                in_scope.append({"target": d.strip(), "type": "URL", "bounty": bounty})

        results.append({
            "platform": "ProjectDiscovery",
            "program_name": name,
            "program_handle": name.lower().replace(" ", "-"),
            "program_url": url,
            "policy_url": url,
            "source_url": url,
            "website": in_scope[0]["target"] if in_scope else None,
            "is_public": True,
            "offers_bounties": bounty,
            "min_bounty": None,
            "max_bounty": None,
            "currency": "USD",
            "submission_state": "OPEN",
            "in_scope": in_scope,
            "out_of_scope": [],
            "raw_metadata": {"domains_count": len(domains)},
        })
    return results


def parse_hackerone_programs(data: list) -> list[dict[str, Any]]:
    """Normalizes HackerOne programs."""
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        targets = item.get("targets", {})
        raw_in_scope = targets.get("in_scope", []) if isinstance(targets, dict) else []
        raw_out_of_scope = targets.get("out_of_scope", []) if isinstance(targets, dict) else []

        in_scope = []
        for t in raw_in_scope:
            ident = t.get("asset_identifier")
            if ident:
                in_scope.append({
                    "target": ident,
                    "type": t.get("asset_type", "URL"),
                    "bounty": bool(t.get("eligible_for_bounty", False)),
                    "instruction": t.get("instruction"),
                })

        out_of_scope = []
        for t in raw_out_of_scope:
            ident = t.get("asset_identifier")
            if ident:
                out_of_scope.append({
                    "target": ident,
                    "type": t.get("asset_type", "URL"),
                })

        results.append({
            "platform": "HackerOne",
            "program_name": item.get("name") or item.get("handle") or "",
            "program_handle": item.get("handle"),
            "program_url": item.get("url"),
            "policy_url": item.get("url"),
            "source_url": item.get("url"),
            "website": item.get("website"),
            "is_public": True,
            "offers_bounties": bool(item.get("offers_bounties", False)),
            "min_bounty": None,
            "max_bounty": None,
            "currency": "USD",
            "submission_state": item.get("submission_state", "open").upper(),
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "raw_metadata": {
                "offers_swag": item.get("offers_swag"),
                "managed_program": item.get("managed_program"),
            },
        })
    return results


def parse_bugcrowd_programs(data: list) -> list[dict[str, Any]]:
    """Normalizes Bugcrowd programs."""
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        targets = item.get("targets", {})
        raw_in_scope = targets.get("in_scope", []) if isinstance(targets, dict) else []
        raw_out_of_scope = targets.get("out_of_scope", []) if isinstance(targets, dict) else []

        in_scope = []
        for t in raw_in_scope:
            tgt = t.get("target") or t.get("uri")
            if tgt:
                in_scope.append({
                    "target": tgt,
                    "type": t.get("type", "website"),
                    "name": t.get("name"),
                })

        out_of_scope = []
        for t in raw_out_of_scope:
            tgt = t.get("target") or t.get("uri")
            if tgt:
                out_of_scope.append({
                    "target": tgt,
                    "type": t.get("type", "website"),
                })

        max_p = item.get("max_payout")
        max_bounty = None
        if max_p is not None:
            try:
                max_bounty = float(max_p)
            except (ValueError, TypeError):
                pass

        url = item.get("url") or ""
        handle = url.rstrip("/").split("/")[-1] if url else None

        results.append({
            "platform": "Bugcrowd",
            "program_name": item.get("name") or "",
            "program_handle": handle,
            "program_url": url,
            "policy_url": url,
            "source_url": url,
            "website": in_scope[0]["target"] if in_scope else None,
            "is_public": True,
            "offers_bounties": bool(max_bounty and max_bounty > 0),
            "min_bounty": None,
            "max_bounty": max_bounty,
            "currency": "USD",
            "submission_state": "OPEN",
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "raw_metadata": {
                "safe_harbor": item.get("safe_harbor"),
                "allows_disclosure": item.get("allows_disclosure"),
            },
        })
    return results


def parse_intigriti_programs(data: list) -> list[dict[str, Any]]:
    """Normalizes Intigriti programs."""
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        targets = item.get("targets", {})
        raw_in_scope = targets.get("in_scope", []) if isinstance(targets, dict) else []
        raw_out_of_scope = targets.get("out_of_scope", []) if isinstance(targets, dict) else []

        in_scope = []
        for t in raw_in_scope:
            tgt = t.get("endpoint") or t.get("target")
            if tgt:
                in_scope.append({
                    "target": tgt,
                    "type": t.get("type", "url"),
                })

        out_of_scope = []
        for t in raw_out_of_scope:
            tgt = t.get("endpoint") or t.get("target")
            if tgt:
                out_of_scope.append({
                    "target": tgt,
                    "type": t.get("type", "url"),
                })

        min_b = item.get("min_bounty", {}).get("value") if isinstance(item.get("min_bounty"), dict) else item.get("min_bounty")
        max_b = item.get("max_bounty", {}).get("value") if isinstance(item.get("max_bounty"), dict) else item.get("max_bounty")

        results.append({
            "platform": "Intigriti",
            "program_name": item.get("name") or item.get("handle") or "",
            "program_handle": item.get("handle"),
            "program_url": item.get("url"),
            "policy_url": item.get("url"),
            "source_url": item.get("url"),
            "website": in_scope[0]["target"] if in_scope else None,
            "is_public": item.get("confidentiality_level") != "InviteOnly",
            "offers_bounties": bool(max_b and max_b > 0),
            "min_bounty": float(min_b) if min_b else None,
            "max_bounty": float(max_b) if max_b else None,
            "currency": "EUR",
            "submission_state": "OPEN" if item.get("status") == "Open" else "PAUSED",
            "in_scope": in_scope,
            "out_of_scope": out_of_scope,
            "raw_metadata": {"tacRequired": item.get("tacRequired")},
        })
    return results


def parse_yeswehack_programs(data: list) -> list[dict[str, Any]]:
    """Normalizes YesWeHack programs."""
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        targets = item.get("targets", {})
        raw_in_scope = targets.get("in_scope", []) if isinstance(targets, dict) else []

        in_scope = []
        for t in raw_in_scope:
            tgt = t.get("target")
            if tgt:
                in_scope.append({
                    "target": tgt,
                    "type": t.get("scope_type", "web-application"),
                })

        min_b = item.get("min_bounty")
        max_b = item.get("max_bounty")

        slug = item.get("slug") or item.get("name", "").lower().replace(" ", "-")
        url = f"https://yeswehack.com/programs/{slug}"

        results.append({
            "platform": "YesWeHack",
            "program_name": item.get("name") or "",
            "program_handle": slug,
            "program_url": url,
            "policy_url": url,
            "source_url": url,
            "website": in_scope[0]["target"] if in_scope else None,
            "is_public": bool(item.get("public", True)),
            "offers_bounties": bool(max_b and max_b > 0),
            "min_bounty": float(min_b) if min_b else None,
            "max_bounty": float(max_b) if max_b else None,
            "currency": "EUR",
            "submission_state": "CLOSED" if item.get("disabled") else "OPEN",
            "in_scope": in_scope,
            "out_of_scope": [],
            "raw_metadata": {"managed": item.get("managed")},
        })
    return results


def parse_federacy_programs(data: list) -> list[dict[str, Any]]:
    """Normalizes Federacy programs."""
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        targets = item.get("targets", {})
        raw_in_scope = targets.get("in_scope", []) if isinstance(targets, dict) else []

        in_scope = []
        for t in raw_in_scope:
            tgt = t.get("target")
            if tgt:
                in_scope.append({
                    "target": tgt,
                    "type": t.get("target_type", "website"),
                })

        url = item.get("url") or ""
        handle = url.rstrip("/").split("/")[-1] if url else None

        results.append({
            "platform": "Federacy",
            "program_name": item.get("name") or "",
            "program_handle": handle,
            "program_url": url,
            "policy_url": url,
            "source_url": url,
            "website": in_scope[0]["target"] if in_scope else None,
            "is_public": True,
            "offers_bounties": bool(item.get("offers_awards", False)),
            "min_bounty": None,
            "max_bounty": None,
            "currency": "USD",
            "submission_state": "OPEN",
            "in_scope": in_scope,
            "out_of_scope": [],
            "raw_metadata": {},
        })
    return results


def fetch_all_public_programs() -> list[dict[str, Any]]:
    """Fetches and normalizes all available public security programs from all platforms."""
    all_programs = []

    # 1. ProjectDiscovery Catalog (800+ programs)
    logger.info("Ingesting ProjectDiscovery public bug-bounty catalog...")
    pd_raw = fetch_raw_dataset("projectdiscovery")
    pd_programs = parse_projectdiscovery_programs(pd_raw)
    all_programs.extend(pd_programs)
    logger.info("Loaded %d programs from ProjectDiscovery", len(pd_programs))

    # 2. HackerOne (440+ programs)
    logger.info("Ingesting HackerOne public bug-bounty programs...")
    h1_raw = fetch_raw_dataset("hackerone")
    h1_programs = parse_hackerone_programs(h1_raw)
    all_programs.extend(h1_programs)
    logger.info("Loaded %d programs from HackerOne", len(h1_programs))

    # 3. Bugcrowd (270+ programs)
    logger.info("Ingesting Bugcrowd public bug-bounty programs...")
    bc_raw = fetch_raw_dataset("bugcrowd")
    bc_programs = parse_bugcrowd_programs(bc_raw)
    all_programs.extend(bc_programs)
    logger.info("Loaded %d programs from Bugcrowd", len(bc_programs))

    # 4. Intigriti (130+ programs)
    logger.info("Ingesting Intigriti public bug-bounty programs...")
    int_raw = fetch_raw_dataset("intigriti")
    int_programs = parse_intigriti_programs(int_raw)
    all_programs.extend(int_programs)
    logger.info("Loaded %d programs from Intigriti", len(int_programs))

    # 5. YesWeHack (50+ programs)
    logger.info("Ingesting YesWeHack public bug-bounty programs...")
    ywh_raw = fetch_raw_dataset("yeswehack")
    ywh_programs = parse_yeswehack_programs(ywh_raw)
    all_programs.extend(ywh_programs)
    logger.info("Loaded %d programs from YesWeHack", len(ywh_programs))

    # 6. Federacy (30+ programs)
    logger.info("Ingesting Federacy public bug-bounty programs...")
    fed_raw = fetch_raw_dataset("federacy")
    fed_programs = parse_federacy_programs(fed_raw)
    all_programs.extend(fed_programs)
    logger.info("Loaded %d programs from Federacy", len(fed_programs))

    logger.info("Total normalized public programs fetched: %d", len(all_programs))
    return all_programs
