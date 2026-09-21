// ---------------------------------------------------------------------------
// API client with graceful demo fallback.
//
// Tries the FastAPI backend (proxied to http://localhost:8000 in dev). When the
// backend or its PostgreSQL database is unreachable, every endpoint falls back
// to generated demo data and `mode` flips to "demo" so the UI can show a badge.
// ---------------------------------------------------------------------------

import {
  demoDashboard,
  demoSummary,
  demoVillages,
  demoTrends,
  demoConditions,
} from "./demoData";

const TIMEOUT_MS = 4000;

let _demoCells = null;

function getDemoCells() {
  if (!_demoCells) _demoCells = demoDashboard();
  return _demoCells;
}

async function getJson(url) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(url, { signal: ctrl.signal, cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

function parseDashboard(payload) {
  const rows = payload?.data ?? payload?.rows ?? [];
  return rows.map((r) => ({
    grid_id: r.grid_id,
    latitude: Number(r.latitude),
    longitude: Number(r.longitude),
    elevation_m: r.elevation_m,
    slope_deg: r.slope_deg,
    distance_to_river_m: r.distance_to_river_m,
    village_name: r.village_name,
    block_name: r.block_name,
    district_name: r.district_name,
    flood_probability: Number(r.flood_probability),
    risk_score: Number(r.risk_score),
    alert_level: String(r.alert_level || "GREEN").toUpperCase(),
    explanation: r.explanation,
    generated_at: r.generated_at,
    model_version: r.model_version,
    horizon_hours: r.horizon_hours,
  }));
}

function parseSummary(p) {
  return {
    total_cells: Number(p.total_cells ?? 0),
    red_cells: Number(p.red_cells ?? 0),
    orange_cells: Number(p.orange_cells ?? 0),
    yellow_cells: Number(p.yellow_cells ?? 0),
    green_cells: Number(p.green_cells ?? 0),
    average_risk: Number(p.average_risk ?? 0),
    maximum_risk: Number(p.maximum_risk ?? 0),
  };
}

async function fetchDashboard() {
  const json = await getJson("/api/dashboard");
  const cells = parseDashboard(json);
  if (!cells.length) throw new Error("Dashboard returned no cells");
  return cells;
}

async function fetchSummary() {
  const json = await getJson("/api/summary");
  return parseSummary(json);
}

async function fetchVillages() {
  const json = await getJson("/api/villages");
  const data = json?.data ?? [];
  const alert = { RED: 4, ORANGE: 3, YELLOW: 2, GREEN: 1 };
  return data.map((v) => ({
    village_name: v.village_name,
    block_name: v.block_name,
    district_name: v.district_name,
    grid_cells: Number(v.grid_cells ?? 0),
    max_risk: Number(v.max_risk ?? 0),
    average_risk: Number(v.average_risk ?? 0),
    p90_risk: Number(v.p90_risk ?? 0),
    village_risk: Number(v.village_risk ?? v.average_risk ?? 0),
    risk_rank: Number(v.risk_rank ?? alert[v.alert_level] ?? 1),
    alert_level: v.alert_level || alertToName(v.risk_rank),
  }));
}

function alertToName(rank) {
  const r = Number(rank);
  if (r >= 4) return "RED";
  if (r === 3) return "ORANGE";
  if (r === 2) return "YELLOW";
  return "GREEN";
}

async function fetchTrends() {
  const json = await getJson("/api/trends");
  const data = json?.data ?? [];
  return data
    .map((t) => ({
      generated_at: t.generated_at,
      average_risk: Number(t.average_risk ?? 0),
      maximum_risk: Number(t.maximum_risk ?? 0),
    }))
    .sort((a, b) => (a.generated_at < b.generated_at ? -1 : 1));
}

async function fetchConditions() {
  const json = await getJson("/api/conditions");
  return {
    rainfall: json?.rainfall ?? null,
    soil_moisture: json?.soil_moisture ?? null,
    river: json?.river ?? null,
  };
}

/**
 * Reads the whole dashboard in one shot. Returns { mode, cells, summary,
 * villages, trends, conditions } where mode is "live" or "demo".
 */
export async function loadDashboard() {
  // Try live first; any failure falls through to demo.
  try {
    const cells = await fetchDashboard();
    let [summary, villages, trends, conditions, health] = await Promise.all([
      fetchSummary().catch(() => demoSummary(cells)),
      fetchVillages().catch(() => demoVillages(cells)),
      fetchTrends().catch(() => demoTrends()),
      fetchConditions().catch(() => demoConditions()),
      getJson("/api/health").catch(() => null),
    ]);
    return {
      mode: "live",
      health,
      cells,
      summary,
      villages,
      trends,
      conditions,
      fetchedAt: new Date().toISOString(),
    };
  } catch {
    const cells = getDemoCells();
    return {
      mode: "demo",
      health: null,
      cells,
      summary: demoSummary(cells),
      villages: demoVillages(cells),
      trends: demoTrends(),
      conditions: demoConditions(),
      fetchedAt: new Date().toISOString(),
    };
  }
}