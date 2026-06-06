"""Self-extension system for AAOS.

Provides capability gap detection, automated tool/skill generation via LLM,
sandbox validation, and continuous self-improvement analysis.
"""

from app.extensions.capability_detector import CapabilityDetector, CapabilityGap
from app.extensions.tool_generator import ToolGenerator
from app.extensions.skill_generator import SkillGenerator
from app.extensions.sandbox import Sandbox, ValidationResult
from app.extensions.self_improvement import SelfImprovementAnalyzer
from app.extensions.agent_factory_ext import SpecializedAgentFactory

__all__ = [
    "CapabilityDetector",
    "CapabilityGap",
    "ToolGenerator",
    "SkillGenerator",
    "Sandbox",
    "ValidationResult",
    "SelfImprovementAnalyzer",
    "SpecializedAgentFactory",
]
