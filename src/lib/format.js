export const ALERT_COLORS = {
  RED: { fill: "#ef4444", bg: "rgba(239,68,68,0.12)", text: "#fca5a5", border: "#b91c1c" },
  ORANGE: { fill: "#f97316", bg: "rgba(249,115,22,0.12)", text: "#fdba74", border: "#c2410c" },
  YELLOW: { fill: "#eab308", bg: "rgba(234,179,8,0.12)", text: "#fde047", border: "#a16207" },
  GREEN: { fill: "#22c55e", bg: "rgba(34,197,94,0.12)", text: "#86efac", border: "#15803d" },
};

export const ALERT_ORDER = ["RED", "ORANGE", "YELLOW", "GREEN"];

export function fmt(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtClock(d) {
  return d.toLocaleTimeString("en-IN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function riskToPct(risk) {
  const r = Number(risk) || 0;
  return Math.min(100, Math.max(0, r)).toFixed(1);
}

export function cap(str, len = 120) {
  if (!str) return "";
  return str.length > len ? str.slice(0, len) + "…" : str;
}