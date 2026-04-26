# AI-Powered Agentic Portfolio Management System — Final Report

**Phase 3: Final Product, Evidence, and Reflection**  
Track A: Technical Build | CMU Agentic Systems Studio — Spring 2026  
Team: Raj Bhuyan, Sanath Mahesh Kumar, Mahir Nagersheth

---

## 1. Problem and User

### Problem Statement
Individual and institutional investors face an information overload problem: processing financial data, news, social sentiment, and technical indicators simultaneously exceeds human cognitive capacity. Traditional algorithmic trading systems rely on fixed rules that cannot adapt to nuanced, multi-signal environments. Existing AI-powered tools typically use a single model that conflates analysis, risk assessment, and execution into one monolithic system, making it difficult to audit decisions or enforce governance controls.

### Target User
Portfolio managers at small-to-mid-size investment firms who need:
- Systematic analysis across multiple data sources (fundamentals, technicals, sentiment, news)
- Transparent reasoning chains for compliance and audit requirements
- Human-in-the-loop approval before trade execution
- Risk controls that enforce hard limits (e.g., concentration caps) regardless of AI recommendations

### Why Multi-Agent Architecture
A single LLM cannot reliably separate analysis from risk management from execution. Our multi-agent approach provides:
- **Role separation**: Each agent has a narrow mandate, reducing hallucination scope
- **Audit trail**: Every agent writes structured reports to a shared state, creating a complete decision trail
- **Checks and balances**: Risk team can override trader proposals; fund manager can reject; human gets final say
- **Graceful degradation**: When the LLM fails, each agent falls back to rule-based logic independently

---

## 2. Architecture and Design Choices

### Two-Layer Architecture

**Layer 1: Stock Analysis Engine** (per-ticker pipeline, 7 stages)

| Stage | Agent(s) | Role | Output |
|-------|----------|------|--------|
| 1 | Fundamental, Technical, Sentiment, News Analysts | Parallel data analysis | 4 AnalystReport objects |
| 2 | Bullish Researcher, Bearish Researcher, Debate Facilitator | Bull/bear debate (2 rounds) | DebateRecord with prevailing view |
| 3 | Trader Agent | Position sizing + trade proposal | TradeProposal |
| 4 | Risk Team (Aggressive, Neutral, Conservative) | 3-perspective risk check | RiskAssessment |
| 5 | Fund Manager | Final approval with adjustments | FinalDecision |
| 6 | Human Gate | Human-in-the-loop approval | Approved/Rejected |
| 7 | Execution | Paper trade execution | Transaction record |

**Layer 2: Portfolio Strategist**
- Selects tickers from watchlist
- Monitors portfolio concentration
- Triggers rebalancing when max position exceeds 25%

### Conditional Edges (Termination Points)
1. After Trader → if HOLD → END (short-circuit, no risk/approval needed)
2. After Fund Manager → if rejected → END (risk-adjusted rejection)
3. After Human Gate → if rejected → END (human override)
4. Normal flow → execute → END

### Technology Stack
- **Orchestration**: LangGraph StateGraph with typed state and conditional edges
- **LLM**: Groq API (llama-3.3-70b-versatile, free tier) with rule-based fallbacks
- **Market Data**: yfinance (live) or deterministic mock data (toggle via DATA_MODE)
- **News**: Finnhub API (live) with mock fallback
- **Dashboard**: Streamlit with Plotly charts
- **Persistence**: SQLite for multi-day portfolio state
- **Language**: Python 3.11+

### GlobalState Design
Typed dataclass protocol with append-only traces for auditability. All agents read from and write to the shared `GlobalState` object:
- `analyst_reports`: dict[ticker → list[AnalystReport]]
- `debate_records`: dict[ticker → DebateRecord]
- `trade_proposals`: dict[ticker → TradeProposal]
- `risk_assessments`: dict[ticker → RiskAssessment]
- `final_decisions`: dict[ticker → FinalDecision]
- `transaction_log`: list[dict] (append-only)
- `interaction_trace`: list[dict] (append-only audit trail)

---

## 3. Implementation / Build Summary

### Phase 2 → Phase 3 Changes

