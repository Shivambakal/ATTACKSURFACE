const API =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL !== undefined ? process.env.NEXT_PUBLIC_API_URL : "")
    : (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");

// In-flight request deduplication map to prevent redundant concurrent fetches
const inFlightRequests = new Map<string, Promise<any>>();

// High-speed in-memory cache for GET requests (10-second TTL)
interface CacheEntry {
  data: any;
  timestamp: number;
}
const apiCache = new Map<string, CacheEntry>();
const CACHE_TTL_MS = 10_000; // 10 seconds

export function clearApiCache(pathPrefix?: string) {
  if (!pathPrefix) {
    apiCache.clear();
    return;
  }
  for (const key of apiCache.keys()) {
    if (key.startsWith(pathPrefix)) {
      apiCache.delete(key);
    }
  }
}

export interface ApiFetchOptions extends RequestInit {
  skipCache?: boolean;
  timeoutMs?: number;
}

export async function apiFetch<T>(path: string, options?: ApiFetchOptions): Promise<T> {
  const method = (options?.method || "GET").toUpperCase();
  const isGet = method === "GET";
  const skipCache = options?.skipCache ?? false;
  const timeoutMs = options?.timeoutMs ?? 45_000;

  // On non-GET mutations (POST/PUT/DELETE/PATCH), invalidate cache so fresh data loads
  if (!isGet) {
    apiCache.clear();
  }

  // Cache hit check for GET requests
  const cacheKey = `${method}:${path}`;
  if (isGet && !skipCache) {
    const cached = apiCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return cached.data as T;
    }
  }

  // Helper for localStorage cached fallback
  const getPersistedCache = (): T | null => {
    if (typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem(`ast_cache:${path}`);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed.data as T;
    } catch {
      return null;
    }
  };

  const setPersistedCache = (data: any) => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(
        `ast_cache:${path}`,
        JSON.stringify({ data, ts: Date.now() })
      );
    } catch {
      // Ignore quota errors
    }
  };

  // In-flight deduplication: if the exact same request is already executing, reuse its promise
  if (isGet && inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey) as Promise<T>;
  }

  const fetchPromise = (async () => {
    let res: Response;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      res = await fetch(`${API}${path}`, {
        cache: "no-store",
        ...options,
        signal: options?.signal || controller.signal,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      });
    } catch (err: any) {
      // If request timed out or network failed, check if we have cached or persisted data
      if (isGet) {
        const memoryFallback = apiCache.get(cacheKey)?.data as T | undefined;
        if (memoryFallback) {
          console.warn(`[API] Returning stale memory cache for ${path} due to connection delay.`);
          return memoryFallback;
        }
        const persistedFallback = getPersistedCache();
        if (persistedFallback) {
          console.warn(`[API] Returning persisted cache for ${path} due to server cold start.`);
          return persistedFallback;
        }
      }

      if (err?.name === "AbortError") {
        throw new Error("Request timed out. The server is taking too long to respond.");
      }
      throw new Error("Unable to reach the service. Check your connection and try again.");
    } finally {
      clearTimeout(timeoutId);
    }

    if (!res.ok) {
      // On 500+ or 503, if we have persisted cached data, gracefully return it
      if (isGet && res.status >= 500) {
        const persisted = getPersistedCache();
        if (persisted) {
          return persisted;
        }
      }

      const rawText = await res.text().catch(() => "");
      let error: { detail?: unknown } = {};
      if (rawText) {
        try {
          error = JSON.parse(rawText);
        } catch {
          error = { detail: rawText };
        }
      }

      const detail = error?.detail;
      let message: string;
      if (typeof detail === "string" && detail.trim()) {
        message = detail.trim();
      } else if (Array.isArray(detail)) {
        message = detail
          .map((item: { msg?: string } | string) =>
            typeof item === "string" ? item : item?.msg || "Validation error"
          )
          .join(". ");
      } else if (detail && typeof detail === "object" && "msg" in detail) {
        message = String((detail as { msg: string }).msg);
      } else if (res.status === 503) {
        message = "Service temporarily unavailable. Database may be offline — please try again shortly.";
      } else if (res.status >= 500) {
        message =
          "Server error during authentication. If this persists, the API database connection is likely misconfigured.";
      } else {
        message = res.statusText || `Request failed with status ${res.status}`;
      }

      if (/^internal server error$/i.test(message)) {
        message =
          "Authentication backend is down (database unreachable). Set DATABASE_URL on the API host to your Postgres URL, then retry.";
      }

      throw new Error(message);
    }

    if (res.status === 204) {
      return {} as T;
    }

    const text = await res.text();
    if (!text) {
      return {} as T;
    }

    let parsed: T;
    try {
      parsed = JSON.parse(text) as T;
    } catch {
      parsed = text as unknown as T;
    }

    // Cache successful GET responses
    if (isGet) {
      apiCache.set(cacheKey, {
        data: parsed,
        timestamp: Date.now(),
      });
      setPersistedCache(parsed);
    }

    return parsed;
  })();

  if (isGet) {
    inFlightRequests.set(cacheKey, fetchPromise);
    fetchPromise.finally(() => {
      inFlightRequests.delete(cacheKey);
    });
  }

  return fetchPromise;
}

export { API };
