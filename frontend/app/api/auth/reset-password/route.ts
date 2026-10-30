import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
    });
    const raw = await response.text();
    let data: unknown;
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch {
      data = { detail: raw || "Password reset failed." };
    }
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Reset password error:", error);
    return NextResponse.json(
      { detail: "Backend connection failed" },
      { status: 500 },
    );
  }
}
