"""Per-user and global daily budget guard."""
import time
from collections import defaultdict

from fastapi import HTTPException

# Pricing: GPT-4o-mini approximation
_INPUT_COST_PER_1K = 0.00015
_OUTPUT_COST_PER_1K = 0.0006


class CostGuard:
    def __init__(self, daily_budget_usd: float = 1.0, global_daily_budget_usd: float = 10.0):
        self.daily_budget_usd = daily_budget_usd
        self.global_daily_budget_usd = global_daily_budget_usd
        self._user_cost: dict[str, float] = defaultdict(float)
        self._global_cost: float = 0.0
        self._reset_day: str = time.strftime("%Y-%m-%d")

    def _reset_if_new_day(self):
        today = time.strftime("%Y-%m-%d")
        if today != self._reset_day:
            self._user_cost.clear()
            self._global_cost = 0.0
            self._reset_day = today

    def check_and_record(self, user_id: str, input_tokens: int, output_tokens: int):
        self._reset_if_new_day()
        cost = (input_tokens / 1000) * _INPUT_COST_PER_1K + (output_tokens / 1000) * _OUTPUT_COST_PER_1K

        if self._global_cost >= self.global_daily_budget_usd:
            raise HTTPException(503, "Global daily budget exhausted. Try tomorrow.")

        if self._user_cost[user_id] >= self.daily_budget_usd:
            raise HTTPException(402, f"Daily budget (${self.daily_budget_usd}) exceeded for your account.")

        self._user_cost[user_id] += cost
        self._global_cost += cost

    def stats(self) -> dict:
        self._reset_if_new_day()
        return {
            "global_cost_usd": round(self._global_cost, 4),
            "global_budget_usd": self.global_daily_budget_usd,
            "user_count": len(self._user_cost),
        }


cost_guard = CostGuard()
