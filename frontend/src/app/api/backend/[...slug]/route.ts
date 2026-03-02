/**
 * Catch-all proxy for /api/backend/* → http://localhost:8000/*
 *
 * Reads the JWT from the httpOnly `token` cookie and injects it as an
 * Authorization: Bearer header before forwarding to FastAPI.
 *
 * More-specific route handlers (query/, validation/run/) take priority over
 * this catch-all, so those routes are unaffected.
 */

import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE = "http://localhost:8000";

async function proxy(request: NextRequest, slug: string[]): Promise<NextResponse> {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  // Reconstruct path: /api/backend/auth/me → /auth/me
  const path = "/" + slug.join("/");

  // Forward query string if present
  const search = request.nextUrl.search;
  const url = `${BACKEND_BASE}${path}${search}`;

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // Forward the original Content-Type so multipart/form-data boundaries are preserved
  const incomingContentType = request.headers.get("content-type");
  if (incomingContentType) {
    headers["Content-Type"] = incomingContentType;
  }

  // Forward request body for methods that have one; use arrayBuffer to preserve binary data
  const hasBody = !["GET", "HEAD"].includes(request.method);
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let backendRes: Response;
  try {
    backendRes = await fetch(url, {
      method: request.method,
      headers,
      body,
    });
  } catch {
    return NextResponse.json(
      { detail: "Unable to reach backend" },
      { status: 502 }
    );
  }

  // Try to parse as JSON; fall back to text
  const contentType = backendRes.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const data = await backendRes.json().catch(() => ({
      detail: "Backend returned invalid JSON",
    }));
    return NextResponse.json(data, { status: backendRes.status });
  }

  const text = await backendRes.text();
  return new NextResponse(text, {
    status: backendRes.status,
    headers: { "Content-Type": contentType || "text/plain" },
  });
}

// Export a handler for every HTTP method Next.js supports

type RouteContext = { params: Promise<{ slug: string[] }> };

export async function GET(req: NextRequest, ctx: RouteContext) {
  const { slug } = await ctx.params;
  return proxy(req, slug);
}

export async function POST(req: NextRequest, ctx: RouteContext) {
  const { slug } = await ctx.params;
  return proxy(req, slug);
}

export async function PATCH(req: NextRequest, ctx: RouteContext) {
  const { slug } = await ctx.params;
  return proxy(req, slug);
}

export async function PUT(req: NextRequest, ctx: RouteContext) {
  const { slug } = await ctx.params;
  return proxy(req, slug);
}

export async function DELETE(req: NextRequest, ctx: RouteContext) {
  const { slug } = await ctx.params;
  return proxy(req, slug);
}
