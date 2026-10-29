import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const token = request.headers.get("authorization")?.split(" ")[1];
  if (!token) {
    return NextResponse.json(
      { detail: "Missing authorization token" },
      { status: 401 },
    );
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/documents`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Document list error:", error);
    return NextResponse.json(
      { detail: "Backend connection failed" },
      { status: 500 },
    );
  }
}
