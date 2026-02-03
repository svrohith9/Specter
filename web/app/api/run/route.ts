import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const body = await request.json();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const resp = await fetch(`${backendUrl}/webhook/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
