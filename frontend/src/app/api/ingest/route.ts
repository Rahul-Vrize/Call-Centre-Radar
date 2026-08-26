import type { NextRequest } from "next/server";

/**
 * Proxy for POST /ingest.
 *
 * The `/api/:path*` rewrite in next.config.ts handles every other endpoint
 * fine, but it gives up at 30 seconds — and a full live ingestion (channel
 * split, transcription, mood scoring, reasoning, citation verification) takes
 * around 27. That is close enough to the limit that it failed intermittently,
 * which is the worst way for a demo to break.
 *
 * A route handler takes precedence over the rewrite for this one path and
 * forwards the request itself, with no such ceiling. The body is streamed
 * rather than buffered so a large upload doesn't sit in memory twice.
 */
export const runtime = "nodejs";
export const maxDuration = 300;

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const upstream = await fetch(`${BACKEND_URL}/ingest`, {
    method: "POST",
    // Content-Type carries the multipart boundary — forward it verbatim or the
    // backend cannot parse the form.
    headers: { "content-type": request.headers.get("content-type") ?? "" },
    body: request.body,
    // Required by undici when streaming a request body.
    duplex: "half",
  } as RequestInit & { duplex: "half" });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
