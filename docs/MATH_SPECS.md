# Portfolio Mathematics Reference

All returns below are simple returns unless stated otherwise. Use decimal values: $1\% = 0.01$.

## Holding-Period Return

**What it does:** Measures the percentage gain or loss between an initial and final portfolio value.

**Use:** Compare a single investment's performance over a chosen holding period.

$$ R = \frac{V_f - V_i}{V_i} = \frac{V_f}{V_i} - 1 $$

Where $V_i$ is the initial value and $V_f$ is the final value. For a security, $R_{i,f} = \frac{P_f}{P_i} - 1$.

```python
holding_period_return = lambda initial_value, final_value: final_value / initial_value - 1
```

## Multi-Period Compounded Return

**What it does:** Combines consecutive periodic returns into the total realised return.

**Use:** Calculate the actual return earned across multiple trading periods.

$$ R_{0,n} = \prod_{t=1}^{n}(1 + R_t) - 1 $$

```python
import numpy as np

compounded_return = lambda period_returns: float(np.prod(1 + period_returns) - 1)
```

## Variance and Volatility

**What it does:** Quantifies return dispersion, with volatility commonly used as a measure of market risk.

**Use:** Volatility measures how much returns change over time; higher volatility generally means greater uncertainty and risk.

$$ s^2 = \frac{1}{n - 1}\sum_{t=1}^{n}(R_t - \bar{R})^2 \qquad s = \sqrt{s^2} $$

```python
sample_variance = lambda period_returns: float(period_returns.var(ddof=1))
sample_volatility = lambda period_returns: float(period_returns.std(ddof=1))
```

## Annualised Return

**What it does:** Converts a periodic return into its equivalent compounded annual return.

**Use:** Compare investments fairly when their returns are measured over different time intervals.

$$ R_a = (1 + R_p)^P - 1 $$

Here, $P$ is the number of periods per year: 252 for trading days, 12 for months, and 1 for annual data. The general frequency conversion is $R_{target} = (1 + R_{source})^{P_{source}/P_{target}} - 1$.

```python
annualize_return = lambda period_return, periods_per_year: (1 + period_return) ** periods_per_year - 1
convert_return_frequency = lambda source_return, source_periods_per_year, target_periods_per_year: (1 + source_return) ** (source_periods_per_year / target_periods_per_year) - 1
```

## Annualised Volatility

**What it does:** Scales periodic volatility to annual volatility using the square-root-of-time assumption.

**Use:** Express daily or monthly return variability as a standard annual risk measure.

$$ \sigma_a = \sigma_p\sqrt{P} $$

```python
import numpy as np

annualize_volatility = lambda period_volatility, periods_per_year: float(period_volatility * np.sqrt(periods_per_year))
```

## Sharpe Ratio

**What it does:** Measures excess return earned per unit of total volatility.

**Use:** Compare risk-adjusted performance; it shows excess return earned for each unit of volatility taken.

$$ \mathrm{Sharpe\ ratio} = \frac{R_a - R_{f,a}}{\sigma_a} $$

The raw ratio $R_a / \sigma_a$ assumes a zero risk-free rate. The risk-free rate and return must use the same annualised frequency.

```python
sharpe_ratio = lambda annual_return, annual_volatility, annual_risk_free_rate=0.0: (annual_return - annual_risk_free_rate) / annual_volatility
```

## Wealth Index and Cumulative Return

**What it does:** Tracks the growth of one currency unit invested through a sequence of returns.

**Use:** Visualise the compounded growth of an investment and compare growth paths across securities.

$$ WI_t = WI_{t-1}(1 + R_t) \qquad CR_t = WI_t - 1 $$

```python
wealth_index = lambda period_returns, initial_wealth=1.0: initial_wealth * (1 + period_returns).cumprod()
cumulative_return = lambda period_returns: float(wealth_index(period_returns).iloc[-1] - 1)
```

## Drawdown

**What it does:** Measures the percentage decline from the highest previous wealth index value.

**Use:** A common downside-risk measure showing the loss from the previous peak and the severity of historical declines.

$$ \mathrm{running\ peak}_t = \max(WI_0, \ldots, WI_t) $$

$$ \mathrm{drawdown}_t = \frac{WI_t - \mathrm{running\ peak}_t}{\mathrm{running\ peak}_t} $$

Drawdown is $0$ at a new peak and negative below that peak.

```python
drawdown = lambda wealth_index_values: wealth_index_values / wealth_index_values.cummax() - 1
```

