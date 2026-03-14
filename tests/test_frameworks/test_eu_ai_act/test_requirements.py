"""Tests for the EU AI Act requirements module."""

from __future__ import annotations

from licit.frameworks.eu_ai_act.requirements import (
    REQUIREMENTS,
    get_requirement,
    get_requirements_by_category,
)


class TestRequirementsData:
    def test_all_have_required_fields(self) -> None:
        for req in REQUIREMENTS:
            assert req.id, f"Requirement missing id: {req}"
            assert req.framework == "eu-ai-act"
            assert req.name
            assert req.description
            assert req.article_ref

    def test_unique_ids(self) -> None:
        ids = [r.id for r in REQUIREMENTS]
        assert len(ids) == len(set(ids)), "Duplicate requirement IDs"

    def test_all_have_category(self) -> None:
        for req in REQUIREMENTS:
            assert req.category, f"{req.id} missing category"


class TestGetRequirement:
    def test_existing_id(self) -> None:
        req = get_requirement("ART-9-1")
        assert req is not None
        assert req.name == "Risk Management System"

    def test_annex_iv(self) -> None:
        req = get_requirement("ANNEX-IV")
        assert req is not None
        assert req.category == "documentation"

    def test_missing_id_returns_none(self) -> None:
        assert get_requirement("NONEXISTENT") is None


class TestGetByCategory:
    def test_human_oversight(self) -> None:
        reqs = get_requirements_by_category("human-oversight")
        ids = {r.id for r in reqs}
        assert "ART-14-1" in ids
        assert "ART-14-4a" in ids
        assert "ART-14-4d" in ids
        assert len(reqs) == 3

    def test_empty_category(self) -> None:
        assert get_requirements_by_category("nonexistent") == []

    def test_deployer_obligations(self) -> None:
        reqs = get_requirements_by_category("deployer-obligations")
        assert len(reqs) == 2
