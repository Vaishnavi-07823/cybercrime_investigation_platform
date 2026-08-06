import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE, api } from "./api";

type CaseRecord = {
  id: string;
  title: string;
  description?: string;
  status: string;
  severity: string;
  case_type: string;
  context: Record<string, unknown>;
};

type Evidence = {
  id: string;
  original_filename: string;
  source_type: string;
  sha256: string;
  processed: boolean;
};

type EventRecord = {
  id: string;
  event_time: string;
  event_type: string;
  event_action: string;
  actor: Record<string, unknown>;
  source: Record<string, unknown>;
};

type Finding = {
  id: string;
  title: string;
  severity: string;
  confidence: number;
  explanation: string[];
  evidence_refs: string[];
};

type Entity = {
  id: string;
  entity_type: string;
  display_value: string;
};

type Claim = {
  id: string;
  text: string;
  reasoning_type: string;
  confidence: string;
  evidence_refs: string[];
  event_refs: string[];
  limitations: string[];
  status: string;
};

type Report = {
  id: string;
  created_at: string;
  pdf_sha256: string;
  json_sha256: string;
};

const initialLogin = { email: "admin@example.local", password: "ChangeMeNow!123" };

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("cip_token") ?? "");
  const [login, setLogin] = useState(initialLogin);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [message, setMessage] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("BEC Investigation Demo");

  const selectedCase = useMemo(
    () => cases.find((item) => item.id === selectedId),
    [cases, selectedId]
  );

  const run = useCallback(async (label: string, fn: () => Promise<void>) => {
    setBusy(true);
    setMessage(label);
    try {
      await fn();
      setMessage(`${label} — completed`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }, []);

  const loadCases = useCallback(async () => {
    if (!token) return;
    const data = await api<CaseRecord[]>("/cases", {}, token);
    setCases(data);
    if (!selectedId && data[0]) setSelectedId(data[0].id);
  }, [token, selectedId]);

  const loadCaseData = useCallback(async () => {
    if (!token || !selectedId) return;
    const [e, ev, f, en, c, r] = await Promise.all([
      api<Evidence[]>(`/cases/${selectedId}/evidence`, {}, token),
      api<EventRecord[]>(`/cases/${selectedId}/events`, {}, token),
      api<Finding[]>(`/cases/${selectedId}/findings`, {}, token),
      api<Entity[]>(`/cases/${selectedId}/entities`, {}, token),
      api<Claim[]>(`/cases/${selectedId}/claims`, {}, token),
      api<Report[]>(`/cases/${selectedId}/reports`, {}, token)
    ]);
    setEvidence(e);
    setEvents(ev);
    setFindings(f);
    setEntities(en);
    setClaims(c);
    setReports(r);
  }, [token, selectedId]);

  useEffect(() => {
    loadCases().catch((error) => setMessage(String(error)));
  }, [loadCases]);

  useEffect(() => {
    loadCaseData().catch((error) => setMessage(String(error)));
  }, [loadCaseData]);

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    await run("Signing in", async () => {
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(login)
      });
      localStorage.setItem("cip_token", result.access_token);
      setToken(result.access_token);
    });
  }

  async function createCase(event: FormEvent) {
    event.preventDefault();
    await run("Creating case", async () => {
      const created = await api<CaseRecord>(
        "/cases",
        {
          method: "POST",
          body: JSON.stringify({
            title: newCaseTitle,
            description: "Business Email Compromise investigation",
            case_type: "bec",
            severity: "high",
            context: { trusted_domains: ["trusted-supplier.example"] }
          })
        },
        token
      );
      await loadCases();
      setSelectedId(created.id);
    });
  }

  async function uploadEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await run("Uploading evidence", async () => {
      await api(`/cases/${selectedId}/evidence`, { method: "POST", body: formData }, token);
      form.reset();
      await loadCaseData();
    });
  }

  async function processAll() {
    await run("Processing evidence", async () => {
      for (const item of evidence.filter((entry) => !entry.processed)) {
        await api(`/evidence/${item.id}/process`, { method: "POST" }, token);
      }
      await loadCaseData();
    });
  }

  async function action(path: string, label: string) {
    await run(label, async () => {
      await api(path, { method: "POST" }, token);
      await loadCaseData();
    });
  }

  async function reviewClaim(claimId: string, decision: "approved" | "rejected") {
    await run(`Marking claim ${decision}`, async () => {
      await api(
        `/claims/${claimId}/review`,
        { method: "PATCH", body: JSON.stringify({ decision }) },
        token
      );
      await loadCaseData();
    });
  }


  async function downloadReport(reportId: string, formatName: "pdf" | "json") {
    await run(`Downloading ${formatName.toUpperCase()} report`, async () => {
      const response = await fetch(`${API_BASE}/reports/${reportId}/download/${formatName}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${reportId}.${formatName}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    });
  }

  function signOut() {
    localStorage.removeItem("cip_token");
    setToken("");
    setCases([]);
    setSelectedId("");
  }

  if (!token) {
    return (
      <main className="login-shell">
        <form className="panel login-card" onSubmit={submitLogin}>
          <p className="eyebrow">Evidence-first investigation</p>
          <h1>Cybercrime Investigation Platform</h1>
          <label>Email<input value={login.email} onChange={(e) => setLogin({ ...login, email: e.target.value })} /></label>
          <label>Password<input type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} /></label>
          <button disabled={busy}>Sign in</button>
          <p className="status">{message}</p>
        </form>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header>
        <div><p className="eyebrow">Analyst workspace</p><h1>Cybercrime Investigation Platform</h1></div>
        <div className="header-actions"><span>{message}</span><button className="secondary" onClick={signOut}>Sign out</button></div>
      </header>

      <aside>
        <form onSubmit={createCase} className="compact-form">
          <input value={newCaseTitle} onChange={(e) => setNewCaseTitle(e.target.value)} />
          <button disabled={busy}>Create case</button>
        </form>
        <h2>Cases</h2>
        {cases.map((item) => (
          <button key={item.id} className={`case-button ${selectedId === item.id ? "active" : ""}`} onClick={() => setSelectedId(item.id)}>
            <strong>{item.title}</strong><small>{item.id}</small><span>{item.severity} · {item.status}</span>
          </button>
        ))}
      </aside>

      <main className="workspace">
        {!selectedCase ? <div className="panel">Create or select a case.</div> : <>
          <section className="panel hero">
            <div><p className="eyebrow">{selectedCase.id}</p><h2>{selectedCase.title}</h2><p>{selectedCase.description}</p></div>
            <div className="action-grid">
              <button onClick={processAll} disabled={busy}>Process evidence</button>
              <button onClick={() => action(`/cases/${selectedId}/detections/run`, "Running detections")} disabled={busy}>Run detections</button>
              <button onClick={() => action(`/cases/${selectedId}/correlations/run`, "Building correlations")} disabled={busy}>Build graph</button>
              <button onClick={() => action(`/cases/${selectedId}/narratives/generate`, "Generating narrative")} disabled={busy}>Generate claims</button>
              <button onClick={() => action(`/cases/${selectedId}/reports/generate`, "Generating report")} disabled={busy}>Generate report</button>
            </div>
          </section>

          <section className="panel">
            <h2>Upload evidence</h2>
            <form onSubmit={uploadEvidence} className="upload-form">
              <select name="source_type" defaultValue="email">
                <option value="email">Email (.eml)</option>
                <option value="auth_log">Authentication JSON</option>
                <option value="mailbox_audit">Mailbox audit JSON</option>
                <option value="generic_json">Generic business-event JSON</option>
              </select>
              <input type="file" name="file" required />
              <button disabled={busy}>Upload</button>
            </form>
          </section>

          <section className="grid two">
            <div className="panel"><h2>Evidence ({evidence.length})</h2>{evidence.map((item) => <article key={item.id} className="item"><strong>{item.original_filename}</strong><span>{item.source_type} · {item.processed ? "processed" : "pending"}</span><code>{item.sha256.slice(0, 24)}…</code></article>)}</div>
            <div className="panel"><h2>Entities ({entities.length})</h2>{entities.map((item) => <article key={item.id} className="item"><strong>{item.entity_type}</strong><span>{item.display_value}</span></article>)}</div>
          </section>

          <section className="panel"><h2>Timeline ({events.length})</h2><div className="timeline">{events.map((item) => <article key={item.id} className="timeline-row"><time>{new Date(item.event_time).toLocaleString()}</time><div><strong>{item.event_type}</strong><span>{item.event_action}</span><code>{JSON.stringify(item.actor)} → {JSON.stringify(item.source)}</code></div></article>)}</div></section>

          <section className="panel"><h2>Findings ({findings.length})</h2><div className="cards">{findings.map((item) => <article key={item.id} className={`finding severity-${item.severity}`}><div><span className="badge">{item.severity}</span><strong>{item.title}</strong></div><p>{item.explanation.join(" ")}</p><small>Confidence {(item.confidence * 100).toFixed(0)}% · Evidence {item.evidence_refs.join(", ")}</small></article>)}</div></section>

          <section className="panel"><h2>AI / deterministic claims ({claims.length})</h2>{claims.map((item) => <article key={item.id} className="claim"><div className="claim-head"><span className="badge">{item.status}</span><span>{item.reasoning_type} · {item.confidence}</span></div><p>{item.text}</p><small>Evidence: {[...item.evidence_refs, ...item.event_refs].join(", ")}</small><p className="limitation">{item.limitations.join(" ")}</p>{item.status === "draft" && <div className="row"><button onClick={() => reviewClaim(item.id, "approved")}>Approve</button><button className="danger" onClick={() => reviewClaim(item.id, "rejected")}>Reject</button></div>}</article>)}</section>

          <section className="panel"><h2>Reports ({reports.length})</h2>{reports.map((item) => <article key={item.id} className="item"><strong>{item.id}</strong><span>{new Date(item.created_at).toLocaleString()}</span><div className="row"><button onClick={() => downloadReport(item.id, "pdf")}>Download PDF</button><button className="secondary" onClick={() => downloadReport(item.id, "json")}>Download JSON</button><code>{item.pdf_sha256.slice(0, 20)}…</code></div></article>)}</section>
        </>}
      </main>
    </div>
  );
}

export default App;
