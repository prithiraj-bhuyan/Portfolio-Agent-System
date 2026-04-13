"""
Agent definitions for the Agentic Portfolio Management System.

Layer 1 — Stock Analysis Engine (per-ticker pipeline):
  Analysts: FundamentalAnalyst, TechnicalAnalyst, SentimentAnalyst, NewsAnalyst
  Research: BullishResearcher, BearishResearcher, DebateFacilitator
  Trading:  TraderAgent
  Risk:     RiskTeam (aggressive, neutral, conservative perspectives)
  Approval: FundManager

Layer 2 — Portfolio Management:
  PortfolioStrategist (selects tickers, checks rebalancing)

Each agent reads from GlobalState, runs analysis (LLM or rules), writes
a structured report back to GlobalState.
"""

import json
from models import (
    AnalystReport, DebateRecord, TradeProposal, RiskAssessment,
    FinalDecision, GlobalState, Signal, RiskLevel, TradeAction,
)
from tools import (
    MarketDataTool, TechnicalAnalysisTool, SentimentTool,
    NewsTool, PortfolioAnalyticsTool,
)
from llm_interface import call_llm, call_llm_json


# ═══════════════════════════════════════════════════════════════════
#  ANALYST AGENTS
# ═══════════════════════════════════════════════════════════════════

class FundamentalAnalyst:
    """Evaluates company financials — P/E, growth, margins, ROE, debt."""

    SYS = """You are a fundamental analyst. Analyze company financials and produce a JSON:
{"signal":"STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL","confidence":0.0-1.0,
"summary":"1 paragraph","key_metrics":{},"reasoning":"detailed"}
Respond ONLY with the JSON, no other text."""

    def __init__(self):
        self.mkt = MarketDataTool()

    def run(self, ticker: str, state: GlobalState) -> AnalystReport:
        fund = self.mkt.get_fundamentals(ticker)
        price = self.mkt.get_price_history(ticker)

        data = call_llm_json(self.SYS, f"""Analyze {ticker}:
Fundamentals: {json.dumps(fund, indent=1)}
Price: ${price['current_price']}, Period return: {price['period_return_pct']}%""")

        if data and "signal" in data:
            report = AnalystReport(
                analyst_type="fundamental", ticker=ticker,
                signal=Signal[data["signal"]], confidence=data["confidence"],
                summary=data["summary"], key_metrics=data.get("key_metrics", {}),
                reasoning=data["reasoning"])
        else:
            report = self._rules(ticker, fund, price)
        state.add_analyst_report(ticker, report)
        return report

    def _rules(self, ticker, f, p):
        pe = f.get("pe_ratio", 25); g = f.get("revenue_growth", 0)
        m = f.get("profit_margin", 0.2); roe = f.get("roe", 0.2)
        de = f.get("debt_to_equity", 1.0)
        s = 0
        if pe and pe < 30: s += 1
        if pe and pe < 20: s += 1
        if g and g > 0.05: s += 1
        if g and g > 0.15: s += 1
        if m and m > 0.20: s += 1
        if roe and roe > 0.20: s += 1
        if de and de < 0.8: s += 1
        sig = [Signal.STRONG_SELL, Signal.SELL, Signal.SELL, Signal.HOLD,
               Signal.BUY, Signal.BUY, Signal.STRONG_BUY, Signal.STRONG_BUY][min(s, 7)]
        return AnalystReport("fundamental", ticker, sig, round(0.35 + s * 0.08, 2),
            f"{ticker}: PE={pe}, Growth={g:.1%}, Margin={m:.1%}, ROE={roe:.1%}",
            {"pe_ratio": pe, "revenue_growth": g, "profit_margin": m, "roe": roe},
            f"Score {s}/7: PE {'<30 ok' if pe and pe<30 else 'high'}, "
            f"growth {'strong' if g and g>0.1 else 'moderate'}, "
            f"margins {'healthy' if m and m>0.2 else 'thin'}")


