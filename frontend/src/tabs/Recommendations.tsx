import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisResult, Finding, Severity } from "@/types/schema";

const SEVERITY_ORDER: Severity[] = ["high", "medium", "low", "information"];

const SEVERITY_VARIANT: Record<Severity, "destructive" | "default" | "secondary" | "outline"> = {
  high: "destructive",
  medium: "default",
  low: "secondary",
  information: "outline",
};

interface Props {
  result: AnalysisResult;
  onUpdateFindings: (findings: Finding[]) => void;
}

export function RecommendationsTab({ result, onUpdateFindings }: Props) {
  const [severityFilter, setSeverityFilter] = useState("all");
  const [entityFilter, setEntityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("open");

  const entities = Array.from(new Set(result.findings.map((f) => f.entity))).sort();

  const filtered = result.findings.filter((f) => {
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    if (entityFilter !== "all" && f.entity !== entityFilter) return false;
    if (statusFilter !== "all" && f.review_status !== statusFilter) return false;
    return true;
  });

  function updateStatus(finding: Finding, status: string) {
    onUpdateFindings(
      result.findings.map((f) =>
        f === finding ? { ...f, review_status: status as Finding["review_status"] } : f,
      ),
    );
  }

  const counts = { high: 0, medium: 0, low: 0, open: 0 };
  for (const f of result.findings) {
    if (f.severity === "high") counts.high++;
    if (f.severity === "medium") counts.medium++;
    if (f.severity === "low") counts.low++;
    if (f.review_status === "open") counts.open++;
  }

  return (
    <div className="space-y-5 pt-4">
      {/* Summary badges */}
      <div className="flex gap-2 flex-wrap">
        {counts.high > 0 && <Badge variant="destructive">High: {counts.high}</Badge>}
        {counts.medium > 0 && <Badge>Medium: {counts.medium}</Badge>}
        {counts.low > 0 && <Badge variant="secondary">Low: {counts.low}</Badge>}
        <Badge variant="outline">Open: {counts.open}</Badge>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        {[
          { label: "Severity", value: severityFilter, set: setSeverityFilter, options: ["all", ...SEVERITY_ORDER] },
          { label: "Entity", value: entityFilter, set: setEntityFilter, options: ["all", ...entities] },
          { label: "Status", value: statusFilter, set: setStatusFilter, options: ["all", "open", "accepted", "ignored"] },
        ].map(({ label, value, set, options }) => (
          <div key={label} className="space-y-1">
            <p className="text-xs text-muted-foreground">{label}</p>
            <select
              className="border border-input rounded-md px-3 py-1.5 text-sm bg-background"
              value={value}
              onChange={(e) => set(e.target.value)}
            >
              {options.map((o) => (
                <option key={o} value={o}>{o === "all" ? `All ${label}s` : o}</option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">No findings match the current filters.</p>
      )}

      {/* Findings grouped by severity */}
      {SEVERITY_ORDER.map((severity) => {
        const group = filtered.filter((f) => f.severity === severity);
        if (group.length === 0) return null;
        return (
          <div key={severity}>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={SEVERITY_VARIANT[severity]}>{severity.toUpperCase()}</Badge>
              <span className="text-xs text-muted-foreground">{group.length} finding{group.length > 1 ? "s" : ""}</span>
            </div>
            <div className="space-y-2">
              {group.map((f, i) => (
                <FindingCard key={i} finding={f} onUpdateStatus={(s) => updateStatus(f, s)} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FindingCard({
  finding: f,
  onUpdateStatus,
}: {
  finding: Finding;
  onUpdateStatus: (status: string) => void;
}) {
  const [showCmd, setShowCmd] = useState(false);
  const [cmdCopied, setCmdCopied] = useState(false);

  async function copyCmd() {
    if (!f.suggested_command) return;
    await navigator.clipboard.writeText(f.suggested_command);
    setCmdCopied(true);
    setTimeout(() => setCmdCopied(false), 2000);
  }

  return (
    <Card className={f.review_status !== "open" ? "opacity-60" : ""}>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm flex items-center justify-between gap-2">
          <span className="flex items-center gap-2 flex-wrap">
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{f.rule_id}</code>
            <span className="font-medium">{f.title}</span>
          </span>
          <Badge variant="outline" className="text-xs shrink-0 capitalize">{f.review_status}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0 space-y-2 text-sm">
        <p className="text-muted-foreground">
          Entity: <code className="text-foreground font-medium">{f.entity}</code>
          {f.field && <> / <code className="text-foreground font-medium">{f.field}</code></>}
          {f.confidence != null && (
            <span className="ml-2 text-xs">({Math.round(f.confidence * 100)}% confidence)</span>
          )}
        </p>
        <p>{f.description}</p>
        <div>
          <p className="font-medium text-xs text-muted-foreground uppercase tracking-wide mb-1">Evidence</p>
          <ul className="list-disc list-inside space-y-0.5 text-muted-foreground text-xs">
            {f.evidence.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
        <p><span className="font-medium">Impact:</span> {f.impact}</p>
        <p><span className="font-medium">Recommendation:</span> {f.recommendation}</p>

        {f.suggested_command && (
          <div>
            <button
              className="text-xs text-blue-600 underline-offset-2 hover:underline"
              onClick={() => setShowCmd((v) => !v)}
            >
              {showCmd ? "Hide" : "Show"} suggested command
            </button>
            {showCmd && (
              <div className="mt-2 relative">
                <pre className="bg-muted rounded-md px-4 py-3 text-xs overflow-x-auto pr-16">
                  {f.suggested_command}
                </pre>
                <button
                  className="absolute top-2 right-2 text-xs px-2 py-1 bg-background border rounded hover:bg-accent"
                  onClick={copyCmd}
                >
                  {cmdCopied ? "✓" : "Copy"}
                </button>
                <p className="text-xs text-amber-700 mt-1">
                  ⚠ Review only — never execute without a backup.
                </p>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 pt-1">
          {f.review_status !== "accepted" && (
            <Button variant="outline" size="sm" onClick={() => onUpdateStatus("accepted")}>
              Accept
            </Button>
          )}
          {f.review_status !== "ignored" && (
            <Button variant="ghost" size="sm" onClick={() => onUpdateStatus("ignored")}>
              Ignore
            </Button>
          )}
          {f.review_status !== "open" && (
            <Button variant="ghost" size="sm" onClick={() => onUpdateStatus("open")}>
              Reopen
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
