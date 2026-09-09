# 50 Target Trial Registry

Create `trial_targets.json` outside source control and point `TRIAL_REGISTRY_PATH` at it. The file must contain exactly 50 objects. Every object must include:

```json
{
  "authorized": true,
  "company": "Verified organization name",
  "primary_domain": "verified.example",
  "scope": ["verified.example", "*.verified.example"],
  "authorization_source": "https://the-public-program-policy.example/...",
  "source": "OFFICIAL_SCOPE"
}
```

Only explicitly authorized public programs belong in this file. Do not use guessed domains, company lists, certificate discoveries, or technology matches as authorization. `authorization_source` must point to the public policy or scope evidence that supports the entry.