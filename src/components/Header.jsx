import { useState, useEffect } from "react";
import { Radar, Radio, RefreshCw, Clock } from "lucide-react";
import { fmtClock, fmtTime } from "../lib/format";

export default function Header({ mode, fetchedAt, onRefresh, refreshing, services }) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <div className="brand-mark">
          <Radar size={22} strokeWidth={1.8} />
        </div>
        <div className="brand-text">
          <h1>CHAMOLI&nbsp;EWS</h1>
          <span>Flash&nbsp;Flood&nbsp;Early&nbsp;Warning&nbsp;System&nbsp;·&nbsp;Uttarakhand</span>
        </div>
      </div>

      <div className="topbar-meta">
        <div className="clock-chip">
          <Clock size={14} />
          <LiveClock />
        </div>
        {mode === "live" ? (
          <span className="mode-badge live">
            <Radio size={12} /> LIVE · API
          </span>
        ) : (
          <span className="mode-badge demo">
            <span className="pulse-dot" /> DEMO DATA
          </span>
        )}
        <span className="update-chip" title={fetchedAt ? new Date(fetchedAt).toString() : ""}>
          Sync {fetchedAt ? fmtTime(fetchedAt) : "—"}
        </span>
        <button
          className="icon-btn"
          onClick={onRefresh}
          disabled={refreshing}
          title="Refresh snapshot"
        >
          <RefreshCw size={16} className={refreshing ? "spin" : ""} />
        </button>
      </div>

      {services && services.length > 0 && (
        <div className="svc-strip">
          {services.map((s) => (
            <span key={s} className={`svc-chip ${s.status === "ok" ? "ok" : "down"}`}>
              {s.name}: {s.status}
            </span>
          ))}
        </div>
      )}
    </header>
  );
}

function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return <span title={now.toString()}>{fmtClock(now)}</span>;
}