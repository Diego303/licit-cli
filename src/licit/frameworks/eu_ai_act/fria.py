"""Fundamental Rights Impact Assessment generator (EU AI Act Art. 27).

Interactive 5-step questionnaire that generates a FRIA document with
auto-detection of answers from project context where possible.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import structlog
from jinja2 import Environment, FileSystemLoader

from licit.core.evidence import EvidenceBundle
from licit.core.project import ProjectContext

logger = structlog.get_logger()


# ── FRIA Steps per Art. 27 ──────────────────────────────────────────

FRIAQuestion = dict[str, Any]
FRIAStep = dict[str, Any]

FRIA_STEPS: list[FRIAStep] = [
    {
        "id": 1,
        "title": "System Description",
        "description": "Describe the AI system, its intended purpose, and scope of deployment.",
        "questions": [
            {
                "id": "1.1",
                "question": "What is the primary purpose of this AI system?",
                "field": "system_purpose",
                "type": "text",
                "auto_detect": True,
                "help": (
                    "e.g., 'Autonomous code generation and modification "
                    "in CI/CD pipelines'"
                ),
            },
            {
                "id": "1.2",
                "question": "What type of AI technology is used?",
                "field": "ai_technology",
                "type": "choice",
                "choices": [
                    "Large Language Model (LLM) for code generation",
                    "AI coding assistant (interactive)",
                    "Autonomous AI agent (headless)",
                    "Multi-agent system",
                    "Other",
                ],
                "auto_detect": True,
            },
            {
                "id": "1.3",
                "question": "Which AI models/providers are used?",
                "field": "models_used",
                "type": "text",
                "auto_detect": True,
                "help": "e.g., 'Claude Sonnet 4 (Anthropic), GPT-4.1 (OpenAI)'",
            },
            {
                "id": "1.4",
                "question": "How many people/systems are affected by the AI's output?",
                "field": "affected_scope",
                "type": "choice",
                "choices": [
                    "Internal development team only (<50 people)",
                    "Internal organization (50-500 people)",
                    "External users of the software produced (500-10,000)",
                    "Large-scale public deployment (10,000+)",
                ],
            },
            {
                "id": "1.5",
                "question": (
                    "Is human review required before AI-generated code "
                    "reaches production?"
                ),
                "field": "human_review",
                "type": "choice",
                "choices": [
                    "Yes -- all AI-generated code requires human review",
                    "Partially -- some automated, some reviewed",
                    "No -- AI-generated code can reach production without human review",
                ],
                "auto_detect": True,
            },
        ],
    },
    {
        "id": 2,
        "title": "Fundamental Rights Identification",
        "description": "Identify which fundamental rights could be affected.",
        "questions": [
            {
                "id": "2.1",
                "question": "Does the AI system process personal data?",
                "field": "processes_personal_data",
                "type": "choice",
                "choices": ["Yes", "No", "Possibly (in source code or configs)"],
            },
            {
                "id": "2.2",
                "question": (
                    "Could the AI system's output affect employment "
                    "or working conditions?"
                ),
                "field": "affects_employment",
                "type": "choice",
                "choices": [
                    "No -- generates code only",
                    "Possibly -- could affect developer productivity metrics",
                    "Yes -- could influence hiring or performance decisions",
                ],
            },
            {
                "id": "2.3",
                "question": (
                    "Could security vulnerabilities in AI-generated code "
                    "affect users' rights?"
                ),
                "field": "affects_security",
                "type": "choice",
                "choices": [
                    "Low risk -- internal tools only",
                    "Medium risk -- user-facing but not critical",
                    "High risk -- handles financial, health, or identity data",
                ],
            },
            {
                "id": "2.4",
                "question": "Could AI-generated code introduce discriminatory behavior?",
                "field": "affects_discrimination",
                "type": "choice",
                "choices": [
                    "No -- code is infrastructure/backend only",
                    "Possibly -- code interacts with user-facing decisions",
                    "Yes -- code implements algorithms that affect people directly",
                ],
            },
        ],
    },
    {
        "id": 3,
        "title": "Impact Assessment",
        "description": (
            "Assess the likelihood and severity of impacts on identified rights."
        ),
        "questions": [
            {
                "id": "3.1",
                "question": "What is the overall risk level of this AI deployment?",
                "field": "risk_level",
                "type": "choice",
                "choices": [
                    "Minimal -- development tooling with full human oversight",
                    "Limited -- some automation with review gates",
                    "High -- autonomous operation with limited oversight",
                    "Unacceptable -- fully autonomous with no safeguards",
                ],
            },
            {
                "id": "3.2",
                "question": (
                    "What is the maximum potential impact if the AI "
                    "generates harmful code?"
                ),
                "field": "max_impact",
                "type": "text",
                "help": (
                    "e.g., 'Security breach affecting user data, "
                    "service outage, financial loss'"
                ),
            },
            {
                "id": "3.3",
                "question": (
                    "How quickly can harmful AI-generated code be "
                    "detected and reverted?"
                ),
                "field": "detection_speed",
                "type": "choice",
                "choices": [
                    "Immediately -- automated tests catch issues before merge",
                    "Hours -- CI/CD catches issues before deployment",
                    "Days -- manual review catches issues",
                    "Unknown -- no systematic detection process",
                ],
            },
        ],
    },
    {
        "id": 4,
        "title": "Mitigation Measures",
        "description": "Document measures to mitigate identified risks.",
        "questions": [
            {
                "id": "4.1",
                "question": (
                    "What guardrails are in place to constrain AI agent behavior?"
                ),
                "field": "guardrails",
                "type": "text",
                "auto_detect": True,
                "help": (
                    "e.g., 'Protected files, blocked commands, "
                    "budget limits, quality gates'"
                ),
            },
            {
                "id": "4.2",
                "question": "What security scanning is performed on AI-generated code?",
                "field": "security_scanning",
                "type": "text",
                "auto_detect": True,
                "help": "e.g., 'vigil scan, Semgrep, Snyk, CodeQL'",
            },
            {
                "id": "4.3",
                "question": "What testing is performed on AI-generated code?",
                "field": "testing",
                "type": "text",
                "auto_detect": True,
                "help": "e.g., 'pytest, jest, integration tests in CI/CD'",
            },
            {
                "id": "4.4",
                "question": "What audit trail exists for AI agent actions?",
                "field": "audit_trail",
                "type": "text",
                "auto_detect": True,
            },
            {
                "id": "4.5",
                "question": "What additional measures are in place or planned?",
                "field": "additional_measures",
                "type": "text",
            },
        ],
    },
    {
        "id": 5,
        "title": "Monitoring & Review",
        "description": "Define ongoing monitoring and periodic review processes.",
        "questions": [
            {
                "id": "5.1",
                "question": "How often will this FRIA be reviewed?",
                "field": "review_frequency",
                "type": "choice",
                "choices": [
                    "Quarterly",
                    "Semi-annually",
                    "Annually",
                    "On significant system changes",
                ],
            },
            {
                "id": "5.2",
                "question": "Who is responsible for monitoring AI system compliance?",
                "field": "responsible_person",
                "type": "text",
                "help": "Name and role of the designated compliance officer",
            },
            {
                "id": "5.3",
                "question": (
                    "How are incidents involving AI-generated code "
                    "reported and handled?"
                ),
                "field": "incident_process",
                "type": "text",
                "help": "Describe the incident response process",
            },
        ],
    },
]


class FRIAGenerator:
    """Interactive FRIA generator with auto-detection capabilities."""

    def __init__(self, context: ProjectContext, evidence: EvidenceBundle) -> None:
        self.context = context
        self.evidence = evidence

    def run_interactive(self) -> dict[str, Any]:
        """Run interactive FRIA questionnaire, returning field->answer mapping."""
        responses: dict[str, Any] = {}

        click.echo("\n" + "=" * 60)
        click.echo("  FUNDAMENTAL RIGHTS IMPACT ASSESSMENT (FRIA)")
        click.echo("  EU AI Act -- Article 27")
        click.echo("=" * 60 + "\n")

        for step in FRIA_STEPS:
            click.echo(f"\n{'─' * 50}")
            click.echo(f"  Step {step['id']}: {step['title']}")
            click.echo(f"  {step['description']}")
            click.echo(f"{'─' * 50}\n")

            questions: list[FRIAQuestion] = step["questions"]
            for q in questions:
                auto_value: str | None = None
                if q.get("auto_detect"):
                    auto_value = self._auto_detect(q["field"])
                    if auto_value:
                        click.echo(f"  [{q['id']}] {q['question']}")
                        click.echo(f"  -> Auto-detected: {auto_value}")
                        if click.confirm("    Accept this value?", default=True):
                            responses[q["field"]] = auto_value
                            continue

                click.echo(f"  [{q['id']}] {q['question']}")
                if q.get("help"):
                    click.echo(f"      ({q['help']})")

                if q["type"] == "choice":
                    choices: list[str] = q["choices"]
                    for i, choice in enumerate(choices, 1):
                        click.echo(f"      {i}. {choice}")
                    idx = click.prompt("    Select", type=int, default=1) - 1
                    idx = max(0, min(idx, len(choices) - 1))
                    responses[q["field"]] = choices[idx]
                else:
                    responses[q["field"]] = click.prompt(
                        "    Answer",
                        default=auto_value or "",
                    )

        from licit import __version__

        now = datetime.now(tz=UTC)
        responses["generated_at"] = now.isoformat()
        responses["project_name"] = self.context.name
        responses["licit_version"] = __version__

        return responses

    def _auto_detect(self, field: str) -> str | None:
        """Auto-detect answers from project context and evidence."""
        from collections.abc import Callable

        detectors: dict[str, Callable[[], str | None]] = {
            "system_purpose": self._detect_system_purpose,
            "ai_technology": self._detect_ai_technology,
            "models_used": self._detect_models_used,
            "human_review": self._detect_human_review,
            "guardrails": self._detect_guardrails,
            "security_scanning": self._detect_security_scanning,
            "testing": self._detect_testing,
            "audit_trail": self._detect_audit_trail,
        }
        detector = detectors.get(field)
        if detector is not None:
            return detector()
        return None

    def _detect_system_purpose(self) -> str | None:
        if self.context.has_architect:
            return (
                "Autonomous code generation and modification in CI/CD "
                "pipelines using AI agents (architect)"
            )
        if self.context.agent_configs:
            agents = sorted({c.agent_type for c in self.context.agent_configs})
            return f"AI-assisted code development using {', '.join(agents)}"
        return None

    def _detect_ai_technology(self) -> str | None:
        if self.context.has_architect:
            return "Autonomous AI agent (headless)"
        if self.context.agent_configs:
            return "AI coding assistant (interactive)"
        return None

    def _detect_models_used(self) -> str | None:
        models: set[str] = set()
        if self.context.architect_config_path:
            try:
                import yaml

                config_path = Path(
                    self.context.root_dir, self.context.architect_config_path
                )
                content = config_path.read_text(encoding="utf-8")
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    model = data.get("llm", {}).get("model")
                    if isinstance(model, str):
                        models.add(model)
            except (OSError, yaml.YAMLError) as exc:
                logger.debug("fria_model_detect_error", error=str(exc))
        return ", ".join(sorted(models)) if models else None

    def _detect_human_review(self) -> str | None:
        if self.evidence.has_human_review_gate:
            return "Yes -- all AI-generated code requires human review"
        return None

    def _detect_guardrails(self) -> str | None:
        parts: list[str] = []
        if self.evidence.has_guardrails:
            parts.append(f"{self.evidence.guardrail_count} guardrail rules")
        if self.evidence.has_quality_gates:
            parts.append(f"{self.evidence.quality_gate_count} quality gates")
        if self.evidence.has_budget_limits:
            parts.append("budget limits")
        return ", ".join(parts) if parts else None

    def _detect_security_scanning(self) -> str | None:
        tools: list[str] = []
        if self.context.security.has_vigil:
            tools.append("vigil (AI-specific security)")
        if self.context.security.has_semgrep:
            tools.append("Semgrep (SAST)")
        if self.context.security.has_snyk:
            tools.append("Snyk (SCA)")
        if self.context.security.has_codeql:
            tools.append("CodeQL (SAST)")
        return ", ".join(tools) if tools else None

    def _detect_testing(self) -> str | None:
        if self.context.test_framework:
            dirs = ", ".join(self.context.test_dirs) if self.context.test_dirs else "detected"
            return f"{self.context.test_framework} ({dirs})"
        return None

    def _detect_audit_trail(self) -> str | None:
        parts: list[str] = []
        if self.context.git_initialized:
            parts.append(f"Git history ({self.context.total_commits} commits)")
        if self.evidence.has_audit_trail:
            parts.append(
                f"Structured audit trail ({self.evidence.audit_entry_count} entries)"
            )
        if self.evidence.has_provenance:
            parts.append("Code provenance tracking (licit)")
        return ", ".join(parts) if parts else None

    def generate_report(self, responses: dict[str, Any], output_path: str) -> None:
        """Generate FRIA report from questionnaire responses."""
        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
            keep_trailing_newline=True,
        )
        template = env.get_template("fria_template.md.j2")

        now = datetime.now(tz=UTC)
        report = template.render(
            responses=responses,
            steps=FRIA_STEPS,
            generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(report, encoding="utf-8")
        logger.info("fria_report_generated", path=output_path)

    def save_data(self, responses: dict[str, Any], data_path: str) -> None:
        """Save FRIA responses as JSON for future updates."""
        Path(data_path).parent.mkdir(parents=True, exist_ok=True)
        Path(data_path).write_text(
            json.dumps(responses, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("fria_data_saved", path=data_path)

