"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Transaction {
  cid: string;
  company: string;
  year: number;
  status: "pending" | "downloaded" | "complete" | "failed";
  pages?: number;
  size_mb?: number;
  sha256?: string;
  source_url?: string;
  error?: string;
  verified_at?: string;
}

interface Manifest {
  meta: {
    target_years: number[];
    companies_count: number;
    updated_at: string;
    live?: boolean;
    current_tx?: string | null;
  };
  transactions: Record<string, Transaction>;
}

interface CompanyView {
  cid: string;
  name: string;
  reports: Record<string, Transaction>;
  completeCount: number;
  failedCount: number;
  totalYears: number;
}

// ---------------------------------------------------------------------------
// Config — try live API first, fall back to static file
// ---------------------------------------------------------------------------

const LIVE_API = "http://localhost:8787/manifest.json";
const STATIC_FILE = "/data/manifest.json";
const POLL_INTERVAL_LIVE = 2000;
const POLL_INTERVAL_STATIC = 30000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildCompanyViews(manifest: Manifest): CompanyView[] {
  const years = manifest.meta.target_years;
  const byCompany = new Map<string, CompanyView>();

  for (const tx of Object.values(manifest.transactions)) {
    if (!byCompany.has(tx.cid)) {
      byCompany.set(tx.cid, {
        cid: tx.cid,
        name: tx.company,
        reports: {},
        completeCount: 0,
        failedCount: 0,
        totalYears: years.length,
      });
    }
    const cv = byCompany.get(tx.cid)!;
    cv.reports[String(tx.year)] = tx;
    if (tx.status === "complete") cv.completeCount++;
    if (tx.status === "failed") cv.failedCount++;
  }

  return Array.from(byCompany.values());
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function LiveBadge({ live, source }: { live: boolean; source: string }) {
  if (!live) {
    return (
      <span className="text-xs text-gray-600 flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-gray-600" />
        {source === "api" ? "idle" : "static"}
      </span>
    );
  }
  return (
    <span className="text-xs text-emerald-400 flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
      LIVE
    </span>
  );
}

function ProgressBar({
  value,
  max,
  color,
  delay = 0,
  height = "h-3",
}: {
  value: number;
  max: number;
  color: string;
  delay?: number;
  height?: string;
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className={`w-full bg-gray-800 rounded-full ${height} overflow-hidden`}>
      <div
        className={`${color} ${height} rounded-full transition-all duration-700 ease-out`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm text-gray-400 mb-1">{label}</p>
      <p className="text-3xl font-bold tabular-nums">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

function StatusDot({ status, active }: { status: string; active?: boolean }) {
  const base =
    status === "complete"
      ? "bg-emerald-500"
      : status === "failed"
      ? "bg-red-500"
      : status === "downloaded"
      ? "bg-blue-500"
      : "bg-gray-700";
  return (
    <div
      className={`w-2.5 h-2.5 rounded-full ${base} ${
        active ? "ring-2 ring-amber-400 animate-pulse" : ""
      }`}
    />
  );
}

function CompanyRow({
  company,
  years,
  currentTx,
}: {
  company: CompanyView;
  years: number[];
  currentTx: string | null;
}) {
  const pct = Math.round((company.completeCount / company.totalYears) * 100);
  const barColor =
    pct === 100 ? "bg-emerald-500" : pct > 0 ? "bg-amber-500" : "bg-gray-700";
  const textColor =
    pct === 100
      ? "text-emerald-400"
      : pct > 0
      ? "text-amber-400"
      : "text-gray-500";

  const isActive = currentTx?.startsWith(company.cid + "_");

  return (
    <div
      className={`grid grid-cols-[180px_1fr_70px_auto] items-center gap-4 py-3 px-4 border-b border-gray-800/50 transition-colors ${
        isActive
          ? "bg-amber-500/5 border-l-2 border-l-amber-500"
          : "hover:bg-gray-900/50"
      }`}
    >
      <div>
        <span className="font-medium text-sm">{company.name}</span>
        <span className="text-xs text-gray-600 ml-2">{company.cid}</span>
        {isActive && (
          <span className="ml-2 text-[10px] text-amber-400 font-mono">
            downloading...
          </span>
        )}
      </div>

      <ProgressBar
        value={company.completeCount}
        max={company.totalYears}
        color={barColor}
        height="h-2"
      />

      <span className={`text-sm font-mono text-right ${textColor}`}>
        {company.completeCount}/{company.totalYears}
      </span>

      <div className="flex gap-1.5">
        {years.map((year) => {
          const tx = company.reports[String(year)];
          const status = tx?.status ?? "pending";
          const isTxActive = currentTx === `${company.cid}_${year}`;
          return (
            <div
              key={year}
              className="flex flex-col items-center gap-0.5"
              title={`${year}: ${status}${tx?.pages ? ` (${tx.pages}p)` : ""}${
                isTxActive ? " — downloading" : ""
              }`}
            >
              <StatusDot status={status} active={isTxActive} />
              <span className="text-[9px] text-gray-600 leading-none">
                {String(year).slice(-2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [source, setSource] = useState<"api" | "static">("static");
  const prevComplete = useRef(0);
  const [delta, setDelta] = useState(0);

  const fetchManifest = useCallback(async () => {
    // Try live API first
    try {
      const r = await fetch(LIVE_API, { cache: "no-store" });
      if (r.ok) {
        const data = await r.json();
        setManifest(data);
        setSource("api");
        return;
      }
    } catch {
      // API not available, fall through
    }

    // Fall back to static file
    try {
      const r = await fetch(STATIC_FILE, { cache: "no-store" });
      if (r.ok) {
        setManifest(await r.json());
        setSource("static");
      }
    } catch {
      // nothing available
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchManifest();
  }, [fetchManifest]);

  // Polling
  useEffect(() => {
    const interval = source === "api" ? POLL_INTERVAL_LIVE : POLL_INTERVAL_STATIC;
    const id = setInterval(fetchManifest, interval);
    return () => clearInterval(id);
  }, [source, fetchManifest]);

  // Track delta (new completions since page load)
  useEffect(() => {
    if (!manifest) return;
    const total = Object.values(manifest.transactions).filter(
      (t) => t.status === "complete"
    ).length;
    if (prevComplete.current > 0 && total > prevComplete.current) {
      setDelta((d) => d + (total - prevComplete.current));
    }
    prevComplete.current = total;
  }, [manifest]);

  if (!manifest) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const years = manifest.meta.target_years;
  const isLive = manifest.meta.live === true;
  const currentTx = manifest.meta.current_tx ?? null;
  const txs = Object.values(manifest.transactions);
  const totalTarget = txs.length;
  const totalComplete = txs.filter((t) => t.status === "complete").length;
  const totalFailed = txs.filter((t) => t.status === "failed").length;
  const totalPending = txs.filter((t) => t.status === "pending").length;
  const pct = Math.round((totalComplete / totalTarget) * 100);

  const companies = buildCompanyViews(manifest);
  const fullComplete = companies.filter(
    (c) => c.completeCount === c.totalYears
  ).length;
  const partial = companies.filter(
    (c) => c.completeCount > 0 && c.completeCount < c.totalYears
  ).length;
  const noReports = companies.filter((c) => c.completeCount === 0).length;

  const sorted = [...companies].sort((a, b) => {
    // Active company first
    if (currentTx) {
      const aActive = currentTx.startsWith(a.cid + "_");
      const bActive = currentTx.startsWith(b.cid + "_");
      if (aActive && !bActive) return -1;
      if (bActive && !aActive) return 1;
    }
    if (a.completeCount === a.totalYears && b.completeCount !== b.totalYears)
      return -1;
    if (b.completeCount === b.totalYears && a.completeCount !== a.totalYears)
      return 1;
    return b.completeCount - a.completeCount;
  });

  return (
    <div className="min-h-screen max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <header className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Aspiratio</h1>
          <p className="text-gray-500 mt-1">
            Annual Report Archive &mdash; OMXS30
          </p>
        </div>
        <LiveBadge live={isLive} source={source} />
      </header>

      {/* Hero */}
      <section className="mb-10">
        <div className="flex items-end gap-3 mb-4">
          <span className="text-7xl font-bold tabular-nums transition-all duration-500">
            {totalComplete}
          </span>
          <span className="text-2xl text-gray-500 mb-2">/ {totalTarget}</span>
          {delta > 0 && (
            <span className="text-lg text-emerald-400 mb-2 font-mono">
              +{delta}
            </span>
          )}
          <span className="text-2xl text-emerald-400 mb-2 ml-auto font-mono">
            {pct}%
          </span>
        </div>
        <ProgressBar
          value={totalComplete}
          max={totalTarget}
          color="bg-emerald-500"
          height="h-4"
        />
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
          <span>
            Updated{" "}
            {new Date(manifest.meta.updated_at).toLocaleString("en-SE")}
          </span>
          {totalPending > 0 && (
            <span className="text-amber-500">{totalPending} pending</span>
          )}
          {totalFailed > 0 && (
            <span className="text-red-400">{totalFailed} failed</span>
          )}
          {currentTx && (
            <span className="text-amber-400 animate-pulse">
              Processing {currentTx}
            </span>
          )}
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-3 gap-4 mb-10">
        <StatCard
          label="Complete"
          value={String(fullComplete)}
          sub={`All ${years.length} years`}
        />
        <StatCard label="Partial" value={String(partial)} sub="Some years" />
        <StatCard
          label="Missing"
          value={String(noReports)}
          sub="No reports yet"
        />
      </section>

      {/* Company list */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Company Coverage</h2>
          <div className="flex gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <StatusDot status="complete" /> complete
            </span>
            <span className="flex items-center gap-1">
              <StatusDot status="failed" /> failed
            </span>
            <span className="flex items-center gap-1">
              <StatusDot status="pending" /> pending
            </span>
          </div>
        </div>
        <div className="bg-gray-900/30 border border-gray-800 rounded-xl overflow-hidden">
          <div className="grid grid-cols-[180px_1fr_70px_auto] gap-4 py-2 px-4 text-xs text-gray-500 border-b border-gray-800">
            <span>Company</span>
            <span>Progress</span>
            <span className="text-right">Count</span>
            <span>Years</span>
          </div>
          {sorted.map((company) => (
            <CompanyRow
              key={company.cid}
              company={company}
              years={years}
              currentTx={currentTx}
            />
          ))}
        </div>
      </section>

      <footer className="mt-10 py-6 border-t border-gray-800 text-center text-xs text-gray-600">
        Aspiratio &mdash; Automated annual report archiving for Nordic markets
      </footer>
    </div>
  );
}
