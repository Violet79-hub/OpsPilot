// Netlify serves the UI; the existing Worker retains its durable D1 data.
const backend = new URL("https://opspilot-evaluated-demo.alexis707199.chatgpt.site");

export default async function proxy(request) {
  const incoming = new URL(request.url);
  const read = ["GET", "HEAD"].includes(request.method);
  const reject = (error, status) => Response.json({ error }, { status, headers: { "Cache-Control": "no-store" } });
  if (!incoming.pathname.startsWith("/api/")) return reject("Unknown API path", 404);
  if (!read) {
    const origin = request.headers.get("origin");
    if ((origin && origin !== incoming.origin) || request.headers.get("sec-fetch-site") === "cross-site") {
      return reject("Cross-origin write refused", 403);
    }
    if (!request.headers.get("content-type")?.startsWith("application/json")) return reject("Use application/json", 415);
  }
  // Copy only the API session, never Netlify/authentication or Cloudflare cookies.
  const headers = new Headers();
  for (const key of ["accept", "content-type"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  const session = request.headers.get("cookie")?.match(/(?:^|;\s*)opspilot_session=([0-9a-f-]{36})(?:;|$)/)?.[1];
  if (session) headers.set("cookie", `opspilot_session=${session}`);
  if (!read) headers.set("origin", backend.origin);
  const body = read ? undefined : await request.text();
  if (body && new TextEncoder().encode(body).length > 80000) return reject("Request too large", 413);
  // Assign pathname separately: an incoming path cannot replace the trusted host.
  const target = new URL(backend);
  target.pathname = incoming.pathname;
  target.search = incoming.search;
  try {
    const upstream = await fetch(target, {
      method: request.method, headers, body, redirect: "manual",
      cache: "no-store", signal: AbortSignal.timeout(55000),
    });
    const outgoing = new Headers({ "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
    for (const key of ["content-type", "x-opspilot-data-source"]) {
      const value = upstream.headers.get(key);
      if (value) outgoing.set(key, value);
    }
    // The cookie has no Domain, so browsers bind it to the Netlify site.
    for (const cookie of upstream.headers.getSetCookie()) {
      if (cookie.startsWith("opspilot_session=")) outgoing.append("Set-Cookie", cookie);
    }
    if (upstream.status >= 300 && upstream.status < 400) return reject("Backend returned an unexpected redirect", 502);
    return new Response(read && request.method === "HEAD" ? null : upstream.body, { status: upstream.status, headers: outgoing });
  } catch {
    return reject("The case service is temporarily unavailable. Please retry.", 502);
  }
}

export const config = { path: "/api/*" };
