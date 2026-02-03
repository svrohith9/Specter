"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Execution = {
  id: string;
  intent: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms?: number | null;
};

type RunResult = {
  result?: {
    execution_id?: string;
    result?: unknown;
  };
  events?: { event: string; node?: string; error?: string; result?: unknown }[];
};

type ToolSpec = {
  name: string;
  description: string;
  params: Record<string, string>;
  category?: string;
  example?: string | null;
};

export default function RunPanel() {
  const [text, setText] = useState("");
  const [agent, setAgent] = useState("default");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<RunResult | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const [toolDetails, setToolDetails] = useState<ToolSpec[]>([]);
  const [selectedTool, setSelectedTool] = useState<ToolSpec | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [backendStatus, setBackendStatus] = useState("ok");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [view, setView] = useState<"summary" | "events">("summary");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<
    { id: string; summary: string; source_count: number; created_at: string }[]
  >([]);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [memoryType, setMemoryType] = useState("all");
  const [memoryLimit, setMemoryLimit] = useState(20);
  const [memoryTab, setMemoryTab] = useState<"summaries" | "entities" | "graph">("summaries");
  const [entities, setEntities] = useState<
    { id: string; type: string; name: string; relations?: { type: string; target_id: string }[] }[]
  >([]);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const inFlight = useRef(false);

  async function loadMeta() {
    if (inFlight.current) return;
    if (typeof document !== "undefined" && document.hidden) return;
    inFlight.current = true;
    try {
      const resp = await fetch("/api/meta");
      const meta = await resp.json();
      if (meta.errors?.tools || meta.errors?.executions) {
        setBackendStatus("offline");
        setTools([`Backend offline (${meta.errors.tools})`]);
      } else {
        setBackendStatus("ok");
        setTools(meta.tools ?? []);
        setToolDetails(meta.tool_details ?? []);
        if (!selectedTool && meta.tool_details?.length) {
          setSelectedTool(meta.tool_details[0]);
        }
      }
      if (meta.errors?.executions) {
        setExecutions([]);
      } else {
        setExecutions(meta.executions ?? []);
      }
      setLastUpdated(new Date().toLocaleTimeString());
    } finally {
      inFlight.current = false;
    }
  }

  async function loadSummaries() {
    try {
      const resp = await fetch("/api/memory/summary");
      const data = await resp.json();
      setSummaries(data.summaries ?? []);
    } catch {
      setSummaries([]);
    }
  }

  async function createSummary() {
    setMemoryBusy(true);
    try {
      await fetch("/api/memory/summarize", { method: "POST" });
      await loadSummaries();
    } finally {
      setMemoryBusy(false);
    }
  }

  async function searchEntities() {
    setMemoryBusy(true);
    try {
      const params = new URLSearchParams();
      if (memoryQuery.trim()) {
        params.set("q", memoryQuery);
      }
      if (memoryType !== "all") {
        params.set("type", memoryType);
      }
      params.set("limit", String(memoryLimit));
      const resp = await fetch(`/api/memory/entities?${params.toString()}`);
      const data = await resp.json();
      setEntities(data.entities ?? []);
    } finally {
      setMemoryBusy(false);
    }
  }

  useEffect(() => {
    loadMeta();
    loadSummaries();
    searchEntities();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => loadMeta(), 10000);
    return () => clearInterval(id);
  }, [autoRefresh]);

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

  const events = useMemo(() => last?.events ?? [], [last]);
  const loadingTools = tools.length === 0;
  const loadingExecs = executions.length === 0;

  const activeCount = executions.filter((ex) => ex.status === "running").length;
  const completedCount = executions.filter((ex) => ex.status === "completed").length;

  return (
    <div className="shell">
      <header className="hero">
        <div className="hero-copy">
          <div className="kicker">Specter Command Center</div>
          <h1>
            Orchestrate execution.
            <span>Move from intent to impact.</span>
          </h1>
          <p>
            Specter is a local-first autonomous agent that compiles tasks into parallel
            execution graphs, keeps a traceable audit trail, and responds with
            deterministic outputs.
          </p>
        </div>
        <div className="hero-status">
          <div className="badge">
            <div className="badge-title">Status</div>
            <div className={`badge-value ${backendStatus}`}>
              {backendStatus === "ok" ? "Live" : "Offline"}
            </div>
            <div className="badge-sub">Port 8000</div>
          </div>
          <div className="badge ghosted">
            <div className="badge-title">Agent</div>
            <div className="badge-value">Specter-1</div>
            <div className="badge-sub">Local runtime</div>
          </div>
        </div>
      </header>

      <section className="stats">
        <div className="stat-card">
          <div className="stat-label">Active runs</div>
          <div className="stat-value">{activeCount}</div>
          <div className="stat-meta">Execution graph nodes in flight</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Completed</div>
          <div className="stat-value">{completedCount}</div>
          <div className="stat-meta">Successful task completions</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Tools online</div>
          <div className="stat-value">{tools.length}</div>
          <div className="stat-meta">Skill registry footprint</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Last sync</div>
          <div className="stat-value">{lastUpdated ?? "—"}</div>
          <div className="stat-meta">Auto refresh {autoRefresh ? "enabled" : "paused"}</div>
        </div>
      </section>

      <section className="workspace">
        <div className="panel command">
          <div className="panel-head">
            <div>
              <h2>Command deck</h2>
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
          <div className="panel-foot">
            <label className="toggle">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span>Auto refresh</span>
            </label>
            <button className="ghost" onClick={loadMeta}>Refresh now</button>
          </div>
        </div>

        <div className="panel result">
          <div className="panel-head">
            <div>
              <h2>Live execution</h2>
              <p>Trace graph events and final payloads.</p>
            </div>
            <div className="row">
              <button
                className={`ghost ${view === "summary" ? "active" : ""}`}
                onClick={() => setView("summary")}
              >
                Summary
              </button>
              <button
                className={`ghost ${view === "events" ? "active" : ""}`}
                onClick={() => setView("events")}
              >
                Trace
              </button>
            </div>
          </div>
          {view === "summary" ? (
            <pre>{last ? JSON.stringify(last, null, 2) : "Run a task to see results."}</pre>
          ) : (
            <div className="trace">
              {events.length === 0 ? (
                <div className="muted">No events yet.</div>
              ) : (
                events.map((evt, idx) => (
                  <div key={idx} className="trace-row">
                    <span className="trace-dot" />
                    <div>
                      <div className="trace-title">{evt.event}</div>
                      {evt.node && <div className="muted">node: {evt.node}</div>}
                      {evt.error && <div className="trace-error">{evt.error}</div>}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </section>

      <section className="grid">
        <div className="card">
          <h3>Tool registry</h3>
          <div className="muted">Available skills in this runtime</div>
          <ul className="list">
            {loadingTools
              ? [1, 2, 3].map((i) => <li key={i} className="skeleton" />)
              : tools.map((tool) => (
                  <li key={tool}>
                    <button
                      className={`ghost list-button ${selectedTool?.name === tool ? "active" : ""}`}
                      onClick={() => {
                        const spec = toolDetails.find((item) => item.name === tool) || null;
                        setSelectedTool(spec);
                      }}
                    >
                      {tool}
                    </button>
                  </li>
                ))}
          </ul>
          <div className="inspector">
            <div className="muted">Tool inspector</div>
            {selectedTool ? (
              <div className="inspector-body">
                <div className="inspector-title">{selectedTool.name}</div>
                <div className="muted">{selectedTool.description}</div>
                {selectedTool.example && (
                  <div className="inspector-example">Example: {selectedTool.example}</div>
                )}
                <div className="inspector-params">
                  {Object.entries(selectedTool.params || {}).map(([key, val]) => (
                    <div key={key} className="param-row">
                      <span className="param-key">{key}</span>
                      <span className="param-type">{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="muted">Select a tool to inspect.</div>
            )}
          </div>
        </div>
        <div className="card">
          <h3>Execution timeline</h3>
          <div className="muted">Recent task runs and status</div>
          <ul className="list">
            {loadingExecs
              ? [1, 2, 3].map((i) => <li key={i} className="skeleton" />)
              : executions.map((ex) => (
                  <li key={ex.id}>
                    <div className="row">
                      <span className="mono">{ex.id}</span>
                      <span className={`status ${ex.status}`}>{ex.status}</span>
                    </div>
                    <div className="muted">{ex.intent}</div>
                    {ex.duration_ms != null && (
                      <div className="muted">Duration: {ex.duration_ms} ms</div>
                    )}
                  </li>
                ))}
          </ul>
        </div>
        <div className="card memory">
          <div className="row">
            <h3>Memory</h3>
            <button className="ghost" onClick={createSummary} disabled={memoryBusy}>
              {memoryBusy ? "Working…" : "Summarize"}
            </button>
          </div>
          <div className="memory-tabs">
            <button
              className={`ghost ${memoryTab === "summaries" ? "active" : ""}`}
              onClick={() => setMemoryTab("summaries")}
            >
              Summaries
            </button>
            <button
              className={`ghost ${memoryTab === "entities" ? "active" : ""}`}
              onClick={() => setMemoryTab("entities")}
            >
              Entities
            </button>
            <button
              className={`ghost ${memoryTab === "graph" ? "active" : ""}`}
              onClick={() => setMemoryTab("graph")}
            >
              Graph
            </button>
          </div>
          {memoryTab === "summaries" && (
            <>
              <div className="muted">Recent summaries</div>
              <ul className="list">
                {summaries.length === 0 ? (
                  <li className="muted">No summaries yet.</li>
                ) : (
                  summaries.map((s) => (
                    <li key={s.id}>
                      <div className="muted">{s.created_at}</div>
                      <div>{s.summary}</div>
                    </li>
                  ))
                )}
              </ul>
            </>
          )}
          <div className="memory-search">
            <input
              className="input"
              value={memoryQuery}
              onChange={(e) => setMemoryQuery(e.target.value)}
              placeholder="Search entities"
            />
            <select
              className="input select"
              value={memoryType}
              onChange={(e) => setMemoryType(e.target.value)}
            >
              <option value="all">All</option>
              <option value="person">Person</option>
              <option value="org">Org</option>
              <option value="location">Location</option>
              <option value="concept">Concept</option>
              <option value="url">URL</option>
              <option value="email">Email</option>
              <option value="number">Number</option>
            </select>
            <select
              className="input select"
              value={memoryLimit}
              onChange={(e) => setMemoryLimit(Number(e.target.value))}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
            <button className="ghost" onClick={searchEntities} disabled={memoryBusy}>
              Search
            </button>
          </div>
          {memoryTab === "entities" && entities.length > 0 && (
            <div className="entity-list">
              {entities.map((ent) => (
                <div key={ent.id} className="entity-row">
                  <div className="entity-title">{ent.name}</div>
                  <div className="muted">{ent.type}</div>
                  {ent.relations?.length ? (
                    <div className="muted">Relations: {ent.relations.length}</div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
          {memoryTab === "graph" && entities.length > 0 && (
            <div className="graph-surface">
              <svg viewBox="0 0 420 220" width="100%" height="220">
                {entities.slice(0, 12).map((ent, idx) => {
                  const col = idx % 4;
                  const row = Math.floor(idx / 4);
                  const x = 40 + col * 120;
                  const y = 30 + row * 70;
                  return (
                    <g key={ent.id}>
                      <circle cx={x} cy={y} r="18" fill="#1f6feb" opacity="0.15" />
                      <circle cx={x} cy={y} r="10" fill="#1f6feb" />
                      <text x={x + 16} y={y + 4} fontSize="10" fill="#1f2937">
                        {ent.name.slice(0, 10)}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          )}
        </div>
        <div className="card">
          <h3>Playbooks</h3>
          <div className="muted">Suggested operator prompts</div>
          <div className="playbook">
            <button
              onClick={() => setText("Summarize today’s tasks and draft a plan")}
              className="ghost"
            >
              Daily planning
            </button>
            <button
              onClick={() => setText("Draft a Q2 product launch checklist")}
              className="ghost"
            >
              Launch checklist
            </button>
            <button
              onClick={() => setText("Create a sales follow-up sequence for new leads")}
              className="ghost"
            >
              Sales follow-up
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
