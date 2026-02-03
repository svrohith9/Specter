import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "";
const fallback = {
  name: process.env.SPECTER_NAME ?? "Specter",
  default_agent: process.env.SPECTER_DEFAULT_AGENT ?? "default",
  default_user_id: process.env.SPECTER_DEFAULT_USER_ID ?? "local",
  data_dir: process.env.SPECTER_DATA_DIR ?? "./data",
  backend_url: backendUrl
};

export async function GET() {
  if (!backendUrl) {
    return NextResponse.json(fallback, { status: 200 });
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);
  try {
    const resp = await fetch(`${backendUrl}/config`, { cache: "no-store", signal: controller.signal });
    const data = await resp.json();
    return NextResponse.json({ ...fallback, ...data, backend_url: backendUrl }, { status: resp.status });
  } catch {
    return NextResponse.json(fallback, { status: 200 });
  } finally {
    clearTimeout(timeout);
  }
}
