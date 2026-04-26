"""
Historical Backtest Engine — Phase 3

Addresses Prof feedback #2: "Pin the backtest period and at least one named
stress event before any Phase 3 evaluation runs."

Pinned periods:
  1. COVID Drawdown:       2020-02-19 → 2020-04-30
  2. Rate-Hike Volatility: 2021-11-01 → 2022-06-30
  3. SVB Stress:           2023-01-01 → 2023-03-31

Uses a RULE-BASED version of the pipeline (no LLM calls) to ensure
reproducibility and avoid API rate limits during evaluation.

Compares agent system vs buy-and-hold baseline for each period.
Reports: Sharpe ratio, max drawdown, cumulative return, win rate.

Run: python backtest.py
"""

import json
import os
import math
from datetime import datetime, timedelta


# ── Backtest periods (pinned, named) ──────────────────────────────
BACKTEST_PERIODS = [
    {
        "name": "COVID Drawdown",
        "start": "2020-02-19",
        "end": "2020-04-30",
        "description": "Market crash triggered by COVID-19 pandemic. S&P 500 fell ~34% from peak.",
        "stress_event": "WHO declares COVID-19 pandemic (March 11, 2020)",
        "tickers": ["AAPL", "MSFT", "AMZN"],
    },
    {
        "name": "Rate-Hike Volatility",
        "start": "2021-11-01",
        "end": "2022-06-30",
        "description": "Fed begins aggressive rate hiking cycle. Tech sector rotation.",
        "stress_event": "FOMC signals accelerated tapering (Nov 2021), first hike Mar 2022",
        "tickers": ["AAPL", "MSFT", "AMZN"],
    },
    {
        "name": "SVB Stress",
        "start": "2023-01-01",
        "end": "2023-03-31",
        "description": "Silicon Valley Bank collapse triggers banking sector contagion fears.",
        "stress_event": "SVB fails (March 10, 2023), FDIC takeover",
        "tickers": ["AAPL", "MSFT", "AMZN"],
    },
]

# ── Tickers for backtesting ──────────────────────────────────────
BACKTEST_TICKERS = ["AAPL", "MSFT", "AMZN"]


