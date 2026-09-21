// ---------------------------------------------------------------------------
// Demo data generator — produces realistic-looking Chamoli district data so the
// dashboard can be previewed even when the backend/PostgreSQL is offline.
// Every generator is seeded → stable across refreshes within a session.
// ---------------------------------------------------------------------------

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const VILLAGES = [
  { name: "Joshimath", block: "Joshimath", lat: 30.556, lon: 79.565 },
  { name: "Govindghat", block: "Joshimath", lat: 30.6247, lon: 79.5968 },
  { name: "Pulna", block: "Joshimath", lat: 30.6865, lon: 79.5841 },
  { name: "Ghat", block: "Ghat", lat: 30.2568, lon: 79.4442 },
  { name: "Pipalkoti", block: "Tharali", lat: 30.431, lon: 79.433 },
  { name: "Nandprayag", block: "Karnaprayag", lat: 30.331, lon: 79.314 },
  { name: "Karnaprayag", block: "Karnaprayag", lat: 30.265, lon: 79.212 },
  { name: "Gopeshwar", block: "Gairsain", lat: 30.412, lon: 79.331 },
  { name: "Chamoli", block: "Gairsain", lat: 30.422, lon: 79.331 },
  { name: "Dewal", block: "Dewal", lat: 30.301, lon: 79.499 },
  { name: "Dasoli", block: "Dasoli", lat: 30.394, lon: 79.589 },
  { name: "Narayanbagar", block: "Narayanbagar", lat: 30.213, lon: 79.371 },
  { name: "Tharali", block: "Tharali", lat: 30.297, lon: 79.557 },
  { name: "Gairsain", block: "Gairsain", lat: 30.054, lon: 79.291 },
  { name: "Auli", block: "Joshimath", lat: 30.532, lon: 79.577 },
  { name: "Tapovan", block: "Joshimath", lat: 30.486, lon: 79.626 },
  { name: "Hanuman Chatti", block: "Joshimath", lat: 30.676, lon: 79.571 },
];

const DAYS = 2;

export function demoDashboard() {
  const rand = mulberry32(20240920);

  // Central temporal pressure for the demo snapshot.
  const temporal = 0.33;

  // Generate grid cells clustered near the Alaknanda valley floor where the
  // real 500 m grid points are densest.
  const cells = [];
  const rivers = [
    { lat: 30.55, lon: 79.58 },
    { lat: 30.33, lon: 79.31 },
    { lat: 30.27, lon: 79.21 },
    { lat: 30.40, lon: 79.33 },
  ];

  const count = 680;
  for (let i = 0; i < count; i += 1) {
    // Pick a valley anchor or a wider-area point.
    let anchor;
    if (rand() < 0.6) {
      anchor = rivers[Math.floor(rand() * rivers.length)];
      const spread = 0.02 + rand() * 0.05;
      const lat = anchor.lat + (rand() - 0.5) * 2 * spread;
      const lon = anchor.lon + (rand() - 0.5) * 2 * spread;
      const dToRiver =
        Math.sqrt((lat - anchor.lat) ** 2 + (lon - anchor.lon) ** 2) * 105000;
      const village = nearestVillage(lat, lon, rand);
      cells.push({
        grid_id: `DM_${String(i + 1).padStart(5, "0")}`,
        latitude: round(lat, 5),
        longitude: round(lon, 5),
        elevation_m: round(1100 + (rand() - 0.4) * 2400, 1),
        slope_deg: round(4 + rand() * 42, 2),
        distance_to_river_m: round(
          (dToRiver + rand() * 400 + (1 - rand()) * 120) * (1 + rand() * 2.2),
          0
        ),
        village_name: village.name,
        block_name: village.block,
        district_name: "Chamoli",
        mapping_method: "spatial_join_500m",
        horizon_hours: 24,
        model_version: "chamoli-multimodal-flood-v2",
      });
    } else {
      const lat = 30.05 + rand() * 0.85;
      const lon = 79.15 + rand() * 0.6;
      const village = nearestVillage(lat, lon, rand);
      cells.push({
        grid_id: `DM_${String(i + 1).padStart(5, "0")}`,
        latitude: round(lat, 5),
        longitude: round(lon, 5),
        elevation_m: round(900 + rand() * 3600, 1),
        slope_deg: round(3 + rand() * 45, 2),
        distance_to_river_m: round(200 + rand() * 9000, 0),
        village_name: village.name,
        block_name: village.block,
        district_name: "Chamoli",
        mapping_method: "spatial_join_500m",
        horizon_hours: 24,
        model_version: "chamoli-multimodal-flood-v2",
      });
    }
  }

  // Susceptibility proxy (mirrors backend formula flavour).
  for (const c of cells) {
    const sus =
      0.55 * Math.min(c.slope_deg / 45, 1) * 0.45 +
      0.35 * Math.exp(-c.distance_to_river_m / 3000) +
      0.1 +
      (rand() - 0.5) * 0.08;
    c.susceptibility = round(clamp(sus, 0, 1), 4);

    // River-proximity cluster boost → a handful of RED / ORANGE cells so the
    // graded alert scale is visibly demonstrated.
    const riverBoost = 0.5 * Math.exp(-c.distance_to_river_m / 1800);
    const noise = (rand() - 0.5) * 0.16;
    const prob = clamp(
      0.75 * temporal + 0.25 * c.susceptibility + riverBoost + noise,
      0,
      0.94
    );
    c.flood_probability = round(prob, 5);
    c.risk_score = round(prob * 100, 2);
    c.alert_level = alertFromProb(c.risk_score);

    const reasons = [];
    if (prob >= 0.5) reasons.push("high recent rainfall accumulation");
    if (c.susceptibility >= 0.55) reasons.push("high spatial susceptibility");
    if (prob >= 0.4) reasons.push("rising Alaknanda river level");
    if (!reasons.length) reasons.push("conditions below major warning thresholds");
    c.explanation = `${c.alert_level} risk. Temporal model probability ${(
      prob * 100
    ).toFixed(1)}%. Spatial susceptibility ${(
      c.susceptibility * 100
    ).toFixed(1)}%. Factors: ${reasons.join(", ")}.`;
    c.generated_at = new Date().toISOString();
  }

  cells.sort((a, b) => b.risk_score - a.risk_score);
  return cells;
}

