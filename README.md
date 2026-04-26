# AI-Powered Agentic Portfolio Management System

**Phase 3: Final Product, Evidence, and Reflection**  
Track A: Technical Build | CMU Agentic Systems Studio — Spring 2026  
Team: Raj Bhuyan, Sanath Mahesh Kumar, Mahir Nagersheth

---

## Overview

A multi-agent portfolio management system that autonomously analyzes stocks and constructs diversified portfolios with human-in-the-loop approval for every trade. Inspired by the [TradingAgents](https://github.com/TauricResearch/TradingAgents) framework (see [inherited vs. original boundary](docs/inherited_vs_original.md)).

**Architecture:** Two layers, 13 agents, 7-stage pipeline built with **LangGraph** and **Groq** (llama-3.3-70b-versatile, free tier).

## Quick Start

```bash
# Create and activate a virtual environment
python -m venv my-env
source my-env/bin/activate   # macOS/Linux
# my-env\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment (create .env in project root)
echo 'GROQ_API_KEY=gsk_your_key_here' > .env
echo 'DATA_MODE=mock' >> .env       # mock | live

# Run the CLI pipeline
python orchestrator.py

# Launch the Streamlit dashboard
streamlit run dashboard.py

# Run evaluation (10 experimental scenarios)
python evaluation/eval_runner.py

# Run CLASSic evaluation framework
python evaluation/classic_evaluator.py

# Run historical backtest (3 stress periods)
python backtest.py

# Generate evidence package
python evaluation/evidence_package.py
```

## Streamlit Dashboard

The interactive dashboard provides 5 tabs:

| Tab | Description |
|-----|-------------|
| 📊 Portfolio Overview | Holdings, P&L, allocation chart, cash trajectory |
| 🤖 Agent Reasoning | Expandable trace of each agent's analysis per ticker |
| 📋 Transaction Log | All executed trades with full interaction trace |
| 👤 Human Approval Gate | Interactive approve/reject for pending trades |
| 📈 CLASSic Report | Cost, latency, token usage, and accuracy metrics |

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
├── orchestrator.py            # LangGraph pipeline + CLI
├── agents.py                  # All 13 agent definitions
├── models.py                  # Data models, enums, GlobalState
├── tools.py                   # 5 tool interfaces (mock + live)
├── llm_interface.py           # Groq LLM wrapper with cost/latency tracking
├── dashboard.py               # Streamlit interactive dashboard
├── backtest.py                # Historical backtest engine (3 periods)
├── persistence.py             # SQLite state persistence
├── requirements.txt
├── .env                       # API keys + DATA_MODE (gitignored)
│
├── evaluation/
│   ├── eval_runner.py         # 10 experimental test scenarios
│   ├── classic_evaluator.py   # CLASSic framework (all 6 elements)
│   ├── evidence_package.py    # Evidence collection automation
│   ├── test_results.json      # Latest eval results
│   └── evidence/              # Generated evidence package
│       ├── test_scenarios.json
│       ├── failure_cases.json
│       ├── classic_report.json
│       ├── backtest_results.json
│       ├── eval_traces.json
│       ├── manifest.json
│       └── before_after_traces/
│
├── sample_runs/
│   ├── interaction_trace.json
│   ├── cycle_results.json
│   └── llm_metrics.json
│
└── docs/
    ├── final_report.md        # 12-15 page final report
    ├── ai_usage_disclosure.md # AI usage disclosure (course policy)
    ├── inherited_vs_original.md # What's adapted vs. original
    ├── contribution_update.md  # Phase 3 ownership split
    ├── video_script.md        # 5-minute video script
    ├── Architecture Diagram.png
    └── Phase2_Deliverable_final.pdf
```

## Evaluation

### Experimental Scenarios (10 tests)

| # | Scenario | Type | Description |
|---|----------|------|-------------|
| 1 | Consensus BUY | Normal | All analysts agree, trade executes |
| 2 | Consensus SELL | Normal | Existing position, bearish signals |
| 3 | Analyst Disagreement | Adversarial | Fund vs. tech conflict, debate arbitrates |
| 4 | News vs Fundamentals | Adversarial | Strong financials + negative news |
| 5 | Sentiment vs PE Risk | Adversarial | Extreme bullish sentiment + high valuation |
| 6 | Concentration Rejection | Failure | Risk team blocks >20% position |
| 7 | Insufficient Cash | Failure | $500 cash, can't afford stock |
| 8 | LLM Fallback | Failure | LLM disabled, rule-based degradation |
| 9 | Multi-ticker Portfolio | Normal | 3-ticker diversification |
| 10 | Trace Completeness | Normal | All 9 agent types in audit trail |

### Historical Backtest (3 periods)

| Period | Dates | Stress Event |
|--------|-------|-------------|
| COVID Drawdown | Feb–Apr 2020 | WHO pandemic declaration |
| Rate-Hike Volatility | Nov 2021–Jun 2022 | Fed tapering + rate hike |
| SVB Stress | Jan–Mar 2023 | SVB failure |

### CLASSic Evaluation Framework

| Element | Implementation |
|---------|---------------|
| Success Criteria | 5 measurable pass/fail thresholds |
| Eval Dataset | 20 labeled traces across 5 categories |
| Code Evaluators | Tool correctness, state consistency, concentration |
| LLM Judge | Reasoning quality scoring (1-5 scale) |
| CLASSic Report | Cost, Latency, Accuracy, Security, Severity |
| Manual Review | Template for 10-15 trace reviews |

## Technology Stack

- **Orchestration:** LangGraph StateGraph
- **LLM:** Groq API (llama-3.3-70b-versatile, free) with rule-based fallbacks
- **Market Data:** yfinance (live) or deterministic mocks
- **News:** Finnhub API (live) or curated mocks
- **Dashboard:** Streamlit + Plotly
- **Persistence:** SQLite
- **Language:** Python 3.11+

## Documentation

- [Final Report](docs/final_report.md)
- [AI Usage Disclosure](docs/ai_usage_disclosure.md)
- [Inherited vs. Original Boundary](docs/inherited_vs_original.md)
- [Contribution Update](docs/contribution_update.md)
- [Video Script](docs/video_script.md)
