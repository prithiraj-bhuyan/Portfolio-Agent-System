"""
Tools layer — each tool provides structured data to agents.
Uses deterministic mock data per ticker for reproducible prototype.
In production, replace with live APIs (yfinance, NewsAPI, Reddit, etc.)
"""

from datetime import datetime, timedelta
import hashlib, math


# ── Helper: deterministic random per ticker ────────────────────────
class _DRng:
    """Deterministic RNG seeded by ticker string."""
    def __init__(self, ticker: str, salt: int = 0):
        import random
        seed = int(hashlib.md5(f"{ticker}{salt}".encode()).hexdigest()[:8], 16)
        self._r = random.Random(seed)

    def uniform(self, a, b):   return self._r.uniform(a, b)
    def randint(self, a, b):   return self._r.randint(a, b)
    def choice(self, seq):     return self._r.choice(seq)


# ── Realistic static data per ticker ──────────────────────────────
_FUNDAMENTALS = {
    "AAPL": dict(market_cap=2.9e12, pe_ratio=28.5, forward_pe=24.1, eps=6.73,
                 dividend_yield=0.005, beta=1.24, high_52w=237.23, low_52w=164.08,
                 profit_margin=0.264, revenue_growth=0.049, debt_to_equity=1.87,
                 roe=1.609, sector="Technology", industry="Consumer Electronics"),
    "ADBE": dict(market_cap=2.0e11, pe_ratio=44.5, forward_pe=28.3, eps=11.82,
                  dividend_yield=0.0, beta=1.28, high_52w=638.25, low_52w=432.15,
                  profit_margin=0.354, revenue_growth=0.112, debt_to_equity=0.58,
                  roe=0.368, sector="Technology", industry="Application Software"),
    "MSFT": dict(market_cap=3.1e12, pe_ratio=35.2, forward_pe=29.7, eps=11.86,
                 dividend_yield=0.007, beta=0.89, high_52w=468.35, low_52w=362.90,
                 profit_margin=0.356, revenue_growth=0.162, debt_to_equity=0.35,
                 roe=0.389, sector="Technology", industry="Software"),
    "AMZN": dict(market_cap=1.9e12, pe_ratio=42.1, forward_pe=28.5, eps=4.39,
                 dividend_yield=0.0, beta=1.15, high_52w=201.20, low_52w=151.61,
                 profit_margin=0.082, revenue_growth=0.118, debt_to_equity=0.63,
                 roe=0.227, sector="Technology", industry="Internet Retail"),
    "NVDA": dict(market_cap=2.8e12, pe_ratio=58.9, forward_pe=32.4, eps=14.92,
                 dividend_yield=0.0003, beta=1.68, high_52w=974.0, low_52w=473.20,
                 profit_margin=0.557, revenue_growth=0.940, debt_to_equity=0.41,
                 roe=1.155, sector="Technology", industry="Semiconductors"),
}

_BASE_PRICES = {"AAPL": 195.50, "ADBE": 525.40, "MSFT": 422.80,
                "AMZN": 186.40, "NVDA": 882.50}

