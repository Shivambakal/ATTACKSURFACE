# Security Model

## Authorized Research Only

This platform is designed exclusively for authorized security research. It collects only public, permitted data from targets the researcher is authorized to observe.

## Collection Safety

- **HTTPS only** — No HTTP, file://, ftp://, or other schemes
- **Same-origin traversal** — Collector stays on the approved domain
- **robots.txt compliance** — Respects disallow rules
- **Bounded page budget** — Maximum pages per snapshot (default: 8)
- **Request delay** — Configurable delay between requests (default: 1s)
- **GET only** — No form submissions, no POST/PUT/DELETE
- **No authentication** — Never authenticates to target services
- **No enumeration** — No directory brute-forcing, path guessing, or port scanning

## SSRF Prevention

- All hostnames validated before DNS resolution
- DNS resolution validated before HTTP connection
- Blocked: localhost, 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- Blocked: link-local (169.254.0.0/16, fe80::/10)
- Blocked: IPv6 private (fc00::/7, ::1)
- Blocked: cloud metadata (169.254.169.254)
- Blocked: file://, ftp://, gopher:// schemes
- DNS rebinding prevention: resolved IPs validated before each request
- Redirect validation: destination revalidated after redirects

## Authentication & Sessions

- Passwords hashed with bcrypt (never stored in plaintext)
- Session tokens are random 48-byte URL-safe strings
- Only SHA-256 hash of session token stored in database
- Raw token given to user once, never stored server-side
- HTTP-only, SameSite=Lax cookies
- Session revocation (single and all-devices)
- Verification and reset tokens expire

## Credential Protection

Credentials (GITHUB_TOKEN, GEMINI_API_KEY, NVIDIA_API_KEY, NVD_API_KEY) are:
- Loaded from environment variables only
- Never hardcoded in source code
- Never exposed in API responses
- Never logged or printed
- Never included in frontend bundles
- Never stored in database records
- Never included in error tracebacks or analytics

## AI Safety (Prompt Injection Defense)

All external content is **untrusted data**:
- System instructions, user input, collected data, evidence, and model output are separated with explicit delimiters
- Collected webpage content can never become instructions
- Injection patterns are detected and neutralized
- AI outputs are validated for hallucination
- AI never fabricates vulnerabilities, CVEs, timestamps, or findings
- If evidence is insufficient, AI says "Insufficient evidence"

## Rate Limiting

- Per-IP rate limits for unauthenticated requests
- Per-user rate limits for authenticated requests
- Per-target collection rate limits
- Provider-level rate limiting (respects API limits)
- Worker concurrency limits

## Data Privacy

- User data is tenant-isolated
- Conservative privacy defaults
- No telemetry by default
- Data export and account deletion supported
- Research notes and findings are private to the user

## Security Knowledge Base & Non-Defamation Boundaries

- **Strict Knowledge Separation**: Global Security Knowledge (CISA KEV, CWE, OWASP) is strictly segregated from Company Security History.
- **No Unproven Vulnerability Claims**: Detecting a third-party technology (e.g., `Log4j` or `nginx`) on a target does **never** classify the target company as vulnerable.
- **Evidence-Only Company Security Events**: Only verified security incidents or proof directly attributable to a company are entered into `SecurityEvent`.
- **Read-Only Contextual Association**: Advisories matching detected technologies are presented purely as research context and weakness radar patterns, never as confirmed target flaws.