export function demoSummary(cells) {
  const count = (lvl) => cells.filter((c) => c.alert_level === lvl).length;
  const risks = cells.map((c) => c.risk_score);
  return {
    total_cells: cells.length,
    red_cells: count("RED"),
    orange_cells: count("ORANGE"),
    yellow_cells: count("YELLOW"),
    green_cells: count("GREEN"),
    average_risk: round(risks.reduce((a, b) => a + b, 0) / risks.length, 2),
    maximum_risk: round(Math.max(...risks), 2),
  };
}

export function demoVillages(cells) {
  const map = new Map();
  for (const c of cells) {
    if (!c.village_name) continue;
    const key = `${c.village_name}|${c.block_name}`;
    const agg = map.get(key) || {
      village_name: c.village_name,
      block_name: c.block_name,
      district_name: c.district_name,
      grid_cells: 0,
      risks: [],
    };
    agg.grid_cells += 1;
    agg.risks.push(c.risk_score);
    map.set(key, agg);
  }

  const data = [...map.values()].map((agg) => {
    const sorted = [...agg.risks].sort((a, b) => a - b);
    const avg = sorted.reduce((a, b) => a + b, 0) / sorted.length;
    const max = sorted[sorted.length - 1];
    const p90 = sorted[Math.floor(sorted.length * 0.9)];
    const villageRisk = 0.75 * avg + 0.25 * p90;
    const alert = alertFromProb(villageRisk);
    return {
      village_name: agg.village_name,
      block_name: agg.block_name,
      district_name: agg.district_name,
      grid_cells: agg.grid_cells,
      max_risk: round(max, 2),
      average_risk: round(avg, 2),
      p90_risk: round(p90, 2),
      risk_rank: alertToRank(alert),
      alert_level: alert,
      village_risk: round(villageRisk, 2),
    };
  });

  data.sort((a, b) => b.village_risk - a.village_risk);
  return data;
}

export function demoTrends() {
  const rand = mulberry32(777);
  const now = new Date();
  now.setMinutes(0, 0, 0);
  const data = [];
  let level = 38 + rand() * 6; // percentage-of-max style risk index
  let drift = 0;
  for (let i = 47; i >= 0; i -= 1) {
    const t = new Date(now.getTime() - i * 3600 * 1000);
    drift = drift * 0.85 + (rand() - 0.5) * 6;
    // occasional rainfall spike
    if (rand() < 0.08) level += 18 + rand() * 22;
    level = level * 0.94 + drift;
    level = clamp(level + (rand() - 0.5) * 4, 12, 96);
    const avg = clamp(level + (rand() - 0.5) * 3, 8, 92);
    const max = clamp(level + 9 + rand() * 14, 14, 100);
    data.push({
      generated_at: t.toISOString(),
      average_risk: round(avg, 2),
      maximum_risk: round(max, 2),
    });
  }
  return data;
}

export function demoConditions() {
  const h = new Date();
  h.setMinutes(0, 0, 0);
  return {
    rainfall: {
      timestamp: new Date(h.getTime() - 2 * 3600 * 1000).toISOString(),
      value_mm: 14.2,
    },
    soil_moisture: {
      timestamp: new Date(h.getTime() - 1 * 3600 * 1000).toISOString(),
      mean: 0.42,
    },
    river: {
      timestamp: new Date(h.getTime() - 3 * 3600 * 1000).toISOString(),
      level_m: 1372.64,
    },
    forecast24h_mm: 41.5,
    forecast: buildForecastSeries(h),
  };
}

function buildForecastSeries(from) {
  const rand = mulberry32(5151);
  const out = [];
  for (let i = 0; i < 24; i += 1) {
    const t = new Date(from.getTime() + i * 3600 * 1000);
    const wave = i > 6 && i < 18 ? 2.4 : 1;
    out.push({
      time: t.toISOString(),
      precipitation_mm: round(clamp(rand() * 6.5 * wave, 0.05, 14), 2),
    });
  }
  return out;
}

// ---------------------------------------------------------------------------

function nearestVillage(lat, lon, rand) {
  let best = VILLAGES[0];
  let bestD = Infinity;
  for (const v of VILLAGES) {
    const d = (v.lat - lat) ** 2 + (v.lon - lon) ** 2;
    if (d < bestD) {
      bestD = d;
      best = v;
    }
  }
  if (bestD > 0.18 && rand() < 0.6) {
    const fallback = VILLAGES[Math.floor(rand() * VILLAGES.length)];
    return fallback;
  }
  return best;
}

function alertFromProb(riskScore) {
  if (riskScore >= 75) return "RED";
  if (riskScore >= 55) return "ORANGE";
  if (riskScore >= 35) return "YELLOW";
  return "GREEN";
}

function alertToRank(alert) {
  return { RED: 4, ORANGE: 3, YELLOW: 2, GREEN: 1 }[alert] || 1;
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

function round(v, d = 2) {
  const p = 10 ** d;
  return Math.round(v * p) / p;
}