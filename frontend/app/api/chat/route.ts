import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const authHeader = request.headers.get("authorization");

    if (!authHeader) {
      return NextResponse.json(
        { detail: "Missing authorization token" },
        { status: 401 }
      );
    }

    const { question } = await request.json();

    if (!question) {
      return NextResponse.json(
        { detail: "Question is required" },
        { status: 400 }
      );
    }

    const params = new URLSearchParams({ question });

    // 2. Appel vers FastAPI
    const response = await fetch(`${BACKEND_URL}/api/chat?${params}`, {
      method: "POST",
      headers: {
        Authorization: authHeader,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      let detail = errorText || "Chat request failed";
      try {
        detail = JSON.parse(errorText).detail || detail;
      } catch {
        // Keep the upstream text when it is not JSON.
      }
      return NextResponse.json(
        { detail },
        { status: response.status }
      );
    }

    if (!response.body) {
      return NextResponse.json(
        { detail: "The chat service returned an empty response." },
        { status: 502 }
      );
    }

    // Buffer the upstream stream so an agent-side socket failure becomes a
    // normal JSON error instead of a failed Next.js response pipe.
    const body = await response.text();
    return new Response(body, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
      },
    });
  } catch (error) {
    console.error("Chat proxy error:", error);
    return NextResponse.json(
      { detail: "The chat service is unavailable. Please try again." },
      { status: 502 }
    );
  }
}