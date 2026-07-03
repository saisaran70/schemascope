import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { connectSQLite, connectMySQL, connectSQLDump, analyzeDb } from "@/api/client";
import type { AnalysisResult, MySQLParams } from "@/types/schema";

type DbType = "sqlite" | "mysql" | "sqldump";
type Status = "idle" | "connecting" | "connected" | "analyzing" | "done" | "error";

interface ConnectTabProps {
  onAnalysisComplete: (result: AnalysisResult, sessionId: string) => void;
}

export function ConnectTab({ onAnalysisComplete }: ConnectTabProps) {
  const [dbType, setDbType] = useState<DbType>("sqlite");
  const [file, setFile] = useState<File | null>(null);
  const [connectedName, setConnectedName] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");

  const [host, setHost] = useState("localhost");
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [port, setPort] = useState("3306");

  // File-based connections: auto-connect as soon as a file is chosen.
  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setError("");
    setStatus("connecting");
    try {
      const resp = dbType === "sqldump"
        ? await connectSQLDump(selected)
        : await connectSQLite(selected);
      setSessionId(resp.session_id);
      setConnectedName(resp.source_name);
      setStatus("connected");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed.");
      setStatus("error");
    }
  }

  // MySQL: explicit button click to connect.
  async function handleMySQLConnect() {
    setError("");
    setStatus("connecting");
    try {
      const params: MySQLParams = {
        host, database, username, password,
        port: Number(port) || 3306,
        ssl: false, timeout: 10,
      };
      const resp = await connectMySQL(params);
      setSessionId(resp.session_id);
      setConnectedName(resp.source_name);
      setStatus("connected");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed.");
      setStatus("error");
    }
  }

  async function handleAnalyze() {
    if (!sessionId) return;
    setStatus("analyzing");
    setError("");
    try {
      const result = await analyzeDb(sessionId);
      setStatus("done");
      onAnalysisComplete(result, sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
      setStatus("error");
    }
  }

  function handleReset() {
    setSessionId(null);
    setStatus("idle");
    setError("");
    setFile(null);
    setConnectedName("");
  }

  const isConnected = status === "connected" || status === "analyzing" || status === "done";

  return (
    <div className="max-w-xl space-y-6 pt-4">
      <div className="rounded-md bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
        SchemaScope is <strong>read-only</strong>. No data will be modified.
      </div>

      {/* DB type toggle */}
      <div className="flex gap-2">
        {([
          { id: "sqldump", label: "SQL Dump (.sql)" },
          { id: "sqlite",  label: "SQLite (.db)" },
          { id: "mysql",   label: "MySQL / Workbench" },
        ] as { id: DbType; label: string }[]).map((t) => (
          <button
            key={t.id}
            onClick={() => { setDbType(t.id); handleReset(); }}
            className={`px-4 py-2 rounded-md border text-sm font-medium transition-colors ${
              dbType === t.id
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background border-input hover:bg-accent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* SQL Dump: file picker — parses CREATE TABLE DDL, no live DB needed */}
      {dbType === "sqldump" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">SQL Dump File</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="sql-file">
                Choose a MySQL dump file (.sql) — schema is parsed automatically
              </Label>
              <Input
                id="sql-file"
                type="file"
                accept=".sql"
                onChange={handleFileChange}
                disabled={status === "connecting" || isConnected}
              />
            </div>
            {status === "connecting" && (
              <p className="text-sm text-muted-foreground">Parsing SQL dump…</p>
            )}
            {isConnected && (
              <p className="text-sm text-green-700">
                ✓ Parsed <strong>{connectedName}</strong>
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* SQLite: file picker — connecting happens automatically on file select */}
      {dbType === "sqlite" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">SQLite Database</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="db-file">
                Choose a database file — connection is tested automatically
              </Label>
              <Input
                id="db-file"
                type="file"
                accept=".db,.sqlite,.sqlite3"
                onChange={handleFileChange}
                disabled={status === "connecting" || isConnected}
              />
            </div>
            {status === "connecting" && (
              <p className="text-sm text-muted-foreground">Connecting…</p>
            )}
            {isConnected && (
              <p className="text-sm text-green-700">
                ✓ Connected to <strong>{connectedName}</strong>
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* MySQL form */}
      {dbType === "mysql" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">MySQL / Workbench</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Host</Label>
                <Input value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" disabled={isConnected} />
              </div>
              <div className="space-y-1.5">
                <Label>Port</Label>
                <Input value={port} onChange={(e) => setPort(e.target.value)} placeholder="3306" disabled={isConnected} />
              </div>
              <div className="space-y-1.5">
                <Label>Database</Label>
                <Input value={database} onChange={(e) => setDatabase(e.target.value)} placeholder="my_database" disabled={isConnected} />
              </div>
              <div className="space-y-1.5">
                <Label>Username</Label>
                <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="root" disabled={isConnected} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Password</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={isConnected} />
            </div>
            {!isConnected && (
              <Button
                onClick={handleMySQLConnect}
                disabled={status === "connecting" || !database || !username}
                className="w-full"
              >
                {status === "connecting" ? "Connecting…" : "Test Connection"}
              </Button>
            )}
            {isConnected && (
              <p className="text-sm text-green-700">✓ Connected to <strong>{connectedName}</strong></p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Action buttons — shown after connection */}
      {isConnected && (
        <div className="flex gap-3 flex-wrap items-center">
          {status === "connected" && (
            <Button onClick={handleAnalyze}>Analyse Database</Button>
          )}
          {status === "analyzing" && (
            <Button disabled>Analysing…</Button>
          )}
          {status === "done" && (
            <span className="text-sm text-green-700">✓ Analysis complete — see other tabs</span>
          )}
          <Button variant="outline" size="sm" onClick={handleReset}>
            {status === "done" ? "Start Over" : "Disconnect"}
          </Button>
        </div>
      )}

      {status === "error" && (
        <Button variant="outline" onClick={handleReset}>Try Again</Button>
      )}
    </div>
  );
}