class TechnicalAnalyst:
    """Analyzes price patterns — RSI, MACD, Bollinger, trends."""

    SYS = """You are a technical analyst. Analyze indicators and produce a JSON:
{"signal":"STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL","confidence":0.0-1.0,
"summary":"1 paragraph","key_metrics":{},"reasoning":"detailed"}
Respond ONLY with the JSON."""

    def __init__(self):
        self.mkt = MarketDataTool()
        self.ta = TechnicalAnalysisTool()

    def run(self, ticker: str, state: GlobalState) -> AnalystReport:
        price = self.mkt.get_price_history(ticker)
        ind = self.ta.compute(price["price_history"])

        data = call_llm_json(self.SYS,
            f"Analyze {ticker} technicals:\n{json.dumps(ind, indent=1)}\n"
            f"Current price: ${price['current_price']}")

        if data and "signal" in data:
            report = AnalystReport(
                "technical", ticker, Signal[data["signal"]], data["confidence"],
                data["summary"], data.get("key_metrics", {}), data["reasoning"])
        else:
            report = self._rules(ticker, ind)
        state.add_analyst_report(ticker, report)
        return report

    def _rules(self, ticker, ind):
        rsi = ind.get("rsi_14", 50)
        macd = ind.get("macd", {}).get("signal_label", "NEUTRAL")
        trend = ind.get("trend", "SIDEWAYS")
        s = 0
        if rsi < 30: s += 2
        elif rsi < 45: s += 1
        elif rsi > 70: s -= 2
        elif rsi > 60: s -= 1
        if macd == "BULLISH": s += 1
        else: s -= 1
        if trend == "UPTREND": s += 1
        elif trend == "DOWNTREND": s -= 1
        if s >= 3: sig = Signal.STRONG_BUY
        elif s >= 1: sig = Signal.BUY
        elif s <= -3: sig = Signal.STRONG_SELL
        elif s <= -1: sig = Signal.SELL
        else: sig = Signal.HOLD
        return AnalystReport("technical", ticker, sig,
            round(min(0.9, 0.4 + abs(s) * 0.12), 2),
            f"{ticker}: RSI={rsi}, MACD={macd}, Trend={trend}",
            {"rsi": rsi, "macd": macd, "trend": trend},
            f"RSI {'oversold' if rsi<30 else 'overbought' if rsi>70 else 'neutral'}, "
            f"MACD {macd}, trend {trend}")


class SentimentAnalyst:
    """Gauges social media sentiment — Reddit, X, StockTwits."""

    def __init__(self):
        self.tool = SentimentTool()

    def run(self, ticker: str, state: GlobalState) -> AnalystReport:
        d = self.tool.get_sentiment(ticker)
        sc = d["overall_score"]
        if sc > 0.5: sig = Signal.STRONG_BUY
        elif sc > 0.2: sig = Signal.BUY
        elif sc < -0.5: sig = Signal.STRONG_SELL
        elif sc < -0.2: sig = Signal.SELL
        else: sig = Signal.HOLD
        report = AnalystReport("sentiment", ticker, sig,
            round(min(0.85, 0.4 + abs(sc) * 0.45), 2),
            f"{ticker} social sentiment: {d['label']} (score={sc:.3f}), "
            f"volume={d['mention_volume']}, trending={d['trending']}",
            {"score": sc, "volume": d["mention_volume"],
             "reddit": d["sources"]["reddit"], "twitter": d["sources"]["twitter"]},
            f"Aggregate sentiment {d['label']}: Reddit={d['sources']['reddit']:.2f}, "
            f"Twitter={d['sources']['twitter']:.2f}")
        state.add_analyst_report(ticker, report)
        return report


class NewsAnalyst:
    """Analyzes recent news and macro context."""

    def __init__(self):
        self.tool = NewsTool()

    def run(self, ticker: str, state: GlobalState) -> AnalystReport:
        d = self.tool.get_news(ticker)
        avg = d["avg_sentiment"]
        if avg > 0.4: sig = Signal.BUY
        elif avg > 0.15: sig = Signal.HOLD
        elif avg < -0.3: sig = Signal.SELL
        else: sig = Signal.HOLD
        report = AnalystReport("news", ticker, sig,
            round(min(0.80, 0.35 + abs(avg) * 0.55), 2),
            f"{ticker} news: avg_sentiment={avg:.3f}, {d['article_count']} articles. "
            f"Macro: {d['macro']}",
            {"avg_sentiment": avg, "articles": d["article_count"],
             "headlines": [a["title"] for a in d["articles"][:3]]},
            f"News {'positive' if avg>0.15 else 'negative' if avg<-0.15 else 'mixed'}. "
            f"Macro backdrop: {d['macro'][:60]}")
        state.add_analyst_report(ticker, report)
        return report


