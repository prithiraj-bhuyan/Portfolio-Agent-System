"""
Streamlit Dashboard — Phase 3 Final Artifact

Interactive web interface for the Agentic Portfolio Management System.
5 tabs: Portfolio Overview | Agent Reasoning | Transaction Log | Human Gate | CLASSic Report

Run: streamlit run dashboard.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import json
import os
import time
from datetime import datetime

# Must be first Streamlit call
st.set_page_config(
    page_title="Agentic Portfolio Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ──
from models import GlobalState, TradeAction
from orchestrator import Orchestrator
from tools import MarketDataTool
from llm_interface import get_llm_metrics, reset_llm_log


# ═══════════════════════════════════════════════════════════════════
#  Custom CSS
# ═══════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
    }
    .stage-card {
        border-left: 4px solid #1f77b4;
        padding: 0.8rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
        border-radius: 0 8px 8px 0;
    }
    .signal-buy { color: #28a745; font-weight: bold; }
    .signal-sell { color: #dc3545; font-weight: bold; }
    .signal-hold { color: #ffc107; font-weight: bold; }
    .status-approved { color: #28a745; }
    .status-rejected { color: #dc3545; }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  Sidebar
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    available_tickers = ["AAPL", "ADBE", "MSFT", "AMZN", "NVDA"]
    selected_tickers = st.multiselect(
        "Watchlist",
        available_tickers,
        default=["AAPL", "ADBE", "MSFT"],
        help="Select tickers to analyze",
    )

    initial_cash = st.number_input(
        "Initial Cash ($)",
        min_value=1000,
        max_value=1_000_000,
        value=100_000,
        step=10_000,
    )

    st.markdown("---")

    # Human gate mode
    human_gate_mode = st.radio(
        "Human Approval Mode",
        ["Auto-Approve", "Interactive"],
        help="Interactive mode lets you approve/reject each trade",
    )

    st.markdown("---")
    st.markdown("### 📈 About")
    st.markdown(
        "**Agentic Portfolio Manager**\n\n"
        "13 AI agents analyze stocks through a 7-stage pipeline "
        "with human-in-the-loop approval.\n\n"
        "*Phase 3 — CMU Agentic Systems Studio*"
    )


# ═══════════════════════════════════════════════════════════════════
#  Persistence helpers
# ═══════════════════════════════════════════════════════════════════

CACHE_PATH = "sample_runs/dashboard_cache.json"

def _save_cache(results, portfolio):
    """Save cycle results + portfolio snapshot to JSON for refresh survival."""
    os.makedirs("sample_runs", exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump({
            "results": results,
            "portfolio": {
                "cash": portfolio.cash,
                "holdings": dict(portfolio.holdings),
                "avg_costs": dict(portfolio.avg_costs),
            },
            "ts": datetime.now().isoformat(),
        }, f, default=str)

def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return None

def _restore_orch(cash):
    """Try to restore orchestrator from SQLite persistence."""
    try:
        from persistence import load_latest_state, init_db
        init_db()
        s = load_latest_state()
        if s and s["holdings"]:
            o = Orchestrator(initial_cash=cash)
            o.state.portfolio.cash = s["cash"]
            o.state.portfolio.holdings = s["holdings"]
            o.state.portfolio.avg_costs = s["avg_costs"]
            return o
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════
#  Session State — restore on refresh
# ═══════════════════════════════════════════════════════════════════

if "orch" not in st.session_state:
    restored = _restore_orch(initial_cash)
    st.session_state.orch = restored if restored else None
if "results" not in st.session_state:
    cached = _load_cache()
    st.session_state.results = cached.get("results") if cached else None
if "cycle_count" not in st.session_state:
    st.session_state.cycle_count = 0


# ═══════════════════════════════════════════════════════════════════
#  Run Cycle
# ═══════════════════════════════════════════════════════════════════

st.markdown('<div class="main-header">📊 Agentic Portfolio Management System</div>',
            unsafe_allow_html=True)
st.markdown("*LangGraph + Groq (llama-3.3-70b) — 13 agents, 7-stage pipeline*")

col_run, col_reset = st.columns([1, 1])
with col_run:
    run_clicked = st.button("🚀 Run Analysis Cycle", type="primary",
                             use_container_width=True)
with col_reset:
    reset_clicked = st.button("🔄 Reset Portfolio", use_container_width=True)

if reset_clicked:
    st.session_state.orch = None
    st.session_state.results = None
    st.session_state.cycle_count = 0
    reset_llm_log()
    for fp in [CACHE_PATH, "portfolio.db"]:
        if os.path.exists(fp):
            os.remove(fp)
    st.rerun()

if run_clicked and selected_tickers:
    interactive = human_gate_mode == "Interactive"
    with st.spinner("Running analysis pipeline... (this may take 30-60 seconds)"):
        if st.session_state.orch is None:
            st.session_state.orch = Orchestrator(
                initial_cash=initial_cash,
                watchlist=selected_tickers,
                interactive=interactive,
            )
        else:
            st.session_state.orch.interactive = interactive
        reset_llm_log()
        results = st.session_state.orch.run_cycle(selected_tickers)
        st.session_state.results = results
        st.session_state.cycle_count += 1
        _save_cache(results, st.session_state.orch.state.portfolio)

    if interactive:
        pend = {t: d for t, d in st.session_state.orch.state.final_decisions.items()
                if not d.approved_by_human and d.action != TradeAction.HOLD}
        if pend:
            st.warning(f"⏳ {len(pend)} trade(s) pending approval — go to **Human Approval Gate** tab")
        else:
            st.success("✅ Analysis complete — no actionable trades proposed.")
    else:
        st.success(f"✅ Cycle #{st.session_state.cycle_count} complete!")


# ═══════════════════════════════════════════════════════════════════
#  Tabs
# ═══════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Portfolio Overview",
    "🤖 Agent Reasoning",
    "📋 Transaction Log",
    "👤 Human Approval Gate",
    "📈 CLASSic Report",
])


# ── Tab 1: Portfolio Overview ─────────────────────────────────────
with tab1:
    if st.session_state.orch:
        orch = st.session_state.orch
        p = orch.state.portfolio
        mkt = MarketDataTool()

        # Calculate totals
        total_invested = 0
        total_value = p.cash
        position_data = []
        for t, s in p.holdings.items():
            price = mkt.get_price_history(t)["current_price"]
            mv = s * price
            cost = s * p.avg_costs.get(t, 0)
            total_value += mv
            total_invested += cost
            position_data.append({
                "Ticker": t,
                "Shares": s,
                "Avg Cost": f"${p.avg_costs.get(t, 0):.2f}",
                "Price": f"${price:.2f}",
                "Market Value": f"${mv:,.2f}",
                "P&L": f"${mv - cost:,.2f}",
                "P&L %": f"{(price / p.avg_costs.get(t, 1) - 1) * 100:.1f}%",
                "Weight": f"{mv / total_value * 100:.1f}%",
            })

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Value", f"${total_value:,.2f}",
                       f"{(total_value / initial_cash - 1) * 100:+.2f}%")
        with col2:
            st.metric("Cash", f"${p.cash:,.2f}",
                       f"{p.cash / total_value * 100:.1f}% of portfolio")
        with col3:
            pnl = total_value - initial_cash
            st.metric("Total P&L", f"${pnl:,.2f}",
                       f"{pnl / initial_cash * 100:+.2f}%")
        with col4:
            st.metric("Positions", len(p.holdings),
                       f"{len(orch.state.transaction_log)} trades")

        # Holdings table
        if position_data:
            st.markdown("### Holdings")
            st.dataframe(position_data, use_container_width=True, hide_index=True)

            # Allocation chart
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                labels = [d["Ticker"] for d in position_data] + ["Cash"]
                values = [float(d["Market Value"].replace("$", "").replace(",", ""))
                          for d in position_data] + [p.cash]
                fig = go.Figure(data=[go.Pie(
                    labels=labels, values=values,
                    hole=0.4, textinfo="label+percent",
                    marker=dict(colors=px.colors.qualitative.Set2),
                )])
                fig.update_layout(title="Portfolio Allocation", height=400,
                                  margin=dict(t=50, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)

            with col_chart2:
                if orch.state.transaction_log:
                    cash_over_time = [initial_cash]
                    for tx in orch.state.transaction_log:
                        cash_over_time.append(tx["cash_after"])
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        y=cash_over_time, mode="lines+markers",
                        name="Cash", line=dict(color="#1f77b4", width=2),
                    ))
                    fig2.update_layout(title="Cash After Each Trade", height=400,
                                       yaxis_title="Cash ($)",
                                       xaxis_title="Trade #",
                                       margin=dict(t=50, b=0))
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No positions yet. Run an analysis cycle to see results.")
    else:
        st.info("👆 Configure your watchlist and click **Run Analysis Cycle** to start.")


# ── Tab 2: Agent Reasoning ────────────────────────────────────────
with tab2:
    if st.session_state.results:
        results = st.session_state.results

        for ticker, data in results["results"].items():
            st.markdown(f"### {ticker}")
            st.markdown(f"**Outcome:** `{data['outcome']}`")

            for stage in data["stages"]:
                stage_name = stage["stage"]

                if stage_name == "analysts":
                    with st.expander(f"📊 Stage 1: Analyst Reports", expanded=True):
                        cols = st.columns(4)
                        for i, (name, report) in enumerate(stage.get("results", {}).items()):
                            with cols[i]:
                                signal = report["signal"]
                                color = ("#28a745" if "BUY" in signal
                                         else "#dc3545" if "SELL" in signal
                                         else "#ffc107")
                                st.markdown(f"**{name}**")
                                st.markdown(f"<span style='color:{color};font-size:1.2em;font-weight:bold'>"
                                            f"{signal}</span>", unsafe_allow_html=True)
                                st.caption(f"Confidence: {report['confidence']:.2f}")
                                st.caption(report["summary"][:100] + "...")

                elif stage_name == "debate":
                    with st.expander("🔍 Stage 2: Bull/Bear Debate"):
                        view = stage.get("view", "N/A")
                        color = ("#28a745" if "BUY" in view
                                 else "#dc3545" if "SELL" in view
                                 else "#ffc107")
                        st.markdown(f"**Prevailing View:** "
                                    f"<span style='color:{color};font-weight:bold'>"
                                    f"{view}</span> (conf={stage.get('confidence', 0):.2f})",
                                    unsafe_allow_html=True)
                        st.markdown(stage.get("summary", ""))

                elif stage_name == "trader":
                    with st.expander("💰 Stage 3: Trade Proposal"):
                        st.markdown(f"**Action:** {stage.get('action', 'N/A')} "
                                    f"{stage.get('quantity', 0)} shares")
                        st.markdown(f"**Rationale:** {stage.get('rationale', 'N/A')}")

                elif stage_name == "risk":
                    with st.expander("⚠️ Stage 4: Risk Assessment"):
                        risk_level = stage.get("risk_level", "N/A")
                        approved = stage.get("approved", False)
                        color = "#28a745" if approved else "#dc3545"
                        st.markdown(f"**Risk Level:** {risk_level}  |  "
                                    f"**Approved:** <span style='color:{color}'>"
                                    f"{'✓ Yes' if approved else '✗ No'}</span>",
                                    unsafe_allow_html=True)
                        if stage.get("concerns"):
                            for c in stage["concerns"]:
                                st.warning(c)
                        if stage.get("adjustments"):
                            st.json(stage["adjustments"])

                elif stage_name == "fund_manager":
                    with st.expander("👔 Stage 5: Fund Manager Decision"):
                        st.markdown(f"**Decision:** {stage.get('action', 'N/A')} "
                                    f"{stage.get('quantity', 0)} shares")
                        st.markdown(f"**Rationale:** {stage.get('rationale', 'N/A')}")

                elif stage_name == "human_gate":
                    with st.expander("👤 Stage 6: Human Approval"):
                        approved = stage.get("approved", False)
                        st.markdown(f"{'✅ Approved' if approved else '❌ Rejected'}")

                elif stage_name == "execute":
                    with st.expander("✅ Stage 7: Execution"):
                        st.markdown(f"**Result:** {stage.get('outcome', 'N/A')}")

            st.markdown("---")
    else:
        st.info("Run an analysis cycle to see agent reasoning traces.")


# ── Tab 3: Transaction Log ────────────────────────────────────────
with tab3:
    if st.session_state.orch and st.session_state.orch.state.transaction_log:
        tx_log = st.session_state.orch.state.transaction_log
        st.markdown(f"### Transaction History ({len(tx_log)} trades)")

        tx_display = []
        for tx in tx_log:
            tx_display.append({
                "Time": tx["timestamp"][:19],
                "Action": tx["action"],
                "Ticker": tx["ticker"],
                "Quantity": tx["quantity"],
                "Price": f"${tx['price']:.2f}",
                "Total": f"${tx['total']:,.2f}",
                "Cash After": f"${tx['cash_after']:,.2f}",
            })
        st.dataframe(tx_display, use_container_width=True, hide_index=True)

        # Interaction trace
        with st.expander("📜 Full Interaction Trace (JSON)"):
            st.json(st.session_state.orch.state.interaction_trace)
    else:
        st.info("No transactions yet.")


# ── Tab 4: Human Approval Gate ────────────────────────────────────
with tab4:
    st.markdown("### 👤 Human-in-the-Loop Approval Gate")

    if human_gate_mode == "Auto-Approve":
        st.info("ℹ️ **Auto-Approve mode is active.** "
                "Switch to **Interactive** mode in the sidebar to manually "
                "approve or reject trades.")
        st.markdown(
            "In Interactive mode, you would see each pending trade with:\n"
            "- Full analyst reports and debate summary\n"
            "- Risk assessment with concerns\n"
            "- Fund manager recommendation\n"
            "- **Approve** / **Reject** buttons\n\n"
            "This ensures human oversight before any trade execution."
        )
    else:
        st.markdown(
            "**Interactive mode active.** Pending trades will appear here "
            "for your review before execution."
        )
        if st.session_state.orch:
            orch = st.session_state.orch
            decisions = orch.state.final_decisions
            res = st.session_state.results
            any_pending = False

            if decisions:
                for ticker, dec in decisions.items():
                    if dec.action == TradeAction.HOLD:
                        continue

                    # Check if already executed
                    already_done = any(
                        tx["ticker"] == ticker for tx in orch.state.transaction_log
                    )

                    if already_done or dec.approved_by_human:
                        status = "✅ Executed"
                        status_color = "#28a745"
                    else:
                        status = "⏳ Pending"
                        status_color = "#ffc107"
                        any_pending = True

                    st.markdown(f"---")
                    st.markdown(
                        f"#### {ticker}: {dec.action.value} {dec.quantity} shares "
                        f"&nbsp; <span style='color:{status_color};font-weight:600;'>{status}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Rationale:** {dec.rationale}")

                    # Show analyst context if available
                    if res and ticker in res.get("results", {}):
                        stages = res["results"][ticker].get("stages", [])
                        a_stage = next((s for s in stages if s["stage"] == "analysts"), None)
                        if a_stage:
                            sigs = " · ".join(
                                f"**{name}**: {info['signal']}" 
                                for name, info in a_stage.get("results", {}).items()
                            )
                            st.caption(f"Analyst signals: {sigs}")
                        r_stage = next((s for s in stages if s["stage"] == "risk"), None)
                        if r_stage:
                            for c in r_stage.get("concerns", []):
                                st.warning(f"⚠️ {c}")

                    if not already_done:
                        col_approve, col_reject = st.columns(2)
                        with col_approve:
                            if st.button(f"✅ Approve {ticker}", key=f"approve_{ticker}",
                                         type="primary", use_container_width=True):
                                outcome = orch.execute_pending_trade(ticker)
                                _save_cache(res, orch.state.portfolio)
                                st.success(f"Trade executed: {outcome}")
                                st.rerun()
                        with col_reject:
                            if st.button(f"❌ Reject {ticker}", key=f"reject_{ticker}",
                                         use_container_width=True):
                                orch.reject_pending_trade(ticker)
                                _save_cache(res, orch.state.portfolio)
                                st.error(f"Trade rejected for {ticker}")
                                st.rerun()

                if not any_pending:
                    st.success("All trades have been processed.")
            else:
                st.info("No pending decisions. Run an analysis cycle first.")
        else:
            st.info("Initialize the system by running an analysis cycle.")


# ── Tab 5: CLASSic Report ─────────────────────────────────────────
with tab5:
    st.markdown("### 📈 CLASSic Evaluation Report")
    st.markdown("*Cost · Latency · Accuracy · Security · Severity*")

    metrics = get_llm_metrics()

    if metrics["total_calls"] > 0:
        # Cost
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cost", f"${metrics['total_cost_usd']:.4f}")
            st.metric("Total Tokens", f"{metrics['total_tokens']:,}")
        with col2:
            st.metric("Avg Latency", f"{metrics['avg_latency_ms']:.0f} ms")
            st.metric("P95 Latency", f"{metrics['p95_latency_ms']:.0f} ms")
        with col3:
            st.metric("Successful Calls", metrics['successful_calls'])
            st.metric("Failed Calls", metrics['failed_calls'])

        # Latency chart
        if metrics["calls"]:
            successful_calls = [c for c in metrics["calls"] if c["status"] == "SUCCESS"]
            if successful_calls:
                fig_lat = go.Figure()
                fig_lat.add_trace(go.Bar(
                    x=[f"{c['caller']}" for c in successful_calls],
                    y=[c["duration_ms"] for c in successful_calls],
                    marker_color=px.colors.qualitative.Set2,
                    text=[f"{c['duration_ms']:.0f}ms" for c in successful_calls],
                    textposition="auto",
                ))
                fig_lat.update_layout(
                    title="Latency by Agent (ms)",
                    xaxis_title="Agent", yaxis_title="Duration (ms)",
                    height=400,
                )
                st.plotly_chart(fig_lat, use_container_width=True)

            # Token usage
            if successful_calls:
                fig_tok = go.Figure()
                fig_tok.add_trace(go.Bar(
                    name="Prompt Tokens",
                    x=[c["caller"] for c in successful_calls],
                    y=[c["prompt_tokens"] for c in successful_calls],
                    marker_color="#1f77b4",
                ))
                fig_tok.add_trace(go.Bar(
                    name="Completion Tokens",
                    x=[c["caller"] for c in successful_calls],
                    y=[c["completion_tokens"] for c in successful_calls],
                    marker_color="#ff7f0e",
                ))
                fig_tok.update_layout(
                    title="Token Usage by Agent",
                    barmode="stack", height=400,
                )
                st.plotly_chart(fig_tok, use_container_width=True)

        # Raw data
        with st.expander("📋 Raw LLM Call Log"):
            st.json(metrics["calls"])

    else:
        st.info("Run an analysis cycle to see LLM cost and latency metrics.")

    # Load saved CLASSic report if available
    classic_path = "evaluation/evidence/classic_report.json"
    if os.path.exists(classic_path):
        st.markdown("---")
        st.markdown("### 📊 Full CLASSic Evaluation Report")
        with open(classic_path) as f:
            classic_data = json.load(f)

        with st.expander("Accuracy by Category"):
            if "accuracy" in classic_data:
                st.json(classic_data["accuracy"])

        with st.expander("Severity Classification"):
            if "severity" in classic_data:
                st.json(classic_data["severity"])

        with st.expander("Security Checks"):
            if "security" in classic_data:
                for check, passed in classic_data["security"].items():
                    st.markdown(f"{'✅' if passed else '❌'} {check}")


# ═══════════════════════════════════════════════════════════════════
#  Footer
# ═══════════════════════════════════════════════════════════════════
st.markdown("---")
st.caption("Agentic Portfolio Management System — Phase 3 | "
           "CMU Agentic Systems Studio Spring 2026 | "
           "Team: Raj Bhuyan, Sanath Mahesh Kumar, Mahir Nagersheth")
