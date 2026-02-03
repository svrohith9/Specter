import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const [toolsResp, execResp] = await Promise.all([
      fetch(`${backendUrl}/tools`, { cache: "no-store", signal: controller.signal }),
      fetch(`${backendUrl}/executions`, { cache: "no-store", signal: controller.signal })
    ]);
    const toolsJson = await toolsResp.json();
    const execJson = await execResp.json();
    return NextResponse.json(
      {
        tools: toolsJson.tools ?? [],
        tool_details: toolsJson.details ?? [],
        executions: execJson.executions ?? [],
        errors: {
          tools: toolsJson.error ?? null,
          executions: execJson.error ?? null
        }
      },
      { status: 200 }
    );
  } catch (err) {
    return NextResponse.json(
      { tools: [], executions: [], errors: { tools: "backend_unreachable", executions: "backend_unreachable" }, detail: String(err) },
      { status: 502 }
    );
  } finally {
    clearTimeout(timeout);
  }
}
