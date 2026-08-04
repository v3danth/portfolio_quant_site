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


