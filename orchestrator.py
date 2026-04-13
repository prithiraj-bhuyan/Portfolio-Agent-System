"""
LangGraph Orchestrator for the Agentic Portfolio Management System.

Uses langgraph.graph.StateGraph to define the 7-stage pipeline:
  1. analysts      → 4 analyst agents run, write reports to state
  2. debate        → bull/bear researchers debate, facilitator decides
  3. trader        → proposes trade based on debate outcome
  4. risk_check    → 3-perspective risk assessment
  5. fund_manager  → final approval with adjustments
  6. human_gate    → human-in-the-loop approval
  7. execute       → paper trade execution

Conditional edges:
  - After trader: if HOLD → skip to end
  - After fund_manager: if rejected → skip to end
  - After human_gate: if rejected → skip to end
"""

from __future__ import annotations
import json
from typing import TypedDict, Any, Optional, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END

from models import GlobalState, TradeAction
from agents import (
    FundamentalAnalyst, TechnicalAnalyst, SentimentAnalyst, NewsAnalyst,
    ResearcherTeam, TraderAgent, RiskTeam, FundManager,
    PortfolioStrategist, MarketDataTool,
)


# ═══════════════════════════════════════════════════════════════════
#  LangGraph State Schema
# ═══════════════════════════════════════════════════════════════════

class PipelineState(TypedDict):
    """State passed through the LangGraph pipeline for ONE ticker."""
    ticker: str
    global_state: Any           # GlobalState object (mutable, shared)
    stage_log: list[dict]       # log of what happened at each stage
    current_stage: str
    outcome: str                # final outcome string
    should_continue: bool       # controls conditional routing


# ═══════════════════════════════════════════════════════════════════
#  Node Functions
# ═══════════════════════════════════════════════════════════════════

def analyst_node(state: PipelineState) -> PipelineState:
    """Stage 1: Run all 4 analyst agents."""
    ticker = state["ticker"]
    gs = state["global_state"]

    analysts = [
        ("Fundamental", FundamentalAnalyst()),
        ("Technical", TechnicalAnalyst()),
        ("Sentiment", SentimentAnalyst()),
        ("News", NewsAnalyst()),
    ]

    results = {}
    for name, agent in analysts:
        report = agent.run(ticker, gs)
        results[name] = {
            "signal": report.signal.value,
            "confidence": report.confidence,
            "summary": report.summary[:120],
        }
        print(f"    [{name:12s}] {report.signal.value:12s}  conf={report.confidence:.2f}")

    state["stage_log"].append({
        "stage": "analysts", "timestamp": datetime.now().isoformat(),
        "results": results,
    })
    state["current_stage"] = "analysts"
    return state


def debate_node(state: PipelineState) -> PipelineState:
    """Stage 2: Bull/Bear debate + facilitator."""
    ticker = state["ticker"]
    gs = state["global_state"]

    team = ResearcherTeam()
    record = team.run(ticker, gs)

    print(f"    Prevailing view: {record.prevailing_view.value}  "
          f"conf={record.consensus_confidence:.2f}")

    state["stage_log"].append({
        "stage": "debate", "timestamp": datetime.now().isoformat(),
        "view": record.prevailing_view.value,
        "confidence": record.consensus_confidence,
        "summary": record.facilitator_summary,
    })
    state["current_stage"] = "debate"
    return state


def trader_node(state: PipelineState) -> PipelineState:
    """Stage 3: Trader proposes a trade."""
    ticker = state["ticker"]
    gs = state["global_state"]

    trader = TraderAgent()
    proposal = trader.run(ticker, gs)

    print(f"    Proposal: {proposal.action.value} {proposal.quantity} shares  "
          f"conf={proposal.confidence:.2f}")

    state["stage_log"].append({
        "stage": "trader", "timestamp": datetime.now().isoformat(),
        "action": proposal.action.value,
        "quantity": proposal.quantity,
        "rationale": proposal.rationale,
    })
    state["current_stage"] = "trader"
    state["should_continue"] = (proposal.action != TradeAction.HOLD)
    if not state["should_continue"]:
        state["outcome"] = "HOLD — no trade proposed"
    return state


