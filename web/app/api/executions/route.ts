import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  const resp = await fetch(`${backendUrl}/executions`, { cache: "no-store" });
  const data = await resp.json();
  return NextResponse.json(data, { status: resp.status });
}
