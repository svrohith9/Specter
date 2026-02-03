"use client";

import { useEffect, useState } from "react";

type Execution = {
  id: string;
  intent: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
};

type RunResult = {
  result?: {
    execution_id?: string;
    result?: unknown;
  };
  events?: unknown[];
};

export default function RunPanel() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<RunResult | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);

  async function loadMeta() {
    const [toolsResp, execResp] = await Promise.all([
      fetch("/api/tools"),
      fetch("/api/executions")
    ]);
    const toolsJson = await toolsResp.json();
    const execJson = await execResp.json();
    setTools(toolsJson.tools ?? []);
    setExecutions(execJson.executions ?? []);
  }

  useEffect(() => {
    loadMeta();
  }, []);

  async function onRun() {
    if (!text.trim()) return;
    setBusy(true);
    setLast(null);
    try {
      const resp = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      const data = await resp.json();
      setLast(data);
      await loadMeta();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">Specter Control</div>
          <h1>Execution-First Workspace</h1>
          <p>Run a task, inspect tool availability, and replay outputs.</p>
        </div>
        <button className="ghost" onClick={loadMeta}>Refresh</button>
      </div>

      <div className="input-row">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Try: Summarize today’s tasks and draft a plan"
        />
        <button className="primary" onClick={onRun} disabled={busy}>
          {busy ? "Running..." : "Execute"}
        </button>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Tools</h3>
          <ul>
            {tools.map((tool) => (
              <li key={tool}>{tool}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>Recent Executions</h3>
          <ul>
            {executions.map((ex) => (
              <li key={ex.id}>
                <div className="row">
                  <span className="mono">{ex.id}</span>
                  <span className={`status ${ex.status}`}>{ex.status}</span>
                </div>
                <div className="muted">{ex.intent}</div>
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>Latest Result</h3>
          <pre>{last ? JSON.stringify(last, null, 2) : "Run something"}</pre>
        </div>
      </div>
    </div>
  );
}
