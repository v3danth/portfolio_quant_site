# Risk Metrics — Easy Guide with Examples

This guide explains every number returned by the portfolio risk endpoint:

```
GET /api/v1/portfolios/risk?userId={id}&lookbackDays=252&riskFreeRate=0.0&benchmarkSymbol=SPY
```

All percentages are **decimals**: `0.20` means 20%. The math follows
`docs/MATH_SPECS.md` and is implemented in `backend/app/services/analytics.py`.

---

## 0. The mental model (read this first)

Think of risk as **"how bumpy is the ride?"** and **"how badly could it hurt?"**

- **Volatility** → how bumpy (up and down) the returns are.
- **Max drawdown** → the biggest drop you would have seen from a peak.
- **Value at Risk** → how bad a *single bad day* can be.
- **Sharpe ratio** → how much reward you got **per unit of bumpiness**.
- **Beta** → how much the portfolio moves **with the market**.

Everything is computed from one thing: **the portfolio's daily returns**.
So let's build those first.

---

## 1. The foundation: the daily return series

### Step 1 — Weights (how much of the portfolio is each stock?)

The endpoint looks at your **current holdings** and gives each stock a weight
equal to its share of the total market value (quantity × latest price):

```
weight of AAPL = (value of AAPL) / (total value of all holdings)
```

**Example — a 2-stock portfolio, 1 share each:**

| Stock | Shares | Latest price | Market value | Weight |
|-------|-------:|-------------:|-------------:|-------:|
| AAPL  | 1      | $133.10      | $133.10      | 0.50   |
| MSFT  | 1      | $133.10      | $133.10      | 0.50   |

Each stock is half the portfolio → weight = 0.50 each.

### Step 2 — Each stock's daily return

Using **adjusted close** prices (so dividends/splits are included):

```
daily return = today's price / yesterday's price − 1
```

AAPL went `100 → 110 → 110 → 121 → 133.10`, so its returns are:

| Day | Price | Return |
|----:|------:|-------:|
| 1   | 100   | —      |
| 2   | 110   | +10%   |
| 3   | 110   | 0%     |
| 4   | 121   | +10%   |
| 5   | 133.10| +10%   |

### Step 3 — The portfolio's daily return

`portfolio return = Σ (weight × stock return)`. 50/50 split:

| Day | AAPL | MSFT | Portfolio = 0.5×A + 0.5×M |
|----:|-----:|-----:|--------------------------:|
| 1   | —    | —    | —                         |
| 2   | +10% | +10% | **+10%**                  |
| 3   | 0%   | +10% | **+5%**                   |
| 4   | +10% | 0%   | **+5%**                   |
| 5   | +10% | +10% | **+10%**                  |

So the portfolio daily returns are: **`[+10%, +5%, +5%, +10%]`**.

The real endpoint does exactly this for every day of the last `lookbackDays`
(default **252 ≈ 1 trading year**), then computes the metrics below from the
resulting series.

---

## 2. The metrics

### `annualized_return` — "How much did I earn in a year?"

**In plain words:** if this year's performance were repeated every year, this
is your yearly growth rate.

**Formula:**

```
wealth = (1 + r₁) × (1 + r₂) × … × (1 + rₙ)      (compounded growth)
annualized_return = wealth ^ (252 / n) − 1
```

**Example (our 4-day series, `n = 4`):**
`wealth = 1.10 × 1.05 × 1.05 × 1.10 = 1.334`
→ the portfolio grew **33.4% in 4 days**. Annualizing that assumes it keeps
up for 252 days, so the number is huge. In practice you use ~252 days, and
the growth is real but annualized.

> **Real response example:** `annualized_return: 0.531` means the portfolio
> grew at an annualized rate of **~53%** over the window.

---

### `annualized_volatility` — "How bumpy is the ride?"

**In plain words:** the average size of a daily swing, scaled up to a yearly
number. The single most common measure of risk.

**Formula:**

```
annualized_volatility = standard_deviation(daily returns) × √252
```

**Example (our series `[0.10, 0.05, 0.05, 0.10]`):**
- average return = 7.5%
- standard deviation (sample, n−1) ≈ 2.9%
- annualized ≈ 2.9% × √252 ≈ **46%**

**How to read it:**
- `0.10` (10%) → calm, low risk.
- `0.30` (30%) → choppy, high risk.
- In one year, a portfolio with 25% vol typically moves ±25% around its trend.

> **Real response example:** `annualized_volatility: 0.247` → **~25%** annual
> volatility — a typical large-cap stock portfolio.

---

### `sharpe_ratio` — "Reward per unit of risk"

**In plain words:** "Would you rather earn 10% with wild swings, or 8% with
smooth sailing?" The Sharpe ratio answers that. Higher = better.

**Formula:**

```
sharpe_ratio = (annualized_return − risk_free_rate) / annualized_volatility
```

**Example:**
- Return 25%, volatility 20% → Sharpe = 0.25/0.20 = **1.25** (good).
- Return 25%, volatility 40% → Sharpe = 0.25/0.40 = **0.625** (same profit,
  but much riskier → worse ratio).

**How to read it:**
- **> 1** → good risk-adjusted performance.
- **< 0** → the portfolio lost money (below the risk-free rate).

> **Real response example:** `sharpe_ratio: 2.15` → the portfolio earned
> **2.15 units of return per unit of risk** — very strong.

---

### `max_drawdown` — "The worst drop you would have lived through"

**In plain words:** from the highest point the portfolio reached, what was the
biggest loss before recovering? It's always `0` or negative.

**Formula:**

