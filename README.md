# Market Signal Dashboard

Personal GitHub Pages dashboard for daily stock-market signal ranking.

This project intentionally avoids paid LLM APIs. Rankings are generated with deterministic Python analysis from free data sources, then rendered as a static Vite + React site.

## Free Data Sources

- Alpaca free IEX market-data feed for daily stock bars
- Optional FRED API key for macro indicators
- GitHub Actions for scheduled generation
- GitHub Pages for static hosting

## Required GitHub Secrets

Add these in `Settings -> Secrets and variables -> Actions`:

- `APCA_API_KEY_ID`
- `APCA_API_SECRET_KEY`

Optional:

- `FRED_API_KEY`

## Local Development

```bash
npm install
npm run dev
```

Generate local data:

```bash
pip install -r requirements.txt
python scripts/analyze_market.py
```

Without Alpaca secrets, the script writes a configuration-required dashboard state instead of fake recommendations.

## Deployment

The workflow in `.github/workflows/update-stocks.yml` runs after U.S. market close on weekdays and can also be started manually from GitHub Actions.

In repository settings, set GitHub Pages source to **GitHub Actions**.

## Methodology

The top 20 list is ranked with:

- 5D, 20D, and 60D price momentum
- 20D average volume and dollar liquidity
- volatility-adjusted return
- relative strength versus SPY
- optional FRED macro context

This is a personal research dashboard, not financial advice.
