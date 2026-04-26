# 5-Minute Video Script — Phase 3 Demo

**Target Length**: 5:00 minutes  
**Format**: Screen recording + voiceover

---

## Shot List & Timing

### Opening (0:00 – 0:30) — Problem Statement
**Screen**: Title slide or architecture diagram  
**Script**:
> "We built an AI-powered portfolio management system that uses 13 autonomous agents to analyze stocks, debate investment theses, assess risk, and execute trades — all with human-in-the-loop approval. Unlike single-model systems, our multi-agent architecture provides transparent reasoning, checks and balances, and graceful degradation when AI fails."

---

### Architecture Overview (0:30 – 1:15) — System Design
**Screen**: Architecture diagram (`docs/Architecture Diagram.png`)  
**Script**:
> "Our system has two layers. Layer 1 is a 7-stage pipeline that runs for each stock ticker. Four analysts run in parallel — fundamental, technical, sentiment, and news. Their reports feed into a bull-bear debate where researchers argue for and against the investment. A facilitator picks the prevailing view. Then a trader proposes a trade, the risk team checks concentration limits, the fund manager approves, and finally the human gets the last word."

> "Layer 2 is the Portfolio Strategist that selects which tickers to analyze and monitors overall portfolio concentration."

> "We use LangGraph for orchestration with three conditional edges — the pipeline can short-circuit if the trader says HOLD, if the fund manager rejects, or if the human vetoes."

---

### Live Demo (1:15 – 3:00) — Streamlit Dashboard
**Screen**: `streamlit run dashboard.py`

**Actions**:
1. **(1:15)** Show the dashboard home screen, explain the sidebar configuration
2. **(1:30)** Select tickers: AAPL, ADBE, MSFT. Set cash to $100,000. Click "Run Analysis Cycle"
3. **(1:45)** Show **Portfolio Overview** tab: holdings table, allocation donut chart, cash-over-time chart
4. **(2:00)** Switch to **Agent Reasoning** tab: expand analyst reports for one ticker, show the debate summary, risk assessment, fund manager decision
5. **(2:20)** Switch to **Transaction Log** tab: show the executed trades
6. **(2:35)** Switch to **Human Approval Gate** tab: explain interactive approve/reject mode
7. **(2:45)** Switch to **CLASSic Report** tab: show cost, latency, token usage charts

**Script during demo**:
> "Here's our Streamlit dashboard — the biggest upgrade from Phase 2 where we only had CLI output. You can configure the watchlist and initial cash in the sidebar."

> "After running a cycle, the Portfolio Overview shows our holdings, P&L, and allocation in real time. Let me drill into the Agent Reasoning tab — you can see exactly what each analyst recommended, how the bull-bear debate resolved, and what the risk team flagged."

> "The CLASSic Report tab shows us the cost and latency of every LLM call — each cycle costs about 2-5 cents and takes about 30-60 seconds."

---

### Evidence & Evaluation (3:00 – 4:00)
**Screen**: Terminal running evaluation + CLASSic report

**Actions**:
1. **(3:00)** Run `python evaluation/eval_runner.py` — show 10 test scenarios running
2. **(3:20)** Highlight the 3 failure cases and how they were handled
3. **(3:35)** Show `evaluation/evidence/classic_report.json` — CLASSic metrics
4. **(3:45)** Run `python backtest.py` — show the 3 historical periods and results

**Script**:
> "For evaluation, we redesigned our tests as experiments rather than regression tests — as the professor recommended. We now have 10 scenarios including 3 documented failure cases and 3 adversarial cases."

> "The CLASSic framework gives us Cost, Latency, Accuracy, Security, and Severity metrics for every evaluation run."

> "Our backtest engine runs the system against three historical stress periods — COVID March 2020, the 2021-22 rate hike cycle, and the SVB crisis in Q1 2023. We compare our agent system against a simple buy-and-hold baseline using Sharpe ratio, max drawdown, and cumulative return."

---

### Failures & Lessons (4:00 – 4:40)
**Screen**: Failure analysis section of report / evidence files

**Script**:
> "Three key failures we found. First, the system has a bullish bias because our mock data skews positive. We addressed this by adding adversarial scenarios where news contradicts fundamentals."

> "Second, the risk team's only hard control is the 20% concentration cap. More sophisticated risk metrics like VaR and correlation analysis would be needed for production."

> "Third, when the LLM is unavailable, the rule-based fallback produces more conservative decisions. This is actually a feature — the fallback errs on the side of caution."

---

### Closing (4:40 – 5:00) — Key Contributions
**Screen**: Summary slide  
**Script**:
> "To summarize: we built a working multi-agent portfolio management system with transparent reasoning, multi-level risk controls, and human oversight. Our Phase 3 contributions include a Streamlit dashboard, CLASSic evaluation framework, historical backtesting, and a comprehensive evidence package. The system demonstrates that multi-agent architectures can provide better auditability and governance than single-model approaches."

> "Thank you."

---

## Recording Notes
- Use screen recording (OBS or QuickTime) with audio
- Resolution: 1920×1080
- Streamlit dashboard should be running at `localhost:8501`
- Have terminal ready for eval_runner.py and backtest.py
- Pre-run the backtest so yfinance data is cached (faster demo)