def fetch_historical_prices(ticker: str, start: str, end: str) -> list[dict]:
    """Fetch historical price data using yfinance."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)
        if df.empty:
            return []
        return [{"date": str(d.date()), "close": round(row["Close"], 2)}
                for d, row in df.iterrows()]
    except Exception as e:
        print(f"  [BACKTEST] Error fetching {ticker}: {e}")
        return []


# ── Rule-based signal generation (no LLM) ─────────────────────────

def compute_technical_signal(prices: list[float]) -> dict:
    """Compute technical indicators and generate signal."""
    if len(prices) < 20:
        return {"signal": "HOLD", "confidence": 0.3, "reason": "Insufficient data"}

    # RSI
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas[-14:]]
    losses = [max(-d, 0) for d in deltas[-14:]]
    ag, al = sum(gains)/14, sum(losses)/14
    rsi = 100 - 100/(1 + ag/al) if al > 0 else 100

    # Moving averages
    sma5 = sum(prices[-5:]) / 5
    sma20 = sum(prices[-20:]) / 20

    # MACD-like
    e12 = _simple_ema(prices, 12)
    e26 = _simple_ema(prices, 26) if len(prices) >= 26 else e12
    macd = e12 - e26

    # Score
    score = 0
    if rsi < 30: score += 2
    elif rsi < 45: score += 1
    elif rsi > 70: score -= 2
    elif rsi > 60: score -= 1

    if macd > 0: score += 1
    else: score -= 1

    if sma5 > sma20 * 1.01: score += 1
    elif sma5 < sma20 * 0.99: score -= 1

    if score >= 3: signal = "STRONG_BUY"
    elif score >= 1: signal = "BUY"
    elif score <= -3: signal = "STRONG_SELL"
    elif score <= -1: signal = "SELL"
    else: signal = "HOLD"

    return {
        "signal": signal,
        "confidence": round(min(0.9, 0.4 + abs(score) * 0.12), 2),
        "rsi": round(rsi, 2),
        "macd": round(macd, 4),
        "sma5_vs_sma20": round((sma5/sma20 - 1) * 100, 2),
        "reason": f"RSI={rsi:.0f}, MACD={'+'if macd>0 else ''}{macd:.2f}, SMA5/20={sma5/sma20:.3f}"
    }


def _simple_ema(data, period):
    if len(data) < period:
        return sum(data) / len(data)
    m = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for p in data[period:]:
        ema = (p - ema) * m + ema
    return ema


def rule_based_decision(tech_signal: dict, current_price: float,
                        cash: float, holdings: int,
                        portfolio_value: float) -> dict:
    """Make a rule-based trade decision (no LLM)."""
    signal = tech_signal["signal"]
    conf = tech_signal["confidence"]

    max_alloc = 0.20  # 20% concentration limit

    if signal in ("BUY", "STRONG_BUY") and cash > current_price:
        # Size based on confidence
        alloc_pct = 0.15 if signal == "STRONG_BUY" else 0.10
        target_value = portfolio_value * alloc_pct
        max_value = portfolio_value * max_alloc
        current_position = holdings * current_price
        available = min(target_value, max_value - current_position, cash)
        qty = max(0, int(available / current_price))
        if qty > 0:
            return {"action": "BUY", "quantity": qty, "confidence": conf}

    elif signal in ("SELL", "STRONG_SELL") and holdings > 0:
        sell_pct = 1.0 if signal == "STRONG_SELL" else 0.5
        qty = max(1, int(holdings * sell_pct))
        return {"action": "SELL", "quantity": qty, "confidence": conf}

    return {"action": "HOLD", "quantity": 0, "confidence": conf}


# ── Backtest runner ───────────────────────────────────────────────

def run_backtest_period(period: dict) -> dict:
    """Run backtest for a single period, comparing agent vs buy-and-hold."""
    name = period["name"]
    start, end = period["start"], period["end"]
    tickers = period["tickers"]

    print(f"\n{'='*60}")
    print(f"  BACKTEST: {name}")
    print(f"  Period: {start} → {end}")
    print(f"  Stress event: {period['stress_event']}")
    print(f"{'='*60}")

    # Fetch all price data
    all_prices = {}
    for ticker in tickers:
        prices = fetch_historical_prices(ticker, start, end)
        if prices:
            all_prices[ticker] = prices
            print(f"  {ticker}: {len(prices)} trading days, "
                  f"${prices[0]['close']} → ${prices[-1]['close']}")

    if not all_prices:
        return {"name": name, "error": "No price data available", "status": "SKIPPED"}

    # ── Buy-and-Hold baseline ──────────────────────────────
    initial_cash = 100_000
    bh_allocation = initial_cash / len(all_prices)
    bh_shares = {}
    bh_cost = 0
    for ticker, prices in all_prices.items():
        shares = int(bh_allocation / prices[0]["close"])
        bh_shares[ticker] = shares
        bh_cost += shares * prices[0]["close"]
    bh_cash = initial_cash - bh_cost

    bh_final = bh_cash + sum(
        bh_shares[t] * p[-1]["close"] for t, p in all_prices.items())
    bh_return = (bh_final / initial_cash - 1) * 100

    # Daily B&H values for Sharpe/drawdown
    min_days = min(len(p) for p in all_prices.values())
    bh_daily = []
    for day in range(min_days):
        val = bh_cash + sum(
            bh_shares[t] * all_prices[t][day]["close"] for t in all_prices)
        bh_daily.append(val)

    bh_sharpe = _sharpe_ratio(bh_daily)
    bh_max_dd = _max_drawdown(bh_daily)

    # ── Agent system (rule-based) ─────────────────────────
    agent_cash = initial_cash
    agent_holdings = {t: 0 for t in all_prices}
    agent_daily = []
    agent_trades = []
    lookback = 20  # need 20 days of data for signals

    for day in range(min_days):
        # Calculate portfolio value
        port_val = agent_cash + sum(
            agent_holdings[t] * all_prices[t][day]["close"] for t in all_prices)
        agent_daily.append(port_val)

        if day < lookback:
            continue  # need warmup period

        # Run decision for each ticker
        for ticker in all_prices:
            closes = [all_prices[ticker][d]["close"] for d in range(max(0, day-29), day+1)]
            current = all_prices[ticker][day]["close"]

            tech = compute_technical_signal(closes)
            decision = rule_based_decision(
                tech, current, agent_cash, agent_holdings[ticker], port_val)

            if decision["action"] == "BUY" and decision["quantity"] > 0:
                cost = decision["quantity"] * current
                if cost <= agent_cash:
                    agent_cash -= cost
                    agent_holdings[ticker] += decision["quantity"]
                    agent_trades.append({
                        "day": day, "date": all_prices[ticker][day]["date"],
                        "ticker": ticker, "action": "BUY",
                        "quantity": decision["quantity"],
                        "price": current, "signal": tech["signal"],
                    })
            elif decision["action"] == "SELL" and decision["quantity"] > 0:
                qty = min(decision["quantity"], agent_holdings[ticker])
                if qty > 0:
                    agent_cash += qty * current
                    agent_holdings[ticker] -= qty
                    agent_trades.append({
                        "day": day, "date": all_prices[ticker][day]["date"],
                        "ticker": ticker, "action": "SELL",
                        "quantity": qty, "price": current,
                        "signal": tech["signal"],
                    })

    agent_final = agent_cash + sum(
        agent_holdings[t] * all_prices[t][-1]["close"] for t in all_prices)
    agent_return = (agent_final / initial_cash - 1) * 100
    agent_sharpe = _sharpe_ratio(agent_daily)
    agent_max_dd = _max_drawdown(agent_daily)

    # Win rate
    wins = sum(1 for t in agent_trades if
               (t["action"] == "BUY" and
                all_prices[t["ticker"]][-1]["close"] > t["price"]) or
               (t["action"] == "SELL" and
                all_prices[t["ticker"]][-1]["close"] < t["price"]))
    win_rate = wins / len(agent_trades) * 100 if agent_trades else 0

    result = {
        "name": name,
        "period": {"start": start, "end": end},
        "stress_event": period["stress_event"],
        "trading_days": min_days,
        "tickers": list(all_prices.keys()),
        "initial_capital": initial_cash,
        "buy_and_hold": {
            "final_value": round(bh_final, 2),
            "return_pct": round(bh_return, 2),
            "sharpe_ratio": round(bh_sharpe, 4),
            "max_drawdown_pct": round(bh_max_dd, 2),
        },
        "agent_system": {
            "final_value": round(agent_final, 2),
            "return_pct": round(agent_return, 2),
            "sharpe_ratio": round(agent_sharpe, 4),
            "max_drawdown_pct": round(agent_max_dd, 2),
            "total_trades": len(agent_trades),
            "win_rate_pct": round(win_rate, 2),
            "final_holdings": {t: s for t, s in agent_holdings.items() if s > 0},
            "final_cash": round(agent_cash, 2),
        },
        "comparison": {
            "return_delta_pct": round(agent_return - bh_return, 2),
            "sharpe_delta": round(agent_sharpe - bh_sharpe, 4),
            "drawdown_improvement_pct": round(bh_max_dd - agent_max_dd, 2),
            "agent_beats_baseline": agent_return > bh_return,
        },
        "trades": agent_trades,
        "status": "COMPLETE",
    }

    # Print summary
    print(f"\n  Buy-and-Hold:  return={bh_return:+.2f}%  Sharpe={bh_sharpe:.4f}  "
          f"MaxDD={bh_max_dd:.2f}%")
    print(f"  Agent System:  return={agent_return:+.2f}%  Sharpe={agent_sharpe:.4f}  "
          f"MaxDD={agent_max_dd:.2f}%  Trades={len(agent_trades)}  WinRate={win_rate:.0f}%")
    beat = "✓ BEATS" if agent_return > bh_return else "✗ TRAILS"
    print(f"  → {beat} baseline by {agent_return - bh_return:+.2f}%")

    return result


def _sharpe_ratio(daily_values: list[float], risk_free_annual: float = 0.04) -> float:
    """Annualized Sharpe ratio from daily portfolio values."""
    if len(daily_values) < 2:
        return 0.0
    returns = [(daily_values[i] / daily_values[i-1] - 1)
               for i in range(1, len(daily_values))]
    if not returns:
        return 0.0
    avg_return = sum(returns) / len(returns)
    std_return = math.sqrt(sum((r - avg_return)**2 for r in returns) / len(returns))
    if std_return == 0:
        return 0.0
    daily_rf = (1 + risk_free_annual) ** (1/252) - 1
    return (avg_return - daily_rf) / std_return * math.sqrt(252)


def _max_drawdown(daily_values: list[float]) -> float:
    """Maximum drawdown percentage."""
    if len(daily_values) < 2:
        return 0.0
    peak = daily_values[0]
    max_dd = 0.0
    for v in daily_values:
        peak = max(peak, v)
        dd = (peak - v) / peak * 100
        max_dd = max(max_dd, dd)
    return max_dd


def run_all_backtests() -> dict:
    """Run backtests across all pinned periods."""
    print("=" * 60)
    print("  HISTORICAL BACKTEST ENGINE — Phase 3")
    print("  Pinned periods with named stress events")
    print("=" * 60)

    results = []
    for period in BACKTEST_PERIODS:
        result = run_backtest_period(period)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("  BACKTEST SUMMARY")
    print(f"{'='*60}")
    for r in results:
        if r.get("status") == "SKIPPED":
            print(f"  {r['name']}: SKIPPED ({r.get('error', 'unknown')})")
            continue
        c = r["comparison"]
        beat = "✓" if c["agent_beats_baseline"] else "✗"
        print(f"  {beat} {r['name']:25s}  Agent={r['agent_system']['return_pct']:+6.2f}%  "
              f"B&H={r['buy_and_hold']['return_pct']:+6.2f}%  "
              f"Δ={c['return_delta_pct']:+6.2f}%")

    # Save results
    os.makedirs("evaluation/evidence", exist_ok=True)
    output_path = "evaluation/evidence/backtest_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "run_date": datetime.now().isoformat(),
            "periods": results,
            "methodology": {
                "agent_strategy": "Rule-based technical analysis (RSI, MACD, SMA crossover)",
                "baseline": "Buy-and-hold with equal allocation",
                "initial_capital": 100_000,
                "concentration_limit": "20%",
                "no_llm_calls": "Rule-based for reproducibility",
            }
        }, f, indent=2, default=str)
    print(f"\n  Saved: {output_path}")

    return {"periods": results}


if __name__ == "__main__":
    run_all_backtests()
