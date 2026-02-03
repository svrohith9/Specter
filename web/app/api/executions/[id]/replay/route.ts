import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function POST(_: Request, context: { params: { id: string } }) {
  const { id } = context.params;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const resp = await fetch(`${backendUrl}/executions/${id}/replay`, {
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
