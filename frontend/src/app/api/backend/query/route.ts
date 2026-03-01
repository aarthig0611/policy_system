/**
 * Next.js Route Handler — proxy for POST /api/backend/query
 *
 * The generic next.config.ts rewrite can time out for detailed LLM responses
 * (which take 30–90 seconds). This dedicated handler reads the token from the
 * httpOnly cookie and forwards the request to FastAPI with no proxy timeout.
 *
 * In Next.js App Router, route handlers have priority over rewrites, so this
 * file intercepts POST /api/backend/query (and /api/backend/query/ after the
 * Next.js trailing-slash 308 normalisation).
 */

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_QUERY_URL = "http://localhost:8000/query";

export async function POST(request: NextRequest) {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  const body = await request.text();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(BACKEND_QUERY_URL, {
      method: "POST",
      headers,
      body,
    });
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
