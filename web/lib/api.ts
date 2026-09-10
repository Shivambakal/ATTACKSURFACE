const API =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL !== undefined ? process.env.NEXT_PUBLIC_API_URL : "")
    : (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000");

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      cache: "no-store",
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new Error("Unable to reach the service. Check your connection and try again.");
  }

  if (!res.ok) {
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

    // Vercel sometimes returns a bare "Internal Server Error" body when the
    // upstream API crashes on a missing DATABASE_URL — make that actionable.
    if (/^internal server error$/i.test(message)) {
      message =
        "Authentication backend is down (database unreachable). Set DATABASE_URL on the API host to your Postgres URL, then retry.";
    }

    throw new Error(message);
  }

  // Support 204 No Content or empty bodies
  if (res.status === 204) {
    return {} as T;
  }

  const text = await res.text();
  if (!text) {
    return {} as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

export { API };