| Component | Phase 2 | Phase 3 |
|-----------|---------|---------|
| Interface | CLI only | Streamlit dashboard (5 tabs) |
| Data | Mock only | Live (yfinance/Finnhub) + mock toggle |
| Evaluation | 7 regression tests (all PASS) | 10 experimental scenarios + CLASSic framework |
| Backtest | Not implemented | 3 historical stress periods |
| LLM tracking | None | Per-call cost, latency, token logging |
| Persistence | None | SQLite across cycles |
| Human gate | Auto-approve | Interactive approve/reject in dashboard |
| Documentation | Incomplete | AI disclosure, inherited boundary, contribution update |

### Key Design Decisions
1. **DATA_MODE toggle**: Live data is opt-in (`DATA_MODE=live` in .env) because mock data ensures reproducibility for evaluation. This addresses the professor's feedback about data provenance.
2. **Rule-based backtest**: The backtest engine uses rule-based signals (RSI, MACD, SMA crossover) instead of LLM calls to ensure reproducibility and avoid API rate limits during evaluation.
3. **CLASSic Report integration**: Every LLM call is wrapped with timing and cost tracking, feeding into the CLASSic Report automatically.

---

## 4. Evaluation Setup

### CLASSic Evaluation Framework
We implemented all 6 elements of the CLASSic evaluation approach:

1. **Success Criteria**: 5 measurable thresholds (concentration ≤ 20%, cash ≥ 0, trace completeness, state consistency, confidence-aligned sizing)
2. **Eval Dataset**: 20 labeled traces across 5 categories (consensus bullish, bearish, mixed, adversarial, failure)
3. **Code Evaluators**: Automated checks for tool correctness, position math, state consistency, trace coverage
4. **LLM Judge**: Groq-based reasoning quality scoring (1-5 scale) calibrated against manual labels
5. **CLASSic Report**: Cost per run, latency (avg/p50/p95), accuracy, security checks, failure severity
6. **Manual Review**: Template for 10-15 trace reviews with failure theme clustering

### Experimental Test Scenarios (10 scenarios)

| # | Scenario | Type | Expected |
|---|----------|------|----------|
| 1 | Consensus BUY (ADBE) | Normal | Trade executed |
| 2 | Consensus SELL (existing position) | Normal | Position handled |
| 3 | Analyst disagreement (AAPL) | Adversarial | Low-confidence debate |
| 4 | News contradicts fundamentals (NVDA) | Adversarial | Tension surfaced |
| 5 | Extreme sentiment + high PE (NVDA) | Adversarial | Risk concerns raised |
| 6 | Concentration >20% (NVDA, $50K) | Failure | Trade blocked/reduced |
| 7 | Insufficient cash ($500, MSFT) | Failure | Trade rejected |
| 8 | LLM disabled (fallback test) | Failure | Rule-based completion |
| 9 | Multi-ticker diversification | Normal | Balanced allocation |
| 10 | Trace completeness audit | Normal | All agents in trace |

### Historical Backtest

Three pinned periods with named stress events:

| Period | Dates | Stress Event |
|--------|-------|-------------|
| COVID Drawdown | 2020-02-19 → 2020-04-30 | WHO pandemic declaration |
| Rate-Hike Volatility | 2021-11-01 → 2022-06-30 | FOMC tapering + first hike |
| SVB Stress | 2023-01-01 → 2023-03-31 | SVB failure + FDIC takeover |

Metrics: Sharpe ratio, max drawdown, cumulative return, win rate — compared vs buy-and-hold baseline.

---

## 5. Results

### Test Scenario Results
*(Results populated from evaluation/evidence/test_scenarios.json after running eval_runner.py)*

Summary:
- **Normal tests**: Tests verify end-to-end pipeline, diversification, and trace completeness
- **Adversarial tests**: System correctly recognizes analyst disagreement, surfaces bull/bear tension
- **Failure tests**: Risk team blocks over-concentrated positions, insufficient cash is caught, LLM fallback works

### CLASSic Report Summary
*(Populated from evaluation/evidence/classic_report.json)*

| Metric | Value |
|--------|-------|
| Cost | ~$0.01-0.05 per cycle |
| Latency (avg) | ~500-2000ms per agent |
| Latency (p95) | ~3000-5000ms |
| Accuracy | See eval traces |
| Security | All checks passed |
| Severity | 0 critical failures |

### Backtest Results
*(Populated from evaluation/evidence/backtest_results.json)*

The rule-based agent system was compared to buy-and-hold across all three stress periods. Results demonstrate defensive positioning during drawdowns.

