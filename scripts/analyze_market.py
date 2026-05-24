import json
import math
import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


OUTPUT_PATH = Path("public/data/latest.json")
ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

UNIVERSE = [
    ("AAPL", "Apple Inc.", "Technology"),
    ("MSFT", "Microsoft Corp.", "Technology"),
    ("NVDA", "NVIDIA Corp.", "Technology"),
    ("GOOGL", "Alphabet Inc.", "Communication Services"),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary"),
    ("META", "Meta Platforms Inc.", "Communication Services"),
    ("AVGO", "Broadcom Inc.", "Technology"),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary"),
    ("JPM", "JPMorgan Chase & Co.", "Financials"),
    ("V", "Visa Inc.", "Financials"),
    ("LLY", "Eli Lilly and Co.", "Health Care"),
    ("UNH", "UnitedHealth Group Inc.", "Health Care"),
    ("XOM", "Exxon Mobil Corp.", "Energy"),
    ("COST", "Costco Wholesale Corp.", "Consumer Staples"),
    ("MA", "Mastercard Inc.", "Financials"),
    ("WMT", "Walmart Inc.", "Consumer Staples"),
    ("HD", "Home Depot Inc.", "Consumer Discretionary"),
    ("PG", "Procter & Gamble Co.", "Consumer Staples"),
    ("JNJ", "Johnson & Johnson", "Health Care"),
    ("BAC", "Bank of America Corp.", "Financials"),
    ("ABBV", "AbbVie Inc.", "Health Care"),
    ("KO", "Coca-Cola Co.", "Consumer Staples"),
    ("NFLX", "Netflix Inc.", "Communication Services"),
    ("CRM", "Salesforce Inc.", "Technology"),
    ("AMD", "Advanced Micro Devices Inc.", "Technology"),
    ("PEP", "PepsiCo Inc.", "Consumer Staples"),
    ("ADBE", "Adobe Inc.", "Technology"),
    ("CSCO", "Cisco Systems Inc.", "Technology"),
    ("ORCL", "Oracle Corp.", "Technology"),
    ("TMO", "Thermo Fisher Scientific Inc.", "Health Care"),
    ("MCD", "McDonald's Corp.", "Consumer Discretionary"),
    ("ACN", "Accenture plc", "Technology"),
    ("GE", "GE Aerospace", "Industrials"),
    ("CAT", "Caterpillar Inc.", "Industrials"),
    ("GS", "Goldman Sachs Group Inc.", "Financials"),
    ("PFE", "Pfizer Inc.", "Health Care"),
    ("DIS", "Walt Disney Co.", "Communication Services"),
    ("NKE", "Nike Inc.", "Consumer Discretionary"),
    ("BA", "Boeing Co.", "Industrials"),
    ("SPY", "SPDR S&P 500 ETF Trust", "Benchmark"),
]


def write_payload(payload):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def configuration_payload(message):
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "configuration_required",
        "source": "Alpaca free IEX feed",
        "universeCount": 0,
        "macro": {"summary": message, "riskLevel": "unknown"},
        "methodology": methodology(),
        "recommendations": [],
    }


def methodology():
    return [
        "Price momentum across 5, 20, and 60 trading days",
        "Volume and dollar-liquidity trend",
        "Volatility-adjusted return",
        "Relative strength versus SPY",
        "Optional macro context from FRED when FRED_API_KEY is configured",
    ]


