# AI-Powered Agentic Portfolio Management System

**Phase 2: Architecture, Prototype, and Evaluation Plan**  
Track A: Technical Build | CMU Agentic Systems Studio — Spring 2026

---

## Overview

A multi-agent portfolio management system that autonomously analyzes stocks and constructs diversified portfolios with human-in-the-loop approval for every trade. Inspired by the [TradingAgents](https://github.com/TauricResearch/TradingAgents) framework.

**Architecture:** Two layers, 13 agents, 7-stage pipeline built with **LangGraph** and **Groq** (llama-3.3-70b-versatile, free tier).

## Quick Start

```bash
# Create and activate a virtual environment
python -m venv my-env
source my-env/bin/activate   # macOS/Linux
# my-env\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Enable LLM-powered analysis
# Create a .env file in the project root:
echo 'GROQ_API_KEY=gsk_your_key_here' > .env

# Run the prototype
python orchestrator.py

# Run evaluation (7 test scenarios)
python evaluation/eval_runner.py
```

The API key is loaded automatically from the `.env` file via `python-dotenv`. The system runs with deterministic mock data if no API key is set.

## Architecture

```
Layer 2: Portfolio Strategist
  └── selects tickers → triggers Layer 1 for each

Layer 1: Stock Analysis Engine (per ticker)
  Stage 1: Analyst Team (4 concurrent agents)
      → Fundamental, Technical, Sentiment, News
  Stage 2: Researcher Team (bull/bear debate + facilitator)
  Stage 3: Trader (proposes trade)
  Stage 4: Risk Management (3 perspectives)
  Stage 5: Fund Manager (final approval)
  Stage 6: Human Gate (approve/reject)
  Stage 7: Execution (paper trade)
```

Conditional edges:
- After Trader → if HOLD → END
- After Fund Manager → if rejected → END
- After Human Gate → if rejected → END

## File Structure

```
├── models.py              # Data models, enums, GlobalState
├── tools.py               # 5 tool interfaces
├── llm_interface.py       # Groq LLM wrapper with fallback
├── agents.py              # All 13 agent definitions
├── orchestrator.py        # LangGraph pipeline + CLI
├── requirements.txt
├── evaluation/
│   └── eval_runner.py     # 7 test scenarios
├── sample_runs/
│   ├── interaction_trace.json
│   └── cycle_results.json
└── docs/
    ├── Phase2_Deliverable.docx
    ├── architecture.mermaid
    └── generate_docx.js
```

## Sample Output

```
PIPELINE: ADBE
  [Fundamental ] BUY     conf=0.75
  [Technical   ] BUY     conf=0.52
  [Sentiment   ] BUY     conf=0.60
  [News        ] HOLD    conf=0.54
  Debate: BUY  conf=0.54
  Trader: BUY 22 shares
  Risk: LOW  Approved
  Human: ✓ APPROVED
  → EXECUTED: BUY 22 × ADBE @ $548.62 = $12,069.64
```

## Evaluation Results

| # | Scenario | Category | Status |
|---|----------|----------|--------|
| 1 | Strong consensus BUY | End-to-end | ✓ PASS |
| 2 | Mixed signals → HOLD | Coordination | ✓ PASS |
| 3 | Concentration limit | Risk mgmt | ✓ PASS |
| 4 | Insufficient cash | Error handling | ✓ PASS |
| 5 | Multi-ticker portfolio | Portfolio mgmt | ✓ PASS |
| 6 | Trace completeness | Observability | ✓ PASS |
| 7 | Existing position | End-to-end | ✓ PASS |

## Technology Stack

- **Orchestration:** LangGraph StateGraph
- **LLM:** Groq API (llama-3.3-70b-versatile, free) with rule-based fallbacks
- **Market Data:** yfinance (live) or deterministic mocks
- **Language:** Python 3.11+
