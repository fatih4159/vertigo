"""Capability gap detector.

Analyses iteration failures, error patterns, and tool usage to identify
missing capabilities that would improve agent performance.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from loguru import logger

from app.database.models import Iteration, ToolCall


@dataclass
class CapabilityGap:
    """A detected missing capability."""

    name: str
    description: str
    evidence: List[str] = field(default_factory=list)
    suggested_tool_name: Optional[str] = None
    suggested_skill_name: Optional[str] = None
    priority: float = 0.0  # 0.0-1.0, higher = more urgent
    gap_type: str = "tool"  # "tool" | "skill" | "knowledge"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_tool_name": self.suggested_tool_name,
            "suggested_skill_name": self.suggested_skill_name,
            "priority": self.priority,
            "gap_type": self.gap_type,
        }


# Patterns that indicate a specific missing capability
_CAPABILITY_PATTERNS: List[tuple[str, str, str, str]] = [
    # (regex pattern, gap name, description, type)
    (
        r"(http|https|url|request|fetch|api.call|download)",
        "http_client",
        "Agent attempted HTTP requests but no HTTP tool is available",
        "tool",
    ),
    (
        r"(database|sql|query|sqlite|postgres|mysql)",
        "database_access",
        "Agent needs database query capability",
        "tool",
    ),
    (
        r"(image|screenshot|vision|ocr|pixel)",
        "image_processing",
        "Agent needs image processing or vision capability",
        "tool",
    ),
    (
        r"(email|smtp|send.mail|inbox)",
        "email_client",
        "Agent needs email sending/receiving capability",
        "tool",
    ),
    (
        r"(schedule|cron|timer|at.time|delay)",
        "task_scheduler",
        "Agent needs time-based task scheduling",
        "tool",
    ),
    (
        r"(search.web|google|bing|duckduckgo|web.search)",
        "web_search",
        "Agent needs web search capability",
        "tool",
    ),
    (
        r"(docker|container|compose|kubernetes)",
        "container_management",
        "Agent needs container management capability",
        "tool",
    ),
    (
        r"(refactor.large|codebase.analysis|architecture)",
        "code_architecture",
        "Agent needs a higher-level code architecture skill",
        "skill",
    ),
    (
        r"(test.coverage|unit.test|integration.test)",
        "comprehensive_testing",
        "Agent needs a comprehensive testing skill",
        "skill",
    ),
]


class CapabilityDetector:
    """Detects capability gaps from agent execution history."""

    def __init__(self, known_tool_names: Optional[List[str]] = None) -> None:
        self.known_tools: set[str] = set(known_tool_names or [])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_from_iterations(
        self,
        iterations: Sequence[Iteration],
        tool_calls: Sequence[ToolCall],
    ) -> List[CapabilityGap]:
        """
        Analyse a batch of iterations and their tool calls.
        Returns a deduplicated list of CapabilityGap objects sorted by priority.
        """
        gaps: Dict[str, CapabilityGap] = {}

        # 1. Analyse failed tool calls
        self._analyze_tool_failures(tool_calls, gaps)

        # 2. Analyse iteration error messages
        self._analyze_iteration_errors(iterations, gaps)

        # 3. Analyze tool usage patterns for missing tools
        self._analyze_usage_patterns(iterations, tool_calls, gaps)

        result = sorted(gaps.values(), key=lambda g: g.priority, reverse=True)
        logger.info(f"CapabilityDetector found {len(result)} capability gaps")
        return result

    def detect_from_error_message(self, error: str) -> List[CapabilityGap]:
        """Quick detection from a single error string."""
        gaps: Dict[str, CapabilityGap] = {}
        self._match_patterns(error.lower(), "error_message", gaps)
        return list(gaps.values())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _analyze_tool_failures(
        self, tool_calls: Sequence[ToolCall], gaps: Dict[str, CapabilityGap]
    ) -> None:
        failure_counts: Counter[str] = Counter()
        error_texts: Dict[str, List[str]] = defaultdict(list)

        for tc in tool_calls:
            if not tc.success:
                failure_counts[tc.tool_name] += 1
                if tc.error_message:
                    error_texts[tc.tool_name].append(tc.error_message)

        for tool_name, count in failure_counts.most_common(10):
            if count >= 2:
                errors = error_texts.get(tool_name, [])
                combined = " ".join(errors).lower()
                self._match_patterns(combined, f"tool_failure:{tool_name}", gaps, priority_boost=0.3)

                # If tool not in known tools, flag as missing tool
                if tool_name not in self.known_tools:
                    gap_key = f"missing_tool_{tool_name}"
                    gaps[gap_key] = CapabilityGap(
                        name=gap_key,
                        description=f"Tool '{tool_name}' was referenced but does not exist",
                        evidence=[f"Referenced {count} times without success"],
                        suggested_tool_name=tool_name,
                        priority=min(0.9, 0.4 + count * 0.1),
                        gap_type="tool",
                    )

    def _analyze_iteration_errors(
        self, iterations: Sequence[Iteration], gaps: Dict[str, CapabilityGap]
    ) -> None:
        for it in iterations:
            if it.status == "failed" and it.result_json:
                error_text = str(it.result_json.get("error", "")).lower()
                summary = str(it.result_json.get("summary", "")).lower()
                combined = f"{error_text} {summary}"
                if combined.strip():
                    self._match_patterns(combined, f"iteration_failure:{it.id}", gaps)

    def _analyze_usage_patterns(
        self,
        iterations: Sequence[Iteration],
        tool_calls: Sequence[ToolCall],
        gaps: Dict[str, CapabilityGap],
    ) -> None:
        # Check for repeated iteration failures suggesting a skill gap
        failed_goals: List[str] = []
        for it in iterations:
            if it.status == "failed" and it.goal:
                failed_goals.append(it.goal.lower())

        if len(failed_goals) >= 3:
            combined = " ".join(failed_goals)
            self._match_patterns(combined, "repeated_goal_failures", gaps, priority_boost=0.2)

        # Low success rate tools
        tool_success: Dict[str, list[bool]] = defaultdict(list)
        for tc in tool_calls:
            tool_success[tc.tool_name].append(tc.success)

        for tool_name, results in tool_success.items():
            if len(results) >= 5:
                success_rate = sum(results) / len(results)
                if success_rate < 0.4:
                    gap_key = f"low_success_rate_{tool_name}"
                    if gap_key not in gaps:
                        gaps[gap_key] = CapabilityGap(
                            name=gap_key,
                            description=(
                                f"Tool '{tool_name}' has a {success_rate:.0%} success rate "
                                f"over {len(results)} calls — consider improving or replacing it"
                            ),
                            evidence=[f"{sum(results)}/{len(results)} calls succeeded"],
                            suggested_tool_name=f"{tool_name}_v2",
                            priority=0.5 * (1.0 - success_rate),
                            gap_type="tool",
                        )

    def _match_patterns(
        self,
        text: str,
        source: str,
        gaps: Dict[str, CapabilityGap],
        priority_boost: float = 0.0,
    ) -> None:
        for pattern, name, description, gap_type in _CAPABILITY_PATTERNS:
            if re.search(pattern, text):
                if name not in gaps:
                    gaps[name] = CapabilityGap(
                        name=name,
                        description=description,
                        evidence=[source],
                        suggested_tool_name=name if gap_type == "tool" else None,
                        suggested_skill_name=name if gap_type == "skill" else None,
                        priority=0.5 + priority_boost,
                        gap_type=gap_type,
                    )
                else:
                    existing = gaps[name]
                    if source not in existing.evidence:
                        existing.evidence.append(source)
                    existing.priority = min(1.0, existing.priority + 0.1 + priority_boost)