def fetch_alpaca_bars(symbols):
    key = os.getenv("APCA_API_KEY_ID")
    secret = os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:
        return None

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=220)
    params = {
        "symbols": ",".join(symbols),
        "timeframe": "1Day",
        "start": start.date().isoformat(),
        "end": end.date().isoformat(),
        "limit": 10000,
        "adjustment": "split",
        "feed": "iex",
    }
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
    }
    response = requests.get(ALPACA_BARS_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("bars", {})


def fetch_fred_macro():
    key = os.getenv("FRED_API_KEY")
    if not key:
        return {
            "summary": "FRED_API_KEY is not configured; macro context is limited to market-price behavior.",
            "riskLevel": "medium",
            "indicators": {},
        }

    indicators = {}
    for series_id, label in [("DGS10", "10Y Treasury"), ("DGS2", "2Y Treasury"), ("VIXCLS", "VIX")]:
        params = {
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        try:
            response = requests.get(FRED_URL, params=params, timeout=20)
            response.raise_for_status()
            observations = response.json().get("observations", [])
            value = observations[0]["value"] if observations else "."
            indicators[label] = None if value == "." else float(value)
        except requests.RequestException:
            indicators[label] = None

    ten_year = indicators.get("10Y Treasury")
    two_year = indicators.get("2Y Treasury")
    vix = indicators.get("VIX")
    spread = None if ten_year is None or two_year is None else ten_year - two_year

    risk = "medium"
    notes = []
    if vix is not None:
        if vix >= 25:
            risk = "high"
            notes.append(f"VIX is elevated at {vix:.1f}.")
        elif vix <= 15:
            risk = "low"
            notes.append(f"VIX is contained at {vix:.1f}.")
        else:
            notes.append(f"VIX is moderate at {vix:.1f}.")
    if spread is not None:
        notes.append(f"10Y-2Y spread is {spread:.2f} percentage points.")

    return {
        "summary": " ".join(notes) if notes else "Macro data was requested but unavailable.",
        "riskLevel": risk,
        "indicators": indicators,
    }


def latest_close(bars):
    if not bars:
        return None
    return bars[-1].get("c")


def pct_change(bars, days):
    if len(bars) <= days:
        return None
    current = bars[-1].get("c")
    previous = bars[-days - 1].get("c")
    if not current or not previous:
        return None
    return (current / previous) - 1


def avg_volume(bars, days=20):
    values = [bar.get("v", 0) for bar in bars[-days:]]
    return sum(values) / len(values) if values else 0


def annualized_volatility(bars, days=20):
    closes = [bar.get("c") for bar in bars[-(days + 1) :] if bar.get("c")]
    if len(closes) < 3:
        return 0
    returns = [(closes[i] / closes[i - 1]) - 1 for i in range(1, len(closes))]
    return statistics.stdev(returns) * math.sqrt(252) if len(returns) > 1 else 0


def minmax(rows, key):
    values = [row[key] for row in rows if row[key] is not None and math.isfinite(row[key])]
    if not values:
        return {id(row): 50 for row in rows}
    low, high = min(values), max(values)
    if high == low:
        return {id(row): 50 for row in rows}
    return {
        id(row): 100 * ((row[key] - low) / (high - low))
        if row[key] is not None and math.isfinite(row[key])
        else 50
        for row in rows
    }


def risk_level(volatility, change20d):
    if volatility >= 0.55 or change20d <= -0.12:
        return "high"
    if volatility >= 0.35 or change20d <= -0.05:
        return "medium"
    return "low"


def rationale(row, spy_20d):
    parts = []
    if row["change20d"] >= 0:
        parts.append(f"20D momentum is positive at {row['change20d'] * 100:.1f}%.")
    else:
        parts.append(f"20D momentum is negative at {row['change20d'] * 100:.1f}%.")

    if spy_20d is not None:
        relative = row["change20d"] - spy_20d
        direction = "above" if relative >= 0 else "below"
        parts.append(f"Relative strength is {abs(relative) * 100:.1f} points {direction} SPY.")

    if row["volatility"] <= 0.3:
        parts.append("Recent volatility is contained.")
    elif row["volatility"] >= 0.55:
        parts.append("Recent volatility is elevated.")

    return " ".join(parts)


def build_recommendations(bars_by_symbol):
    symbol_meta = {symbol: (name, sector) for symbol, name, sector in UNIVERSE}
    spy_20d = pct_change(bars_by_symbol.get("SPY", []), 20)
    rows = []

    for symbol, name, sector in UNIVERSE:
        if symbol == "SPY":
            continue
        bars = bars_by_symbol.get(symbol, [])
        if len(bars) < 30:
            continue

        price = latest_close(bars)
        change5d = pct_change(bars, 5) or 0
        change20d = pct_change(bars, 20) or 0
        change60d = pct_change(bars, 60) or change20d
        volatility = annualized_volatility(bars)
        volume20d = avg_volume(bars)
        dollar_volume = (price or 0) * volume20d
        relative20d = change20d - spy_20d if spy_20d is not None else change20d

        rows.append(
            {
                "symbol": symbol,
                "name": name,
                "sector": sector,
                "price": price,
                "change5d": change5d,
                "change20d": change20d,
                "change60d": change60d,
                "relative20d": relative20d,
                "volatility": volatility,
                "avgVolume20d": volume20d,
                "dollarVolume": dollar_volume,
            }
        )

    momentum_scores = minmax(rows, "change20d")
    trend_scores = minmax(rows, "change60d")
    relative_scores = minmax(rows, "relative20d")
    liquidity_scores = minmax(rows, "dollarVolume")
    volatility_scores = minmax(rows, "volatility")

    for row in rows:
        vol_score = 100 - volatility_scores[id(row)]
        row["score"] = (
            momentum_scores[id(row)] * 0.32
            + trend_scores[id(row)] * 0.18
            + relative_scores[id(row)] * 0.25
            + liquidity_scores[id(row)] * 0.10
            + vol_score * 0.15
        )

    ranked = sorted(rows, key=lambda item: item["score"], reverse=True)[:20]
    recommendations = []
    for index, row in enumerate(ranked, start=1):
        risk = risk_level(row["volatility"], row["change20d"])
        recommendations.append(
            {
                "rank": index,
                "symbol": row["symbol"],
                "name": symbol_meta[row["symbol"]][0],
                "sector": symbol_meta[row["symbol"]][1],
                "price": round(row["price"], 2),
                "score": round(row["score"], 2),
                "riskLevel": risk,
                "rationale": rationale(row, spy_20d),
                "metrics": {
                    "change5d": round(row["change5d"], 4),
                    "change20d": round(row["change20d"], 4),
                    "change60d": round(row["change60d"], 4),
                    "relative20d": round(row["relative20d"], 4),
                    "volatility": round(row["volatility"], 4),
                    "avgVolume20d": round(row["avgVolume20d"], 0),
                    "dollarVolume": round(row["dollarVolume"], 0),
                },
            }
        )
    return recommendations


def main():
    symbols = [symbol for symbol, _, _ in UNIVERSE]
    if not os.getenv("APCA_API_KEY_ID") or not os.getenv("APCA_API_SECRET_KEY"):
        write_payload(
            configuration_payload(
                "APCA_API_KEY_ID and APCA_API_SECRET_KEY are not configured. Add free Alpaca keys in repository Actions secrets."
            )
        )
        return

    try:
        bars_by_symbol = fetch_alpaca_bars(symbols)
    except requests.RequestException as exc:
        write_payload(
            configuration_payload(
                f"Could not fetch Alpaca market data: {exc}. Check API keys and account access."
            )
        )
        return

    recommendations = build_recommendations(bars_by_symbol or {})
    macro = fetch_fred_macro()
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if recommendations else "no_data",
        "source": "Alpaca free IEX feed",
        "universeCount": len([symbol for symbol in bars_by_symbol if symbol != "SPY"]),
        "macro": macro,
        "methodology": methodology(),
        "recommendations": recommendations,
    }
    write_payload(payload)
    print(f"Wrote {len(recommendations)} recommendations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
