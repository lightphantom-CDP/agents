# Investment Scorer — real-time timing scores (Warren Buffett lens)

A small, **dependency-free** Python tool that answers one question on a schedule:

> _"Is right now a reasonable price to add to my holdings?"_

It scores the portfolio you described — the **S&P 500** (tracked via the `SPY`
ETF) plus **NVIDIA**, **Amazon**, and **Meta** — through a Warren‑Buffett‑style
lens: great businesses, at a fair price, bought patiently.

> ⚠️ **This is an educational tool, _not_ financial advice.** The scores are
> mechanical signals computed from public, delayed (~15 min) market data. They
> are not a recommendation to buy or sell any security. Investing involves risk,
> including loss of principal. Do your own research and/or consult a licensed
> advisor.

---

## Quick start

No installation and no API keys required — it uses only the Python standard
library and public Yahoo Finance endpoints. You need Python 3.12+.

```bash
# From the repository root:
python -m investment_scorer                 # pretty console report
python -m investment_scorer --snapshot      # also write investment_scorer/SNAPSHOT.md
python -m investment_scorer --markdown out.md
python -m investment_scorer --json out.json # machine-readable output
python -m investment_scorer --no-fundamentals  # price/timing only (faster, offline-ish)
python -m investment_scorer --quiet --json -   # JSON only, to stdout
```

A ready-made example of the output lives in
[`SNAPSHOT.md`](SNAPSHOT.md).

## Run it hourly (real-time-ish)

You asked to check **every hour**. Three easy ways:

1. **GitHub Actions (recommended, zero setup).** The workflow at
   [`.github/workflows/investment-scores.yml`](../.github/workflows/investment-scores.yml)
   runs the scorer every hour and puts the report in the run's **Summary** tab
   (plus a downloadable `SNAPSHOT.md` artifact). GitHub only runs scheduled
   workflows on the **default branch**, so the cron kicks in once this is merged
   to `main`; until then use the **"Run workflow"** button.

2. **Local cron** (macOS/Linux):

   ```cron
   0 * * * * cd /path/to/repo && /usr/bin/python3 -m investment_scorer --snapshot >> /tmp/scores.log 2>&1
   ```

3. **Just run the command** whenever you're deciding whether to buy.

> Markets are only open ~6.5 hours on weekdays; outside those hours the price is
> simply the last close, so scores won't change much.

---

## How the score works

Each holding gets two independent **0–100** sub-scores that are then blended
into a **composite**. Higher = a more attractive entry *right now*.

### 1. Timing sub-score — "is the price attractive today?"

| Factor | Idea | Weight |
|---|---|---:|
| **RSI(14)** | Oversold (low) = opportunity; overbought (high) = wait | 30% |
| **52-week range position** | Near the low is cheaper than near the high | 25% |
| **Price vs 200-day average** | Discount to the long-term trend line | 25% |
| **Drawdown from 52-week high** | "Be greedy when others are fearful" | 20% |

### 2. Quality / value sub-score — the Buffett lens

| Factor | Idea | Weight |
|---|---|---:|
| **Return on equity** | Durable, high ROE ≈ a competitive moat | 20% |
| **Net profit margin** | Fat, stable margins ≈ pricing power | 18% |
| **Debt / equity** | Low leverage survives bad years | 15% |
| **Free cash flow** | Real cash, not just accounting earnings | 10% |
| **Valuation (P/E, PEG, P/B)** | Pay a fair price for the business | 25% |
| **Growth** | The business is still compounding | 12% |

For the S&P 500 (a diversified fund, not a single business) the quality inputs
are limited, so it leans on valuation + timing, and the report reminds you that
**for a broad index, steady buying beats timing.**

### 3. Composite & verdict

* **Stocks:** 55% quality + 45% timing.
* **Index:** 30% "value" + 70% timing.

| Composite | Verdict | What it suggests |
|---:|---|---|
| 78–100 | **STRONG BUY ZONE** | Attractive entry |
| 62–77 | **ACCUMULATE** | Good time to add |
| 46–61 | **FAIR** | Keep dollar-cost averaging, no urgency |
| 32–45 | **PATIENCE** | A little rich — smaller buys / wait |
| 0–31 | **EXPENSIVE** | Wait for a better price |

Every factor is mapped through a transparent piece-wise-linear curve (see
[`scoring.py`](scoring.py)), and any missing data point is dropped with the
remaining weights renormalised — never silently treated as zero.

---

## Your goal — an honest reality check

You want to grow **$4,000 → 1,000,000,000 IDR** (about **$55,000–$61,000**,
depending on the exchange rate the tool fetches live) in **3–4 years**.

The tool computes what that actually requires:

* A lump sum alone implies roughly a **90–140% annual return** — that is
  *extremely* aggressive (closer to speculation than Buffett-style investing)
  and would mean taking on a real risk of large losses. For context, the S&P
  500's long-run return is ~10%/yr, and even legendary investors rarely sustain
  20–25%/yr for years.
* The realistic lever is **regular contributions**. The report prints the
  **monthly amount** needed to hit the target under conservative (10%),
  strong (15%), and exceptional (25%) return assumptions, so you can plan around
  a savings rate instead of hoping for a moon-shot return.

A Buffett-flavoured summary: **buy quality at fair prices, add steadily, keep
costs and taxes low, and give it time.** Chasing a 15× in 3–4 years by timing
the market is not what "be greedy when others are fearful" means.

---

## Customising

Everything tweakable lives in [`config.py`](config.py):

* `HOLDINGS` — change or add tickers.
* `TIMING_WEIGHTS`, `QUALITY_WEIGHTS`, `COMPOSITE_BLEND` — re-weight the model.
* `VERDICT_BANDS` — relabel the score bands.
* `GOAL` — set your `start_capital_usd`, `target_idr`, horizon, and (importantly)
  `monthly_contribution_usd` to see realistic projections.

## Files

| File | Purpose |
|---|---|
| `yahoo.py` | Standard-library Yahoo Finance client (history, fundamentals, FX) |
| `indicators.py` | RSI, moving averages, drawdown, range position |
| `scoring.py` | Timing + Buffett quality/value factors → composite + verdict |
| `goal.py` | USD/IDR conversion, required CAGR, contribution planner |
| `report.py` | Console + Markdown rendering |
| `cli.py` | `python -m investment_scorer` entry point |
| `config.py` | Holdings, weights, verdict bands, goal |

---

_Data: Yahoo Finance public endpoints (delayed). No affiliation. Again: this is
educational software, not financial advice._
