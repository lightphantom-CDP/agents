# Warren Buffett Investment Scorer

**An hourly, real-time "is this a good price to add?" scorer for a long-term,
value-minded investor.**

Built for a concrete plan: dollar-cost-average into the **S&P 500 (SPY)** plus
three large-cap compounders — **NVIDIA (NVDA)**, **Amazon (AMZN)** and
**Meta (META)** — starting from **$4,000**, with the audacious goal of reaching
**1,000,000,000 IDR (~$55–60k) in 3–4 years**. Every hour it fetches live prices,
scores each holding from 0–100, and tells you whether now is a sensible moment to
put money to work — then it does the honest math on the goal itself.

> **This is an educational decision-support tool, NOT financial advice.** Markets
> can and do go down. Do your own research and consider a licensed advisor.

---

## Why this design (the Warren Buffett lens)

Buffett's core ideas are baked into the score:

1. **Margin of safety** — prefer buying quality when it is *on sale*, not at
   euphoric highs. ("Be fearful when others are greedy, greedy when others are
   fearful.")
2. **Buy great businesses and hold** — reward an intact long-term uptrend; don't
   try to catch falling knives.
3. **Be patient** — a *HOLD / WAIT* is a legitimate answer. Cash is a position.
4. **Temperament over prediction** — the tool sizes your *regular* buys; it does
   not promise to call tops and bottoms.

The catch: Buffett buys on *valuation*, and he'd be the first to say you cannot
turn $4,000 into a billion rupiah in a few years without either enormous luck or
steady contributions. The tool says so plainly (see **Goal check** below).

---

## Quick start (no dependencies to install)

The core runs on the **Python 3.9+ standard library only** — no pandas, no numpy,
no API key.

```bash
cd 6_mcp/community_contributions/warren_buffett_investment_scorer

# Score the default portfolio using live prices
python -m investment_scorer

# No network? Use deterministic offline demo data
python -m investment_scorer --demo

# Machine-readable output (great for piping into an agent)
python -m investment_scorer --json
```

### Example (offline `--demo` data)

```
====================================================================
  WARREN BUFFETT INVESTMENT SCORER  -  hourly entry-price check
====================================================================
  2026-08-05 22:44 UTC   |   US market closed (approx) - prices are last close

  PORTFOLIO SIGNAL:  62.9/100  ->  NEUTRAL - DCA
  [#############-------]
  Fair value overall - stick to your regular dollar-cost-averaging buy.

  ----------------------------------------------------------------
  TICKER       PRICE   SCORE  BAR                   CALL
  ----------------------------------------------------------------
  NVDA    USD 127.93   65.5  [##########------]  NEUTRAL - DCA
  META    USD 132.15   64.3  [##########------]  NEUTRAL - DCA
  AMZN    USD 266.15   63.5  [##########------]  NEUTRAL - DCA
  SPY     USD 170.50   60.7  [##########------]  NEUTRAL - DCA
  ----------------------------------------------------------------

  * NVIDIA scores 65/100 -> NEUTRAL - DCA. Strongest pillar: Valuation (93); weakest: Trend / quality (0).
      - Valuation (margin of safety):   93  (2% up its 52-wk range, 39.8% below the 52-wk high)
      - Technical timing:   82  (RSI 27, -28.6% vs 200DMA, MACD down)
      - Trend / quality:     0  (below 200DMA, 50<200 (weak), 6-mo -34%)
      - Momentum / pullback: 54  (-39.8% off highs, 1-mo -11.0%)
```

_(Values above are synthetic demo data so the example is reproducible.)_

---

## How the 0–100 score works

Each holding is scored on four transparent pillars that deliberately **pull
against each other**, so the highest scores land on *a healthy pullback inside an
intact uptrend* — a patient investor's fat pitch.

| Pillar | Weight | What it measures | High score when… |
|--------|:------:|------------------|------------------|
| **Valuation (margin of safety)** | 35% | Position in the 52-week range + discount from the 52-week high (plus P/E if `yfinance` is installed) | Trading well below recent highs / cheap |
| **Technical timing** | 30% | RSI(14), distance from the 200-day average, MACD | Oversold, below/near the 200DMA, momentum turning up |
| **Trend / quality** | 20% | Price vs 200DMA, 50/200 golden cross, 6-month momentum | Durable long-term uptrend intact |
| **Momentum / pullback** | 15% | Drawdown from the 52-week high | A *healthy* 5–20% dip (not "at highs", not "falling knife") |

The weighted blend maps to a recommendation:

| Score | Call |
|------:|------|
| ≥ 80 | **STRONG BUY** — fat pitch |
| 66–79 | **BUY / ACCUMULATE** |
| 50–65 | **NEUTRAL — DCA** (keep your regular schedule) |
| 35–49 | **HOLD / WAIT** for a better price |
| < 35 | **EXPENSIVE — AVOID ADDING** |

> **Note on the S&P 500:** with only price data available (no fundamentals), an
> index sitting at fresh all-time highs will score *low on valuation by design* —
> that is the margin-of-safety lens working, not a bug. For a pure index, treat a
> low score as "make this a smaller buy this hour", not "sell".

---

## Goal check

The tool converts your rupiah target to USD at the **live USD/IDR rate**, then
reports:

- the annual return the **lump sum alone** would need (spoiler: for
  $4,000 → 1B IDR in 3–4 years it's roughly **~100–150%/yr** — far beyond even
  Buffett's legendary ~20%/yr), and
- the **monthly contribution** required under sober return assumptions (8/10/15/20%).

Example verdict (live FX):

```
  Target: 1.00B IDR  ~=  $55,800 USD  (USD/IDR 17,930 live)
  Starting cash: $4,000
  Lump-sum-only return required -> 3y: 141%/yr   3.5y: 118%/yr   4y: 93%/yr
  Verdict: Very aggressive ... The realistic path is regular contributions.

  Monthly saving needed to reach the goal:
      @ 10%/yr over 4y: ~$860/month
      @ 15%/yr over 4y: ~$755/month
```

The takeaway a good advisor would give: **the entry-timing score helps you buy
well, but hitting this goal is driven far more by how much you add each month
than by perfect timing.** Automate the contributions; let the score tilt their
*size*.

---

## Run it every hour (cron)

```bash
# edit your crontab
crontab -e

# check every hour on the hour, logging to reports/cron.log
0 * * * * /full/path/to/warren_buffett_investment_scorer/run_hourly.sh
```

`run_hourly.sh` resolves its own path, prefers `uv` (used throughout this course)
and falls back to `python3`. Reports are written to `reports/` as timestamped
`report_YYYYMMDD_HHMMSS.{md,json}` plus a rolling `latest.{md,json}`.

### Phone alerts (optional)

Set the same Pushover variables the rest of the course uses, and you'll get a
push only when something crosses into buy territory:

```bash
export PUSHOVER_TOKEN=...   # https://pushover.net
export PUSHOVER_USER=...
python -m investment_scorer --notify
```

---

## Use it from your agents (MCP)

`mcp_server.py` exposes the scorer as MCP tools so the LangGraph / OpenAI-Agents /
AutoGen agents from earlier weeks can ask about entry prices in natural language:

- `score_ticker(symbol, name="", demo=False)`
- `score_portfolio(demo=False)`
- `investment_goal_plan(cash_usd=4000, target_idr=1e9, min_years=3, max_years=4)`

Example `mcp_params` entry (stdio):

```python
investment_scorer = {
    "command": "uv",
    "args": ["run", "mcp_server.py"],
    # cwd: this folder
}
```

---

## Configuration

| Override | How |
|----------|-----|
| Watch-list | `SCORER_TICKERS="SPY:S&P 500:0.4,NVDA:NVIDIA:0.2,..."` env var |
| Starting cash | `--cash 4000` |
| Target (IDR) | `--target-idr 1000000000` |
| Horizon | `--min-years 3 --max-years 4` |
| Fallback FX | `--fx 16500` (used only if the live rate can't be fetched) |
| Output dir | `--output ./reports` |
| Loop mode | `--loop --interval 3600` (self-schedule instead of cron) |

Richer valuation (real trailing/forward P/E) is automatic **if** `yfinance` is
installed — otherwise the valuation pillar uses the always-available price-based
proxy. Install it with `pip install yfinance` (see `requirements.txt`).

---

## Data & resilience

- **Source:** Yahoo Finance's public `v8/finance/chart` endpoint — one call
  returns both a near-real-time quote and a year of daily bars, no API key.
- **Resilience:** every request retries with backoff and rotates between Yahoo
  hosts; successful fetches are cached for 15 minutes (an hourly cron never
  hammers the API within the same hour).
- **Never hard-fails:** if the network is unavailable or rate-limited, the tool
  falls back to deterministic synthetic data and prints a clear **data warning**
  so you never mistake fallback numbers for live ones.

---

## Tests

Fully offline and deterministic — no network required:

```bash
python -m unittest discover -s tests -t .
```

---

## Files

```
warren_buffett_investment_scorer/
├── investment_scorer/
│   ├── config.py       # portfolio, weights, goal, score bands
│   ├── data.py         # Yahoo fetch + retries + cache + demo fallback
│   ├── indicators.py   # SMA/EMA/RSI/MACD/drawdown/volatility (pure Python)
│   ├── scoring.py      # the 4-pillar composite scoring engine
│   ├── goal.py         # FX, required CAGR, monthly-contribution math
│   ├── report.py       # console / Markdown / JSON rendering
│   ├── notify.py       # optional Pushover alerts
│   └── cli.py          # `python -m investment_scorer`
├── mcp_server.py       # optional MCP tools for the course's agents
├── run_hourly.sh       # cron wrapper
├── tests/              # offline unit tests
├── requirements.txt
└── README.md
```

---

_Disclaimer: Educational decision-support only — not financial advice. Investing
involves risk, including possible loss of principal. Past performance does not
guarantee future results._
