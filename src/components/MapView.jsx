import { useEffect, useRef, useState, useMemo } from "react";
import L from "leaflet";
import { Search, SlidersHorizontal, Lock } from "lucide-react";
import { ALERT_ORDER, ALERT_COLORS, fmt } from "../lib/format";

const CENTER = [30.32, 79.4];

export default function MapView({ cells, onSelect, onZoom }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);

  const [filters, setFilters] = useState(() => new Set(ALERT_ORDER));
  const [query, setQuery] = useState("");
  const [minRisk, setMinRisk] = useState(0);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: CENTER,
      zoom: 10,
      zoomControl: false,
      attributionControl: true,
      preferCanvas: false,
    });
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }
    ).addTo(map);

    const canvasRenderer = L.canvas({ padding: 0.5 });
    layerRef.current = L.layerGroup([], { renderer: canvasRenderer }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cells
      .filter(
        (c) =>
          filters.has(c.alert_level) &&
          c.risk_score >= minRisk &&
          (!q || String(c.village_name || "").toLowerCase().includes(q))
      )
      .sort((a, b) => b.risk_score - a.risk_score);
  }, [cells, filters, query, minRisk]);

  useEffect(() => {
    if (!mapRef.current || !layerRef.current) return;

    const layer = layerRef.current;
    layer.clearLayers();

    // Cap markers so the canvas renderer stays smooth on huge grids.
    const draw = visible.length > 3500 ? visible.slice(0, 3500) : visible;

    const markers = [];
    for (const c of draw) {
      if (c.latitude == null || c.longitude == null) continue;
      const col = ALERT_COLORS[c.alert_level] || ALERT_COLORS.GREEN;
      const radius = 4 + (c.risk_score / 100) * 9;
      const m = L.circleMarker([c.latitude, c.longitude], {
        radius,
        stroke: true,
        color: col.border,
        weight: 0.6,
        opacity: c.alert_level === "RED" ? 0.95 : 0.8,
        fillColor: col.fill,
        fillOpacity: c.alert_level === "RED" ? 0.72 : 0.55,
        interactive: true,
      });
      m.bindTooltip(
        `<div class="tip">
          <b>${c.grid_id}</b> · ${c.alert_level}<br/>
          ${fmt(c.risk_score, 2)} risk · ${c.village_name || "unmapped"}<br/>
          ${c.latitude.toFixed(4)}, ${c.longitude.toFixed(4)}
        </div>`,
        { direction: "top", className: "leaflet-tip" }
      );
      m.on("click", () => onSelect(c));
      markers.push(m);
    }

    const featureGroup = L.featureGroup(markers);
    featureGroup.addTo(layer);

    // Keep a sensible viewport: zoom fit only on first meaningful paint.
    if (markers.length && !mapRef.current._fittedOnce) {
      const bounds = featureGroup.getBounds();
      if (bounds.isValid()) {
        mapRef.current.fitBounds(bounds.pad(0.12), { maxZoom: 12 });
      }
      mapRef.current._fittedOnce = true;
    }

    onZoom?.(Math.min(draw.length, cells.length), cells.length);
  }, [visible, cells.length, onSelect, onZoom]);

  const toggleFilter = (lvl) => {
    setFilters((prev) => {
      const next = new Set(prev);
      if (next.has(lvl)) next.delete(lvl);
      else next.add(lvl);
      if (next.size === 0) next.add(lvl); // never fully empty
      return next;
    });
  };

  return (
    <div className="map-panel">
      <div className="map-tools">
        <div className="map-pills">
          {ALERT_ORDER.map((lvl) => (
            <button
              key={lvl}
              className={`pill ${filters.has(lvl) ? "on" : "off"}`}
              style={
                filters.has(lvl)
                  ? {
                    background: `${ALERT_COLORS[lvl].fill}22`,
                    borderColor: `${ALERT_COLORS[lvl].fill}99`,
                  }
                  : undefined
              }
              onClick={() => toggleFilter(lvl)}
            >
              <i style={{ background: ALERT_COLORS[lvl].fill }} />
              {lvl}
            </button>
          ))}
        </div>

        <div className="map-search">
          <Search size={14} className="mono" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter village…"
          />
        </div>

        <div className="risk-slider">
          <SlidersHorizontal size={14} />
          <input
            type="range"
            min={0}
            max={95}
            step={5}
            value={minRisk}
            onChange={(e) => setMinRisk(Number(e.target.value))}
          />
          <span className="mono">≥{minRisk}</span>
        </div>
      </div>

      <div className="map-container" ref={containerRef} />

      <div className="map-foot">
        <span>
          Showing <b className="mono">{fmt(visible.length)}</b> cells
          {visible.length > cells.length ? "" : ` of ${fmt(cells.length)}`}
        </span>
        {cells.length > 3500 && visible.length > 3500 && (
          <span>
            <Lock size={11} /> rendered top 3500 by risk
          </span>
        )}
      </div>
    </div>
  );
}