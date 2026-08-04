# Quantitative Portfolio Management System (QPMS): Mathematical & Engineering Specifications

This document defines the functional requirements and analytical foundations for the Quantitative Portfolio Management System (QPMS). Built for institutional-grade asset allocation and style factor tilts, the QPMS integrates state-of-the-art pricing models, robust multivariate statistical estimators, cross-sectional sorting engines, and multi-asset optimization frameworks.

---

## 1. Asset Pricing & Systematic Risk Engines


### 1.1 Capital Asset Pricing Model (CAPM) Engine

**One-Line Description:** Computes the expected equilibral return of a security or portfolio based on its systematic exposure (Beta) to the market risk premium.

**Mathematical Specification:**

$$E[R_p] = R_{fr} + \beta_p (E[R_m] - R_{fr})$$

Where:

* $E[R_p]$: Long-term expected return of the portfolio/asset.
* $R_{fr}$: Annualized risk-free rate of return.
* $\beta_p$: Portfolio Beta coefficient (sensitivity to market systematic movements).
* $E[R_m]$: Long-term expected return of the market index.
* $E[R_m] - R_{fr}$: Expected market risk premium.

**Pythonic Implementation:**

```python
def calculate_capm_return(
    risk_free_rate: float,
    portfolio_beta: float,
    expected_market_return: float
) -> float:
    """
    Calculates expected asset/portfolio return via the Capital Asset Pricing Model.
    """
    market_risk_premium = expected_market_return - risk_free_rate
    expected_return = risk_free_rate + (portfolio_beta * market_risk_premium)
    return expected_return
```

---


### 1.2 Multi-Factor Style & Risk Model Engine

**One-Line Description:** Models asset returns as a linear dependency on multiple risk premier factors, extending beyond a singular market factor.

**Mathematical Specification:**

$$E[R_p] = R_{fr} + \sum_{k=1}^{K} \beta_{p,k} \lambda_k$$

Where:

* $\beta_{p,k}$: Sensitivity factor loading of the portfolio to style factor $k$.
* $\lambda_k$: Expected risk premium of style factor $k$ (e.g., Fama-French premium or Momentum).

**Factors in Scope:**

1. **Market Premium (MKT):** Systematic equity market exposure premium.
2. **Size (SMB - Small Minus Big):** Outperformance Premium of low-cap stocks over large-cap stocks.
3. **Value (HML - High Minus Low):** Value style outperformance (high book-to-market) relative to Growth.
4. **Profitability (RMW - Robust Minus Weak):** Profitability tilt capturing firm-level earnings quality factors.
5. **Investment (CMA - Conservative Minus Aggressive):** Firms with conservative asset investment policies vs. aggressive.
6. **Momentum (MOM):** Asset price trend continuation premium (Winners vs. Losers).

**Pythonic Implementation:**

```python
from typing import Dict

def calculate_multi_factor_return(
    risk_free_rate: float,
    factor_loadings: Dict[str, float],
    factor_premiums: Dict[str, float]
) -> float:
    """
    Computes expected portfolio returns given risk factor loadings and premiums.
    """
    expected_excess_return = sum(
        factor_loadings.get(factor, 0.0) * factor_premiums.get(factor, 0.0)
        for factor in factor_loadings
    )
    return risk_free_rate + expected_excess_return
```

---


### 1.3 Factor Loadings Estimation Engine (Robust Ensemble Regression)

**One-Line Description:** Resolves factor-exposure sensitivities using robust estimation methodologies containing Ordinary Least Squares (OLS) and L2-regularized Ridge estimators to prevent regression multicollinearity.

**Analytical Specification:**

We solve for the coefficient vector $\mathbf{B}$ using a balanced combination of classical Ordinary Least Squares and Ridge optimization (Tikhonov Regularization):

$$\hat{\mathbf{B}}_{\mathrm{OLS}} = \left(\mathbf{X}^T\mathbf{X}\right)^{-1}\mathbf{X}^T\mathbf{y}$$

$$\hat{\mathbf{B}}_{\mathrm{Ridge}} = \left(\mathbf{X}^T\mathbf{X} + \alpha \mathbf{I}\right)^{-1}\mathbf{X}^T\mathbf{y}$$

