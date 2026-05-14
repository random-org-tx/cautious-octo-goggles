import fs from "fs";

const SYMBOLS = [
  "aapl.us",
  "msft.us",
  "googl.us",
  "amzn.us",
  "nvda.us",
  "meta.us",
  "tsla.us"
];

// Stooq API (no key required)
async function fetchStock(symbol) {
  const url = `https://stooq.com/q/l/?s=${symbol}&f=sd2t2ohlcv&h&e=json`;

  const res = await fetch(url);
  const json = await res.json();

  const d = json?.symbols?.[0];

  if (!d) return null;

  return {
    ticker: symbol.replace(".us","").toUpperCase(),
    price: Number(d.close),
    high: Number(d.high),
    low: Number(d.low),
    volume: Number(d.volume),
    updatedAt: new Date().toISOString()
  };
}

async function run() {
  const results = [];

  for (const s of SYMBOLS) {
    try {
      const data = await fetchStock(s);
      if (data) results.push(data);
    } catch (e) {
      console.error("Failed:", s);
    }
  }

  fs.writeFileSync(
    "./data/stocks.json",
    JSON.stringify(results, null, 2)
  );

  console.log("Dataset updated:", results.length);
}

run();
