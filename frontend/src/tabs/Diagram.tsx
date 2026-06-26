import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Button } from "@/components/ui/button";
import { fetchDiagram, downloadMermaid } from "@/api/client";

// Initialize once at module level — avoids React StrictMode double-init races.
mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

// Module-level counter — each render call gets a DOM id that has never existed before.
let _erId = 0;

const OVER_LIMIT_MARKER = "%% Schema has";

interface Props {
  sessionId: string;
  entityNames: string[];
}

export function DiagramTab({ sessionId, entityNames }: Props) {
  const [svgContent, setSvgContent] = useState("");
  const [source, setSource] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [maximized, setMaximized] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Entity filter state — starts empty (= "show all up to 200").
  const [filterOpen, setFilterOpen] = useState(false);
  const [checkedEntities, setCheckedEntities] = useState<Set<string>>(new Set());
  const [entitySearch, setEntitySearch] = useState("");

  // Trigger is bumped when the user clicks "Render selected".
  const [renderTrigger, setRenderTrigger] = useState(0);

  // Focus the overlay div when maximized so Escape key closes it immediately.
  useEffect(() => {
    if (maximized) overlayRef.current?.focus();
  }, [maximized]);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      setSvgContent("");

      const selected = checkedEntities.size > 0 ? Array.from(checkedEntities) : undefined;

      try {
        const src = await fetchDiagram(sessionId, selected);
        if (!active) return;
        setSource(src);

        if (src.includes(OVER_LIMIT_MARKER)) {
          // Too many entities — expose the filter panel, don't try to render.
          setFilterOpen(true);
          setLoading(false);
          return;
        }

        const id = `schemascope_er_${++_erId}`;
        const { svg } = await mermaid.render(id, src);
        if (!active) return;
        setSvgContent(svg);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof Error
            ? err.message
            : "Could not render diagram. Use 'Download .mmd' to open it in Mermaid Live Editor.",
        );
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, renderTrigger]);

  function toggleEntity(name: string) {
    setCheckedEntities((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

  function selectAll() { setCheckedEntities(new Set(entityNames)); }
  function clearAll()  { setCheckedEntities(new Set()); }

  async function handleCopy() {
    await navigator.clipboard.writeText(source);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const visibleEntities = entityNames.filter((n) =>
    n.toLowerCase().includes(entitySearch.toLowerCase()),
  );

  return (
    <div className="space-y-4 pt-4">
      {/* Toolbar */}
      <div className="flex gap-2 flex-wrap items-center">
        <Button variant="outline" size="sm" onClick={handleCopy} disabled={!source}>
          {copied ? "✓ Copied" : "Copy Source"}
        </Button>
        <Button variant="outline" size="sm" onClick={() => downloadMermaid(sessionId)}>
          Download .mmd
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFilterOpen((v) => !v)}
        >
          {filterOpen ? "Hide" : "Filter"} entities
          {checkedEntities.size > 0 && (
            <span className="ml-1 text-xs text-primary">({checkedEntities.size} selected)</span>
          )}
        </Button>
        {(filterOpen || checkedEntities.size > 0) && (
          <Button
            size="sm"
            onClick={() => setRenderTrigger((n) => n + 1)}
            disabled={loading}
          >
            {loading ? "Rendering…" : "Render diagram"}
          </Button>
        )}
        {svgContent && (
          <Button variant="outline" size="sm" onClick={() => setMaximized(true)}>
            ⛶ Maximize
          </Button>
        )}
      </div>

      {/* Entity filter panel */}
      {filterOpen && (
        <div className="border rounded-lg p-4 space-y-3 bg-muted/30">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">
              Select entities to include ({entityNames.length} total)
            </p>
            <div className="flex gap-2">
              <button type="button" onClick={selectAll} className="text-xs text-primary underline-offset-2 hover:underline">
                Select all
              </button>
              <button type="button" onClick={clearAll} className="text-xs text-muted-foreground underline-offset-2 hover:underline">
                Clear
              </button>
            </div>
          </div>
          <input
            type="text"
            placeholder="Search entities…"
            value={entitySearch}
            onChange={(e) => setEntitySearch(e.target.value)}
            className="w-full border rounded-md px-3 py-1.5 text-sm bg-background"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1 max-h-56 overflow-y-auto">
            {visibleEntities.map((name) => (
              <label key={name} className="flex items-center gap-1.5 text-xs cursor-pointer hover:bg-accent rounded px-1 py-0.5">
                <input
                  type="checkbox"
                  checked={checkedEntities.has(name)}
                  onChange={() => toggleEntity(name)}
                  className="shrink-0"
                />
                <span className="font-mono truncate">{name}</span>
              </label>
            ))}
          </div>
          {checkedEntities.size === 0 && (
            <p className="text-xs text-muted-foreground">
              No entities selected — clicking "Render diagram" will show all (up to 200).
            </p>
          )}
        </div>
      )}

      {loading && <p className="text-sm text-muted-foreground">Rendering diagram…</p>}

      {error && (
        <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          {error}
        </div>
      )}

      {/* SVG stored in state — safe because it comes from the local Mermaid library. */}
      {svgContent && (
        <div className="border rounded-lg bg-white overflow-auto max-h-[680px] p-4">
          <div
            className="flex justify-center"
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        </div>
      )}

      {/* Always expose raw source for copy/paste into mermaid.live */}
      {source && (
        <details className="text-sm" open={!!error && !svgContent}>
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground select-none">
            {error ? "Show raw Mermaid source (paste into mermaid.live)" : "Show Mermaid source"}
          </summary>
          <pre className="mt-2 bg-muted rounded-md p-4 text-xs overflow-x-auto">{source}</pre>
        </details>
      )}

      {/* Fullscreen overlay */}
      {maximized && svgContent && (
        <div
          ref={overlayRef}
          className="fixed inset-0 z-50 bg-white flex flex-col"
          onKeyDown={(e) => e.key === "Escape" && setMaximized(false)}
          tabIndex={-1}
        >
          {/* Overlay toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b bg-white shrink-0">
            <span className="text-sm font-medium text-muted-foreground">ER Diagram — fullscreen</span>
            <button
              type="button"
              onClick={() => setMaximized(false)}
              className="text-sm px-3 py-1 rounded border hover:bg-accent"
            >
              ✕ Close
            </button>
          </div>
          {/* Scrollable diagram area */}
          <div className="flex-1 overflow-auto p-6">
            <div
              className="flex justify-center"
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
