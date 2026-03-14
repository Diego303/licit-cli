"""Structured requirements for EU AI Act compliance evaluation.

Contains all evaluable articles and their metadata as ControlRequirement
instances, organized by category.
"""

from licit.core.models import ControlRequirement

EU_AI_ACT_FRAMEWORK = "eu-ai-act"
EU_AI_ACT_VERSION = "2024/1689"

REQUIREMENTS: list[ControlRequirement] = [
    ControlRequirement(
        id="ART-9-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Risk Management System",
        description=(
            "Establish a risk management system for the AI system, "
            "including identification, analysis, and mitigation of risks."
        ),
        article_ref="Article 9(1)",
        category="risk-management",
    ),
    ControlRequirement(
        id="ART-10-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Data Governance",
        description=(
            "Training, validation, and testing data shall be subject "
            "to appropriate data governance and management practices."
        ),
        article_ref="Article 10(1)",
        category="data-governance",
    ),
    ControlRequirement(
        id="ART-12-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Record Keeping — Automatic Logging",
        description=(
            "AI systems shall be designed with capabilities enabling "
            "automatic recording of events (logs) over the lifetime."
        ),
        article_ref="Article 12(1)",
        category="record-keeping",
    ),
    ControlRequirement(
        id="ART-13-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Transparency — Information for Deployers",
        description=(
            "AI systems shall be designed to ensure their operation is "
            "sufficiently transparent to enable deployers to interpret "
            "output and use it appropriately."
        ),
        article_ref="Article 13(1)",
        category="transparency",
    ),
    ControlRequirement(
        id="ART-14-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Human Oversight",
        description=(
            "AI systems shall be designed to be effectively overseen "
            "by natural persons during the period of use."
        ),
        article_ref="Article 14(1)",
        category="human-oversight",
    ),
    ControlRequirement(
        id="ART-14-4a",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Human Oversight — Understand Capabilities",
        description=(
            "Individuals assigned to human oversight shall be able to "
            "properly understand the relevant capacities and limitations "
            "of the AI system."
        ),
        article_ref="Article 14(4)(a)",
        category="human-oversight",
    ),
    ControlRequirement(
        id="ART-14-4d",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Human Oversight — Ability to Intervene",
        description=(
            "Individuals shall be able to decide not to use the AI system "
            "or to disregard, override, or reverse its output."
        ),
        article_ref="Article 14(4)(d)",
        category="human-oversight",
    ),
    ControlRequirement(
        id="ART-26-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Deployer — Use in Accordance with Instructions",
        description=(
            "Deployers shall use AI systems in accordance with "
            "instructions of use accompanying the system."
        ),
        article_ref="Article 26(1)",
        category="deployer-obligations",
    ),
    ControlRequirement(
        id="ART-26-5",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Deployer — Monitoring",
        description=(
            "Deployers shall monitor the operation of the AI system "
            "on the basis of the instructions of use."
        ),
        article_ref="Article 26(5)",
        category="deployer-obligations",
    ),
    ControlRequirement(
        id="ART-27-1",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Fundamental Rights Impact Assessment (FRIA)",
        description=(
            "Before putting an AI system into use, deployers shall "
            "carry out an assessment of the impact on fundamental rights."
        ),
        article_ref="Article 27(1)",
        category="fria",
    ),
    ControlRequirement(
        id="ANNEX-IV",
        framework=EU_AI_ACT_FRAMEWORK,
        name="Technical Documentation",
        description=(
            "Technical documentation shall contain information on the "
            "AI system's intended purpose, design, development, testing, "
            "and performance."
        ),
        article_ref="Annex IV",
        category="documentation",
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
