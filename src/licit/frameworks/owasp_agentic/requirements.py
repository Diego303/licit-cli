"""Structured requirements for OWASP Agentic Top 10 compliance evaluation.

Contains all 10 risk categories from the OWASP Top 10 for Agentic AI
Security as ControlRequirement instances, organized by risk category.

Reference: OWASP Top 10 for Agentic AI Security (2025)
"""

from licit.core.models import ControlRequirement

OWASP_AGENTIC_FRAMEWORK = "owasp-agentic"
OWASP_AGENTIC_VERSION = "2025"

REQUIREMENTS: list[ControlRequirement] = [
    ControlRequirement(
        id="ASI01",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Excessive Agency",
        description=(
            "AI agents should be granted only the minimum permissions "
            "and capabilities necessary to perform their intended tasks. "
            "Excessive agency increases the blast radius of errors or attacks."
        ),
        article_ref="ASI-01",
        category="access-control",
    ),
    ControlRequirement(
        id="ASI02",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Prompt Injection",
        description=(
            "AI agents must be protected against adversarial manipulation "
            "through crafted inputs that alter agent behavior, bypass "
            "guardrails, or cause unintended actions."
        ),
        article_ref="ASI-02",
        category="input-security",
    ),
    ControlRequirement(
        id="ASI03",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Supply Chain Vulnerabilities",
        description=(
            "AI agent dependencies — including models, plugins, tools, "
            "and third-party integrations — must be verified, pinned, "
            "and monitored for known vulnerabilities."
        ),
        article_ref="ASI-03",
        category="supply-chain",
    ),
    ControlRequirement(
        id="ASI04",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Insufficient Logging and Monitoring",
        description=(
            "All agent actions, decisions, tool invocations, and errors "
            "must be logged with sufficient detail to support audit, "
            "incident response, and compliance verification."
        ),
        article_ref="ASI-04",
        category="observability",
    ),
    ControlRequirement(
        id="ASI05",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Improper Output Handling",
        description=(
            "Output from AI agents must be validated and sanitized before "
            "being used in downstream systems, executed as code, or "
            "presented to users."
        ),
        article_ref="ASI-05",
        category="output-security",
    ),
    ControlRequirement(
        id="ASI06",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Lack of Human Oversight",
        description=(
            "AI agents operating in production must have mechanisms for "
            "human review, intervention, override, and shutdown — especially "
            "for high-impact or irreversible actions."
        ),
        article_ref="ASI-06",
        category="human-oversight",
    ),
    ControlRequirement(
        id="ASI07",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Insufficient Sandboxing",
        description=(
            "AI agents must operate within restricted environments with "
            "limited access to file systems, networks, and system resources. "
            "Sandbox escapes must be prevented by design."
        ),
        article_ref="ASI-07",
        category="isolation",
    ),
    ControlRequirement(
        id="ASI08",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Unbounded Resource Consumption",
        description=(
            "AI agents must have explicit limits on resource consumption "
            "including API calls, token usage, execution time, and cost "
            "to prevent runaway execution and denial of service."
        ),
        article_ref="ASI-08",
        category="resource-limits",
    ),
    ControlRequirement(
        id="ASI09",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Poor Error Handling",
        description=(
            "AI agents must handle errors gracefully without leaking "
            "sensitive information, entering uncontrolled states, or "
            "bypassing security controls during failure recovery."
        ),
        article_ref="ASI-09",
        category="error-handling",
    ),
    ControlRequirement(
        id="ASI10",
        framework=OWASP_AGENTIC_FRAMEWORK,
        name="Sensitive Data Exposure",
        description=(
            "AI agents must not expose, log, or transmit sensitive data "
            "such as credentials, personal information, or proprietary code "
            "beyond their intended scope."
        ),
        article_ref="ASI-10",
        category="data-protection",
    ),
]


def get_requirement(req_id: str) -> ControlRequirement | None:
    """Look up a single requirement by ID."""
    for req in REQUIREMENTS:
        if req.id == req_id:
            return req
    return None


def get_requirements_by_category(category: str) -> list[ControlRequirement]:
    """Get all requirements in a given category."""
    return [r for r in REQUIREMENTS if r.category == category]
