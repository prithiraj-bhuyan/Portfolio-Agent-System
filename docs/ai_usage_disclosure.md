# AI Usage Disclosure

**Project**: AI-Powered Agentic Portfolio Management System  
**Course**: CMU Agentic Systems Studio — Spring 2026  
**Team**: Raj Bhuyan, Sanath Mahesh Kumar, Mahir Nagersheth

---

## AI Tools Used in This Project

### 1. Groq API (llama-3.3-70b-versatile) — Core System Component

**Purpose**: Primary LLM powering all agent reasoning within the portfolio management system.

**Usage**:
- Fundamental Analyst: Analyzes company financials and generates signal recommendations
- Technical Analyst: Interprets price patterns and technical indicators
- Bullish/Bearish Researchers: Construct investment arguments in multi-round debate
- Debate Facilitator: Synthesizes bull/bear arguments into a prevailing view
- Trader Agent: Proposes trade actions with position sizing
- LLM Judge (evaluation): Assesses reasoning quality of agent decisions

**How it works**: Each agent sends a structured system prompt + user prompt to the Groq API. The response is parsed as JSON. If the LLM call fails or returns malformed data, every agent falls back to deterministic rule-based logic.

**Transparency**: All LLM calls are logged with timing, token usage, and cost estimates. The full call log is available in `sample_runs/llm_metrics.json` and the CLASSic Report.

### 2. GitHub Copilot / AI Coding Assistants

**Purpose**: Code generation assistance during development.

**Usage**:
- Boilerplate code generation (dataclass definitions, Streamlit layout)
- Debugging assistance for LangGraph conditional edges
- Documentation drafting and formatting

**What was reviewed**: All AI-generated code was reviewed, tested, and modified by team members. No code was used verbatim without understanding and verification.

### 3. ChatGPT / Claude — Research and Planning

**Purpose**: Research assistance for architecture design and evaluation methodology.

**Usage**:
- Researching LangGraph patterns and best practices
- Understanding CLASSic evaluation framework components
- Drafting evaluation scenario descriptions
- Reviewing financial analysis methodology (RSI, MACD, Sharpe ratio)

**What was adapted**: Research outputs informed our design decisions but were not copied directly. All architecture choices reflect our specific requirements.

---

## Boundary: AI-Assisted vs. Human-Written

| Component | AI Assistance Level | Human Contribution |
|-----------|--------------------|--------------------|
| Architecture design | Low — brainstorming only | Full design, role definitions, conditional edges |
| Agent implementations | Medium — boilerplate help | Logic design, fallback rules, prompt engineering |
| Evaluation framework | Low — CLASSic research | Scenario design, threshold selection, analysis |
| Streamlit dashboard | Medium — layout help | Tab design, integration logic, UX decisions |
| Backtest engine | Low | Full implementation of rule-based strategy |
| Documentation | Medium — drafting aid | Content decisions, accuracy verification |
| Risk controls | None | Full design of concentration caps, fallbacks |

---

*Disclosure prepared per course policy requirements, Spring 2026.*