_NEWS = {
    "AAPL": [
        dict(title="Apple reports record Q4 revenue of $94.9B", sentiment=0.75, source="Reuters"),
        dict(title="Apple Intelligence drives strong iPhone upgrade cycle", sentiment=0.60, source="Bloomberg"),
        dict(title="Services revenue hits all-time high of $25B", sentiment=0.70, source="CNBC"),
        dict(title="China iPhone sales decline 3% amid competition", sentiment=-0.40, source="WSJ"),
    ],
    "ADBE": [
        dict(title="Adobe Firefly AI generates over 12 billion images", sentiment=0.80, source="Reuters"),
        dict(title="Creative Cloud ARR surpasses $13B milestone", sentiment=0.70, source="Bloomberg"),
        dict(title="Adobe faces growing competition from Canva and Figma alternatives", sentiment=-0.40, source="WSJ"),
        dict(title="Document Cloud AI assistant drives enterprise upsell", sentiment=0.55, source="TechCrunch"),
    ],
    "MSFT": [
        dict(title="Azure cloud growth accelerates to 31%", sentiment=0.80, source="Reuters"),
        dict(title="Copilot drives Microsoft 365 enterprise adoption", sentiment=0.65, source="Bloomberg"),
        dict(title="LinkedIn revenue growth moderates", sentiment=-0.15, source="WSJ"),
        dict(title="Gaming division Activision integration pays off", sentiment=0.40, source="CNBC"),
    ],
    "AMZN": [
        dict(title="AWS growth re-accelerates to 19%", sentiment=0.70, source="Reuters"),
        dict(title="Amazon expands same-day delivery network", sentiment=0.45, source="Bloomberg"),
        dict(title="Retail margins under pressure from rising costs", sentiment=-0.35, source="WSJ"),
    ],
    "NVDA": [
        dict(title="NVIDIA Blackwell GPU demand outpaces supply", sentiment=0.85, source="Reuters"),
        dict(title="Data center revenue triples year-over-year", sentiment=0.90, source="Bloomberg"),
        dict(title="Valuation concerns mount as P/E exceeds 50", sentiment=-0.45, source="WSJ"),
        dict(title="China export restrictions tighten", sentiment=-0.50, source="FT"),
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Tool 1: Market Data
# ═══════════════════════════════════════════════════════════════════
class MarketDataTool:

    def get_price_history(self, ticker: str, days: int = 30) -> dict:
        rng = _DRng(ticker, 1)
        base = _BASE_PRICES.get(ticker, 120.0)
        price = base * 0.96
        history = []
        for i in range(days):
            price *= (1 + rng.uniform(-0.012, 0.018))
            history.append({
                "date": str((datetime.now() - timedelta(days=days - i)).date()),
                "close": round(price, 2),
            })
        current = history[-1]["close"]
        return dict(
            ticker=ticker,
            current_price=current,
            open=round(current * 0.999, 2),
            high=round(current * 1.008, 2),
            low=round(current * 0.993, 2),
            volume=rng.randint(30_000_000, 70_000_000),
            price_history=history,
            period_return_pct=round((current / history[0]["close"] - 1) * 100, 2),
        )

    def get_fundamentals(self, ticker: str) -> dict:
        base = _FUNDAMENTALS.get(ticker, dict(
            market_cap=5e11, pe_ratio=18.0, forward_pe=15.5, eps=5.0,
            dividend_yield=0.01, beta=1.0, high_52w=150.0, low_52w=100.0,
            profit_margin=0.20, revenue_growth=0.10, debt_to_equity=0.50,
            roe=0.25, sector="Technology", industry="Software"))
        return {"ticker": ticker, **base}


# ═══════════════════════════════════════════════════════════════════
# Tool 2: Technical Analysis
# ═══════════════════════════════════════════════════════════════════
class TechnicalAnalysisTool:

    def compute(self, price_history: list[dict]) -> dict:
        closes = [p["close"] for p in price_history]
        if len(closes) < 14:
            return {"error": "Need >= 14 data points"}
        return dict(
            sma_10=round(sum(closes[-10:]) / 10, 2),
            sma_20=round(sum(closes[-20:]) / 20, 2) if len(closes) >= 20 else None,
            rsi_14=self._rsi(closes, 14),
            macd=self._macd(closes),
            bollinger=self._bollinger(closes),
            price_vs_sma10="ABOVE" if closes[-1] > sum(closes[-10:]) / 10 else "BELOW",
            trend=self._trend(closes),
        )

    def _rsi(self, c, p=14):
        deltas = [c[i] - c[i - 1] for i in range(1, len(c))]
        gains = [max(d, 0) for d in deltas[-p:]]
        losses = [max(-d, 0) for d in deltas[-p:]]
        ag, al = sum(gains) / p, sum(losses) / p
        if al == 0: return 100.0
        return round(100 - 100 / (1 + ag / al), 2)

    def _macd(self, c):
        e12, e26 = self._ema(c, 12), self._ema(c, 26)
        line = e12 - e26
        return dict(macd_line=round(line, 4),
                    signal_label="BULLISH" if line > 0 else "BEARISH")

    def _ema(self, data, period):
        if len(data) < period:
            return sum(data) / len(data)
        m = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for p in data[period:]:
            ema = (p - ema) * m + ema
        return ema

    def _bollinger(self, c, p=20):
        if len(c) < p: return {}
        w = c[-p:]
        sma = sum(w) / p
        std = math.sqrt(sum((x - sma) ** 2 for x in w) / p)
        return dict(upper=round(sma + 2 * std, 2), middle=round(sma, 2),
                    lower=round(sma - 2 * std, 2),
                    position="ABOVE_UPPER" if c[-1] > sma + 2 * std
                    else "BELOW_LOWER" if c[-1] < sma - 2 * std
                    else "WITHIN")

    def _trend(self, c):
        if len(c) < 20: return "INSUFFICIENT"
        s5, s20 = sum(c[-5:]) / 5, sum(c[-20:]) / 20
        if s5 > s20 * 1.015: return "UPTREND"
        if s5 < s20 * 0.985: return "DOWNTREND"
        return "SIDEWAYS"


# ═══════════════════════════════════════════════════════════════════
# Tool 3: Sentiment (mock — would use Reddit/X/FinBERT in prod)
# ═══════════════════════════════════════════════════════════════════
class SentimentTool:

    def get_sentiment(self, ticker: str) -> dict:
        rng = _DRng(ticker, 42)
        score = round(rng.uniform(-0.2, 0.65), 3)
        vol = rng.randint(800, 4500)
        return dict(
            ticker=ticker, overall_score=score,
            label="BULLISH" if score > 0.2 else "BEARISH" if score < -0.2 else "NEUTRAL",
            mention_volume=vol, trending=vol > 2500,
            sources=dict(reddit=round(rng.uniform(-0.3, 0.7), 3),
                         twitter=round(rng.uniform(-0.3, 0.7), 3)),
        )


# ═══════════════════════════════════════════════════════════════════
# Tool 4: News (mock — would use NewsAPI/Bloomberg in prod)
# ═══════════════════════════════════════════════════════════════════
class NewsTool:

    def get_news(self, ticker: str) -> dict:
        articles = _NEWS.get(ticker, [
            dict(title=f"{ticker} posts mixed results", sentiment=0.1, source="MW"),
            dict(title=f"Analysts raise {ticker} price target", sentiment=0.4, source="Reuters"),
        ])
        avg = round(sum(a["sentiment"] for a in articles) / len(articles), 3)
        return dict(ticker=ticker, article_count=len(articles), articles=articles,
                    avg_sentiment=avg,
                    macro="Fed holding rates; inflation cooling; tech sector resilient")


# ═══════════════════════════════════════════════════════════════════
# Tool 5: Portfolio Analytics
# ═══════════════════════════════════════════════════════════════════
class PortfolioAnalyticsTool:

    def analyze(self, holdings, avg_costs, current_prices, cash) -> dict:
        mkt_val = sum(s * current_prices.get(t, 0) for t, s in holdings.items())
        total = mkt_val + cash
        invested = sum(s * avg_costs.get(t, 0) for t, s in holdings.items())
        positions = {}
        for t, s in holdings.items():
            p = current_prices.get(t, 0)
            c = avg_costs.get(t, 0)
            mv = s * p
            positions[t] = dict(
                shares=s, avg_cost=c, price=p,
                market_value=round(mv, 2),
                weight_pct=round(mv / total * 100, 2) if total else 0,
                pnl=round((p - c) * s, 2),
                pnl_pct=round((p / c - 1) * 100, 2) if c else 0,
            )
        weights = [p["weight_pct"] for p in positions.values()]
        return dict(
            total_value=round(total, 2), cash=round(cash, 2),
            cash_pct=round(cash / total * 100, 2) if total else 100,
            invested=round(mkt_val, 2),
            total_pnl=round(mkt_val - invested, 2),
            positions=positions,
            num_positions=len(holdings),
            max_concentration=round(max(weights, default=0), 2),
        )