$$\hat{\mathbf{B}}_{\mathrm{Ensemble}} = w_{\mathrm{OLS}} \hat{\mathbf{B}}_{\mathrm{OLS}} + w_{\mathrm{Ridge}} \hat{\mathbf{B}}_{\mathrm{Ridge}}$$

**Pythonic Implementation:**

```python
import numpy as np

def fit_ensemble_factor_loadings(
    historical_excess_returns: np.ndarray,
    factor_matrix: np.ndarray,
    ridge_coefficient: float = 0.1,
    ols_weight: float = 0.5
) -> np.ndarray:
    """
    Estimates factor loadings via OLS-Ridge Ensemble regression to maintain high stability.
    """
    x_matrix = factor_matrix
    y_vector = historical_excess_returns
    
    # 1. OLS Beta Estimation
    xt_x = x_matrix.T @ x_matrix
    ols_betas = np.linalg.solve(xt_x, x_matrix.T @ y_vector)
    
    # 2. Ridge Beta Estimation (with shrinkage factor)
    identity_matrix = np.eye(x_matrix.shape[1])
    ridge_betas = np.linalg.solve(xt_x + ridge_coefficient * identity_matrix, x_matrix.T @ y_vector)
    
    # 3. Ensemble Blending
    ensemble_betas = (ols_weight * ols_betas) + ((1.0 - ols_weight) * ridge_betas)
    return ensemble_betas
```

---


## 2. Factor Strategy & Cross-Sectional Sorting


### 2.1 Univariate Factor Sorting Engine

**One-Line Description:** Ranks individual equities and places them into deciles based on a single factor (e.g., Momentum) to systematically filter the top 3 high-exposure deciles.

**Operational Spec:**

1. Rank portfolio universe by sorting factor values in ascending order.
2. Map securities to deciles (0 to 9) using quantile thresholds.
3. Filter and select securities that lie in the top 3 deciles (Deciles 7, 8, and 9) to construct the active investment tilt portfolio.

**Pythonic Implementation:**

```python
import pandas as pd

def sort_universe_univariate(
    universe_data: pd.DataFrame,
    factor_column: str,
    num_deciles: int = 10,
    target_threshold: int = 7
) -> pd.DataFrame:
    """
    Constructs a long portfolio targeting the top 3 deciles of a specific factor.
    """
    df = universe_data.copy()
    df['factor_deciles'] = pd.qcut(
        df[factor_column], 
        q=num_deciles, 
        labels=False, 
        duplicates='drop'
    )
    high_exposure_portfolio = df[df['factor_deciles'] >= target_threshold]
    return high_exposure_portfolio.sort_values(by=factor_column, ascending=False)
```

---


### 2.2 Bivariate Factor Sorting Engine

**One-Line Description:** Extends sorting across two orthogonal factor dimensions (e.g., Size and Profitability) by sequentially stratifying the universe to isolate independent factor risk premiums.

**Operational Spec:**

1. Stratify the stock universe into multi-quantile groups on the control factor (Factor A).
2. Within each control bin, perform secondary rank-sorting on the target factor (Factor B).
3. Extract assets falling into the top quantiles across both dimensions to form a size-controlled tilt strategy.

**Pythonic Implementation:**

```python
import pandas as pd

def sort_universe_bivariate(
    universe_data: pd.DataFrame,
    factor_a_column: str,
    factor_b_column: str,
    bins_a: int = 3,
    bins_b: int = 3
) -> pd.DataFrame:
    """
    Builds a double-sorted multi-factor portfolio (e.g., Size-Value tilt)
    and isolates the strongest tier intersection.
    """
    df = universe_data.copy()
    
    # Step 1: Sort by Factor A
    df['bin_factor_a'] = pd.qcut(df[factor_a_column], q=bins_a, labels=False, duplicates='drop')
    
    # Step 2: Sort by Factor B within each Factor A bin
    df['bin_factor_b'] = df.groupby('bin_factor_a')[factor_b_column].transform(
        lambda group: pd.qcut(group, q=bins_b, labels=False, duplicates='drop')
    )
    
    # Filter for securities in the top tier of both dimensions
    intersection_portfolio = df[
        (df['bin_factor_a'] == bins_a - 1) & 
        (df['bin_factor_b'] == bins_b - 1)
    ]
    return intersection_portfolio.sort_values(by=[factor_a_column, factor_b_column], ascending=False)
```

---


