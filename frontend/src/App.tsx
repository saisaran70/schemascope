import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ConnectTab } from "@/tabs/Connect";
import { SchemaExplorerTab } from "@/tabs/SchemaExplorer";
import { DiagramTab } from "@/tabs/Diagram";
import { RecommendationsTab } from "@/tabs/Recommendations";
import { downloadMarkdown, downloadJSON, downloadMermaid, restoreSession } from "@/api/client";
import type { AnalysisResult, Finding } from "@/types/schema";

const CACHE_KEY = "schemascope_cache";

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState("connect");
  const [exportError, setExportError] = useState("");
  const [restoring, setRestoring] = useState(true);

  // On mount: restore the last analysis from localStorage so the user doesn't
  // have to re-analyze after every page refresh or server restart.
  useEffect(() => {
    async function tryRestore() {
      try {
        const raw = localStorage.getItem(CACHE_KEY);
        if (!raw) return;
        const { result: cachedResult } = JSON.parse(raw) as { result: AnalysisResult };
        if (!cachedResult) return;
        const resp = await restoreSession(cachedResult);
        setResult(cachedResult);
        setSessionId(resp.session_id);
        setActiveTab("explorer");
      } catch {
        // Cache miss or server unavailable — start fresh, that's fine.
      } finally {
        setRestoring(false);
      }
    }
    tryRestore();
  }, []);

  function handleAnalysisComplete(r: AnalysisResult, sid: string) {
    setResult(r);
    setSessionId(sid);
    setActiveTab("explorer");
    // Persist so the next page load auto-restores without re-analysing.
    localStorage.setItem(CACHE_KEY, JSON.stringify({ result: r }));
  }

  function handleUpdateFindings(findings: Finding[]) {
    if (!result) return;
    setResult({ ...result, findings });
  }

  async function handleExport(fn: () => Promise<void>) {
    setExportError("");
    try { await fn(); }
    catch (err) { setExportError(err instanceof Error ? err.message : "Export failed."); }
  }

  const analyzed = !!result && !!sessionId;
  const openHighCount = result?.findings.filter((f) => f.review_status === "open" && f.severity === "high").length ?? 0;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold tracking-tight">SchemaScope</h1>
            {result && (
              <p className="text-xs text-muted-foreground">
                {result.analysis_metadata.source_name} · {result.analysis_metadata.entity_count} entities · {result.analysis_metadata.finding_count} findings
              </p>
            )}
          </div>
          {analyzed && (
            <div className="flex gap-2 flex-wrap justify-end">
              <Button variant="outline" size="sm" onClick={() => handleExport(() => downloadMarkdown(sessionId!))}>Markdown</Button>
              <Button variant="outline" size="sm" onClick={() => handleExport(() => downloadJSON(sessionId!))}>JSON</Button>
              <Button variant="outline" size="sm" onClick={() => handleExport(() => downloadMermaid(sessionId!))}>Mermaid</Button>
            </div>
          )}
        </div>
        {exportError && (
          <div className="max-w-6xl mx-auto px-6 pb-2">
            <p className="text-xs text-red-600">{exportError}</p>
          </div>
        )}
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {restoring && (
          <p className="text-sm text-muted-foreground mb-4">Restoring last session…</p>
        )}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="connect">Connect</TabsTrigger>
            <TabsTrigger value="explorer" disabled={!analyzed}>Schema Explorer</TabsTrigger>
            <TabsTrigger value="diagram" disabled={!analyzed}>ER Diagram</TabsTrigger>
            <TabsTrigger value="recommendations" disabled={!analyzed}>
              Recommendations
              {openHighCount > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-xs rounded-full bg-destructive text-destructive-foreground">
                  {openHighCount}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="connect">
            <ConnectTab onAnalysisComplete={handleAnalysisComplete} />
          </TabsContent>
          <TabsContent value="explorer">
            {result && <SchemaExplorerTab result={result} />}
          </TabsContent>
          <TabsContent value="diagram">
            {analyzed && result && (
              <DiagramTab
                sessionId={sessionId!}
                entityNames={result.entities.map((e) => e.name)}
              />
            )}
          </TabsContent>
          <TabsContent value="recommendations">
            {result && <RecommendationsTab result={result} onUpdateFindings={handleUpdateFindings} />}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
