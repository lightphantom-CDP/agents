# Investment Advisor — real-time buy scores + a Buffett-style DCA plan

A small, dependency-free tool that answers one question on demand (e.g. every
hour): **"Is right now a relatively good price to add to my positions?"**

It scores the **S&P 500 (SPY)**, **NVIDIA (NVDA)**, **Amazon (AMZN)** and
**Meta (META)** from 0–100, turns those scores into a disciplined
dollar-cost-averaging plan for your cash, and then checks that plan honestly
against your savings goal.

> **This is an educational tool, not financial advice.** See
> [Honest goal check](#honest-goal-check-please-read) and the disclaimer at the
> bottom before acting on anything here.

---

## Quick start

No API key and no third-party packages are required — it uses only the Python
3.12 standard library and Yahoo Finance's public data endpoint.

```bash
# From the repository root:
python -m investment_advisor                       # default watchlist & goal
python -m investment_advisor --format markdown     # nice for a GitHub summary
python -m investment_advisor --format json --save scores.json
```

Custom inputs:

```bash
python -m investment_advisor \
  --cash 4000 \
  --target-idr 1000000000 \
  --tickers SPY,NVDA,AMZN,META \
  --horizons 3,4 \
  --tranches 12
```

Run the tests (offline, deterministic):

```bash
python -m unittest discover -s investment_advisor -p "test_*.py"
```

### CLI options

| Flag | Default | Meaning |
|---|---|---|
| `--cash` | `4000` | Cash available to invest, in USD. |
| `--target-idr` | `1000000000` | Savings goal, in IDR. |
| `--usd-idr` | live | Override the USD→IDR rate (otherwise fetched live). |
| `--tickers` | `SPY,NVDA,AMZN,META` | Comma-separated watchlist. |
| `--horizons` | `3,4` | Goal horizons in years. |
| `--tranches` | `12` | How many DCA tranches to split your cash into. |
| `--format` | `text` | `text`, `markdown`, or `json`. |
| `--save PATH` | — | Also write the rendered output to a file. |

---

## What the score means

The score is a **Warren-Buffett-flavoured value/entry gauge**, not a trading
signal and not a price prediction. Higher = today looks like a relatively
better entry versus the asset's own recent history. It blends five sub-scores:

| Sub-score | Weight | Idea (Buffett lens) |
|---|---:|---|
| Value in 52-week range | 25% | Cheaper within its own range = more margin of safety. |
| Drawdown from the high | 20% | "Be greedy when others are fearful" — reward discounts. |
| RSI(14) | 20% | Oversold = attractive; overbought = wait. |
| Trend / quality | 20% | Avoid falling knives *and* wildly extended prices. |
| Short-term pullback | 15% | A dip inside a longer-term uptrend is a gift. |

Scores map to an action label:

| Score | Action |
|---:|---|
| ≥ 78 | STRONG BUY |
| 62–78 | BUY / ADD |
| 48–62 | ACCUMULATE (DCA) |
| 34–48 | HOLD / PATIENT |
| < 34 | WAIT / EXPENSIVE |

For a **broad index** the right long-run behaviour is almost always to keep
buying on schedule; the score mostly influences *how much* to add to the
higher-risk single stocks.

---

## The DCA plan

Buffett's advice for most people is a low-cost S&P 500 index fund bought
steadily over time. This tool follows that spirit:

- The **index (SPY) is the core**; NVDA/AMZN/META are higher-risk *satellites*.
- Your cash is split into **tranches** (default 12) so you dollar-cost average
  instead of trying to time a lump sum.
- Each tranche is spread across the watchlist by policy weight, then gently
  **tilted toward whatever currently scores as better value**.
- A "market temperature" reading nudges tranche sizing modestly (lean in when
  things look cheap, keep more dry powder when they look rich) — never
  aggressively, because timing is unreliable.

---

## Honest goal check (please read)

You start with **$4,000** and want **1,000,000,000 IDR** (≈ **$55,000–$62,000**
depending on the exchange rate) in **3–4 years**. The tool does this maths for
you every run, and it is blunt about it:

- Reaching the goal **from the starting pot alone** needs roughly **~90%/year
  for 4 years** or **~140%/year for 3 years**.
- For scale: the long-run S&P 500 averages **~10%/year**, and Warren Buffett's
  *legendary* lifetime record is **~20%/year**. Even a sustained 30%/year would
  turn $4,000 into only ~$8,800–$11,400 over this horizon — far short of the
  goal.
- Chasing ~100%+/year requires extreme, concentrated speculation, which is the
  **opposite** of a Buffett mindset (capital preservation + margin of safety)
  and can easily wipe out the account.

**What actually works** — the tool prints, for each horizon, the monthly
saving required at a plausible **12%/year**. Typically that's on the order of
**~$800–$1,200/month** of fresh contributions on top of the $4,000. So the
realistic paths are:

1. **Add regular contributions** (the single biggest lever), and/or
2. **Extend the horizon** (compounding needs time), and/or
3. **Moderate the target**.

Investing well is the easy part; **funding the plan and staying patient** is
what gets you there.

---

## Scheduling the hourly check

### GitHub Actions (included)

`.github/workflows/investment-scores.yml` runs every hour, prints the report to
the job summary, and uploads a JSON snapshot as an artifact. It needs no
secrets. GitHub only runs `schedule` triggers from the **default branch** (and
disables scheduled workflows in forks / after long inactivity), so merge it to
`main` — or trigger it manually via **Run workflow**.

### Local cron

```cron
# Every hour, on the hour — append a markdown report to a log file.
0 * * * * cd /path/to/repo && /usr/bin/python3 -m investment_advisor --format markdown >> ~/investment-scores.log 2>&1
```

---

## How it works (architecture)

| Module | Responsibility |
|---|---|
| `data.py` | Fetch + parse Yahoo chart JSON and the USD/IDR rate (stdlib `urllib`). |
| `indicators.py` | SMA, Wilder RSI, drawdown, 52-week range position, volatility. |
| `scoring.py` | Combine indicators into the 0–100 buy score + action. |
| `planner.py` | Goal feasibility maths and the score-tilted DCA allocation. |
| `advisor.py` | Orchestrates everything (data providers are injectable for tests). |
| `report.py` | Render text / markdown / JSON. |
| `__main__.py` | CLI. |

The network layer is isolated from the pure logic, so the whole pipeline is
unit-tested offline with synthetic data (no live calls in CI).

### Data & limitations

- Prices are delayed (Yahoo's free feed); on weekends/holidays you get the last
  session's close. The report always shows a **"Data as of"** timestamp.
- The score uses **price/technical** inputs, not deep fundamentals (earnings,
  moat, management). A cheap-looking price can still be "cheap for a reason".
- No tax, brokerage-fee, or Indonesia-specific account modelling.

---

## Disclaimer

This project is for **education and personal experimentation only**. It is
**not** financial, investment, tax, or legal advice, and nothing here is a
recommendation to buy or sell any security. Markets are uncertain; individual
stocks can fall 50%+ and never recover. Past performance does not predict future
results. Only invest money you can afford to leave untouched, do your own
research, and consider consulting a licensed financial advisor.