## 3. Quantitative Asset Allocation & Frontiers

The frontend interface provides active switches to optimize user portfolio weight structures utilizing modern allocation frameworks.


### 3.1 Mean-Variance Optimization (MVO) Engine

**One-Line Description:** Identifies optimal portfolio weighting configurations along the Markowitz Efficient Frontier to maximize risk-adjusted performance (Sharpe Ratio).

**Mathematical Specification:**

Maximize the portfolio Sharpe Ratio subject to full investment budgets and long-only weight requirements:

$$\max_{\mathbf{w}} \frac{\mathbf{w}^T \boldsymbol{\mu} - R_{fr}}{\sqrt{\mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w}}}$$

$$\text{Subject to: } \sum_{i=1}^{N} w_i = 1, \quad w_i \ge 0 \quad \forall i$$

Where:

* $\mathbf{w}$: Column vector of optimal asset allocation weights.
* $\boldsymbol{\mu}$: Expected vector of asset return forecasts.
* $\boldsymbol{\Sigma}$: Quantitative covariance matrix of historical asset returns.

**Pythonic Implementation:**

```python
import numpy as np

def optimize_mean_variance_analytical(
    expected_returns: np.ndarray,
    covariance_matrix: np.ndarray,
    risk_free_rate: float
) -> np.ndarray:
    """
    Calculates analytical maximum Sharpe ratio weights (assuming unconstrained short sales).
    Used as an optimization proxy before quadratic solvers.
    """
    unscaled_weights = np.linalg.solve(covariance_matrix, expected_returns - risk_free_rate)
    optimal_weights = unscaled_weights / np.sum(unscaled_weights)
    return optimal_weights
```

---


### 3.2 Black-Litterman Asset Allocation Model Engine

**One-Line Description:** Integrates market equilibrium assumptions with subjective analyst opinions to overcome standard portfolio-construction optimization instability.

**Mathematical Specification:**

Updates the return vector using Bayes' rule:

$$E[\mathbf{R}] = \left[ (\tau \boldsymbol{\Sigma})^{-1} + \mathbf{P}^T \boldsymbol{\Omega}^{-1} \mathbf{P} \right]^{-1} \left[ (\tau \boldsymbol{\Sigma})^{-1} \boldsymbol{\Pi} + \mathbf{P}^T \boldsymbol{\Omega}^{-1} \mathbf{Q} \right]$$

Where:

* $E[\mathbf{R}]$: Posterior expected stock return vector.
* $\boldsymbol{\Pi}$: Market implied equilibrium expected returns (extracted via reverse-optimization).
* $\boldsymbol{\Sigma}$: Long-term historical covariance matrix of stock returns.
* $\mathbf{P}$: Selection mapping matrix identifying assets with subjective opinions.
* $\mathbf{Q}$: Quantitative view value expectation vector.
* $\boldsymbol{\Omega}$: Covariance matrix representing subjective view uncertainty.
* $\tau$: Market calibration scaling parameter.

**Pythonic Implementation:**

```python
import numpy as np

def calculate_black_litterman_posterior(
    implied_returns: np.ndarray,
    covariance_matrix: np.ndarray,
    view_selector_matrix: np.ndarray,
    view_expected_returns: np.ndarray,
    view_uncertainty_matrix: np.ndarray,
    scaling_constant: float = 0.05
) -> np.ndarray:
    """
    Calculates the posterior expected excess asset returns using the Black-Litterman model.
    """
    scaled_covariance_inv = np.linalg.inv(scaling_constant * covariance_matrix)
    omega_inv = np.linalg.inv(view_uncertainty_matrix)
    p_transpose_omega_inv = view_selector_matrix.T @ omega_inv
    
    posterior_precision = scaled_covariance_inv + p_transpose_omega_inv @ view_selector_matrix
    posterior_information = scaled_covariance_inv @ implied_returns + p_transpose_omega_inv @ view_expected_returns
    
    posterior_returns = np.linalg.solve(posterior_precision, posterior_information)
    return posterior_returns
```

---


## 4. App Features & Technical Integration View (QPMS)

The application maps the analytical engines described above into an intuitive, production-ready, and interactive **Quantitative Portfolio Management System (QPMS)** dashboard and API. Below is the technical specification of the user-facing features, frontend components, and backend mapping:

---

