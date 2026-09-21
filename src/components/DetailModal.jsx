import { X, MapPin, Mountain, Gauge, Activity } from "lucide-react";
import { ALERT_COLORS, fmt, fmtTime } from "../lib/format";

export default function DetailModal({ cell, onClose }) {
  if (!cell) return null;
  const c = ALERT_COLORS[cell.alert_level] || ALERT_COLORS.GREEN;

  const rows = [
    ["Latitude", fmt(cell.latitude, 4)],
    ["Longitude", fmt(cell.longitude, 4)],
    ["Elevation", cell.elevation_m != null ? `${fmt(cell.elevation_m, 0)} m` : "—"],
    ["Slope", cell.slope_deg != null ? `${fmt(cell.slope_deg, 1)}°` : "—"],
    ["Dist. to river", cell.distance_to_river_m != null ? `${fmt(cell.distance_to_river_m, 0)} m` : "—"],
    ["Horizon", `${cell.horizon_hours ?? 24} h`],
    ["Generated", fmtTime(cell.generated_at)],
    ["Model", cell.model_version || "—"],
  ];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head" style={{ borderColor: c.border }}>
          <div className="modal-title">
            <MapPin size={18} style={{ color: c.fill }} />
            <div>
              <span className="kicker">GRID CELL {cell.grid_id}</span>
              <h3>{cell.village_name || "Unmapped area"}</h3>
            </div>
          </div>
          <button className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div className="alert-gauge">
            <div className="alert-badge" style={{ background: c.bg, color: c.text, borderColor: c.border }}>
              {cell.alert_level}
            </div>
            <div className="gauge-track">
              <div
                className="gauge-fill"
                style={{
                  width: `${Math.min(100, cell.risk_score)}%`,
                  background: c.fill,
                  boxShadow: `0 0 14px ${c.border}`,
                }}
              />
            </div>
            <div className="gauge-meta">
              <span className="mono strong" style={{ color: c.text }}>
                {fmt(cell.risk_score, 2)} / 100
              </span>
              <span>
                <Activity size={12} /> flood probability {fmt(cell.flood_probability * 100, 2)}%
              </span>
            </div>
          </div>

          <div className="kv-grid">
            {rows.map(([k, v]) => (
              <div className="kv" key={k}>
                <span>{k}</span>
                <b className="mono">{v}</b>
              </div>
            ))}
          </div>

          <div className="explain">
            <span className="kicker">
              <Gauge size={12} /> MODEL EXPLANATION
            </span>
            <p>{cell.explanation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}