# ═══════════════════════════════════════════════════════════════════
#  RESEARCHER TEAM  (Bull / Bear debate + Facilitator)
# ═══════════════════════════════════════════════════════════════════

class ResearcherTeam:
    """Conducts multi-round bull/bear debate, facilitator picks winner."""

    BULL_SYS = """You are a BULLISH researcher. Build the strongest investment case FOR this stock.
Use analyst data. Respond with JSON: {"argument":"...","key_points":["p1","p2","p3"]}"""
    BEAR_SYS = """You are a BEARISH researcher. Build the strongest case AGAINST investing.
Find risks, weaknesses. Respond with JSON: {"argument":"...","key_points":["p1","p2","p3"]}"""
    FACIL_SYS = """You are a debate facilitator. Review the bull and bear arguments plus analyst data.
Determine the prevailing view. Respond with JSON:
{"prevailing_view":"STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL","confidence":0.0-1.0,
"summary":"1 paragraph synthesis"}"""

    ROUNDS = 2

    def run(self, ticker: str, state: GlobalState) -> DebateRecord:
        reports = state.analyst_reports.get(ticker, [])
        report_text = "\n".join(
            f"  {r.analyst_type}: {r.signal.value} conf={r.confidence} — {r.summary}"
            for r in reports)

        rounds = []
        for rnd in range(self.ROUNDS):
            ctx = f"Ticker: {ticker}\nRound {rnd+1}/{self.ROUNDS}\n\nAnalyst Reports:\n{report_text}"
            if rounds:
                ctx += f"\n\nPrior debate:\n{json.dumps(rounds, indent=1)}"

            bull = call_llm_json(self.BULL_SYS, ctx)
            bear = call_llm_json(self.BEAR_SYS, ctx)
            rounds.append({
                "round": rnd + 1,
                "bull": bull or self._fallback_bull(reports),
                "bear": bear or self._fallback_bear(reports),
            })

        # Facilitator
        facil_ctx = f"Ticker: {ticker}\nAnalyst Reports:\n{report_text}\n\nDebate:\n{json.dumps(rounds, indent=1)}"
        facil = call_llm_json(self.FACIL_SYS, facil_ctx)

        if facil and "prevailing_view" in facil:
            view = Signal[facil["prevailing_view"]]
            conf = facil["confidence"]
            summary = facil["summary"]
        else:
            view, conf, summary = self._facilitator_rules(reports)

        rec = DebateRecord(ticker, rounds, view, round(conf, 2), summary)
        state.set_debate(ticker, rec)
        return rec

    def _fallback_bull(self, reports):
        bullish = [r for r in reports if r.signal in (Signal.BUY, Signal.STRONG_BUY)]
        return {"argument": f"{len(bullish)} of {len(reports)} analysts are bullish",
                "key_points": [r.summary[:80] for r in bullish[:3]] or ["momentum"]}

    def _fallback_bear(self, reports):
        bearish = [r for r in reports if r.signal in (Signal.SELL, Signal.STRONG_SELL)]
        return {"argument": f"{len(bearish)} of {len(reports)} analysts flag risks",
                "key_points": [r.summary[:80] for r in bearish[:3]] or ["valuation"]}

    def _facilitator_rules(self, reports):
        if not reports:
            return Signal.HOLD, 0.5, "No analyst data available."
        scores = {"STRONG_BUY": 2, "BUY": 1, "HOLD": 0, "SELL": -1, "STRONG_SELL": -2}
        total = sum(scores.get(r.signal.value, 0) * r.confidence for r in reports)
        avg = total / len(reports)
        if avg > 0.8: view = Signal.STRONG_BUY
        elif avg > 0.3: view = Signal.BUY
        elif avg < -0.8: view = Signal.STRONG_SELL
        elif avg < -0.3: view = Signal.SELL
        else: view = Signal.HOLD
        conf = min(0.90, 0.4 + abs(avg) * 0.3)
        return view, conf, (
            f"Weighted analyst score: {avg:.2f}. "
            f"Bullish: {sum(1 for r in reports if r.signal in (Signal.BUY,Signal.STRONG_BUY))}/{len(reports)}, "
            f"Bearish: {sum(1 for r in reports if r.signal in (Signal.SELL,Signal.STRONG_SELL))}/{len(reports)}.")