def risk_node(state: PipelineState) -> PipelineState:
    """Stage 4: Risk management team assessment."""
    ticker = state["ticker"]
    gs = state["global_state"]

    risk = RiskTeam()
    assessment = risk.run(ticker, gs)

    print(f"    Risk: {assessment.risk_level.value}  Approved: {assessment.approved}")
    for c in assessment.concerns:
        print(f"      ⚠ {c}")

    state["stage_log"].append({
        "stage": "risk", "timestamp": datetime.now().isoformat(),
        "risk_level": assessment.risk_level.value,
        "approved": assessment.approved,
        "concerns": assessment.concerns,
        "adjustments": assessment.adjustments,
    })
    state["current_stage"] = "risk"
    return state


def fund_manager_node(state: PipelineState) -> PipelineState:
    """Stage 5: Fund manager final decision."""
    ticker = state["ticker"]
    gs = state["global_state"]

    fm = FundManager()
    decision = fm.run(ticker, gs)

    print(f"    Decision: {decision.action.value} {decision.quantity} shares")

    state["stage_log"].append({
        "stage": "fund_manager", "timestamp": datetime.now().isoformat(),
        "action": decision.action.value,
        "quantity": decision.quantity,
        "rationale": decision.rationale,
    })
    state["current_stage"] = "fund_manager"
    state["should_continue"] = (decision.action != TradeAction.HOLD)
    if not state["should_continue"]:
        state["outcome"] = f"REJECTED by fund manager"
    return state


def human_gate_node(state: PipelineState) -> PipelineState:
    """Stage 6: Human-in-the-loop approval (auto-approved for prototype)."""
    ticker = state["ticker"]
    gs = state["global_state"]
    decision = gs.final_decisions.get(ticker)

    # For prototype: auto-approve. In production: interactive prompt.
    approved = True
    if decision:
        decision.approved_by_human = approved

    print(f"    Human approval: {'✓ APPROVED' if approved else '✗ REJECTED'}")

    state["stage_log"].append({
        "stage": "human_gate", "timestamp": datetime.now().isoformat(),
        "approved": approved,
    })
    state["current_stage"] = "human_gate"
    state["should_continue"] = approved
    if not approved:
        state["outcome"] = "REJECTED by human"
    return state


def execute_node(state: PipelineState) -> PipelineState:
    """Stage 7: Execute the paper trade."""
    ticker = state["ticker"]
    gs = state["global_state"]
    decision = gs.final_decisions.get(ticker)

    if not decision or decision.action == TradeAction.HOLD:
        state["outcome"] = "No trade executed"
        return state

    price = MarketDataTool().get_price_history(ticker)["current_price"]

    try:
        rec = gs.execute_trade(ticker, decision.action, decision.quantity, price)
        state["outcome"] = (f"EXECUTED: {decision.action.value} {decision.quantity} "
                            f"× {ticker} @ ${price:.2f} = ${rec['total']:,.2f}")
        print(f"    ✓ {state['outcome']}")
        print(f"    Cash remaining: ${gs.portfolio.cash:,.2f}")
    except ValueError as e:
        state["outcome"] = f"FAILED: {e}"
        print(f"    ✗ {state['outcome']}")

    state["stage_log"].append({
        "stage": "execute", "timestamp": datetime.now().isoformat(),
        "outcome": state["outcome"],
    })
    state["current_stage"] = "execute"
    return state


# ═══════════════════════════════════════════════════════════════════
#  Conditional edge routers
# ═══════════════════════════════════════════════════════════════════

def after_trader(state: PipelineState) -> Literal["risk_check", "end"]:
    return "risk_check" if state["should_continue"] else "end"


def after_fund_manager(state: PipelineState) -> Literal["human_gate", "end"]:
    return "human_gate" if state["should_continue"] else "end"


def after_human(state: PipelineState) -> Literal["execute", "end"]:
    return "execute" if state["should_continue"] else "end"


