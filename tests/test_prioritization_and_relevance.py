"""Unit tests for publication/project prioritization by resume purpose,
sorting by relevance metrics (citations, qualis, likes/stars, forks),
metric exclusion from rendered output, and 10-item limits for non-single-page templates.
"""

import re
import pytest

from src.templates import (
    render_builtin_template,
    deduplicate_and_sort_publications,
    deduplicate_and_sort_projects,
    _allocate_single_page_budget,
    extract_qualis_score,
    _pub_relevance_key,
    _proj_relevance_key,
)


def test_extract_qualis_score_mapping():
    assert extract_qualis_score({"qualis": "A1"}) == 90
    assert extract_qualis_score({"qualis": "A2"}) == 80
    assert extract_qualis_score({"qualis": "A3"}) == 70
    assert extract_qualis_score({"qualis": "A4"}) == 60
    assert extract_qualis_score({"qualis": "B1"}) == 50
    assert extract_qualis_score({"qualis": "B2"}) == 40
    assert extract_qualis_score({"qualis": "B3"}) == 30
    assert extract_qualis_score({"qualis": "B4"}) == 20
    assert extract_qualis_score({"qualis": "C"}) == 10
    assert extract_qualis_score({"venue": "Revista Brasileira (Qualis A1)"}) == 90
    assert extract_qualis_score({"venue": "Conferência Internacional [B2]"}) == 40
    assert extract_qualis_score({}) == 0


def test_publication_relevance_sorting_and_metrics_hidden():
    pubs = [
        {"title": "Paper Low", "venue": "Revista C", "qualis": "C", "year": "2025", "citations": 0},
        {"title": "Paper High Citations", "venue": "Revista B", "qualis": "B1", "year": "2021", "citations": 120},
        {"title": "Paper Top Tier", "venue": "Revista Top (Qualis A1)", "year": "2024", "citations": 10},
        {"title": "Paper Medium Citations", "venue": "Revista A", "qualis": "A2", "year": "2023", "citations": 50},
    ]

    sorted_pubs = deduplicate_and_sort_publications(pubs)
    titles = [p["title"] for p in sorted_pubs]
    assert titles == [
        "Paper High Citations",   # 120 citations
        "Paper Medium Citations", # 50 citations
        "Paper Top Tier",         # 10 citations
        "Paper Low",              # 0 citations
    ]

    # Verify that Qualis or citation numbers are cleaned from venue
    for p in sorted_pubs:
        assert "Qualis" not in p["venue"]
        assert "A1" not in p["venue"]

    cv = {
        "name": "Test Author",
        "email": "test@example.com",
        "publications": sorted_pubs,
    }
    rendered = render_builtin_template("modern_pro", cv, {}, resume_type="academico")
    assert "Paper High Citations" in rendered
    assert "Paper Medium Citations" in rendered
    # Metrics must never appear in rendered LaTeX
    assert "120 citations" not in rendered.lower()
    assert "qualis" not in rendered.lower()


def test_project_relevance_sorting_and_metrics_hidden():
    projects = [
        {"name": "Proj Low", "description": "Basic tool", "stars": 0, "forks": 0, "year": "2022"},
        {"name": "Proj Popular", "description": "Highly starred (150 stars)", "likes": 150, "forks": 5, "year": "2021"},
        {"name": "Proj Forked", "description": "Heavily forked project", "stars": 20, "forks": 40, "year": "2023"},
        {"name": "Proj Recent", "description": "New active project", "stars": 20, "forks": 2, "year": "2025"},
    ]

    sorted_projs = deduplicate_and_sort_projects(projects)
    names = [p["name"] for p in sorted_projs]
    assert names == [
        "Proj Popular", # 150 likes/stars
        "Proj Forked",  # 20 stars, 40 forks
        "Proj Recent",  # 20 stars, 2 forks
        "Proj Low",     # 0 stars, 0 forks
    ]

    cv = {
        "name": "Test Developer",
        "email": "dev@example.com",
        "projects": sorted_projs,
    }
    rendered = render_builtin_template("modern_pro", cv, {}, resume_type="profissional")
    assert "Proj Popular" in rendered
    # Metric counts (e.g. 150 stars) must not leak into rendered description
    assert "150 stars" not in rendered.lower()
    assert "40 forks" not in rendered.lower()


def test_single_page_budget_prioritization_rules():
    # When budget is tight (e.g. budget = 18):
    # Professional: 2 exp -> max projects -> publications only if space left
    n_exp, n_proj, n_pub = _allocate_single_page_budget(
        total_exp=3,
        total_proj=5,
        total_pubs=5,
        budget=18.0,
        weight_exp=3.0,
        weight_proj=2.5,
        weight_pub=2.0,
        resume_type="profissional",
    )
    assert n_proj > 0
    assert n_proj >= n_pub

    # Academic: 2 exp -> max publications -> projects only if space left
    n_exp_a, n_proj_a, n_pub_a = _allocate_single_page_budget(
        total_exp=3,
        total_proj=5,
        total_pubs=5,
        budget=18.0,
        weight_exp=3.0,
        weight_proj=2.5,
        weight_pub=2.0,
        resume_type="academico",
    )
    assert n_pub_a > 0
    assert n_pub_a >= n_proj_a


@pytest.mark.parametrize("template_id", [
    "modern_pro",
    "academic_classic",
    "overleaf_russell_ti",
    "overleaf_awesome_cv",
    "ai_ats_max",
])
def test_other_templates_limit_projects_and_publications_to_10(template_id):
    """Multi-page / general templates must strictly display at most 10 projects and 10 publications."""
    many_projects = [
        {"name": f"Project {i:02d}", "description": f"Description for project {i}", "stars": 20 - i}
        for i in range(1, 16)
    ]
    many_publications = [
        {"title": f"Paper Title {i:02d}", "venue": f"Venue {i}", "year": f"20{25 - i:02d}", "citations": 30 - i}
        for i in range(1, 16)
    ]

    cv = {
        "name": "Full Profile User",
        "email": "full@example.com",
        "projects": many_projects,
        "publications": many_publications,
        "experience": [{"role": "Senior Engineer", "organization": "Tech Corp", "period": "2020 - Present"}],
        "education": [{"degree": "B.Sc.", "institution": "University", "period": "2016 - 2020"}],
    }

    rendered = render_builtin_template(template_id, cv, {}, resume_type="profissional")

    # The top 10 projects (1 to 10) must be included, projects 11 to 15 must be excluded
    for i in range(1, 11):
        assert f"Project {i:02d}" in rendered, f"Project {i:02d} missing in {template_id}"
    for i in range(11, 16):
        assert f"Project {i:02d}" not in rendered, f"Project {i:02d} should not be in {template_id}"

    # The top 10 publications (1 to 10) must be included, publications 11 to 15 must be excluded
    for i in range(1, 11):
        assert f"Paper Title {i:02d}" in rendered, f"Paper Title {i:02d} missing in {template_id}"
    for i in range(11, 16):
        assert f"Paper Title {i:02d}" not in rendered, f"Paper Title {i:02d} should not be in {template_id}"
