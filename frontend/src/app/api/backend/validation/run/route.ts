/**
 * Next.js Route Handler — proxy for POST /api/backend/validation/run
 *
 * The validation harness calls Ollama for every gold-standard question and
 * takes 30–120 seconds. The generic next.config.ts rewrite proxy would time
 * out. This handler reads the token cookie and proxies with no timeout.
 */

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = "http://localhost:8000/validation/run";

export async function POST(_request: NextRequest) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(BACKEND_URL, { method: "POST", headers });
  } catch {
    return NextResponse.json(
      { detail: "Unable to reach backend" },
      { status: 502 }
    );
  }

  const data = await backendRes.json().catch(() => ({
    detail: "Backend returned invalid response",
  }));
  return NextResponse.json(data, { status: backendRes.status });
}