# ═══════════════════════════════════════════════════════════════════
#  TRADER AGENT
# ═══════════════════════════════════════════════════════════════════

class TraderAgent:
    """Proposes trades based on research outcome. Position sizing ≤ 20%."""

    SYS = """You are a trader at an investment firm. Based on the debate outcome and data,
decide BUY/SELL/HOLD with quantity. Never allocate > 20% of portfolio to one stock.
Respond ONLY with JSON:
{"action":"BUY|SELL|HOLD","quantity":int,"price_target":float_or_null,
"stop_loss":float_or_null,"rationale":"...","confidence":0.0-1.0}"""

    def run(self, ticker: str, state: GlobalState) -> TradeProposal:
        debate = state.debate_records.get(ticker)
        reports = state.analyst_reports.get(ticker, [])
        p = state.portfolio
        price_data = MarketDataTool().get_price_history(ticker)
        cp = price_data["current_price"]

        prompt = (f"Ticker: {ticker}, Price: ${cp}\n"
                  f"Cash: ${p.cash:.2f}, Holdings: {json.dumps(p.holdings)}\n"
                  f"Debate view: {debate.prevailing_view.value if debate else 'N/A'}, "
                  f"conf: {debate.consensus_confidence if debate else 'N/A'}\n"
                  f"Debate summary: {debate.facilitator_summary if debate else 'N/A'}\n"
                  f"Analyst signals: {', '.join(r.signal.value for r in reports)}")

        data = call_llm_json(self.SYS, prompt)

        if data and "action" in data:
            prop = TradeProposal(
                ticker, TradeAction[data["action"]], data["quantity"],
                data.get("price_target"), data.get("stop_loss"),
                data["rationale"],
                [r.signal.value for r in reports], data["confidence"])
        else:
            prop = self._rules(ticker, state, cp)
        state.set_proposal(ticker, prop)
        return prop

    def _rules(self, ticker, state, price):
        db = state.debate_records.get(ticker)
        view = db.prevailing_view if db else Signal.HOLD
        conf = db.consensus_confidence if db else 0.5
        if view in (Signal.BUY, Signal.STRONG_BUY):
            alloc = state.portfolio.cash * (0.18 if view == Signal.STRONG_BUY else 0.12)
            qty = max(1, int(alloc / price))
            act = TradeAction.BUY
        elif view in (Signal.SELL, Signal.STRONG_SELL):
            qty = state.portfolio.holdings.get(ticker, 0)
            act = TradeAction.SELL if qty > 0 else TradeAction.HOLD
            if act == TradeAction.HOLD: qty = 0
        else:
            act, qty = TradeAction.HOLD, 0
        return TradeProposal(
            ticker, act, qty,
            round(price * 1.10, 2) if act == TradeAction.BUY else None,
            round(price * 0.95, 2) if act == TradeAction.BUY else None,
            f"Debate: {view.value} (conf={conf:.2f}). "
            f"{'Allocating ~15% of cash.' if act==TradeAction.BUY else 'No position change.'}",
            [view.value], conf)


# ═══════════════════════════════════════════════════════════════════
#  RISK MANAGEMENT TEAM  (3 perspectives)
# ═══════════════════════════════════════════════════════════════════

