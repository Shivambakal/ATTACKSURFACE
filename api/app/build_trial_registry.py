"""Script to generate verified 50-target trial registry from seed_companies.json."""
from __future__ import annotations

import json
from pathlib import Path

def generate_trial_registry():
    current_dir = Path(__file__).parent
    seed_file = current_dir / "data" / "seed_companies.json"
    if not seed_file.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_file}")

    companies = json.loads(seed_file.read_text(encoding="utf-8"))
    
    entries = []
    domains_seen = set()

    for c in companies:
        domain = c.get("canonical_domain", "").strip().lower()
        if not domain or domain in domains_seen:
            continue
        
        name = c.get("name", "").strip()
        auth_src = c.get("bug_bounty_url") or c.get("security_policy_url")
        if not auth_src:
            continue

        source_platform = "Official VDP"
        if "hackerone" in auth_src.lower():
            source_platform = "HackerOne"
        elif "bugcrowd" in auth_src.lower():
            source_platform = "Bugcrowd"
        elif "intigriti" in auth_src.lower():
            source_platform = "Intigriti"
        elif "yeswehack" in auth_src.lower():
            source_platform = "YesWeHack"
        elif "google" in auth_src.lower():
            source_platform = "Google VRP"
        elif "microsoft" in auth_src.lower():
            source_platform = "Microsoft Bounty"
        elif "apple" in auth_src.lower():
            source_platform = "Apple Security Bounty"

        domains_seen.add(domain)
        entries.append({
            "authorized": True,
            "company": name,
            "primary_domain": domain,
            "scope": [domain, f"*.{domain}"],
            "authorization_source": auth_src,
            "source": source_platform,
        })

        if len(entries) == 50:
            break

    if len(entries) != 50:
        raise ValueError(f"Expected 50 entries, got {len(entries)}")

    # Write to api/data/trial_targets.json
    api_data_dir = current_dir.parent / "data"
    api_data_dir.mkdir(parents=True, exist_ok=True)
    out_file_api = api_data_dir / "trial_targets.json"
    out_file_api.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {out_file_api}")

    # Write to root data/trial_targets.json
    root_data_dir = current_dir.parent.parent / "data"
    root_data_dir.mkdir(parents=True, exist_ok=True)
    out_file_root = root_data_dir / "trial_targets.json"
    out_file_root.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {out_file_root}")

if __name__ == "__main__":
    generate_trial_registry()
