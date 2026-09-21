import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import { TrendingUp, Activity } from "lucide-react";
import { fmt } from "../lib/format";

function tickLabel(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(
    d.getMonth() + 1
  ).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:00`;
}

function TooltipBox({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="re-tooltip">
      <div className="re-tooltip-head">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="re-tooltip-row">
          <i style={{ background: p.color }} />
          <span>{p.name}</span>
          <b className="mono">{fmt(p.value, 2)}</b>
        </div>
      ))}
    </div>
  );
}

export default function TrendsChart({ trends }) {
  const avg = trends.length
    ? trends.reduce((a, b) => a + b.average_risk, 0) / trends.length
    : 0;

  return (
    <div className="chart-card">
      <div className="card-head">
        <div>
          <span className="kicker">
            <TrendingUp size={13} /> MODEL HISTORY
          </span>
          <h3>Risk Trend — last 48 hours</h3>
        </div>
        <div className="chart-metrics">
          <span className="metric-chip">
            <Activity size={12} /> Mean <b className="mono">{fmt(avg, 2)}</b>
          </span>
        </div>
      </div>

      <div className="chart-body">
        {trends.length ? (
          <ResponsiveContainer width="100%" height={290}>
            <AreaChart data={trends} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="gAvg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="gMax" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f97316" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#f97316" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis
                dataKey="generated_at"
                tickFormatter={tickLabel}
                tick={{ fill: "#64748b", fontSize: 11, fontFamily: "inherit" }}
                axisLine={{ stroke: "rgba(148,163,184,0.2)" }}
                tickLine={false}
                minTickGap={48}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#64748b", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={36}
                label={{
                  value: "RISK",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#475569",
                  fontSize: 10,
                  letterSpacing: 2,
                }}
              />
              <ReferenceLine
                y={75}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />
              <ReferenceLine
                y={55}
                stroke="#f97316"
                strokeDasharray="4 4"
                strokeOpacity={0.35}
              />
              <ReferenceLine
                y={35}
                stroke="#eab308"
                strokeDasharray="4 4"
                strokeOpacity={0.3}
              />
              <Tooltip content={<TooltipBox />} />
              <Legend
                iconType="dot"
                iconSize={8}
                wrapperStyle={{ fontSize: 11, color: "#94a3b8" }}
              />
              <Area
                type="monotone"
                dataKey="maximum_risk"
                name="Maximum risk"
                stroke="#f97316"
                strokeWidth={1.8}
                fill="url(#gMax)"
              />
              <Area
                type="monotone"
                dataKey="average_risk"
                name="Average risk"
                stroke="#38bdf8"
                strokeWidth={2}
                fill="url(#gAvg)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty">No trend data available.</div>
        )}
      </div>
    </div>
  );
}