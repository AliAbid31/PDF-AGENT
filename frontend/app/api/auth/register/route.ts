import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const raw = await response.text();
    let data: unknown;
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch {
      data = {
        detail:
          response.status >= 500
            ? "The authentication server failed while creating the account."
            : raw || "Registration failed.",
      };
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Register error:", error);
    return NextResponse.json(
      { detail: "Backend connection failed" },
      { status: 500 }
    );
  }
}
