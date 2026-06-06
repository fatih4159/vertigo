"""Self-improvement analyzer.

Periodically analyses agent performance data, identifies patterns in failures
and inefficiencies, and stores an improvement report in long-term memory.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Iteration, ToolCall
from app.storage.repositories import IterationRepository, MemoryRepository, ToolCallRepository


@dataclass
class ToolPerformance:
    name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    common_errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        return d


@dataclass
class ImprovementReport:
    agent_id: str
    generated_at: str
    iterations_analyzed: int
    tool_performance: List[ToolPerformance] = field(default_factory=list)
    common_failure_patterns: List[str] = field(default_factory=list)
    efficiency_score: float = 0.0  # 0.0-1.0
    recommendations: List[str] = field(default_factory=list)
    worst_tools: List[str] = field(default_factory=list)
    best_tools: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "generated_at": self.generated_at,
            "iterations_analyzed": self.iterations_analyzed,
            "tool_performance": [t.to_dict() for t in self.tool_performance],
            "common_failure_patterns": self.common_failure_patterns,
            "efficiency_score": self.efficiency_score,
            "recommendations": self.recommendations,
            "worst_tools": self.worst_tools,
            "best_tools": self.best_tools,
        }

    def to_summary_text(self) -> str:
        lines = [
            f"Self-Improvement Report — {self.generated_at}",
            f"Analyzed {self.iterations_analyzed} iterations.",
            f"Efficiency score: {self.efficiency_score:.2%}",
            "",
        ]
        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")
        if self.worst_tools:
            lines.append(f"Worst performing tools: {', '.join(self.worst_tools)}")
        if self.best_tools:
            lines.append(f"Best performing tools: {', '.join(self.best_tools)}")
        return "\n".join(lines)


class SelfImprovementAnalyzer:
    """Analyses execution history and produces improvement reports."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    async def analyze(self, agent_id: str, limit: int = 200) -> ImprovementReport:
        """Run full analysis pipeline and store result in long-term memory."""
        logger.info(f"Running self-improvement analysis for agent {agent_id}")

        # Fetch recent iterations
        iter_repo = IterationRepository(self.db)
        iterations = await iter_repo.list_for_agent(agent_id, limit=limit, offset=0)

        # Fetch tool calls for these iterations
        tool_calls: List[ToolCall] = []
        tc_repo = ToolCallRepository(self.db)
        for it in iterations:
            calls = await tc_repo.list_for_iteration(it.id)
            tool_calls.extend(calls)

        report = self._build_report(agent_id, iterations, tool_calls)

        # Store in long-term memory
        mem_repo = MemoryRepository(self.db)
        await mem_repo.upsert(
            agent_id=agent_id,
            memory_type="long",
            key="self_improvement_report",
            content=report.to_summary_text(),
            metadata_json=report.to_dict(),
        )
        await self.db.commit()

        logger.info(
            f"Self-improvement analysis complete for {agent_id}. "
            f"Score: {report.efficiency_score:.2%}"
        )
        return report

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_report(
        self,
        agent_id: str,
        iterations: Sequence[Iteration],
        tool_calls: Sequence[ToolCall],
    ) -> ImprovementReport:
        report = ImprovementReport(
            agent_id=agent_id,
            generated_at=datetime.utcnow().isoformat(),
            iterations_analyzed=len(iterations),
        )

        if not iterations:
            report.recommendations.append("No iterations to analyze yet. Start the agent.")
            return report

        # --- Iteration stats ---
        status_counts: Counter[str] = Counter(it.status for it in iterations)
        success_rate = status_counts.get("success", 0) / max(1, len(iterations))
        report.efficiency_score = success_rate

        if success_rate < 0.3:
            report.common_failure_patterns.append(
                f"Very low iteration success rate: {success_rate:.0%}"
            )
            report.recommendations.append(
                "Review masterprompt — agent is failing most iterations. "
                "Consider simplifying the goal or providing more context."
            )
        elif success_rate < 0.6:
            report.recommendations.append(
                "Iteration success rate is moderate. Identify common failure reasons."
            )

        # --- Token efficiency ---
        token_counts = [it.tokens_used for it in iterations if it.tokens_used > 0]
        if token_counts:
            avg_tokens = sum(token_counts) / len(token_counts)
            if avg_tokens > 3000:
                report.recommendations.append(
                    f"High average token usage ({avg_tokens:.0f}/iter). "
                    "Consider compressing memory or tightening the planning prompt."
                )

        # --- Tool performance ---
        tool_stats: Dict[str, ToolPerformance] = {}
        tool_durations: Dict[str, List[float]] = defaultdict(list)
        tool_errors: Dict[str, List[str]] = defaultdict(list)

        for tc in tool_calls:
            if tc.tool_name not in tool_stats:
                tool_stats[tc.tool_name] = ToolPerformance(name=tc.tool_name)
            perf = tool_stats[tc.tool_name]
            perf.total_calls += 1
            if tc.success:
                perf.success_count += 1
            else:
                perf.failure_count += 1
                if tc.error_message:
                    tool_errors[tc.tool_name].append(tc.error_message[:100])
            tool_durations[tc.tool_name].append(tc.duration_ms)

        for name, perf in tool_stats.items():
            durs = tool_durations[name]
            perf.avg_duration_ms = sum(durs) / len(durs) if durs else 0.0
            errs = tool_errors[name]
            if errs:
                err_counter: Counter[str] = Counter(errs)
                perf.common_errors = [e for e, _ in err_counter.most_common(3)]
            report.tool_performance.append(perf)

        # Sort by success rate
        report.tool_performance.sort(key=lambda p: p.success_rate)
        report.worst_tools = [
            p.name for p in report.tool_performance if p.success_rate < 0.5 and p.total_calls >= 3
        ]
        report.best_tools = [
            p.name
            for p in sorted(report.tool_performance, key=lambda p: p.success_rate, reverse=True)
            if p.success_rate > 0.8 and p.total_calls >= 3
        ]

        for tool_name in report.worst_tools:
            report.recommendations.append(
                f"Tool '{tool_name}' has poor reliability. Consider regenerating it."
            )

        # Slow tools
        for perf in report.tool_performance:
            if perf.avg_duration_ms > 5000 and perf.total_calls >= 3:
                report.recommendations.append(
                    f"Tool '{perf.name}' is slow (avg {perf.avg_duration_ms:.0f}ms). "
                    "Check for timeouts or inefficient logic."
                )

        return report
