import { fmt } from "../lib/format";

export default function StatCard({ label, value, sub, icon: Icon, tone, accent }) {
  return (
    <div className={`stat-card ${tone ? `tone-${tone}` : ""}`}>
      <div className="stat-head">
        <span className="stat-label">{label}</span>
        {Icon && (
          <span className="stat-icon" style={accent ? { color: accent } : undefined}>
            <Icon size={16} />
          </span>
        )}
      </div>
      <div className="stat-value mono">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
      <div
        className="stat-glow"
        style={accent ? { background: accent } : undefined}
      />
    </div>
  );
}

export function RiskBar({ label, count, total, color, border, bg }) {
  const pct = total ? (count / total) * 100 : 0;
  return (
    <div className="risk-bar">
      <div className="risk-bar-head">
        <span className="risk-bar-label">
          <i style={{ background: color }} />
          {label}
        </span>
        <span className="mono">
          {fmt(count)} <b>· {pct.toFixed(1)}%</b>
        </span>
      </div>
      <div className="risk-track">
        <div
          className="risk-fill"
          style={{
            width: `${pct}%`,
            background: bg || color,
            boxShadow: `0 0 12px ${border || color}`,
          }}
        />
      </div>
    </div>
  );
}