class RiskTeam:
    """Aggressive, Neutral, Conservative risk agents deliberate."""

    def run(self, ticker: str, state: GlobalState) -> RiskAssessment:
        prop = state.trade_proposals.get(ticker)
        if not prop:
            raise ValueError(f"No proposal for {ticker}")
        p = state.portfolio
        price = MarketDataTool().get_price_history(ticker)["current_price"]
        trade_val = prop.quantity * price
        port_val = p.cash + sum(
            MarketDataTool().get_price_history(t)["current_price"] * s
            for t, s in p.holdings.items()
        ) if p.holdings else p.cash
        conc = trade_val / port_val * 100 if port_val else 0

        concerns, adj = [], {}

        # Aggressive: mostly fine
        # Neutral: cap concentration
        if conc > 20:
            concerns.append(f"Concentration {conc:.1f}% > 20% limit")
            adj["reduced_quantity"] = int(port_val * 0.20 / price)
        # Conservative: check confidence & stop-loss
        if prop.confidence < 0.5:
            concerns.append(f"Low confidence ({prop.confidence:.2f})")
        if not prop.stop_loss and prop.action == TradeAction.BUY:
            concerns.append("No stop-loss — adding 5% trailing stop")
            adj["stop_loss"] = round(price * 0.95, 2)
        if prop.action == TradeAction.BUY and trade_val > p.cash:
            concerns.append("Insufficient cash")

        risk = (RiskLevel.HIGH if len(concerns) >= 3
                else RiskLevel.MODERATE if concerns
                else RiskLevel.LOW)
        ok = risk != RiskLevel.CRITICAL and not (
            prop.action == TradeAction.BUY and trade_val > p.cash)

        ra = RiskAssessment(
            ticker, prop.to_dict(), risk, ok, adj, concerns,
            {"trade_value": round(trade_val, 2),
             "concentration_pct": round(conc, 2),
             "cash_after": round(p.cash - trade_val if prop.action == TradeAction.BUY
                                 else p.cash + trade_val, 2)})
        state.set_risk(ticker, ra)
        return ra


# ═══════════════════════════════════════════════════════════════════
#  FUND MANAGER
# ═══════════════════════════════════════════════════════════════════

class FundManager:
    """Final decision gate — applies risk adjustments, flags for human approval."""

    def run(self, ticker: str, state: GlobalState) -> FinalDecision:
        ra = state.risk_assessments.get(ticker)
        prop = state.trade_proposals.get(ticker)
        if not ra or not prop:
            raise ValueError(f"Missing data for {ticker}")
        if not ra.approved:
            dec = FinalDecision(ticker, TradeAction.HOLD, 0,
                f"Rejected by risk team: {'; '.join(ra.concerns)}", False)
        else:
            qty = ra.adjustments.get("reduced_quantity", prop.quantity)
            if qty <= 0:
                dec = FinalDecision(ticker, TradeAction.HOLD, 0,
                    f"Risk adjustments reduced quantity to 0: {'; '.join(ra.concerns)}", False)
            else:
                dec = FinalDecision(ticker, prop.action, qty,
                    f"Approved (risk={ra.risk_level.value}). {prop.rationale}",
                    True)  # always require human sign-off
        state.set_decision(ticker, dec)
        return dec


# ═══════════════════════════════════════════════════════════════════
#  PORTFOLIO STRATEGIST  (Layer 2)
# ═══════════════════════════════════════════════════════════════════

class PortfolioStrategist:
    """Selects tickers to analyze, monitors rebalancing needs."""

    def __init__(self, watchlist: list[str]):
        self.watchlist = watchlist
        self.analytics = PortfolioAnalyticsTool()
        self.mkt = MarketDataTool()

    def select_tickers(self, state: GlobalState) -> list[str]:
        return self.watchlist

    def portfolio_summary(self, state: GlobalState) -> dict:
        prices = {t: self.mkt.get_price_history(t)["current_price"]
                  for t in state.portfolio.holdings}
        return self.analytics.analyze(
            state.portfolio.holdings, state.portfolio.avg_costs,
            prices, state.portfolio.cash)

    def should_rebalance(self, state: GlobalState) -> bool:
        s = self.portfolio_summary(state)
        return s.get("max_concentration", 0) > 25
