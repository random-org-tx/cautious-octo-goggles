import fs from "fs";

const BASE_URL =
  "https://stooq.com/q/l/?s=";

const symbols = [
  "aapl.us",
  "msft.us",
  "googl.us",
  "amzn.us",
  "nvda.us",
  "meta.us",
  "tsla.us"
];

// ---------- SAFE FETCH ----------
async function fetchPrice(symbol) {
  try {
    const res = await fetch(
      `${BASE_URL}${symbol}&f=sd2t2ohlcv&h&e=json`
    );

    const json = await res.json();
    const d = json?.symbols?.[0];

    if (!d) return null;

    return {
      price: Number(d.close) || null,
      high: Number(d.high) || null,
      low: Number(d.low) || null,
      volume: Number(d.volume) || null,
      updatedAt: new Date().toISOString()
    };

  } catch (e) {
    return null;
  }
}

// ---------- MAIN PIPELINE ----------
async function run() {

  // 1. Load bootstrap dataset (CRITICAL)
  const base = JSON.parse(
    fs.readFileSync("./data/stocks.json", "utf-8")
  );

  const updated = [];

  for (let i = 0; i < base.length; i++) {

    const stock = base[i];
    const symbol = symbols[i];

    const live = await fetchPrice(symbol);

    updated.push({
      ticker: stock.ticker,
      company: stock.company,
      sector: stock.sector,

      // fallback-safe enrichment
      price: live?.price ?? stock.basePrice,
      high: live?.high ?? null,
      low: live?.low ?? null,
      volume: live?.volume ?? null,

      updatedAt: live?.updatedAt ?? new Date().toISOString()
    });
  }

  // 2. Write back dataset
  fs.writeFileSync(
    "./data/stocks.json",
    JSON.stringify(updated, null, 2)
  );

  console.log("Dataset updated:", updated.length);
}

run();
