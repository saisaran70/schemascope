import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Button } from "@/components/ui/button";
import { fetchDiagram, downloadMermaid } from "@/api/client";

mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });

let _erId = 0;
const OVER_LIMIT_MARKER = "%% Schema has";

// ---------------------------------------------------------------------------
// Module detection & colour mapping
// ---------------------------------------------------------------------------

const MODULES = ["all", "patient", "doctor", "mco"] as const;
type Module = (typeof MODULES)[number];

const MODULE_META: Record<string, { bg: string; header: string; pill: string; label: string }> = {
  patient:       { bg: "#dbeafe", header: "#bfdbfe", pill: "#3b82f6", label: "Patient" },
  doctor:        { bg: "#dcfce7", header: "#bbf7d0", pill: "#22c55e", label: "Doctor"  },
  mco:           { bg: "#fef9c3", header: "#fef08a", pill: "#ca8a04", label: "MCO"     },
  booking:       { bg: "#fae8ff", header: "#f5d0fe", pill: "#a855f7", label: "Booking" },
  payment:       { bg: "#fce7f3", header: "#fbcfe8", pill: "#ec4899", label: "Payment" },
  auth:          { bg: "#e0f2fe", header: "#bae6fd", pill: "#0ea5e9", label: "Auth"    },
  notifications: { bg: "#ecfdf5", header: "#a7f3d0", pill: "#10b981", label: "Notifications" },
  admin:         { bg: "#f1f5f9", header: "#e2e8f0", pill: "#64748b", label: "Admin"   },
  other:         { bg: "#f8fafc", header: "#e2e8f0", pill: "#94a3b8", label: "Other"   },
};

// Which modules appear in the colour legend when "All" is active.
const LEGEND_MODULES = ["patient", "doctor", "mco", "booking", "payment", "auth"];

function getEntityModule(name: string): string {
  const n = name.toLowerCase();
  const first = n.split("_")[0];

  if (first === "patient" || ["patients","addresses","family_members","health_records",
    "industries","states","offers","banners","callback_requests"].includes(n)) return "patient";

  if (first === "doctor" || ["doctors","specializations","qualifications","colleges",
    "languages","expertise","reviews","categories","time_slots","custom_time_slots",
    "slots_availability","doctor_achivements","doctor_achievements","insta_consultation_requests",
    "insta_consultaion_documents"].includes(n)) return "doctor";

  if (first === "mco" || ["mcos","services","checklists","protocols","requirements",
    "inventory_items","products","service_types","service_categories","trending_services",
    "popular_services","top_services","service_checklists","service_protocols",
    "service_requirements","service_inventory_items","service_reviews","service_tests",
    "service_products","services_ratings","mco_services","mco_reviews","mco_inventory_items",
    "mco_products","inventory_item_requests"].includes(n)) return "mco";

  if (first === "booking" || n === "bookings" || ["prescriptions","medications",
    "medical_histories","patient_samples","patient_sample_notes","patient_referred",
    "patient_tests","patient_sample_tests","recommendations","documents",
    "recurring_bookings","tests_master","sample_types","container_types","templates",
    "tests","medications_templates","medtel_api_response","bookings_timeline"].includes(n))
    return "booking";

  if (first === "payment" || ["payments","invoices","payment_bookings"].includes(n))
    return "payment";

  if (["users","otps"].includes(n) || first === "auth") return "auth";

  if (["notifications","chat_messages","sms","whatsapp","exotel","tokbox_sessions"].includes(n)
    || first === "notification") return "notifications";

  if (["coupons","faqs","legal_documents","support_contacts"].includes(n)
    || first === "admin") return "admin";

  return "other";
}