### 4.1 Cross-Sectional Factor Screener & Sort Console (User Workspace)

* **Functional Description:** Allows users to interactively filter and rank the stock universe according to style factor exposures to construct dynamic factor-tilted basket portfolios.
* **Frontend Components (User Interface):**
  * **Sort Mode Selector:** Toggle switch between **Univariate Sort** (sorting on a single factor dimension) and **Bivariate Sort** (sequential/double-sorting on two orthogonal factors).
  * **Factor Parameter Inputs:** Dropdown lists to select primary and secondary factors of interest (e.g., *Momentum (MOM)* as Factor A, *Value (HML)* as Factor B).
  * **Quantile Granularity Sliders:** Sliders to configure sorting depth (e.g., divide into deciles or quintiles) and style active-tilt selection thresholds (e.g., target only the top 3 deciles).
* **Workflow & Backend Execution:**
  1. The user selects parameters on the frontend side (e.g., Double Sort on Size (SMB) and Profitability (RMW) into $3 \times 3$ bins).
  2. The frontend triggers a `POST` request to `/api/v1/factors/sort` containing the parameters.
  3. The backend executes the double-sorting pythonic logic over the database-stored stock price and style factors data.
  4. The frontend renders a stylized datagrid displaying the identified subset, showing their sector, market capitalization, style exposures, and selected bin rankings.

---

### 4.2 Dynamic Strategic Asset Allocator

* **Functional Description & Interface:** Empowers investors to execute advanced allocation math on their portfolios at the click of a button, transitioning beyond simple static weights.
* **Frontend Components (User Interface):**
  * **Optimizer Toggle:** Choose between three major allocation regimes:
    * **CAPM Return Engine:** Allocates based on single-indicator systematic risk beta sensitivities.
    * **Mean-Variance Optimization (MVO):** Triggers efficient frontier calculation based on historical return covariance matrix.
    * **Black-Litterman Allocation:** Allows blending of baseline market equilibrium with active subjectivist analyst views.
  * **Subjective View Editor (Black-Litterman Specific):** An interactive matrix grid where the user can build subjective market views:
    * *Select Target Asset / Index Group* (Matrix $\mathbf{P}$)
    * *Input Expected Premium change %* (Vector $\mathbf{Q}$)
    * *Set Confidence Sliders* (Mapping directly into the subjective uncertainty matrix $\boldsymbol{\Omega}$).
* **Workflow & Backend Execution:**
  1. Setting up opinions instantly recalibrates the analytical expected return vector using the Bayes' update step.
  2. The backend returns newly optimized weight vectors.
  3. The frontend displays the allocation output on an interactive, color-coded donut chart overlaid with the historical/prior allocation for immediate delta comparison.

---

### 4.3 Portfolio Performance & Style Exposure Dashboard

* **Functional Description:** Visualizes the ultimate risk-adjusted performance of the selected strategy alongside historical style drift characteristics.
* **Frontend Components (User Interface):**
  * **Cumulative Wealth Chart:** High-performance line chart mapping the Portfolio Wealth Index (recalculated daily) against market indices like the S&P 500 benchmark.
  * **Risk Attribution Grid:** Real-time calculation cards displaying:
    * **Annualized Sharpe Ratio** (incorporating adjustable dynamic risk-free rate input)
    * **Peak-to-Trough Drawdown Curves** (to track downside exposure periods)
    * **Annualized Volatility**
  * **Style Factor Radar Chart:** A radar chart displaying the portfolio's net systematic style factor exposures (loadings resolved on-the-fly using the robust OLS-Ridge Ensemble estimation engine).

---

### 4.4 Unified REST API Documentation (QPMS Core)

The frontend communicates with a resilient back-end architecture configured with the following endpoint architecture:

* `GET /api/v1/stocks/` - Retrieves listed equities, prices, and basic style profiles.
* `POST /api/v1/factors/sort` - Processes univariate/bivariate sorting configurations against current market metrics.
* `POST /api/v1/optimize/mvo` - Calculates maximum Sharpe analytical weights.
* `POST /api/v1/optimize/black-litterman` - Computes posterior expected returns and optimal allocation weights incorporating subjective inputs.
* `GET /api/v1/portfolio/analytics` - Computes performance analytics, Wealth Indexes, and OLS-Ridge computed factor loadings for radar plotting.

