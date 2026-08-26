import type { NextConfig } from "next";

// The FastAPI service. Inside docker compose this is the service name; running
// the two locally it's localhost. Server components talk to it directly (see
// src/lib/api.ts); the browser goes through the rewrites below.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Proxy the API and the audio files through Next's own origin. Two reasons
  // this matters more than it looks:
  //   1. No CORS config on the FastAPI side, ever.
  //   2. The <audio>/wavesurfer playhead depends on HTTP Range requests
  //      surviving to the backend's StaticFiles mount. Same-origin keeps that
  //      simple and avoids preflight on range headers.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/:path*` },
      { source: "/audio/:path*", destination: `${BACKEND_URL}/audio/:path*` },
    ];
  },
};

export default nextConfig;
