# src/composite_scoring.py - Composite scoring experiments
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from ..core.config import get_config_value

@dataclass
class ScoringResult:
    """Result of composite scoring"""
    hybrid_score: float
    ce_score: Optional[float]
    composite_score: float
    strategy: str
    alpha: float

class CompositeScorer:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load composite scoring configuration"""
        return {
            "enabled": get_config_value("reranker.composite_scoring.enabled", False),
            "alpha": get_config_value("reranker.composite_scoring.alpha", 0.8),
            "strategies": get_config_value("reranker.composite_scoring.strategies", [])
        }

    def calculate_composite_score(self,
                                hybrid_score: float,
                                ce_score: Optional[float],
                                strategy: str = "default",
                                alpha: Optional[float] = None) -> ScoringResult:
        """Calculate composite score using specified strategy"""

        if not self.config["enabled"] or ce_score is None:
            # Fallback to hybrid score only
            return ScoringResult(
                hybrid_score=hybrid_score,
                ce_score=ce_score,
                composite_score=hybrid_score,
                strategy="hybrid_only",
                alpha=0.0
            )

        # Get strategy configuration
        strategy_config = self._get_strategy_config(strategy)
        effective_alpha = alpha if alpha is not None else strategy_config["alpha"]

        # Calculate composite score
        composite_score = effective_alpha * ce_score + (1 - effective_alpha) * hybrid_score

        return ScoringResult(
            hybrid_score=hybrid_score,
            ce_score=ce_score,
            composite_score=composite_score,
            strategy=strategy,
            alpha=effective_alpha
        )

    def _get_strategy_config(self, strategy: str) -> Dict[str, Any]:
        """Get configuration for scoring strategy"""
        # Find strategy in config
        for s in self.config["strategies"]:
            if s["name"] == strategy:
                return s

        # Default strategy
        return {
            "name": strategy,
            "alpha": self.config["alpha"]
        }

    def get_available_strategies(self) -> List[str]:
        """Get list of available scoring strategies"""
        strategies = ["hybrid_only"]  # Always available
        if self.config["enabled"]:
            strategies.extend([s["name"] for s in self.config["strategies"]])
        return strategies

    def experiment_with_strategies(self,
                                 hybrid_score: float,
                                 ce_score: Optional[float]) -> Dict[str, ScoringResult]:
        """Run experiments with all available strategies"""
        results = {}

        for strategy in self.get_available_strategies():
            results[strategy] = self.calculate_composite_score(
                hybrid_score, ce_score, strategy
            )

        return results

    def normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalize scores to 0-1 range using min-max normalization"""
        if not scores:
            return scores

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [1.0] * len(scores)

        return [(s - min_score) / (max_score - min_score) for s in scores]

    def rank_by_composite(self,
                         candidates: List[Dict[str, Any]],
                         strategy: str = "default") -> List[Dict[str, Any]]:
        """Rank candidates by composite score"""
        if not candidates:
            return candidates

        # Calculate composite scores for all candidates
        scored_candidates = []
        for candidate in candidates:
            hybrid_score = candidate.get("hybrid_score", 0.0)
            ce_score = candidate.get("ce_score")

            result = self.calculate_composite_score(
                hybrid_score, ce_score, strategy
            )

            scored_candidate = candidate.copy()
            scored_candidate["composite_score"] = result.composite_score
            scored_candidate["scoring_strategy"] = result.strategy
            scored_candidate["scoring_alpha"] = result.alpha

            scored_candidates.append(scored_candidate)

        # Sort by composite score (descending)
        scored_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        return scored_candidates

# Global composite scorer instance
composite_scorer = CompositeScorer()

def calculate_final_score(hybrid_score: float,
                         ce_score: Optional[float],
                         strategy: str = "default") -> float:
    """Calculate final score using composite scoring"""
    result = composite_scorer.calculate_composite_score(
        hybrid_score, ce_score, strategy
    )
    return result.composite_score

def get_scoring_strategies() -> List[str]:
    """Get available scoring strategies"""
    return composite_scorer.get_available_strategies()

def experiment_scoring(hybrid_score: float, ce_score: Optional[float]) -> Dict[str, ScoringResult]:
    """Run scoring experiments with all strategies"""
    return composite_scorer.experiment_with_strategies(hybrid_score, ce_score)
