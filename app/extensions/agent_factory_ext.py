"""Specialized agent factory.

Creates pre-configured agent instances optimized for specific domains
such as coding, research, testing, security review, etc.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.storage.repositories import AgentRepository


# -----------------------------------------------------------------
# Masterprompt templates
# -----------------------------------------------------------------

_MASTERPROMPTS: Dict[str, str] = {
    "coding": """You are an expert software engineer AI agent.
Your primary goal is to write, review, and improve code.

Guidelines:
- Write clean, well-commented, tested code
- Follow the principle of least surprise
- Prefer readability over cleverness
- Always run tests after making changes
- Use git to commit working changes with descriptive messages
- When you encounter an error, read the stack trace carefully and fix root causes
""",
    "research": """You are a research AI agent specialized in gathering and synthesizing information.

Guidelines:
- Break down complex questions into searchable sub-questions
- Cross-reference multiple sources before drawing conclusions
- Cite your sources and note uncertainty
- Produce structured summaries with clear findings
- Store key findings in long-term memory for future reference
""",
    "testing": """You are a QA and testing AI agent.

Guidelines:
- Write comprehensive test suites: unit, integration, and e2e
- Aim for >80% code coverage
- Test happy paths AND edge cases AND error conditions
- Use pytest with async support where needed
- Analyze test failures systematically before fixing
- Document what each test validates and why
""",
    "devops": """You are a DevOps and infrastructure AI agent.

Guidelines:
- Automate repetitive deployment and maintenance tasks
- Monitor system health and respond to alerts
- Keep infrastructure as code (docker-compose, Dockerfile)
- Document every change in git with clear commit messages
- Always verify changes in a safe environment before production
- Prefer incremental changes over big-bang deployments
""",
    "security": """You are a security-focused AI agent specializing in code review and vulnerability detection.

Guidelines:
- Scan code for OWASP Top 10 vulnerabilities
- Check for hardcoded secrets, weak crypto, injection flaws
- Validate input handling and output encoding
- Review dependency versions for known CVEs
- Produce actionable findings with severity ratings
- Suggest fixes, not just problems
""",
    "data": """You are a data engineering and analysis AI agent.

Guidelines:
- Clean and validate data before processing
- Write efficient, vectorized data transformations
- Document data schemas and transformations
- Handle missing values and outliers explicitly
- Produce clear visualizations and summaries
- Store processed datasets with versioning
""",
}

_DEFAULT_CONFIG: Dict[str, Any] = {
    "max_iterations_per_run": 50,
    "enable_git": True,
    "enable_memory": True,
}

_DOMAIN_CONFIGS: Dict[str, Dict[str, Any]] = {
    "coding": {"preferred_tools": ["write_file", "read_file", "run_command", "git_commit"]},
    "research": {"preferred_tools": ["web_search", "read_file", "write_file"]},
    "testing": {
        "preferred_tools": ["run_command", "read_file", "write_file"],
        "always_run_tests": True,
    },
    "devops": {"preferred_tools": ["run_command", "write_file", "git_commit"]},
    "security": {"preferred_tools": ["read_file", "run_command", "search_code"]},
    "data": {"preferred_tools": ["run_command", "read_file", "write_file"]},
}


class SpecializedAgentFactory:
    """Creates domain-specialized agent records in the database."""

    SUPPORTED_DOMAINS = list(_MASTERPROMPTS.keys())

    @classmethod
    async def create_specialized(
        cls,
        domain: str,
        name: Optional[str] = None,
        model: Optional[str] = None,
        project_id: Optional[str] = None,
        extra_config: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Create a new agent configured for a specific domain.

        Returns agent dict. If db_session provided, persists to DB.
        """
        if domain not in _MASTERPROMPTS:
            raise ValueError(
                f"Unknown domain '{domain}'. "
                f"Supported: {cls.SUPPORTED_DOMAINS}"
            )

        agent_name = name or f"{domain.capitalize()}-Agent-{__import__('uuid').uuid4().hex[:6].upper()}"
        masterprompt = _MASTERPROMPTS[domain]
        model_name = model or settings.OLLAMA_DEFAULT_MODEL

        config = {**_DEFAULT_CONFIG, **_DOMAIN_CONFIGS.get(domain, {})}
        if extra_config:
            config.update(extra_config)

        agent_data: Dict[str, Any] = {
            "name": agent_name,
            "masterprompt": masterprompt,
            "model_name": model_name,
            "config_json": config,
            "project_id": project_id,
        }

        if db_session is not None:
            repo = AgentRepository(db_session)
            agent = await repo.create(
                name=agent_name,
                masterprompt=masterprompt,
                model_name=model_name,
                config_json=config,
                project_id=project_id,
            )
            await db_session.commit()
            logger.info(f"Created specialized {domain} agent: {agent.id}")
            agent_data["id"] = agent.id
            agent_data["created_at"] = agent.created_at.isoformat()

        return agent_data

    @classmethod
    def get_masterprompt(cls, domain: str) -> str:
        """Return the masterprompt template for a domain."""
        if domain not in _MASTERPROMPTS:
            raise ValueError(f"Unknown domain '{domain}'")
        return _MASTERPROMPTS[domain]

    @classmethod
    def list_domains(cls) -> List[Dict[str, str]]:
        """List available domains with descriptions."""
        descriptions = {
            "coding": "Software development, code writing, review, and debugging",
            "research": "Information gathering, synthesis, and structured summaries",
            "testing": "Test writing, coverage analysis, and QA automation",
            "devops": "Infrastructure automation, deployment, and monitoring",
            "security": "Security review, vulnerability detection, and CVE analysis",
            "data": "Data engineering, transformation, analysis, and visualization",
        }
        return [
            {"domain": d, "description": descriptions.get(d, "")}
            for d in cls.SUPPORTED_DOMAINS
        ]
