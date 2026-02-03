import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = url.searchParams.get("q") ?? "";
  const type = url.searchParams.get("type") ?? "";
  const limit = url.searchParams.get("limit") ?? "20";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (type && type !== "all") params.set("ent_type", type);
    params.set("limit", limit);
    const resp = await fetch(
      `${backendUrl}/knowledge/entities/list?user_id=local&${params.toString()}`,
      { cache: "no-store", signal: controller.signal }
    );
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
