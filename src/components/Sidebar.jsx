import {
  LayoutDashboard,
  Map as MapIcon,
  ListTree,
  TrendingUp,
  Database,
  Layers,
} from "lucide-react";
import { ALERT_ORDER, ALERT_COLORS } from "../lib/format";

const NAV = [
  { id: "overview", label: "District Overview", icon: LayoutDashboard },
  { id: "map", label: "Risk Map", icon: MapIcon },
  { id: "villages", label: "Village Watchlist", icon: ListTree },
  { id: "trends", label: "Trend Analysis", icon: TrendingUp },
];

export default function Sidebar({
  active,
  onNavigate,
  mode,
  modelVersion,
  summary,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-scrim" />

      <nav className="nav">
        {NAV.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${active === item.id ? "active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={16} />
              <span>{item.label}</span>
              {item.id === "villages" && summary?.red_cells ? (
                <em className="nav-count">{summary.red_cells}</em>
              ) : null}
            </button>
          );
        })}
      </nav>

      <div className="legend">
        <div className="legend-head">
          <Layers size={13} />
          <span>ALERT SCALE</span>
        </div>
        {ALERT_ORDER.map((lvl) => (
          <div className="legend-row" key={lvl}>
            <span
              className="legend-swatch"
              style={{ background: ALERT_COLORS[lvl].fill }}
            />
            <span className="legend-label">{lvl}</span>
            <span className="legend-value">
              {summary ? summary[`${lvl.toLowerCase()}_cells`] ?? 0 : 0}
            </span>
          </div>
        ))}
      </div>

      <div className="sidebar-foot">
        <div className="sys-row">
          <Database size={12} />
          <span>{mode === "live" ? "Backend connected" : "Offline · demo"}</span>
        </div>
        <div className="sys-row">
          <Layers size={12} />
          <span className="mono">{modelVersion}</span>
        </div>
      </div>
    </aside>
  );
}