# ═══════════════════════════════════════════════════════════════════
#  Build the LangGraph
# ═══════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """Construct and compile the LangGraph pipeline."""

    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("analysts", analyst_node)
    graph.add_node("debate", debate_node)
    graph.add_node("trader", trader_node)
    graph.add_node("risk_check", risk_node)
    graph.add_node("fund_manager", fund_manager_node)
    graph.add_node("human_gate", human_gate_node)
    graph.add_node("execute", execute_node)
    graph.add_node("end", lambda s: s)    # terminal no-op

    # Linear edges
    graph.add_edge("analysts", "debate")
    graph.add_edge("debate", "trader")
    graph.add_edge("risk_check", "fund_manager")

    # Conditional edges
    graph.add_conditional_edges("trader", after_trader,
                                {"risk_check": "risk_check", "end": "end"})
    graph.add_conditional_edges("fund_manager", after_fund_manager,
                                {"human_gate": "human_gate", "end": "end"})
    graph.add_conditional_edges("human_gate", after_human,
                                {"execute": "execute", "end": "end"})

    # Terminal
    graph.add_edge("execute", "end")
    graph.add_edge("end", END)

    # Entry point
    graph.set_entry_point("analysts")

    return graph.compile()


# ═══════════════════════════════════════════════════════════════════
#  High-level Orchestrator
# ═══════════════════════════════════════════════════════════════════

class Orchestrator:
    """Runs the LangGraph pipeline for multiple tickers."""

    def __init__(self, initial_cash: float = 100_000.0,
                 watchlist: list[str] | None = None):
        self.state = GlobalState(initial_cash=initial_cash)
        self.watchlist = watchlist or ["AAPL", "GOOGL", "MSFT"]
        self.strategist = PortfolioStrategist(self.watchlist)
        self.graph = build_graph()

    def run_cycle(self, tickers: list[str] | None = None) -> dict:
        tickers = tickers or self.strategist.select_tickers(self.state)
        cycle_start = datetime.now().isoformat()
        results = {}

        for ticker in tickers:
            print(f"\n{'═'*60}")
            print(f"  PIPELINE: {ticker}")
            print(f"{'═'*60}")

            initial_state: PipelineState = {
                "ticker": ticker,
                "global_state": self.state,
                "stage_log": [],
                "current_stage": "",
                "outcome": "",
                "should_continue": True,
            }

            final = self.graph.invoke(initial_state)
            results[ticker] = {
                "outcome": final["outcome"],
                "stages": final["stage_log"],
            }
            print(f"\n  → OUTCOME: {final['outcome']}")

        summary = self.strategist.portfolio_summary(self.state)
        return {
            "cycle_start": cycle_start,
            "cycle_end": datetime.now().isoformat(),
            "tickers": tickers,
            "results": results,
            "portfolio": summary,
            "transactions": self.state.transaction_log,
        }


# ═══════════════════════════════════════════════════════════════════
#  CLI Entry Point
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  AGENTIC PORTFOLIO MANAGEMENT SYSTEM")
    print("  LangGraph + Groq Prototype  —  Phase 2 Demo")
    print("=" * 60)

    orch = Orchestrator(
        initial_cash=100_000.0,
        watchlist=["AAPL", "GOOGL", "MSFT"],
    )

    results = orch.run_cycle()

    # ── Summary ──
    print(f"\n{'═'*60}")
    print("  CYCLE COMPLETE — PORTFOLIO SUMMARY")
    print(f"{'═'*60}")
    p = orch.state.portfolio
    print(f"  Cash:     ${p.cash:>12,.2f}")
    for t, s in p.holdings.items():
        cost = p.avg_costs[t]
        print(f"  {t:5s}:    {s:>5d} shares @ avg ${cost:.2f}")
    print(f"  Trades:   {len(orch.state.transaction_log)}")

    for tx in orch.state.transaction_log:
        print(f"    {tx['action']:4s} {tx['quantity']:>4d} {tx['ticker']:5s} "
              f"@ ${tx['price']:>8.2f}  =  ${tx['total']:>10,.2f}")

    # ── Save artifacts ──
    import os
    os.makedirs("sample_runs", exist_ok=True)

    with open("sample_runs/interaction_trace.json", "w") as f:
        f.write(orch.state.get_trace_json())

    with open("sample_runs/cycle_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n  Saved: sample_runs/interaction_trace.json")
    print(f"  Saved: sample_runs/cycle_results.json")

    return results


if __name__ == "__main__":
    main()
