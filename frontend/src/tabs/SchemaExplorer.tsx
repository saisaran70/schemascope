import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { AnalysisResult, EntityInfo } from "@/types/schema";

interface Props { result: AnalysisResult; }

export function SchemaExplorerTab({ result }: Props) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const tables = result.entities.filter((e) => e.entity_type === "table");
  const views = result.entities.filter((e) => e.entity_type === "view");
  const declared = result.relationships.filter((r) => r.declared);
  const totalFields = result.entities.reduce((n, e) => n + e.fields.length, 0);
  const high = result.findings.filter((f) => f.severity === "high").length;
  const medium = result.findings.filter((f) => f.severity === "medium").length;
  const low = result.findings.filter((f) => f.severity === "low").length;

  const filtered = result.entities.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase()),
  );

  function toggle(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

  return (
    <div className="space-y-6 pt-4">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Tables", value: tables.length },
          { label: "Views", value: views.length },
          { label: "Total Fields", value: totalFields },
          { label: "Relationships", value: declared.length },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="pt-5 pb-4">
              <div className="text-2xl font-bold">{value}</div>
              <div className="text-sm text-muted-foreground">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Findings badges */}
      <div className="flex gap-2 flex-wrap">
        {high > 0 && <Badge variant="destructive">High: {high}</Badge>}
        {medium > 0 && <Badge>Medium: {medium}</Badge>}
        {low > 0 && <Badge variant="secondary">Low: {low}</Badge>}
        {result.warnings.length > 0 && (
          <Badge variant="warning">{result.warnings.length} warning{result.warnings.length > 1 ? "s" : ""}</Badge>
        )}
      </div>

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-sm text-amber-800">⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Search */}
      <Input
        placeholder="Search entities…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {/* Entity list */}
      <div className="space-y-2">
        {filtered.length === 0 && (
          <p className="text-sm text-muted-foreground">No entities match.</p>
        )}
        {filtered.map((entity) => (
          <EntityCard
            key={entity.name}
            entity={entity}
            isExpanded={expanded.has(entity.name)}
            onToggle={() => toggle(entity.name)}
          />
        ))}
      </div>
    </div>
  );
}

function EntityCard({
  entity,
  isExpanded,
  onToggle,
}: {
  entity: EntityInfo;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <Card className="cursor-pointer select-none" onClick={onToggle}>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-medium flex items-center justify-between">
          <span className="flex items-center gap-2">
            <code className="text-sm">{entity.name}</code>
            <Badge variant="outline" className="text-xs capitalize">
              {entity.entity_type}
            </Badge>
            <span className="text-xs text-muted-foreground">{entity.fields.length} fields</span>
          </span>
          <span className="text-muted-foreground text-xs">{isExpanded ? "▲" : "▼"}</span>
        </CardTitle>
      </CardHeader>
      {isExpanded && (
        <CardContent className="px-4 pb-4 pt-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left border-b">
                  {["Field", "Type", "Nullable", "PK", "FK Target", "Default"].map((h) => (
                    <th key={h} className="pb-2 pr-4 text-muted-foreground font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entity.fields.map((f) => (
                  <tr key={f.name} className="border-b border-muted last:border-0">
                    <td className="py-1 pr-4 font-mono font-medium">{f.name}</td>
                    <td className="py-1 pr-4 text-muted-foreground">{f.data_type}</td>
                    <td className="py-1 pr-4">{f.nullable ? "✓" : "—"}</td>
                    <td className="py-1 pr-4">{f.primary_key ? <span className="text-primary font-bold">PK</span> : "—"}</td>
                    <td className="py-1 pr-4 text-muted-foreground">{f.foreign_key_target ?? "—"}</td>
                    <td className="py-1 text-muted-foreground">{f.default_value ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {entity.indexes.length > 0 && (
            <div className="mt-3 space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Indexes</p>
              {entity.indexes.map((idx, i) => (
                <p key={i} className="text-xs font-mono text-muted-foreground">
                  {idx.name}({idx.columns.join(", ")}){idx.unique ? " UNIQUE" : ""}
                </p>
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