## Time-Weighted Return (TWR)

**What it does:** Measures the compounded growth of the portfolio while removing the distorting effect of deposits and withdrawals (external cash flows).

**Use:** The GIPS / institutional standard (how Morgan Stanley reports performance). It answers "how well did the strategy perform?" independent of *when* the investor added or removed money, so managers are judged only on decisions they control.

For each period, strip the cash flow $CF_t$ that entered (buy, $+$) or left (sell, $-$) the portfolio at the start of the period before comparing to the prior value:

$$ r_t = \frac{V_t - CF_t}{V_{t-1}} - 1 \qquad R_{TWR} = \prod_{t=1}^{n}(1 + r_t) - 1 $$

Where $V_t$ is the portfolio value at time $t$ and $CF_t$ is the net external cash flow during period $t$. The annualised figure uses the geometric convention $(1 + R_{TWR})^{P/n} - 1$.

```python
import numpy as np
import pandas as pd

def time_weighted_returns(value, cash_flows):
    prev = value.shift(1)
    returns = (value - cash_flows) / prev - 1
    return returns.iloc[1:].replace([np.inf, -np.inf], np.nan).dropna()

time_weighted_return = lambda value, cash_flows: float(np.prod(1 + time_weighted_returns(value, cash_flows)) - 1)
```

## Money-Weighted Return (XIRR)

**What it does:** Finds the single annualised rate of return that makes the net present value of every dated cash flow equal to zero — the internal rate of return for irregularly spaced flows.

**Use:** The retail / investor-experience standard (how Zerodha shows the headline return). It *rewards* good timing of contributions, so it answers "what return did *this investor* actually earn on their money?"

Treat buys as negative cash flows and the current portfolio value as a final positive cash flow. Solve for the rate $r$ satisfying:

$$ \sum_{i=1}^{N} \frac{C_i}{(1 + r)^{(d_i - d_0)/365}} = 0 $$

Where $C_i$ is the cash flow on date $d_i$ and $d_0$ is the earliest date. Solved numerically (Newton–Raphson with a bisection fallback for robustness).

```python
def xirr(dated_amounts, guess=0.1):
    d0 = min(d for d, _ in dated_amounts)
    years = [ (d - d0).days / 365.0 for d, _ in dated_amounts ]
    amounts = [ a for _, a in dated_amounts ]

    def npv(rate):
        return sum(a / (1 + rate) ** t for a, t in zip(amounts, years))

    # Newton-Raphson with bisection fallback (see services/analytics.py)
    return _solve_newton(npv, guess) or _solve_bisection(npv)
```

**TWR vs. XIRR:** TWR isolates *strategy skill* (cash-flow neutral); XIRR captures the *investor's realised experience* (cash-flow sensitive). Reporting both gives the complete picture — the manager's performance and the account holder's actual return.

## Present Value and Future Value

**What it does:** Moves a single cash flow across time using a per-period interest (discount) rate — future money is worth less today.

**Use:** The building block of every valuation; it lets us compare cash received at different dates on a common "today" basis.

$$ FV = PV\,(1 + r)^{n} \qquad PV = \frac{FV}{(1 + r)^{n}} $$

Where $r$ is the periodic rate and $n$ is the number of periods. Example: at $r = 5\%$, a payment of $100$ in one year is worth $100 / 1.05 = 95.24$ today.

```python
import pandas as pd

future_value = lambda present_value, rate, periods: present_value * (1 + rate) ** periods
present_value = lambda future_value, rate, periods: future_value / (1 + rate) ** periods
```

## Net Present Value (NPV)

**What it does:** Sums the present values of every dated cash flow (outflows negative, inflows positive) at a single discount rate.

**Use:** Decide whether an investment creates value — accept when $NPV > 0$, because the project earns more than the discount rate.

$$ NPV = \sum_{t=0}^{n} \frac{CF_t}{(1 + r)^{t}} $$

Where $CF_t$ is the cash flow at period $t$ (the $t = 0$ flow is the initial cost) and $r$ is the discount rate.

```python
import pandas as pd

def net_present_value(cash_flows: pd.Series, rate: float) -> float:
    periods = pd.Series(range(len(cash_flows)), index=cash_flows.index)
    return float((cash_flows / (1 + rate) ** periods).sum())
```

## Discounted Cash Flow (DCF)

**What it does:** Values an asset as the present value of its expected future cash flows discounted at the required rate of return.

