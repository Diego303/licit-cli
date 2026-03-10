"""Auto-detection of project characteristics."""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class AgentConfigFile:
    """A detected agent configuration file."""

    path: str
    agent_type: str  # "claude-code", "cursor", "architect", "copilot", "generic"
    exists: bool = True


@dataclass
class CICDConfig:
    """Detected CI/CD configuration."""

    platform: str  # "github-actions", "gitlab-ci", "jenkins", "none"
    config_path: str | None = None
    has_ai_steps: bool = False


@dataclass
class SecurityTooling:
    """Detected security tooling in the project."""

    has_vigil: bool = False
    has_semgrep: bool = False
    has_snyk: bool = False
    has_codeql: bool = False
    has_trivy: bool = False
    has_eslint_security: bool = False
    vigil_config_path: str | None = None
    sarif_files: list[str] = field(default_factory=list)


@dataclass
class ProjectContext:
    """Complete auto-detected project context."""

    root_dir: str
    name: str

    # Language & framework
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)

    # Agent configs
    agent_configs: list[AgentConfigFile] = field(default_factory=list)
    has_architect: bool = False
    architect_config_path: str | None = None

    # CI/CD
    cicd: CICDConfig = field(default_factory=lambda: CICDConfig(platform="none"))

    # Testing
    test_framework: str | None = None
    test_dirs: list[str] = field(default_factory=list)

    # Security
    security: SecurityTooling = field(default_factory=SecurityTooling)

    # Git
    git_initialized: bool = False
    total_commits: int = 0
    total_contributors: int = 0
    first_commit_date: str | None = None
    last_commit_date: str | None = None


