import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.text();

    const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body,
    });

    const raw = await response.text();
    let data: unknown;
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch {
      data = { detail: raw || "Login failed." };
    }
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Login error:", error);
    return NextResponse.json(
      { detail: "Backend connection failed" },
      { status: 500 }
    );
  }
}
