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
  const [agent, setAgent] = useState("default");
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
        body: JSON.stringify({ text, agent_id: agent })
      });
      const data = await resp.json();
      setLast(data);
      await loadMeta();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <div className="kicker">Specter Control Plane</div>
          <h1>
            Command the execution layer.
            <span>Ship outcomes, not prompts.</span>
          </h1>
          <p>
            A local-first autonomous agent that turns intent into parallel execution.
          </p>
        </div>
        <div className="badge">
          <div className="badge-title">Status</div>
          <div className="badge-value">Live</div>
          <div className="badge-sub">Port 8000</div>
        </div>
      </header>

      <section className="control">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Run a task</h2>
              <p>Natural language in. Deterministic execution out.</p>
            </div>
            <div className="chip">Agent: {agent}</div>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Try: Create a launch plan for a new app with milestones"
          />
          <div className="row">
            <input
              className="input"
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
              placeholder="agent id"
            />
            <button className="primary" onClick={onRun} disabled={busy}>
              {busy ? "Executing…" : "Execute"}
            </button>
          </div>
        </div>

        <div className="panel result">
          <div className="panel-head">
            <div>
              <h2>Latest output</h2>
              <p>Execution trace and result payload.</p>
            </div>
            <button className="ghost" onClick={loadMeta}>Refresh</button>
          </div>
          <pre>{last ? JSON.stringify(last, null, 2) : "Run a task to see results."}</pre>
        </div>
      </section>

      <section className="grid">
        <div className="card">
          <h3>Tools</h3>
          <ul className="list">
            {tools.map((tool) => (
              <li key={tool}>{tool}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h3>Executions</h3>
          <ul className="list">
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
          <h3>Playbook</h3>
          <div className="muted">Suggested prompts</div>
          <div className="playbook">
            <button onClick={() => setText("Summarize today’s tasks and draft a plan")}
              className="ghost">
              Daily planning
            </button>
            <button onClick={() => setText("Draft a Q2 product launch checklist")}
              className="ghost">
              Launch checklist
            </button>
            <button onClick={() => setText("Create a sales follow-up sequence for new leads")}
              className="ghost">
              Sales follow-up
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
