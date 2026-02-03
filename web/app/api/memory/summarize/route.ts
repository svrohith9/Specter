import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const url = new URL(request.url);
  const userId = url.searchParams.get("user_id") ?? "";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    const resp = await fetch(`${backendUrl}/knowledge/summarize${query}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal
    });
    const data = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    return NextResponse.json(
      { error: "backend_unreachable", detail: String(err) },
      { status: 502 }
    );
  } finally {
    clearTimeout(timeout);
  }
}
