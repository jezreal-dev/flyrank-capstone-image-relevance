"""Cost and token attribution tracking with an enforceable budget guard."""
import os
import sqlite3
import time
from typing import Dict, Any
from app.core.database import get_db_connection

# Default token pricing (Gemini 1.5 Flash reference: $0.075 / 1M prompt, $0.30 / 1M completion)
PROMPT_COST_PER_MILLION = 0.075
COMPLETION_COST_PER_MILLION = 0.30

class BudgetExceededError(Exception):
    """Raised when cumulative AI spend surpasses the configured budget ceiling."""
    pass

class CostTracker:
    def __init__(self, budget_limit_usd: float | None = None):
        self.budget_limit_usd = budget_limit_usd or float(os.getenv("COST_BUDGET_LIMIT_USD", "10.00"))

    def get_total_spend(self, db_conn: sqlite3.Connection | None = None) -> float:
        query = "SELECT COALESCE(SUM(cost_usd), 0.0) as total FROM cost_log"
        if db_conn:
            row = db_conn.execute(query).fetchone()
            return float(row["total"])
        with get_db_connection() as conn:
            row = conn.execute(query).fetchone()
            return float(row["total"])

    def record_call(
        self,
        operation: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float = 0.0,
        is_free_tier: bool = True
    ) -> Dict[str, Any]:
        """Records an individual AI call with token and cost attribution."""
        with get_db_connection() as conn:
            current_spend = self.get_total_spend(conn)
            if current_spend >= self.budget_limit_usd:
                raise BudgetExceededError(
                    f"Cumulative AI spend (${current_spend:.4f}) exceeded budget ceiling (${self.budget_limit_usd:.2f})"
                )

            # Compute theoretical cost
            cost_usd = 0.0
            if not is_free_tier:
                prompt_cost = (input_tokens / 1_000_000.0) * PROMPT_COST_PER_MILLION
                completion_cost = (output_tokens / 1_000_000.0) * COMPLETION_COST_PER_MILLION
                cost_usd = round(prompt_cost + completion_cost, 6)

            cursor = conn.execute(
                """
                INSERT INTO cost_log (operation, model_name, input_tokens, output_tokens, cost_usd, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (operation, model_name, input_tokens, output_tokens, cost_usd, latency_ms)
            )
            conn.commit()
            log_id = cursor.lastrowid

            return {
                "id": log_id,
                "operation": operation,
                "model_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms
            }

    def get_summary(self) -> Dict[str, Any]:
        with get_db_connection() as conn:
            summary = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_calls,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost_usd), 0.0) as total_cost_usd
                FROM cost_log
                """
            ).fetchone()

            by_op = conn.execute(
                """
                SELECT operation, COUNT(*) as count, SUM(cost_usd) as cost, SUM(input_tokens + output_tokens) as tokens
                FROM cost_log GROUP BY operation
                """
            ).fetchall()

            return {
                "budget_limit_usd": self.budget_limit_usd,
                "total_calls": summary["total_calls"],
                "total_input_tokens": summary["total_input_tokens"],
                "total_output_tokens": summary["total_output_tokens"],
                "total_cost_usd": round(summary["total_cost_usd"], 6),
                "remaining_budget_usd": round(max(0.0, self.budget_limit_usd - summary["total_cost_usd"]), 6),
                "breakdown_by_operation": [dict(r) for r in by_op]
            }

tracker = CostTracker()
