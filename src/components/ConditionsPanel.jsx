import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Droplets, Landmark, CloudRain, Waves } from "lucide-react";
import { fmt, fmtTime } from "../lib/format";

function ConditionTile({ icon: Icon, label, value, unit, time, accent }) {
  return (
    <div className="cond-tile">
      <div className="cond-icon" style={{ color: accent }}>
        <Icon size={17} />
      </div>
      <div className="cond-mid">
        <span className="cond-label">{label}</span>
        <span className="cond-value mono">
          {value} <em>{unit}</em>
        </span>
      </div>
      <span className="cond-time">{time}</span>
    </div>
  );
}

function barColor(v) {
  if (v >= 8) return "#ef4444";
  if (v >= 4) return "#f97316";
  if (v >= 1) return "#eab308";
  return "#38bdf8";
}

export default function ConditionsPanel({ conditions }) {
  const fc = conditions?.forecast ?? [];
  const total24 = (conditions?.forecast24h_mm ?? fc.reduce((a, b) => a + b.precipitation_mm, 0));

  return (
    <div className="cond-panel">
      <div className="card-head">
        <div>
          <span className="kicker">
            <Droplets size={13} /> TELEMETRY
          </span>
          <h3>Current conditions</h3>
        </div>
      </div>

      <div className="cond-grid">
        <ConditionTile
          icon={CloudRain}
          label="Rainfall · last h"
          value={conditions?.rainfall ? fmt(conditions.rainfall.value_mm, 1) : "—"}
          unit="mm"
          time={conditions?.rainfall ? fmtTime(conditions.rainfall.timestamp) : "—"}
          accent="#38bdf8"
        />
        <ConditionTile
          icon={Waves}
          label="Soil moisture · mean"
          value={conditions?.soil_moisture ? fmt(conditions.soil_moisture.mean, 2) : "—"}
          unit="m³/m³"
          time={conditions?.soil_moisture ? fmtTime(conditions.soil_moisture.timestamp) : "—"}
          accent="#34d399"
        />
        <ConditionTile
          icon={Landmark}
          label="Alaknanda level"
          value={conditions?.river ? fmt(conditions.river.level_m, 2) : "—"}
          unit="m"
          time={conditions?.river ? fmtTime(conditions.river.timestamp) : "—"}
          accent="#fbbf24"
        />
      </div>

      <div className="fc-head">
        <span className="kicker">OPEN-METEO · next 24 h</span>
        <span className="fc-total mono">
          ≈ {fmt(total24, 1)} mm accumulation
        </span>
      </div>

      <div className="fc-chart">
        {fc.length ? (
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={fc} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
              <XAxis
                dataKey="time"
                tickFormatter={(t) => {
                  const d = new Date(t);
                  return `${String(d.getHours()).padStart(2, "0")}:00`;
                }}
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={{ stroke: "rgba(148,163,184,0.18)" }}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis hide />
              <Tooltip
                cursor={{ fill: "rgba(148,163,184,0.08)" }}
                content={({ active, payload }) =>
                  active && payload?.length ? (
                    <div className="re-tooltip">
                      <div className="re-tooltip-row">
                        <i style={{ background: "#38bdf8" }} />
                        <span>precip</span>
                        <b className="mono">{fmt(payload[0].value, 2)} mm</b>
                      </div>
                    </div>
                  ) : null
                }
              />
              <Bar dataKey="precipitation_mm" radius={[2, 2, 0, 0]}>
                {fc.map((_, i) => (
                  <Cell key={i} fill={barColor(fc[i].precipitation_mm)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty compact">No forecast available.</div>
        )}
      </div>
    </div>
  );
}