import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const token = request.headers.get("authorization")?.split(" ")[1];

    if (!token) {
      return NextResponse.json(
        { detail: "Missing authorization token" },
        { status: 401 }
      );
    }

    const { question } = await request.json();

    const params = new URLSearchParams({ question });

    const response = await fetch(`${BACKEND_URL}/api/chat?${params}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { detail: "Chat request failed" },
        { status: response.status }
      );
    }

    return new NextResponse(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Chat error:", error);
    return NextResponse.json(
      { detail: "Backend connection failed" },
      { status: 500 }
    );
  }
}
