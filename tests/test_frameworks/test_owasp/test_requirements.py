"""Tests for the OWASP Agentic Top 10 requirements definitions."""

from __future__ import annotations

from licit.core.models import ControlRequirement
from licit.frameworks.owasp_agentic.requirements import (
    OWASP_AGENTIC_FRAMEWORK,
    OWASP_AGENTIC_VERSION,
    REQUIREMENTS,
    get_requirement,
    get_requirements_by_category,
)


class TestRequirementsData:
    def test_exactly_ten_requirements(self) -> None:
        assert len(REQUIREMENTS) == 10

    def test_all_have_unique_ids(self) -> None:
        ids = [r.id for r in REQUIREMENTS]
        assert len(ids) == len(set(ids))

    def test_all_ids_start_with_asi(self) -> None:
        for req in REQUIREMENTS:
            assert req.id.startswith("ASI"), f"{req.id} does not start with ASI"

    def test_all_belong_to_owasp_framework(self) -> None:
        for req in REQUIREMENTS:
            assert req.framework == OWASP_AGENTIC_FRAMEWORK

    def test_all_have_name_and_description(self) -> None:
        for req in REQUIREMENTS:
            assert req.name, f"{req.id} has empty name"
            assert req.description, f"{req.id} has empty description"

    def test_all_have_article_ref(self) -> None:
        for req in REQUIREMENTS:
            assert req.article_ref, f"{req.id} has no article_ref"

    def test_all_have_category(self) -> None:
        for req in REQUIREMENTS:
            assert req.category, f"{req.id} has no category"

    def test_framework_constants(self) -> None:
        assert OWASP_AGENTIC_FRAMEWORK == "owasp-agentic"
        assert OWASP_AGENTIC_VERSION == "2025"

    def test_requirements_are_control_requirement_instances(self) -> None:
        for req in REQUIREMENTS:
            assert isinstance(req, ControlRequirement)


class TestGetRequirement:
    def test_found(self) -> None:
        req = get_requirement("ASI01")
        assert req is not None
        assert req.name == "Excessive Agency"

    def test_not_found(self) -> None:
        assert get_requirement("ASI99") is None

    def test_case_sensitive(self) -> None:
        assert get_requirement("asi01") is None


class TestGetByCategory:
    def test_existing_category(self) -> None:
        results = get_requirements_by_category("access-control")
        assert len(results) >= 1
        assert all(r.category == "access-control" for r in results)

    def test_empty_category(self) -> None:
        results = get_requirements_by_category("nonexistent")
        assert results == []

    def test_all_categories_non_empty(self) -> None:
        categories = {r.category for r in REQUIREMENTS if r.category}
        for cat in categories:
            assert len(get_requirements_by_category(cat)) >= 1
