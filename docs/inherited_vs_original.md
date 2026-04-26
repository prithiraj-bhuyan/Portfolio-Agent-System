# Inherited vs. Original Boundary

**Project**: AI-Powered Agentic Portfolio Management System  
**Inspiration**: [TradingAgents](https://github.com/TauricResearch/TradingAgents) (Tauric Research)

---

## Purpose

This document explicitly names which components are copied from TradingAgents, which are adapted from it, and which are original to our team. This addresses the professor's feedback: *"The inherited-vs-original boundary that Phase 1 feedback asked for is not drawn anywhere, which matters both for the audit trail and for what you can claim credit for in Phase 3."*

---

## Component Classification

### Copied from TradingAgents (0 components)
No code was directly copied from the TradingAgents repository. Our implementation is built from scratch, though the overall concept (multi-agent trading system) draws inspiration from the project.

### Adapted / Inspired By TradingAgents (3 components)

| Component | What We Took | What We Changed |
|-----------|-------------|-----------------|
| **Multi-agent architecture concept** | Idea of having separate analyst, researcher, and risk agents | Redesigned as a 2-layer system with LangGraph StateGraph (TradingAgents uses a different orchestration pattern) |
| **Bull/Bear debate pattern** | Concept of adversarial researcher debate | Implemented as 2-round structured debate with JSON-formatted arguments and a separate facilitator agent |
| **Risk team multi-perspective** | Idea of having aggressive/neutral/conservative risk perspectives | Implemented as a single RiskTeam class with rule-based checks rather than 3 separate LLM-powered agents |

### Original to Our Team (all Phase 3 components + core architecture)

| Component | File(s) | Description |
|-----------|---------|-------------|
| **LangGraph StateGraph pipeline** | `orchestrator.py` | 7-stage pipeline with 3 conditional edges and 4 termination points. Uses LangGraph typed state, not a custom scheduler. |
| **GlobalState typed protocol** | `models.py` | Typed dataclass protocol with append-only traces. All inter-agent communication flows through this shared state. |
| **Rule-based fallbacks** | `agents.py` | Every LLM-powered agent has an independent rule-based fallback. This was our Phase 2 design decision. |
| **Streamlit dashboard** | `dashboard.py` | 5-tab interactive interface (Portfolio, Agent Reasoning, Transactions, Human Gate, CLASSic Report) |
| **CLASSic evaluation framework** | `evaluation/classic_evaluator.py` | All 6 CLASSic elements: success criteria, eval dataset, code evaluators, LLM judge, CLASSic report, manual review |
| **Historical backtest engine** | `backtest.py` | 3 pinned stress periods, rule-based strategy, Sharpe/drawdown comparison |
| **Experimental evaluation design** | `evaluation/eval_runner.py` | 10 scenarios with failure/adversarial cases (replacing regression tests) |
| **LLM cost/latency tracking** | `llm_interface.py` | Per-call timing, token, and cost logging for CLASSic Report |
| **SQLite persistence** | `persistence.py` | Multi-day portfolio state persistence |
| **Evidence package generator** | `evaluation/evidence_package.py` | Automated evidence collection with before/after traces |
| **Live data integration** | `tools.py` | yfinance + Finnhub with graceful mock fallback |
| **Concentration cap enforcement** | `agents.py` (RiskTeam) | Dual-level enforcement at Trader (soft) and Risk Team (hard) |
| **Human-in-the-loop gate** | `orchestrator.py`, `dashboard.py` | Interactive approval in Streamlit, auto-approve in CLI |

---

## Summary

- **0 components** are directly copied from TradingAgents
- **3 high-level concepts** are adapted/inspired (multi-agent architecture, bull/bear debate, multi-perspective risk)
- **13+ components** are original to our team, including all Phase 3 additions

The overall system design, implementation, evaluation framework, and documentation are original work by our team.

---

*Boundary documented per Phase 1 and Phase 2 professor feedback.*