// Post-process the Mermaid SVG string to colour entity header boxes by module.
function applyModuleColors(svgStr: string, names: string[]): string {
  try {
    const colorMap = new Map<string, { bg: string; header: string }>();
    for (const name of names) {
      const meta = MODULE_META[getEntityModule(name)] ?? MODULE_META.other;
      // Both the safe/escaped name variants
      colorMap.set(name.toLowerCase(), meta);
      colorMap.set(name.toLowerCase().replace(/[^a-z0-9]/g, "_"), meta);
    }

    const parser = new DOMParser();
    const doc = parser.parseFromString(svgStr, "image/svg+xml");
    const root = doc.documentElement;

    // Strategy A — entity groups have id="entity-Name"
    root.querySelectorAll("g[id]").forEach((g) => {
      const rawId = (g.getAttribute("id") ?? "").toLowerCase();
      const candidate = rawId.replace(/^entity-/, "");
      const meta = colorMap.get(candidate);
      if (!meta) return;
      const rects = g.querySelectorAll("rect");
      // First rect = header box
      if (rects[0]) (rects[0] as SVGRectElement).setAttribute("fill", meta.header);
      // Remaining rects = field rows (leave as-is or give a lighter tint)
    });

    // Strategy B — find text whose full content matches an entity name exactly
    root.querySelectorAll("text").forEach((text) => {
      const content = (text.textContent ?? "").trim().toLowerCase();
      const meta = colorMap.get(content);
      if (!meta) return;
      const parent = text.parentElement;
      if (!parent) return;
      const rect = parent.querySelector("rect");
      if (rect && !(rect as SVGRectElement).getAttribute("data-colored")) {
        (rect as SVGRectElement).setAttribute("fill", meta.header);
        (rect as SVGRectElement).setAttribute("data-colored", "1");
      }
    });

    return new XMLSerializer().serializeToString(doc);
  } catch {
    return svgStr;
  }
}

// ---------------------------------------------------------------------------
// Pan/Zoom canvas (CSS transform — no will-change, no blurriness)
// ---------------------------------------------------------------------------

