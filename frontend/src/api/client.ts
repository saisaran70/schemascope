import type { AnalysisResult, ConnectResponse, MySQLParams } from "@/types/schema";

const BASE = "/api";

function sessionHeaders(sessionId: string): Record<string, string> {
  return { "x-session-id": sessionId };
}

async function checkResponse(res: Response): Promise<Response> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // keep default
    }
    throw new Error(detail);
  }
  return res;
}

export async function connectSQLite(file: File): Promise<ConnectResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/connect/sqlite`, { method: "POST", body: form });
  await checkResponse(res);
  return res.json();
}

export async function connectMySQL(params: MySQLParams): Promise<ConnectResponse> {
  const res = await fetch(`${BASE}/connect/mysql`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  await checkResponse(res);
  return res.json();
}

export async function analyzeDb(sessionId: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: sessionHeaders(sessionId),
  });
  await checkResponse(res);
  return res.json();
}

export async function fetchMermaidSource(sessionId: string): Promise<string> {
  const res = await fetch(`${BASE}/export/mermaid`, {
    headers: sessionHeaders(sessionId),
  });
  await checkResponse(res);
  return res.text();
}

/** Fetch Mermaid source for in-browser rendering.
 *  Pass entities[] to limit the diagram to a subset; omit to show all (up to maxEntities). */
export async function fetchDiagram(
  sessionId: string,
  entities?: string[],
  maxEntities = 200,
): Promise<string> {
  const params = new URLSearchParams({ max_entities: String(maxEntities) });
  if (entities && entities.length > 0) {
    entities.forEach((e) => params.append("entities", e));
  }
  const res = await fetch(`${BASE}/diagram?${params}`, {
    headers: sessionHeaders(sessionId),
  });
  await checkResponse(res);
  return res.text();
}

export async function disconnect(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: "DELETE" });
}

export async function restoreSession(cachedResult: object): Promise<ConnectResponse> {
  const res = await fetch(`${BASE}/sessions/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cachedResult),
  });
  await checkResponse(res);
  return res.json();
}

async function triggerDownload(
  sessionId: string,
  endpoint: string,
): Promise<void> {
  const res = await fetch(`${BASE}${endpoint}`, {
    headers: sessionHeaders(sessionId),
  });
  await checkResponse(res);
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") ?? "";
  const match = cd.match(/filename="([^"]+)"/);
  const filename = match?.[1] ?? "schemascope_export";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const downloadMarkdown = (sid: string) => triggerDownload(sid, "/export/markdown");
export const downloadJSON = (sid: string) => triggerDownload(sid, "/export/json");
export const downloadMermaid = (sid: string) => triggerDownload(sid, "/export/mermaid");
