import { useCallback, useEffect, useRef, useState } from "react";
import {
  Map as MapIcon,
  Grid3x3,
  TrendingUp,
  AlertTriangle,
  Siren,
  Home,
  Activity,
  Database,
} from "lucide-react";

import { loadDashboard } from "./lib/api";
import { fmt, ALERT_COLORS, ALERT_ORDER } from "./lib/format";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import StatCard, { RiskBar } from "./components/StatCard";
import MapView from "./components/MapView";
import ConditionsPanel from "./components/ConditionsPanel";
import TrendsChart from "./components/TrendsChart";
import VillagesTable from "./components/VillagesTable";
import DetailModal from "./components/DetailModal";

const SECTIONS = ["overview", "map", "villages", "trends"];

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [active, setActive] = useState("overview");
  const [selected, setSelected] = useState(null);
  const sectionRefs = useRef({});

  const load = useCallback(async (silent) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const d = await loadDashboard();
      setData(d);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load(false);
    const tick = setInterval(() => load(true), 5 * 60 * 1000);
    return () => clearInterval(tick);
  }, [load]);

  // Scroll-spy
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(e.target.id);
        }
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    SECTIONS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, [data]);

  const navigate = (id) => {
    setActive(id);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const summary = data?.summary;
  const villages = data?.villages ?? [];
  const cells = data?.cells ?? [];

  const atRiskVillages = villages.filter((v) => v.alert_level !== "GREEN").length;
  const districtRisk = villages.length
    ? villages.reduce((a, b) => a + (b.village_risk ?? 0), 0) / villages.length
    : 0;

  const gradient = districtRisk >= 75 ? "#ef4444" : districtRisk >= 55 ? "#f97316" : districtRisk >= 35 ? "#eab308" : "#22c55e";

  if (loading && !data) {
    return (
      <div className="boot">
        <div className="boot-card">
          <div className="boot-icon">
            <Database size={26} />
          </div>
          <div className="boot-line" />
          <div className="boot-line short" />
          <p>Connecting to Chamoli EWS backend…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header
        mode={data?.mode}
        fetchedAt={data?.fetchedAt}
        onRefresh={() => load(true)}
        refreshing={refreshing}
      />

      <div className="layout">
        <Sidebar
          active={active}
          onNavigate={navigate}
          mode={data?.mode}
          modelVersion={data?.cells?.[0]?.model_version || "chamoli-flood-v2"}
          summary={summary}
        />

        <main className="main">
          {data?.mode === "demo" && (
            <div className="demo-banner">
              <AlertTriangle size={14} />
              Backend offline — showing simulated data so you can review the UI.
            </div>
          )}

          {/* ============ OVERVIEW ============ */}
          <section id="overview" className="section">
            <div className="section-head">
              <div>
                <span className="kicker">LIVE SNAPSHOT</span>
                <h2>District Overview</h2>
              </div>
              <span className="head-tag mono">
                <Siren size={13} /> {summary ? `${fmt(summary.red_cells)}` : 0} RED / {summary ? `${fmt(summary.orange_cells)}` : 0} ORANGE
              </span>
            </div>

            <div className="kpi-row">
              <StatCard
                label="Grid cells"
                value={summary ? fmt(summary.total_cells) : "—"}
                icon={Grid3x3}
                accent="#38bdf8"
              />
              <StatCard
                label="Average risk"
                value={summary ? fmt(summary.average_risk, 2) : "—"}
                sub="district mean"
                icon={Activity}
                accent="#34d399"
              />
              <StatCard
                label="Maximum risk"
                value={summary ? fmt(summary.maximum_risk, 2) : "—"}
                sub="highest cell"
                icon={TrendingUp}
                accent="#fbbf24"
              />
              <StatCard
                label="RED cells"
                value={summary ? fmt(summary.red_cells) : "—"}
                sub="critical alert"
                icon={Siren}
                tone="red"
                accent="#ef4444"
              />
              <StatCard
                label="Villages at risk"
                value={fmt(atRiskVillages)}
                sub={`of ${fmt(villages.length)} mapped`}
                icon={Home}
                accent="#f97316"
              />
            </div>

            <div id="map" className="section map-anchor">
              <div className="section-head compact">
                <div>
                  <span className="kicker">
                    <MapIcon size={13} /> GIS GRID
                  </span>
                  <h2>Risk Map</h2>
                </div>
              </div>

              <div className="overview-grid">
                <div className="map-wrap">
                  <MapView cells={cells} onSelect={setSelected} />
                </div>

                <div className="side-col">
                  <div className="district-card" style={{ "--grad": gradient }}>
                    <span className="kicker">DISTRICT STATUS</span>
                    <div className="district-score mono" style={{ color: gradient }}>
                      {fmt(districtRisk, 1)}
                    </div>
                    <div className="district-scale">
                      {ALERT_ORDER.map((lvl) => (
                        <span
                          key={lvl}
                          className={districtRisk >= (75 - (ALERT_ORDER.indexOf(lvl)) * 20) ? "on" : ""}
                          style={districtRisk >= (75 - ALERT_ORDER.indexOf(lvl) * 20) ? { background: ALERT_COLORS[lvl].fill } : undefined}
                        />
                      ))}
                    </div>
                    <div className="district-meta">
                      <span>Chamoli · Alaknanda basin</span>
                      <span className="mono">
                        24 h horizon · weighted village score
                      </span>
                    </div>
                  </div>

                  <AlertDistribution summary={summary} />

                  <ConditionsPanel conditions={data?.conditions} />
                </div>
              </div>
            </div>
          </section>

          {/* ============ VILLAGES ============ */}
          <section id="villages" className="section">
            <VillagesTable
              villages={villages}
              onSelect={(lvl) => {
                if (lvl !== "ALL") navigate("map");
              }}
            />
          </section>

          {/* ============ TRENDS ============ */}
          <section id="trends" className="section">
            <TrendsChart trends={data?.trends ?? []} />
            <div className="readout">
              <span className="kicker">MODEL READOUT</span>
              <p>
                Random Forest (18 features) → 24 h temporal probability fused with
                static spatial susceptibility (0.75 × temporal + 0.25 × spatial).
                Threshold 0.20 · ROC-AUC 0.80 · version v2.
              </p>
            </div>
          </section>

          <footer className="foot">
            <span className="mono">
              River gauge: Joshimath · 30.57°N, 79.55°E
            </span>
            <span>Not an official warning system — competition baseline. Recalibrate with operational gauge data before deployment.</span>
          </footer>
        </main>
      </div>

      <DetailModal cell={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function AlertDistribution({ summary }) {
  if (!summary) return null;
  const total = summary.total_cells || 1;
  return (
    <div className="dist-card">
      <span className="kicker">ALERT DISTRIBUTION</span>
      {ALERT_ORDER.map((lvl) => (
        <RiskBar
          key={lvl}
          label={lvl}
          count={summary[`${lvl.toLowerCase()}_cells`] ?? 0}
          total={total}
          color={ALERT_COLORS[lvl].fill}
          border={ALERT_COLORS[lvl].border}
          bg={ALERT_COLORS[lvl].bg}
        />
      ))}
    </div>
  );
}