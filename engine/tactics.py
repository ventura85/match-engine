from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Tactic:
    style: str = "balanced"  # 'defensive' | 'balanced' | 'attacking'

    @property
    def action_rate_mod(self) -> float:
        return {"defensive": 0.92, "balanced": 1.00, "attacking": 1.08}.get(self.style, 1.0)

    @property
    def shot_prob_mod(self) -> float:
        return {"defensive": 0.95, "balanced": 1.00, "attacking": 1.08}.get(self.style, 1.0)

    @property
    def goal_prob_mod(self) -> float:
        return {"defensive": 0.95, "balanced": 1.00, "attacking": 1.06}.get(self.style, 1.0)
