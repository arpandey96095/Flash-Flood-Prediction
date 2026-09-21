import { useMemo, useState } from "react";
import { ArrowUpDown, ShieldAlert, Search, ChevronsUpDown } from "lucide-react";
import { ALERT_ORDER, ALERT_COLORS, fmt } from "../lib/format";

function AlertChip({ level }) {
  const c = ALERT_COLORS[level] || ALERT_COLORS.GREEN;
  return (
    <span className="chip" style={{ color: c.text, background: c.bg, borderColor: c.border }}>
      {level}
    </span>
  );
}

const COLS = [
  { key: "village_name", label: "Village", numeric: false },
  { key: "block_name", label: "Block", numeric: false },
  { key: "grid_cells", label: "Cells", numeric: true },
  { key: "village_risk", label: "Village Risk", numeric: true },
  { key: "average_risk", label: "Avg", numeric: true },
  { key: "max_risk", label: "Max", numeric: true },
  { key: "alert_level", label: "Alert", numeric: false, chip: true },
];

export default function VillagesTable({ villages, onSelect, selectedLevel }) {
  const [sort, setSort] = useState({ key: "village_risk", dir: "desc" });
  const [query, setQuery] = useState("");
  const [levelFilter, setLevelFilter] = useState("ALL");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return villages
      .filter((v) => {
        if (levelFilter !== "ALL" && v.alert_level !== levelFilter) return false;
        if (!q) return true;
        return (
          String(v.village_name || "").toLowerCase().includes(q) ||
          String(v.block_name || "").toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        const av = a[sort.key];
        const bv = b[sort.key];
        const cmp =
          typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
        return sort.dir === "asc" ? cmp : -cmp;
      });
  }, [villages, query, levelFilter, sort]);

  const toggleSort = (key) =>
    setSort((s) => ({
      key,
      dir: s.key === key ? (s.dir === "desc" ? "asc" : "desc") : "desc",
    }));

  return (
    <div className="table-card">
      <div className="card-head wrap">
        <div>
          <span className="kicker">
            <ShieldAlert size={13} /> VILLAGE WATCHLIST
          </span>
          <h3>Village-level risk aggregation</h3>
        </div>
        <div className="table-controls">
          <div className="map-search">
            <Search size={14} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search village / block…"
            />
          </div>
          <select
            className="sel"
            value={levelFilter}
            onChange={(e) => {
              setLevelFilter(e.target.value);
              onSelect?.(e.target.value);
            }}
          >
            <option value="ALL">All alerts</option>
            {ALERT_ORDER.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {COLS.map((c) => (
                <th
                  key={c.key}
                  className={c.numeric ? "num" : ""}
                  onClick={() => toggleSort(c.key)}
                >
                  <span className="th-inner">
                    {c.label}
                    <ArrowUpDown size={11} className="sort-ico" />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((v, i) => (
              <tr key={`${v.village_name}-${i}`}>
                <td className="vname">
                  <i className="dot" style={{ background: ALERT_COLORS[v.alert_level]?.fill }} />
                  {v.village_name}
                </td>
                <td>{v.block_name || "—"}</td>
                <td className="num mono">{fmt(v.grid_cells)}</td>
                <td className="num mono strong">
                  {fmt(v.village_risk, 1)}
                </td>
                <td className="num mono">{fmt(v.average_risk, 1)}</td>
                <td className="num mono">{fmt(v.max_risk, 1)}</td>
                <td>
                  <AlertChip level={v.alert_level} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <div className="empty">No villages match the filters.</div>}
      </div>

      <div className="table-foot mono">
        <ChevronsUpDown size={12} /> {fmt(rows.length)} of {fmt(villages.length)} villages
      </div>
    </div>
  );
}