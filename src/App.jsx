import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  BarChart3,
  CalendarClock,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal
} from "lucide-react";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2
});

const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1
});

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

function formatDate(value) {
  if (!value) return "Not generated yet";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function scoreClass(score) {
  if (score >= 75) return "strong";
  if (score >= 60) return "watch";
  return "neutral";
}

function Trend({ value }) {
  if (value === null || value === undefined) return <span className="muted">n/a</span>;
  const up = value >= 0;
  const Icon = up ? ArrowUp : ArrowDown;
  return (
    <span className={up ? "positive" : "negative"}>
      <Icon size={14} strokeWidth={2.2} />
      {percent.format(value)}
    </span>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("all");
  const [risk, setRisk] = useState("all");
  const [sort, setSort] = useState("rank");
  const [error, setError] = useState("");

  async function loadData() {
    setError("");
    try {
      const response = await fetch(`${import.meta.env.BASE_URL}data/latest.json`, {
        cache: "no-store"
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setData(await response.json());
    } catch (err) {
      setError(`Could not load dashboard data: ${err.message}`);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const recommendations = data?.recommendations ?? [];
  const sectors = useMemo(
    () => ["all", ...Array.from(new Set(recommendations.map((item) => item.sector))).sort()],
    [recommendations]
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const rows = recommendations.filter((item) => {
      const matchesQuery =
        !needle ||
        item.symbol.toLowerCase().includes(needle) ||
        item.name.toLowerCase().includes(needle);
      const matchesSector = sector === "all" || item.sector === sector;
      const matchesRisk = risk === "all" || item.riskLevel === risk;
      return matchesQuery && matchesSector && matchesRisk;
    });

    return [...rows].sort((a, b) => {
      if (sort === "score") return b.score - a.score;
      if (sort === "momentum") return b.metrics.change20d - a.metrics.change20d;
      if (sort === "volatility") return a.metrics.volatility - b.metrics.volatility;
      return a.rank - b.rank;
    });
  }, [recommendations, query, risk, sector, sort]);

  const status = data?.status ?? "loading";
  const isConfigured = status === "ok";

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Personal Market Signals</p>
          <h1>Daily stock dashboard</h1>
          <p className="subhead">
            Top 20 watchlist candidates from free market data and transparent scoring.
          </p>
        </div>
        <button className="iconButton" onClick={loadData} aria-label="Refresh data">
          <RefreshCw size={18} />
        </button>
      </header>

      <section className="notice">
        <ShieldCheck size={18} />
        <p>
          This dashboard is for personal research. It ranks market signals, not personalized
          financial advice. Verify any trade independently.
        </p>
      </section>

      <section className="summaryGrid">
        <div className="stat">
          <CalendarClock size={18} />
          <span>Generated</span>
          <strong>{formatDate(data?.generatedAt)}</strong>
        </div>
        <div className="stat">
          <BarChart3 size={18} />
          <span>Universe</span>
          <strong>{data?.universeCount ?? 0} symbols</strong>
        </div>
        <div className="stat">
          <AlertTriangle size={18} />
          <span>Macro Risk</span>
          <strong>{data?.macro?.riskLevel ?? "unknown"}</strong>
        </div>
      </section>

      {!isConfigured && (
        <section className="setupPanel">
          <h2>Configuration required</h2>
          <p>
            Add free Alpaca API secrets in GitHub Actions to generate live rankings:
            <code>APCA_API_KEY_ID</code> and <code>APCA_API_SECRET_KEY</code>. Add
            <code>FRED_API_KEY</code> only if you want macro indicators.
          </p>
        </section>
      )}

      {error && <section className="errorPanel">{error}</section>}

      <section className="analysisPanel">
        <div>
          <p className="label">Market Context</p>
          <h2>{data?.macro?.summary ?? "Waiting for generated data"}</h2>
        </div>
        <ul>
          {(data?.methodology ?? []).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="controls" aria-label="Dashboard filters">
        <label className="searchBox">
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search ticker or company"
          />
        </label>
        <label>
          <SlidersHorizontal size={16} />
          <select value={sector} onChange={(event) => setSector(event.target.value)}>
            {sectors.map((item) => (
              <option key={item} value={item}>
                {item === "all" ? "All sectors" : item}
              </option>
            ))}
          </select>
        </label>
        <label>
          <AlertTriangle size={16} />
          <select value={risk} onChange={(event) => setRisk(event.target.value)}>
            <option value="all">All risk levels</option>
            <option value="low">Low risk</option>
            <option value="medium">Medium risk</option>
            <option value="high">High risk</option>
          </select>
        </label>
        <label>
          <BarChart3 size={16} />
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="rank">Rank</option>
            <option value="score">Score</option>
            <option value="momentum">20D momentum</option>
            <option value="volatility">Lowest volatility</option>
          </select>
        </label>
      </section>

      <section className="rankList">
        {filtered.length === 0 && (
          <div className="emptyState">
            {isConfigured ? "No symbols match the current filters." : "No generated rankings yet."}
          </div>
        )}
        {filtered.map((item) => (
          <article className="rankRow" key={item.symbol}>
            <div className="rank">#{item.rank}</div>
            <div className="identity">
              <strong>{item.symbol}</strong>
              <span>{item.name}</span>
            </div>
            <div className="scoreBlock">
              <span className={`score ${scoreClass(item.score)}`}>{item.score.toFixed(1)}</span>
              <small>{item.sector}</small>
            </div>
            <div className="metric">
              <span>Price</span>
              <strong>{currency.format(item.price)}</strong>
            </div>
            <div className="metric">
              <span>20D</span>
              <strong>
                <Trend value={item.metrics.change20d} />
              </strong>
            </div>
            <div className="metric">
              <span>Volatility</span>
              <strong>{percent.format(item.metrics.volatility)}</strong>
            </div>
            <div className="metric">
              <span>Avg Volume</span>
              <strong>{formatNumber(item.metrics.avgVolume20d)}</strong>
            </div>
            <p className="rationale">{item.rationale}</p>
            <div className={`riskPill ${item.riskLevel}`}>{item.riskLevel} risk</div>
          </article>
        ))}
      </section>
    </main>
  );
}