function ZoomableDiagram({
  svgContent,
  height = "680px",
}: {
  svgContent: string;
  height?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const innerRef     = useRef<HTMLDivElement>(null);
  const labelRef     = useRef<HTMLSpanElement>(null);
  const scaleRef     = useRef(1);
  const offsetRef    = useRef({ x: 0, y: 0 });
  const dragging     = useRef(false);
  const dragStart    = useRef({ mx: 0, my: 0, ox: 0, oy: 0 });

  function commit() {
    const inner = innerRef.current;
    if (!inner) return;
    const { x, y } = offsetRef.current;
    inner.style.transform = `translate(${x}px, ${y}px) scale(${scaleRef.current})`;
    if (labelRef.current)
      labelRef.current.textContent = `${Math.round(scaleRef.current * 100)}%`;
  }

  function zoomAt(factor: number, cx: number, cy: number) {
    const prev = scaleRef.current;
    const next = Math.max(0.05, Math.min(10, prev * factor));
    const { x, y } = offsetRef.current;
    scaleRef.current  = next;
    offsetRef.current = { x: cx - (next / prev) * (cx - x), y: cy - (next / prev) * (cy - y) };
    commit();
  }

  useEffect(() => {
    scaleRef.current  = 1;
    offsetRef.current = { x: 0, y: 0 };
    commit();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [svgContent]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - r.left, e.clientY - r.top);
    };
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!dragging.current) return;
      offsetRef.current = {
        x: dragStart.current.ox + e.clientX - dragStart.current.mx,
        y: dragStart.current.oy + e.clientY - dragStart.current.my,
      };
      const inner = innerRef.current;
      if (inner) {
        const { x, y } = offsetRef.current;
        inner.style.transform = `translate(${x}px, ${y}px) scale(${scaleRef.current})`;
      }
    }
    function onUp() {
      if (!dragging.current) return;
      dragging.current = false;
      if (containerRef.current) containerRef.current.style.cursor = "grab";
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
  }, []);

  function onMouseDown(e: React.MouseEvent) {
    if (e.button !== 0) return;
    e.preventDefault();
    dragging.current = true;
    if (containerRef.current) containerRef.current.style.cursor = "grabbing";
    dragStart.current = { mx: e.clientX, my: e.clientY, ox: offsetRef.current.x, oy: offsetRef.current.y };
  }

  function zoomButton(factor: number) {
    const el = containerRef.current;
    if (!el) return;
    zoomAt(factor, el.clientWidth / 2, el.clientHeight / 2);
  }

  return (
    <div className="flex flex-col gap-2" style={{ height }}>
      <div className="flex items-center gap-1.5 flex-wrap shrink-0">
        <button type="button" onClick={() => zoomButton(1.5)}
          className="px-2.5 py-1 border rounded text-base font-bold hover:bg-accent leading-none" title="Zoom in">+</button>
        <button type="button" onClick={() => zoomButton(1 / 1.5)}
          className="px-2.5 py-1 border rounded text-base font-bold hover:bg-accent leading-none" title="Zoom out">−</button>
        <span ref={labelRef}
          className="w-14 text-center text-xs tabular-nums border rounded py-1 bg-muted/40 shrink-0">100%</span>
        <button type="button" onClick={() => { scaleRef.current = 1; offsetRef.current = { x: 0, y: 0 }; commit(); }}
          className="px-2.5 py-1 border rounded text-xs hover:bg-accent">Reset</button>
        <span className="text-xs text-muted-foreground ml-1 hidden sm:block">Scroll to zoom · drag to pan</span>
      </div>
      <div ref={containerRef}
        className="flex-1 min-h-0 border rounded-lg bg-white overflow-hidden"
        style={{ cursor: "grab" }}
        onMouseDown={onMouseDown}>
        <div ref={innerRef} style={{ transformOrigin: "0 0" }}
          dangerouslySetInnerHTML={{ __html: svgContent }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Diagram tab
// ---------------------------------------------------------------------------

interface Props {
  sessionId: string;
  entityNames: string[];
}

export function DiagramTab({ sessionId, entityNames }: Props) {
  const [svgContent, setSvgContent]           = useState("");
  const [source, setSource]                   = useState("");
  const [copied, setCopied]                   = useState(false);
  const [error, setError]                     = useState<string | null>(null);
  const [loading, setLoading]                 = useState(true);
  const [maximized, setMaximized]             = useState(false);
  const overlayRef                            = useRef<HTMLDivElement>(null);

  const [activeModule, setActiveModule]       = useState<Module>("all");
  const [filterOpen, setFilterOpen]           = useState(false);
  const [checkedEntities, setCheckedEntities] = useState<Set<string>>(new Set());
  const [entitySearch, setEntitySearch]       = useState("");
  const [renderTrigger, setRenderTrigger]     = useState(0);

  useEffect(() => { if (maximized) overlayRef.current?.focus(); }, [maximized]);

  // Count entities per module for slicer badge counts
  const moduleCounts = entityNames.reduce<Record<string, number>>((acc, n) => {
    const m = getEntityModule(n);
    const bucket = (["patient", "doctor", "mco"] as const).includes(m as "patient" | "doctor" | "mco") ? m : "other";
    acc[bucket] = (acc[bucket] ?? 0) + 1;
    return acc;
  }, {});

  function handleModuleClick(mod: Module) {
    setActiveModule(mod);
    setFilterOpen(false);
    if (mod === "all") {
      setCheckedEntities(new Set());
    } else {
      const modEntities = entityNames.filter((n) => {
        const em = getEntityModule(n);
        // "other" pill shows everything that is not patient/doctor/mco
        if (mod === "mco") return em === "mco";
        return em === mod;
      });
      setCheckedEntities(new Set(modEntities));
    }
    setRenderTrigger((n) => n + 1);
  }

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
          setFilterOpen(true);
          setLoading(false);
          return;
        }

        const id = `schemascope_er_${++_erId}`;
        const { svg } = await mermaid.render(id, src);
        if (!active) return;

        // Apply module colours in the "All" view
        const finalSvg = activeModule === "all"
          ? applyModuleColors(svg, entityNames)
          : svg;

        setSvgContent(finalSvg);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message
          : "Could not render diagram. Use 'Download .mmd' to open it in Mermaid Live Editor.");
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

  // ---- module slicer pill styles ----
  function slicerClass(mod: Module) {
    const active = mod === activeModule;
    const color = mod === "all" ? null : MODULE_META[mod];
    if (active && color)
      return `border-2 font-semibold text-xs px-3 py-1 rounded-full transition-all`
           + ` border-[${color.pill}] bg-[${color.bg}] text-gray-800`;
    if (active)
      return "border-2 border-foreground bg-foreground text-background font-semibold text-xs px-3 py-1 rounded-full transition-all";
    return "border text-xs px-3 py-1 rounded-full hover:bg-accent transition-all text-muted-foreground";
  }

  return (
    <div className="space-y-4 pt-4">

      {/* Module slicer */}
      <div className="flex items-center gap-2 flex-wrap">
        {MODULES.map((mod) => (
          <button
            key={mod}
            type="button"
            onClick={() => handleModuleClick(mod)}
            className={slicerClass(mod)}
            style={mod !== "all" && mod === activeModule
              ? { borderColor: MODULE_META[mod].pill, backgroundColor: MODULE_META[mod].bg }
              : mod !== "all"
                ? { borderColor: MODULE_META[mod].pill + "66" }
                : undefined}
          >
            {mod === "all" ? "All Tables" : `${MODULE_META[mod].label} App`}
            {mod !== "all" && (
              <span className="ml-1.5 opacity-60">
                ({moduleCounts[mod] ?? 0})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Colour legend — visible only in All view */}
      {activeModule === "all" && (
        <div className="flex items-center gap-3 flex-wrap text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Colour key:</span>
          {LEGEND_MODULES.map((m) => (
            <span key={m} className="flex items-center gap-1">
              <span
                className="w-3 h-3 rounded-sm border"
                style={{ background: MODULE_META[m].header, borderColor: MODULE_META[m].pill + "88" }}
              />
              {MODULE_META[m].label}
            </span>
          ))}
        </div>
      )}

      {/* Toolbar */}
      <div className="flex gap-2 flex-wrap items-center">
        <Button variant="outline" size="sm" onClick={handleCopy} disabled={!source}>
          {copied ? "✓ Copied" : "Copy Source"}
        </Button>
        <Button variant="outline" size="sm" onClick={() => downloadMermaid(sessionId)}>
          Download .mmd
        </Button>
        <Button variant="outline" size="sm" onClick={() => setFilterOpen((v) => !v)}>
          {filterOpen ? "Hide" : "Filter"} entities
          {checkedEntities.size > 0 && (
            <span className="ml-1 text-xs text-primary">({checkedEntities.size})</span>
          )}
        </Button>
        {(filterOpen || checkedEntities.size > 0) && (
          <Button size="sm" onClick={() => setRenderTrigger((n) => n + 1)} disabled={loading}>
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
              <button type="button" onClick={selectAll}
                className="text-xs text-primary underline-offset-2 hover:underline">Select all</button>
              <button type="button" onClick={clearAll}
                className="text-xs text-muted-foreground underline-offset-2 hover:underline">Clear</button>
            </div>
          </div>
          <input type="text" placeholder="Search entities…" value={entitySearch}
            onChange={(e) => setEntitySearch(e.target.value)}
            className="w-full border rounded-md px-3 py-1.5 text-sm bg-background" />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-1 max-h-56 overflow-y-auto">
            {visibleEntities.map((name) => {
              const mod = getEntityModule(name);
              const meta = MODULE_META[mod] ?? MODULE_META.other;
              return (
                <label key={name}
                  className="flex items-center gap-1.5 text-xs cursor-pointer hover:bg-accent rounded px-1 py-0.5">
                  <input type="checkbox" checked={checkedEntities.has(name)}
                    onChange={() => toggleEntity(name)} className="shrink-0" />
                  <span
                    className="w-2 h-2 rounded-sm shrink-0"
                    style={{ background: meta.header, border: `1px solid ${meta.pill}88` }}
                  />
                  <span className="font-mono truncate">{name}</span>
                </label>
              );
            })}
          </div>
          {checkedEntities.size === 0 && (
            <p className="text-xs text-muted-foreground">
              No entities selected — "Render diagram" will show all (up to 200).
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

      {svgContent && <ZoomableDiagram svgContent={svgContent} height="680px" />}

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
        <div ref={overlayRef}
          className="fixed inset-0 z-50 bg-white flex flex-col"
          onKeyDown={(e) => e.key === "Escape" && setMaximized(false)}
          tabIndex={-1}>
          <div className="flex items-center justify-between px-4 py-2 border-b bg-white shrink-0">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-muted-foreground">ER Diagram — fullscreen</span>
              {activeModule === "all" && (
                <div className="flex items-center gap-2 flex-wrap">
                  {LEGEND_MODULES.map((m) => (
                    <span key={m} className="flex items-center gap-1 text-xs text-muted-foreground">
                      <span className="w-2.5 h-2.5 rounded-sm border"
                        style={{ background: MODULE_META[m].header, borderColor: MODULE_META[m].pill + "88" }} />
                      {MODULE_META[m].label}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <button type="button" onClick={() => setMaximized(false)}
              className="text-sm px-3 py-1 rounded border hover:bg-accent">✕ Close</button>
          </div>
          <div className="flex-1 min-h-0 p-4">
            <ZoomableDiagram svgContent={svgContent} height="100%" />
          </div>
        </div>
      )}
    </div>
  );
}