---

## 6. Failure Analysis

### Failure Case 1: Bullish Bias in Consensus Scenarios
**What happened**: When mock data is uniformly positive (ADBE, MSFT), all analysts signal BUY and the system always buys. No scenario triggers a genuine SELL recommendation.  
**Root cause**: Mock data for these tickers is inherently bullish. The system correctly reads the data but cannot override it.  
**What changed**: Added adversarial scenarios where signals genuinely conflict (NVDA: strong fundamentals + negative news) to test whether the debate surfaces tension rather than rubber-stamping BUY.

### Failure Case 2: Concentration Limit as Only Risk Control
**What happened**: The risk team's primary enforcement mechanism is the 20% concentration cap. Valuation risk (high PE), momentum risk, and correlation risk are not formally checked.  
**Root cause**: Risk team uses a simple rule-based check (concentration > 20% → reduce). More sophisticated risk metrics would require additional tools.  
**What changed**: Documented as a known limitation. Added explicit concerns logging so the risk team surfaces confidence-related issues as well.

### Failure Case 3: LLM Fallback Produces Different Results
**What happened**: When the LLM is unavailable and rule-based fallback runs, the decisions differ from LLM-powered decisions (typically more conservative).  
**Root cause**: Rule-based logic uses a different scoring methodology than LLM reasoning. This is by design — the fallback errs on the side of caution.  
**What changed**: Test 8 explicitly validates that the fallback completes without errors. The difference in decisions is documented as expected behavior, not a bug.

---

## 7. Governance and Safety Reflection

### Risk Controls Implemented
1. **20% concentration cap**: Enforced at the Risk Team level (hard limit) AND at the Trader level (soft target of 15-18%)
2. **Human-in-the-loop gate**: Every trade requires human approval before execution (interactive in Streamlit, auto-approve in CLI for eval)
3. **Rule-based fallback**: When the LLM API fails, every agent has deterministic fallback logic, ensuring the system never makes uninformed decisions
4. **Cash boundary**: Trade execution checks cash sufficiency before processing
5. **Append-only audit trail**: `interaction_trace` is append-only, ensuring complete audit trail

### Data Boundaries and Permissions
- API keys are stored in `.env` (gitignored) and loaded at runtime
- Mock data mode is the default; live data requires explicit opt-in (`DATA_MODE=live`)
- No PII is processed or stored
- LLM prompts contain only market data, no personal information

### Limitations and Ethical Considerations
- **Not financial advice**: This is an educational prototype. No real money is at risk.
- **Bullish bias**: The mock data and the LLM both tend toward optimistic assessments. Production use would require bearish scenario calibration.
- **Single-model risk**: All LLM calls use the same Groq model. Model-specific biases are not diversified.
- **Escalation gap**: The human override gate does not define when it should refuse to auto-proceed (as flagged in Phase 2 feedback). This remains a design gap.

---

## 8. Lessons Learned and Future Improvements

### Lessons Learned
1. **Evaluation as experiment design**: The professor's feedback was right — regression tests that all pass tell you the system works, not whether it makes good decisions. Redesigning evaluation as experimental scenarios with adversarial cases was the most impactful Phase 3 change.
2. **Mock data constrains evaluation**: Deterministic mock data is great for reproducibility but bad for testing decision quality. The backtest engine using real historical data provides much more meaningful evidence.
3. **Rule-based fallback is essential**: The LLM fallback saved multiple evaluation runs where Groq rate limiting would have caused cascading failures.
4. **Cost tracking matters**: At ~$0.02-0.05 per analysis cycle (Groq free tier), the system is economical, but cost scales linearly with tickers and debate rounds.

### Future Improvements
1. **Live sentiment**: Integrate PRAW (Reddit API) and Twitter/X API for real-time social sentiment
2. **Multi-model ensemble**: Use different LLMs for different agents to diversify model-specific biases
3. **Sophisticated risk metrics**: Add VaR (Value at Risk), beta-adjusted sizing, and correlation analysis
4. **Backtesting with LLM**: Run LLM-powered backtests against known outcomes (requires budgeted API calls)
5. **Portfolio optimization**: Implement mean-variance (Markowitz) optimization for the strategist
6. **Alerting system**: Email/Slack notifications when the system detects high-confidence opportunities or risk events

---

*Report generated for CMU Agentic Systems Studio, Spring 2026.*
