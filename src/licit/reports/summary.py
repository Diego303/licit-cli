"""Terminal summary printer for compliance reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from licit.reports.unified import UnifiedReport


def print_summary(report: UnifiedReport) -> None:
    """Print a compact compliance summary to the terminal."""
    click.echo("\n  Compliance Summary")
    click.echo(f"  {'─' * 45}")
    click.echo(f"  Project: {report.project_name}")
    click.echo(f"  Generated: {report.generated_at}")
    click.echo()

    for fw in report.frameworks:
        s = fw.summary
        rate_bar = _progress_bar(s.compliance_rate)
        click.echo(f"  {fw.name} ({fw.version})")
        click.echo(f"    {rate_bar} {s.compliance_rate:.1f}%")
        click.echo(
            f"    {s.compliant} compliant | "
            f"{s.partial} partial | "
            f"{s.non_compliant} non-compliant"
        )
        click.echo()

    click.echo(f"  {'─' * 45}")
    overall_bar = _progress_bar(report.overall_compliance_rate)
    click.echo(f"  Overall: {overall_bar} {report.overall_compliance_rate:.1f}%")
    click.echo(
        f"  {report.overall_compliant}/{report.overall_total} controls compliant"
    )


def _progress_bar(percentage: float, width: int = 20) -> str:
    """Render a simple text progress bar."""
    filled = int(percentage / 100 * width)
    filled = max(0, min(filled, width))
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}]"