```
wealth on day t = previous wealth × (1 + return t)
drawdown on day t = (wealth − highest peak so far) / highest peak
max_drawdown = the most negative drawdown
```

**Example — returns `[+10%, −5%, +10%, −20%]`:**

| Day | Wealth | Peak so far | Drawdown |
|----:|-------:|------------:|---------:|
| 1   | 1.10   | 1.10        | 0%       |
| 2   | 1.045  | 1.10        | −5%      |
| 3   | 1.15   | 1.15        | 0%       |
| 4   | 0.92   | 1.15        | **−20%** |

→ `max_drawdown = −0.20`, meaning at some point the portfolio was **20% below
its peak**.

> **Real response example:** `max_drawdown: −0.137` → the deepest dip was
> **~14% below the previous high** during the window.

---

### `value_at_risk_95` / `value_at_risk_99` — "How bad is a bad day?"

**In plain words:** on 95% (or 99%) of days, you will NOT lose more than this
amount of your portfolio in a single day. Reported as a positive loss.

**Formula:**

```
VaR_95 = − (the 5% worst return, i.e. the 5th percentile of daily returns)
VaR_99 = − (the 1% worst return, i.e. the 1st percentile)
```

**Example — sort 20 daily returns from worst to best:**
`−5%, −4%, −3%, … , +6%`
- 5% of 20 days = 1 day → VaR_95 ≈ the loss of the **2nd-worst day ≈ 4%**.
- VaR_99 ≈ the loss of the **worst day ≈ 5%**.

**How to read it:**
- `value_at_risk_95: 0.02` → "I expect to lose **at most ~2%** of the
  portfolio on any given day, with 95% confidence."

> **Real response example:** `value_at_risk_95: 0.019` → on 95% of days the
> portfolio loses **no more than ~1.9%**; `value_at_risk_99: 0.041` → even on
> the worst 1% of days, the loss was capped around **4.1%**.

---

### `beta` — "How much do I move with the market?"

**In plain words:** if the benchmark (e.g. SPY) moves 1%, how much does my
portfolio move? It measures *systematic risk* — risk you can't avoid by
diversifying.

**Formula:**

```
beta = Cov(portfolio returns, benchmark returns) / Var(benchmark returns)
```

**How to read it:**
- **1.0** → moves in line with the market.
- **1.5** → amplified: market +1% → portfolio +1.5% (but market −1% → −1.5%).
- **0.5** → dampened: only half the market's move.
- **null** → the benchmark wasn't found or had no price data (e.g. `SPY` isn't
  in this database; try `benchmarkSymbol=AAPL`).

> **Real response example:** `beta: 0.95` → the portfolio moves ~95% as much as
> the benchmark, i.e. about market-level systematic risk.

---

### `benchmark_metrics` — "What did the market do, for comparison?"

The **same six metrics computed for the benchmark itself** over the identical
window, so you can compare directly.

> **Real response example (benchmark = AAPL):**
>
> | Metric            | My Portfolio | Benchmark (AAPL) |
> |-------------------|-------------:|-----------------:|
> | annualized_return | 0.531        | 0.506            |
> | annualized_vol    | 0.247        | 0.259            |
> | sharpe_ratio      | 2.15         | 1.95             |
> | max_drawdown      | −0.137       | −0.138           |
> | VaR_95            | 0.019        | 0.020            |
>
> → My portfolio earned slightly more (0.531 vs 0.506) with **less**
> volatility (0.247 vs 0.259), so its Sharpe is better (2.15 vs 1.95).
> The benchmark's `beta` is `null` (a benchmark vs itself is meaningless).

---

## 3. Reading your actual API response (annotated)

```json
{
  "portfolio_id": 2,          // "My Portfolio"
  "weights_count": 2,         // 2 holdings with price data
  "observations": 251,        // 251 daily returns (252 days − 1)
  "window_start": "2025-08-04", "window_end": "2026-08-04",  // 1-year window
  "risk_free_rate": 0,        // no risk-free rate used in Sharpe
  "benchmark": "AAPL",        // beta/comparison vs AAPL
  "metrics": {
    "annualized_return": 0.531,        // ~53%/yr
    "annualized_volatility": 0.247,    // ~25% vol — moderately bumpy
    "sharpe_ratio": 2.15,              // strong reward-per-risk
    "max_drawdown": -0.137,            // worst dip ~14%
    "value_at_risk_95": 0.019,         // 95% of days lose ≤ ~1.9%
    "value_at_risk_99": 0.041,         // 99% of days lose ≤ ~4.1%
    "beta": 0.95                       // ~market-level market sensitivity
  },
  "benchmark_metrics": { ... }         // same metrics for AAPL
}
```

---

## 4. Quick reference

| Field | Question it answers | Formula | Code |
|-------|--------------------|---------|------|
| `annualized_return` | What yearly growth? | `wealth^(252/n) − 1` | `annualized_return()` |
| `annualized_volatility` | How bumpy? | `std × √252` | `annualized_volatility()` |
| `sharpe_ratio` | Reward per unit of risk? | `(return − rf) / vol` | `sharpe_ratio()` |
| `max_drawdown` | Worst peak-to-trough drop? | `min(wealth/peak − 1)` | `max_drawdown()` |
| `value_at_risk_95/99` | How bad is a bad day? | `−quantile(returns, 0.05/0.01)` | `historical_var()` |
| `beta` | Moves with the market? | `Cov / Var` | `beta()` |
| `benchmark_metrics` | What did the market do? | same six, on the benchmark | — |

**Rule of thumb for a healthy portfolio:** moderate volatility, Sharpe > 1,
manageable drawdown, and a small daily VaR.