**Use:** The core intrinsic-value model — estimate what a stock or project is worth today from the cash it is expected to generate.

$$ DCF = \sum_{t=1}^{n} \frac{CF_t}{(1 + r)^{t}} $$

Where $CF_t$ is the forecast cash flow in year $t$ and $r$ is the discount rate. Example: three payments of $50$ discounted at $r = 12\%$ give $50/1.12 + 50/1.12^2 + 50/1.12^3$.

```python
import pandas as pd

def discounted_cash_flow(future_cash_flows: pd.Series, rate: float) -> float:
    periods = pd.Series(range(1, len(future_cash_flows) + 1), index=future_cash_flows.index)
    return float((future_cash_flows / (1 + rate) ** periods).sum())
```

## Gordon Growth Model (Perpetuity Value)

**What it does:** Prices a cash flow that grows at a constant rate $g$ forever, discounted at rate $r$.

**Use:** Estimate a stock's fair value or a DCF terminal value when cash flows are assumed to grow steadily in perpetuity (requires $r > g$).

$$ P_0 = \frac{CF_1}{r - g} $$

Where $CF_1$ is next period's cash flow, $r$ is the discount rate and $g$ is the constant growth rate. With $g = 0$ this collapses to $P_0 = CF / r$.

```python
gordon_growth_value = lambda next_cash_flow, discount_rate, growth_rate=0.0: next_cash_flow / (discount_rate - growth_rate)
```

## Earnings Yield and Value Premium

**What it does:** The earnings (or cash-flow) yield is the inverse of the price multiple — how much return each unit of price buys — and its rise defines the "cheapness" a value investor seeks.

**Use:** Compare valuations across stocks; a higher yield (lower price for the same cash flow) signals a cheaper, potentially higher-expected-return holding.

$$ \text{earnings yield} = \frac{CF}{P} = \frac{1}{P/CF} $$

Example: a cash flow of $5$ costs $10\%$ at a price of $50$ but only $5\%$ at $100$; combining a cheap price with higher profitability ($10/50 = 20\%$) captures the *value premium* — yield rises when cash flow goes up while price falls.

```python
import pandas as pd

earnings_yield = lambda cash_flow, price: cash_flow / price

def earnings_yields(cash_flows: pd.Series, prices: pd.Series) -> pd.Series:
    return cash_flows / prices
```

## Geometric Brownian Motion (GBM)

**What it does:** Models a stock price as continuous compounding with a deterministic drift plus a random shock proportional to volatility — the standard equation behind Black–Scholes and Monte-Carlo price simulation.

**Use:** Simulate future price paths for option pricing, risk (VaR) and scenario analysis, ensuring prices stay positive and returns compound multiplicatively.

$$ \frac{dS_t}{S_t} = \mu\,dt + \sigma\sqrt{dt}\;\varepsilon_t \qquad \varepsilon_t \sim N(0, 1) $$

Where $\mu$ is the drift (often $r + \sigma \times \text{Sharpe}$), $\sigma$ is volatility, $dt$ is the time step and $\varepsilon_t$ is a standard-normal shock. Each simulated return is $\mu\,dt + \sigma\sqrt{dt}\,\varepsilon_t$.

```python
import numpy as np
import pandas as pd

def simulate_gbm(start_price: float, drift: float, volatility: float, steps: int, dt: float = 1 / 252, seed: int | None = None) -> pd.Series:
    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal(steps)
    increments = drift * dt + volatility * np.sqrt(dt) * shocks
    prices = start_price * np.exp(np.cumsum(increments))
    return pd.Series(prices, index=pd.RangeIndex(1, steps + 1, name="step"))
```

## Cyclically Adjusted P/E (CAPE / Shiller P/E)

**What it does:** Divides the real (inflation-adjusted) price by the average of real earnings over the last 10 years, smoothing out the business cycle.

**Use:** Gauge whether a market is expensive or cheap relative to history; a high CAPE signals low expected long-run returns, unlike a one-year P/E distorted by cyclical earnings.

$$ CAPE = \frac{P_{real}}{\frac{1}{10}\sum_{t=1}^{10} E_{real,\,t}} $$

Where $P_{real}$ is the current inflation-adjusted price and $E_{real,t}$ are the real earnings of the past 10 years.

```python
import pandas as pd

def cape_ratio(real_price: float, real_earnings: pd.Series, years: int = 10) -> float:
    average_earnings = real_earnings.tail(years).mean()
    return float(real_price / average_earnings)
```