class ProjectDetector:
    """Auto-detects project characteristics from filesystem and git."""

    AGENT_CONFIG_PATTERNS: dict[str, str] = {
        "CLAUDE.md": "claude-code",
        ".claude/settings.json": "claude-code",
        ".cursorrules": "cursor",
        ".cursor/rules": "cursor",
        "AGENTS.md": "github-agents",
        ".github/agents/*.md": "github-agents",
        ".github/copilot-instructions.md": "copilot",
        ".architect/config.yaml": "architect",
        "architect.yaml": "architect",
        ".prompts/**/*.md": "generic",
    }

    CICD_PATTERNS: dict[str, str] = {
        ".github/workflows/*.yml": "github-actions",
        ".github/workflows/*.yaml": "github-actions",
        ".gitlab-ci.yml": "gitlab-ci",
        "Jenkinsfile": "jenkins",
        ".circleci/config.yml": "circleci",
    }

    def detect(self, root_dir: str) -> ProjectContext:
        """Full project detection."""
        root = Path(root_dir)
        ctx = ProjectContext(root_dir=root_dir, name=root.name)

        self._detect_name(root, ctx)
        self._detect_languages(root, ctx)
        self._detect_agent_configs(root, ctx)
        self._detect_cicd(root, ctx)
        self._detect_testing(root, ctx)
        self._detect_security(root, ctx)
        self._detect_git(root, ctx)

        logger.info(
            "project_detected",
            name=ctx.name,
            languages=ctx.languages,
            agent_configs=len(ctx.agent_configs),
            cicd=ctx.cicd.platform,
        )
        return ctx

    def _detect_name(self, root: Path, ctx: ProjectContext) -> None:
        """Detect project name from config files."""
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib

                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name")
                if isinstance(name, str):
                    ctx.name = name
            except Exception as exc:
                logger.debug("pyproject_parse_error", error=str(exc))

        pkg = root / "package.json"
        if pkg.exists() and not pyproject.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                name = data.get("name")
                if isinstance(name, str):
                    ctx.name = name
            except json.JSONDecodeError as exc:
                logger.debug("package_json_parse_error", error=str(exc))

    def _detect_languages(self, root: Path, ctx: ProjectContext) -> None:
        """Detect languages from config files and file extensions."""
        if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
            ctx.languages.append("python")
            ctx.package_managers.append("pip")
        if (root / "package.json").exists():
            ctx.languages.append("javascript")
            ctx.package_managers.append("npm")
            if (root / "tsconfig.json").exists():
                ctx.languages.append("typescript")
        if (root / "go.mod").exists():
            ctx.languages.append("go")
            ctx.package_managers.append("go-modules")
        if (root / "Cargo.toml").exists():
            ctx.languages.append("rust")
            ctx.package_managers.append("cargo")
        if (root / "pom.xml").exists() or (root / "build.gradle").exists():
            ctx.languages.append("java")
            ctx.package_managers.append("maven" if (root / "pom.xml").exists() else "gradle")

        self._detect_frameworks(root, ctx)

    def _detect_frameworks(self, root: Path, ctx: ProjectContext) -> None:
        """Detect web/app frameworks."""
        if "python" in ctx.languages:
            content = ""
            pyproject = root / "pyproject.toml"
            if pyproject.exists():
                content += pyproject.read_text(encoding="utf-8")
            reqs = root / "requirements.txt"
            if reqs.exists():
                content += reqs.read_text(encoding="utf-8")
            content_lower = content.lower()
            if "fastapi" in content_lower:
                ctx.frameworks.append("fastapi")
            if "flask" in content_lower:
                ctx.frameworks.append("flask")
            if "django" in content_lower:
                ctx.frameworks.append("django")

        if "javascript" in ctx.languages or "typescript" in ctx.languages:
            pkg = root / "package.json"
            if pkg.exists():
                content = pkg.read_text(encoding="utf-8").lower()
                if "react" in content:
                    ctx.frameworks.append("react")
                if "next" in content:
                    ctx.frameworks.append("nextjs")
                if "express" in content:
                    ctx.frameworks.append("express")

    def _detect_agent_configs(self, root: Path, ctx: ProjectContext) -> None:
        """Detect agent configuration files."""
        for pattern, agent_type in self.AGENT_CONFIG_PATTERNS.items():
            if "*" in pattern:
                matches = list(root.glob(pattern))
                for match in matches:
                    ctx.agent_configs.append(
                        AgentConfigFile(
                            path=str(match.relative_to(root)),
                            agent_type=agent_type,
                        )
                    )
            else:
                path = root / pattern
                if path.exists():
                    ctx.agent_configs.append(
                        AgentConfigFile(path=pattern, agent_type=agent_type)
                    )

        if (root / ".architect").is_dir() or (root / "architect.yaml").exists():
            ctx.has_architect = True
            if (root / ".architect" / "config.yaml").exists():
                ctx.architect_config_path = ".architect/config.yaml"
            elif (root / "architect.yaml").exists():
                ctx.architect_config_path = "architect.yaml"

    def _detect_cicd(self, root: Path, ctx: ProjectContext) -> None:
        """Detect CI/CD platform."""
        for pattern, platform in self.CICD_PATTERNS.items():
            if "*" in pattern:
                if list(root.glob(pattern)):
                    ctx.cicd = CICDConfig(platform=platform, config_path=pattern)
                    return
            else:
                if (root / pattern).exists():
                    ctx.cicd = CICDConfig(platform=platform, config_path=pattern)
                    return

    def _detect_testing(self, root: Path, ctx: ProjectContext) -> None:
        """Detect test framework and directories."""
        if "python" in ctx.languages:
            for d in ["tests", "test"]:
                if (root / d).is_dir():
                    ctx.test_dirs.append(d)
                    ctx.test_framework = "pytest"
        if "javascript" in ctx.languages or "typescript" in ctx.languages:
            for d in ["__tests__", "tests", "test"]:
                if (root / d).is_dir():
                    ctx.test_dirs.append(d)
            pkg = root / "package.json"
            if pkg.exists():
                content = pkg.read_text(encoding="utf-8").lower()
                if "jest" in content:
                    ctx.test_framework = "jest"
                elif "vitest" in content:
                    ctx.test_framework = "vitest"

    def _detect_security(self, root: Path, ctx: ProjectContext) -> None:
        """Detect security tooling."""
        ctx.security.has_vigil = (root / ".vigil.yaml").exists()
        if ctx.security.has_vigil:
            ctx.security.vigil_config_path = ".vigil.yaml"
        ctx.security.has_semgrep = (
            (root / ".semgrep.yml").exists() or (root / ".semgrep").is_dir()
        )
        ctx.security.has_snyk = (root / ".snyk").exists()
        ctx.security.has_codeql = (root / ".github" / "codeql").is_dir()

        for sarif in root.rglob("*.sarif"):
            ctx.security.sarif_files.append(str(sarif.relative_to(root)))

    def _detect_git(self, root: Path, ctx: ProjectContext) -> None:
        """Detect git information."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=5,
            )
            ctx.git_initialized = result.returncode == 0
            if not ctx.git_initialized:
                return

            r = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip().isdigit():
                ctx.total_commits = int(r.stdout.strip())

            r = subprocess.run(
                ["git", "shortlog", "-sn", "HEAD"],
                capture_output=True,
                text=True,
                cwd=root,
                timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                ctx.total_contributors = len(r.stdout.strip().splitlines())

        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("git_detection_failed", error=str(exc))
