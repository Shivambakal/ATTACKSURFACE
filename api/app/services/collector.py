import asyncio, hashlib, logging, re
from urllib.parse import urljoin, urlparse, urldefrag
import httpx
from bs4 import BeautifulSoup
from ..config import settings
from .target_safety import assert_public_destination, safe_https_url

log = logging.getLogger(__name__)

async def robots_allows(client: httpx.AsyncClient, origin: str, path: str, cache: dict[str, list[str]]) -> bool:
    if origin in cache:
        return not any(path.startswith(rule) for rule in cache[origin])
    try:
        response = await client.get(urljoin(origin, "/robots.txt"))
        if response.status_code >= 400:
            cache[origin] = []
            return True
        blocked_rules = []
        active = False
        for line in response.text.splitlines():
            key, _, value = line.partition(":")
            if key.strip().lower() == "user-agent": active = value.strip() in ("*", settings.collector_user_agent)
            if active and key.strip().lower() == "disallow" and value.strip(): blocked_rules.append(value.strip())
        cache[origin] = blocked_rules
        return not any(path.startswith(rule) for rule in blocked_rules)
    except httpx.HTTPError:
        return False

def normalize(url: str) -> str:
    clean, _ = urldefrag(url)
    return clean.rstrip("/") or clean

async def collect(domain: str) -> list[dict]:
    assert_public_destination(domain)
    origin = f"https://{domain}"
    queue, seen, observations, robots_cache = [origin], set(), [], {}
    limits = httpx.Limits(max_connections=1)
    async with httpx.AsyncClient(headers={"User-Agent": settings.collector_user_agent}, timeout=12, follow_redirects=True, limits=limits) as client:
        while queue and len(observations) < settings.max_pages_per_snapshot:
            url = normalize(queue.pop(0))
            if url in seen: continue
            seen.add(url)
            parsed = urlparse(url)
            if not safe_https_url(url, domain) or not await robots_allows(client, origin, parsed.path or "/", robots_cache):
                continue
            try:
                response = None
                for attempt in range(3):
                    try:
                        response = await client.get(url)
                        if response.status_code not in (429, 500, 502, 503, 504): break
                    except httpx.HTTPError:
                        if attempt == 2: raise
                    await asyncio.sleep((attempt + 1) * settings.request_delay_seconds)
                if response is None: continue
                # httpx follows redirects; reject a redirect that escapes the approved host.
                if not safe_https_url(str(response.url), domain): continue
                if "text/html" not in response.headers.get("content-type", "") or response.status_code >= 400: continue
                soup = BeautifulSoup(response.text, "html.parser")
                for node in soup(["script", "style", "noscript"]): node.decompose()
                text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:12000]
                tech = sorted({x for x in [response.headers.get("server"), response.headers.get("x-powered-by")] if x})
                observations.append({"url": url, "kind": "page", "status_code": response.status_code,
                    "title": soup.title.get_text(strip=True) if soup.title else None,
                    "content_hash": hashlib.sha256(text.encode()).hexdigest(), "text_excerpt": text[:2000],
                    "technologies": tech, "headers": {k.lower(): v for k,v in response.headers.items() if k.lower() in ("server", "x-powered-by", "content-security-policy")}})
                for link in soup.select("a[href]"):
                    candidate = normalize(urljoin(url, link["href"]))
                    cp = urlparse(candidate)
                    if cp.scheme == "https" and cp.netloc == domain and candidate not in seen: queue.append(candidate)
                await asyncio.sleep(settings.request_delay_seconds)
            except httpx.HTTPError as exc: log.warning("collection request failed", extra={"url": url, "error": str(exc)})
    return observations
