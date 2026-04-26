"""
SQLite persistence layer for multi-day portfolio state.

Tables:
  - portfolio_state: cash, total_value snapshots per cycle
  - holdings: per-ticker positions
  - transactions: all executed trades
  - interaction_traces: agent interaction log
  - llm_call_logs: LLM cost/latency tracking
"""

import sqlite3
import json
import os
from datetime import datetime
from models import GlobalState, PortfolioState


DB_PATH = os.environ.get("PORTFOLIO_DB", "portfolio.db")


def _get_conn(db_path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None):
    """Create tables if they don't exist."""
    conn = _get_conn(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            cash REAL NOT NULL,
            total_value REAL NOT NULL,
            num_positions INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            shares INTEGER NOT NULL,
            avg_cost REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            cash_after REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS interaction_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            agent TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS llm_call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            caller TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms REAL NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0.0,
            error TEXT
        );
    """)
    conn.commit()
    conn.close()


def save_state(state: GlobalState, cycle_id: str, db_path: str = None):
    """Persist current GlobalState to SQLite."""
    conn = _get_conn(db_path)
    ts = datetime.now().isoformat()
    p = state.portfolio

    # Portfolio state snapshot
    total = p.cash + sum(
        s * p.avg_costs.get(t, 0) for t, s in p.holdings.items()
    )
    conn.execute(
        "INSERT INTO portfolio_state (cycle_id, timestamp, cash, total_value, num_positions) VALUES (?, ?, ?, ?, ?)",
        (cycle_id, ts, p.cash, total, len(p.holdings)))

    # Holdings
    for ticker, shares in p.holdings.items():
        conn.execute(
            "INSERT INTO holdings (cycle_id, ticker, shares, avg_cost, timestamp) VALUES (?, ?, ?, ?, ?)",
            (cycle_id, ticker, shares, p.avg_costs.get(ticker, 0), ts))

    # Transactions
    for tx in state.transaction_log:
        conn.execute(
            "INSERT INTO transactions (cycle_id, timestamp, ticker, action, quantity, price, total, cash_after) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cycle_id, tx["timestamp"], tx["ticker"], tx["action"],
             tx["quantity"], tx["price"], tx["total"], tx["cash_after"]))

    # Interaction traces
    for trace in state.interaction_trace:
        conn.execute(
            "INSERT INTO interaction_traces (cycle_id, timestamp, agent, action, details) VALUES (?, ?, ?, ?, ?)",
            (cycle_id, trace["timestamp"], trace["agent"], trace["action"],
             json.dumps(trace["details"])))

    conn.commit()
    conn.close()


def save_llm_logs(call_log: list[dict], cycle_id: str, db_path: str = None):
    """Persist LLM call log to SQLite."""
    conn = _get_conn(db_path)
    for entry in call_log:
        conn.execute(
            "INSERT INTO llm_call_logs (cycle_id, timestamp, caller, model, status, duration_ms, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cycle_id, entry["timestamp"], entry["caller"], entry["model"],
             entry["status"], entry["duration_ms"], entry["prompt_tokens"],
             entry["completion_tokens"], entry["total_tokens"],
             entry["estimated_cost_usd"], entry.get("error")))
    conn.commit()
    conn.close()


def load_latest_state(db_path: str = None) -> dict | None:
    """Load the most recent portfolio state for resuming."""
    conn = _get_conn(db_path)

    row = conn.execute(
        "SELECT * FROM portfolio_state ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        conn.close()
        return None

    cycle_id = row["cycle_id"]

    # Get holdings for that cycle
    holdings_rows = conn.execute(
        "SELECT * FROM holdings WHERE cycle_id = ?", (cycle_id,)).fetchall()
    holdings = {r["ticker"]: r["shares"] for r in holdings_rows}
    avg_costs = {r["ticker"]: r["avg_cost"] for r in holdings_rows}

    conn.close()
    return {
        "cycle_id": cycle_id,
        "cash": row["cash"],
        "total_value": row["total_value"],
        "holdings": holdings,
        "avg_costs": avg_costs,
    }


def get_transaction_history(limit: int = 100, db_path: str = None) -> list[dict]:
    """Get recent transaction history."""
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_llm_cost_summary(db_path: str = None) -> dict:
    """Aggregate LLM cost/latency metrics across all cycles."""
    conn = _get_conn(db_path)

    rows = conn.execute(
        "SELECT * FROM llm_call_logs ORDER BY id DESC").fetchall()
    conn.close()

    if not rows:
        return {"total_calls": 0, "total_cost_usd": 0, "avg_latency_ms": 0}

    total_cost = sum(r["estimated_cost_usd"] for r in rows)
    latencies = [r["duration_ms"] for r in rows if r["status"] == "SUCCESS"]

    return {
        "total_calls": len(rows),
        "successful": sum(1 for r in rows if r["status"] == "SUCCESS"),
        "failed": sum(1 for r in rows if r["status"] == "ERROR"),
        "total_cost_usd": round(total_cost, 4),
        "total_tokens": sum(r["total_tokens"] for r in rows),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
    }
