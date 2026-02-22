/**
 * Next.js Route Handler — auth cookie management.
 *
 * POST /api/auth  — Exchange email + password for a JWT, store it in an
 *                   httpOnly cookie named `token`.
 * DELETE /api/auth — Clear the `token` cookie (logout).
 */

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const FASTAPI_LOGIN_URL = "http://localhost:8000/auth/login";
const COOKIE_NAME = "token";

// ---------------------------------------------------------------------------
// POST — Login
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
  let body: { email?: string; password?: string };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { ok: false, error: "Invalid request body" },
      { status: 400 }
    );
  }

  const { email, password } = body;

  if (!email || !password) {
    return NextResponse.json(
      { ok: false, error: "email and password are required" },
      { status: 400 }
    );
  }

  // Forward credentials to FastAPI
  let fastapiRes: Response;
  try {
    fastapiRes = await fetch(FASTAPI_LOGIN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    console.error("FastAPI login request failed:", err);
    return NextResponse.json(
      { ok: false, error: "Unable to reach authentication service" },
      { status: 502 }
    );
  }

  if (!fastapiRes.ok) {
    const detail = await fastapiRes
      .json()
      .then((d) => d.detail ?? "Authentication failed")
      .catch(() => "Authentication failed");

    return NextResponse.json(
      { ok: false, error: detail },
      { status: fastapiRes.status }
    );
  }

  const data = await fastapiRes.json();
  const { access_token } = data;

  if (!access_token) {
    return NextResponse.json(
      { ok: false, error: "No token returned from server" },
      { status: 500 }
    );
  }

  // Set httpOnly cookie
  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    // 8 hours — matches typical JWT expiry; adjust to match FastAPI settings
    maxAge: 60 * 60 * 8,
  });

  return NextResponse.json({ ok: true });
}

// ---------------------------------------------------------------------------
// DELETE — Logout
// ---------------------------------------------------------------------------

export async function DELETE() {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
  return NextResponse.json({ ok: true });
}
