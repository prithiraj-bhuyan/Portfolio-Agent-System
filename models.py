"""
Core data models for the Agentic Portfolio Management System.
Defines structured communication protocol between all agents.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime
import json


# ── Enums ──────────────────────────────────────────────────────────
class Signal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TradeAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ── Structured Reports (communication protocol) ───────────────────
@dataclass
class AnalystReport:
    analyst_type: str
    ticker: str
    signal: Signal
    confidence: float
    summary: str
    key_metrics: dict
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        d = self.__dict__.copy()
        d["signal"] = self.signal.value
        return d


@dataclass
class DebateRecord:
    ticker: str
    rounds: list[dict]
    prevailing_view: Signal
    consensus_confidence: float
    facilitator_summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        d = self.__dict__.copy()
        d["prevailing_view"] = self.prevailing_view.value
        return d


@dataclass
class TradeProposal:
    ticker: str
    action: TradeAction
    quantity: int
    price_target: Optional[float]
    stop_loss: Optional[float]
    rationale: str
    supporting_signals: list[str]
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        d = self.__dict__.copy()
        d["action"] = self.action.value
        return d


@dataclass
class RiskAssessment:
    ticker: str
    original_proposal: dict
    risk_level: RiskLevel
    approved: bool
    adjustments: dict
    concerns: list[str]
    risk_metrics: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        d = self.__dict__.copy()
        d["risk_level"] = self.risk_level.value
        return d


@dataclass
class FinalDecision:
    ticker: str
    action: TradeAction
    quantity: int
    rationale: str
    requires_human_approval: bool
    approved_by_human: Optional[bool] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        d = self.__dict__.copy()
        d["action"] = self.action.value
        return d


@dataclass
class PortfolioState:
    cash: float
    holdings: dict          # ticker -> shares
    avg_costs: dict         # ticker -> avg cost basis
    total_value: float = 0.0

    def to_dict(self):
        return self.__dict__.copy()


# ── Global shared state ───────────────────────────────────────────
class GlobalState:
    """Shared state all agents read/write via structured protocol."""

    def __init__(self, initial_cash: float = 100_000.0):
        self.portfolio = PortfolioState(
            cash=initial_cash, holdings={}, avg_costs={}, total_value=initial_cash,
        )
        self.analyst_reports: dict[str, list[AnalystReport]] = {}
        self.debate_records: dict[str, DebateRecord] = {}
        self.trade_proposals: dict[str, TradeProposal] = {}
        self.risk_assessments: dict[str, RiskAssessment] = {}
        self.final_decisions: dict[str, FinalDecision] = {}
        self.transaction_log: list[dict] = []
        self.interaction_trace: list[dict] = []

    # ── logging ──
    def log(self, agent: str, action: str, details: dict):
        self.interaction_trace.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "details": details,
        })

    # ── writers ──
    def add_analyst_report(self, ticker: str, report: AnalystReport):
        self.analyst_reports.setdefault(ticker, []).append(report)
        self.log(report.analyst_type, "REPORT",
                 {"ticker": ticker, "signal": report.signal.value,
                  "confidence": report.confidence})

    def set_debate(self, ticker: str, rec: DebateRecord):
        self.debate_records[ticker] = rec
        self.log("ResearchTeam", "DEBATE",
                 {"ticker": ticker, "view": rec.prevailing_view.value})

    def set_proposal(self, ticker: str, prop: TradeProposal):
        self.trade_proposals[ticker] = prop
        self.log("Trader", "PROPOSAL",
                 {"ticker": ticker, "action": prop.action.value, "qty": prop.quantity})

    def set_risk(self, ticker: str, ra: RiskAssessment):
        self.risk_assessments[ticker] = ra
        self.log("RiskTeam", "ASSESSMENT",
                 {"ticker": ticker, "approved": ra.approved,
                  "level": ra.risk_level.value})

    def set_decision(self, ticker: str, dec: FinalDecision):
        self.final_decisions[ticker] = dec
        self.log("FundManager", "DECISION",
                 {"ticker": ticker, "action": dec.action.value, "qty": dec.quantity})

    # ── execution ──
    def execute_trade(self, ticker: str, action: TradeAction,
                      quantity: int, price: float) -> dict:
        if quantity <= 0:
            raise ValueError("Trade quantity must be > 0")
        p = self.portfolio
        if action == TradeAction.BUY:
            cost = quantity * price
            if cost > p.cash:
                raise ValueError(f"Insufficient cash: need ${cost:.2f}, have ${p.cash:.2f}")
            p.cash -= cost
            prev = p.holdings.get(ticker, 0)
            prev_cost = p.avg_costs.get(ticker, 0.0)
            total_cost = prev * prev_cost + cost
            new_shares = prev + quantity
            p.holdings[ticker] = new_shares
            p.avg_costs[ticker] = total_cost / new_shares
        elif action == TradeAction.SELL:
            curr = p.holdings.get(ticker, 0)
            if quantity > curr:
                raise ValueError(f"Cannot sell {quantity} of {ticker}, hold {curr}")
            p.holdings[ticker] = curr - quantity
            p.cash += quantity * price
            if p.holdings[ticker] == 0:
                del p.holdings[ticker]
                del p.avg_costs[ticker]

        rec = {"timestamp": datetime.now().isoformat(), "ticker": ticker,
               "action": action.value, "quantity": quantity,
               "price": price, "total": round(quantity * price, 2),
               "cash_after": round(p.cash, 2)}
        self.transaction_log.append(rec)
        self.log("Execution", "TRADE", rec)
        return rec

    def get_trace_json(self) -> str:
        return json.dumps(self.interaction_trace, indent=2)
